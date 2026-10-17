"""Stateful, file-only SFX tools. Host LLM supplies artistic decisions."""
from __future__ import annotations
import copy, hashlib, json, math, os, re, shutil, subprocess, sys, time, uuid
from itertools import groupby
from contextlib import contextmanager
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STATE=Path(os.environ.get('SOUNDPILOT_STATE',Path(os.environ.get('LOCALAPPDATA',Path.home()))/'SoundPilotLearning')).resolve()
os.environ['SOUNDPILOT_STATE']=str(STATE)
sys.path.insert(0,str(ROOT/'engine'))
import soundpilot as s
import revision_audio as ra

def initialize():
    for folder in ('data','outputs','jobs','batches','history','locks'):(STATE/folder).mkdir(parents=True,exist_ok=True)
    for name,target in [('config.json',STATE/'config.json'),('style_profile.json',s.DATA/'style_profile.json'),('examples.json',s.DATA/'examples.json')]:
        if not target.exists():shutil.copyfile(ROOT/'seed'/name,target)
    # Recover derived files from the single authoritative memory commit.
    with lock('state'):
        if (STATE/'memory.json').exists():
            bundle=s.read_json(STATE/'memory.json')
            s.write_json(s.DATA/'style_profile.json',bundle['profile']);s.write_json(s.DATA/'examples.json',bundle['examples'])
    if (ROOT/'seed'/'zoom_style.json').exists() and not (s.DATA/'zoom_style.json').exists():
        s.write_json(s.DATA/'zoom_style.json',s.read_json(ROOT/'seed'/'zoom_style.json'))
    if (ROOT/'seed'/'hook_style.json').exists() and not (s.DATA/'hook_style.json').exists():
        s.write_json(s.DATA/'hook_style.json',s.read_json(ROOT/'seed'/'hook_style.json'))

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def stable_digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def ident():return uuid.uuid4().hex[:16]
def safe_id(value):
    if not re.fullmatch('[a-f0-9]{16}',value):raise ValueError('Invalid job/batch ID.')
    return value
def job_path(job):return STATE/'jobs'/safe_id(job)
def job_data(job):return s.read_json(job_path(job)/'job.json')
def batch_data(batch):return s.read_json(STATE/'batches'/(safe_id(batch)+'.json'))

@contextmanager
def lock(name,timeout=1200):
    """OS locks release on crashes; sidecar contains no project data."""
    path=STATE/'locks'/(hashlib.sha256(name.encode()).hexdigest()+'.lock')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as f:
        f.seek(0);f.write(b'0');f.flush();began=time.monotonic()
        while True:
            try:
                f.seek(0)
                if os.name=='nt':
                    import msvcrt;msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl;fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic()-began>timeout:raise TimeoutError('Another SoundPilot operation holds this lock.')
                time.sleep(.15)
        try:yield
        finally:
            f.seek(0)
            if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(f,fcntl.LOCK_UN)

def configure(draft_root:str,library:str,model_root:str=''):
    initialize()
    with lock('state'):
        cfg=s.config()
        for name,value in [('draft_root',draft_root),('library',library)]:
            path=Path(value).resolve()
            if not path.is_dir():raise ValueError(f'{name} must be an existing directory.')
            cfg[name]=str(path)
        cfg['model_root']=str(Path(model_root).resolve()) if model_root else str(STATE/'models')
        cfg['sidebar_settings']='';s.write_json(STATE/'config.json',cfg)
        sounds=s.scan_library(progress=lambda _:None)
        if len({a['name'].casefold() for a in sounds})!=len(sounds):raise ValueError('Duplicate sound filenames across folders: resolve ambiguity before connecting.')
    return {'configured':True,'state':str(STATE),'sounds':len(sounds),'style_version':s.read_json(s.DATA/'style_profile.json')['version']}

def pack(value):
    """Lossless tables; identical columns inherit defaults without dropping rows."""
    encode=lambda v:json.dumps(v,ensure_ascii=False,separators=(',',':'))
    if isinstance(value,list):
        if value and all(isinstance(x,dict) for x in value):
            keys=list(value[0])
            if all(set(x)==set(keys) for x in value):
                rows=[[pack(x[k]) for k in keys] for x in value]
                table={'$columns':keys,'$rows':rows}
                # JSON comparison distinguishes true/1, 1/1.0 and nested types.
                same=[i for i,k in enumerate(keys) if len(value)>1 and all(encode(x[k])==encode(value[0][k]) for x in value)]
                variable=[i for i in range(len(keys)) if i not in same]
                if same:
                    inherited={'$defaults':{keys[i]:rows[0][i] for i in same},'$columns':[keys[i] for i in variable],
                        '$rows':[[row[i] for i in variable] for row in rows]}
                    if len(encode(inherited))+40<len(encode(table)):table=inherited
                ordinary=[dict(zip(keys,row)) for row in rows]
                # Tiny tables can cost more than their plain dictionaries.
                return ordinary if len(encode(ordinary))+16<len(encode(table)) else table
            parts=[pack(list(group)) for _,group in groupby(value,key=lambda x:tuple(sorted(x)))]
            ordinary=[pack(x) for x in value];segmented={'$segments':parts}
            return segmented if len(encode(segmented))+40<len(encode(ordinary)) else ordinary
        return [pack(x) for x in value]
    if isinstance(value,dict):
        result={k:pack(v) for k,v in value.items()}
        if set(value) in ({'$columns','$rows'},{'$defaults','$columns','$rows'},{'$segments'},{'$literal'}):return {'$literal':result}
        return result
    return value
def unpack(value):
    if isinstance(value,dict):
        if set(value)=={'$literal'}:return {k:unpack(v) for k,v in value['$literal'].items()}
        if set(value)=={'$segments'}:return [row for part in value['$segments'] for row in unpack(part)]
        if set(value)=={'$defaults','$columns','$rows'}:
            defaults=unpack(value['$defaults'])
            return [{**copy.deepcopy(defaults),**dict(zip(value['$columns'],[unpack(v) for v in row]))} for row in value['$rows']]
        if set(value)=={'$columns','$rows'}:return [dict(zip(value['$columns'],[unpack(v) for v in row])) for row in value['$rows']]
        return {k:unpack(v) for k,v in value.items()}
    if isinstance(value,list):return [unpack(x) for x in value]
    return value

# Bookkeeping fields the planner never needs; filtering by video_signature happens before they are dropped.
BRIEF_DROP={'reference','video_signature','gain_envelope','gain_basis','cue_source','scope'}

def sfx_density():
    """Planned vs final SFX counts from every revision report, cached until history changes."""
    cache=STATE/'data'/'sfx_density.json';files=list((STATE/'history').glob('*.json'))
    newest=max((f.stat().st_mtime for f in files),default=0)
    if cache.exists():
        cached=s.read_json(cache)
        if cached.get('newest')==newest and cached.get('files')==len(files):return cached['density']
    n=more=planned=manual=added=removed=0;minutes=0.
    for f in files:
        report=s.read_json(f).get('report')
        diff=report.get('diff') if isinstance(report,dict) else None
        job=STATE/'jobs'/str(report.get('job_id') if diff else '')/'job.json'
        if not diff or 'timing' not in diff or not job.is_file():continue
        m=len(diff['matches']);p,q=m+len(diff['removed']),m+len(diff['added'])
        n+=1;more+=q>p;planned+=p;manual+=q;added+=len(diff['added']);removed+=len(diff['removed']);minutes+=s.read_json(job)['duration']/60
    density=None if not n or not minutes else {'revisions':n,'manual_had_more':more,'planned_per_minute':round(planned/minutes,1),
        'manual_per_minute':round(manual/minutes,1),'user_added':added,'user_removed':removed}
    s.write_json(cache,{'newest':newest,'files':len(files),'density':density})
    return density

def scene_memory_for_video(profile,signature):
    """Exclude this footage's manual timestamps, including legacy rule receipts."""
    feedback=profile.get('learned_feedback',[])
    own_refs={f.get('reference') for f in feedback if f.get('video_signature')==signature and f.get('reference')}
    return ([f for f in feedback if f.get('video_signature')!=signature],
        [r for r in profile.get('revision_rules',[]) if r.get('video_signature')!=signature and r.get('reference') not in own_refs])

def prepare_batch(targets:list[dict],workers:int=2,include_zoom:bool=True,include_hook:bool=False):
    initialize()
    # CapCut's exit save rewrites trivial draft fields, which breaks source_hash at apply and forces a full restage.
    if s.capcut_running():raise ValueError('Close CapCut before prepare; its exit save would invalidate the prepared plans.')
    if not 1<=len(targets)<=5:raise ValueError('Choose one to five project/timeline pairs.')
    if workers not in (1,2):raise ValueError('One or two workers preserve the tested CPU settings.')
    if not isinstance(include_zoom,bool):raise ValueError('include_zoom must be true/false; false is the explicit SFX-only mode.')
    if include_zoom and not (STATE/'data'/'zoom_style.json').exists():raise ValueError('Default SFX + zoom needs learned zoom style; learn references first or request SFX-only mode.')
    if include_hook and not (STATE/'data'/'hook_style.json').exists():raise ValueError('Full combo needs the learned native hook settings first.')
    batch=ident();jobs=[];seen=set()
    with lock('state'):
        profile=s.read_json(s.DATA/'style_profile.json');examples=s.read_json(s.DATA/'examples.json');sounds=s.scan_library(progress=lambda _:None)
        if len({a['name'].casefold() for a in sounds})!=len(sounds):raise ValueError('Duplicate sound filenames in library.')
        for target in targets:
            project=s.project_path(target['project']);timeline,draft,path=s.load_timeline(project,target['timeline'])
            pair=(str(project),timeline['id'])
            if pair in seen:raise ValueError('Duplicate target in batch.')
            seen.add(pair);job=ident();folder=job_path(job);folder.mkdir()
            record={'job_id':job,'batch_id':batch,'project':project.name,'timeline':timeline['name'],'timeline_id':timeline['id'],
                'source_hash':digest(path),'duration':draft['duration']/s.MICRO,'style_version':profile['version'],'status':'queued',
                'has_existing_sfx':bool(list(s.flatten_sfx(draft,sounds,project))),'created_at':time.time(),'plan_schema_version':2,'zoom_required':include_zoom,'hook_required':include_hook}
            for filename,value in [('job.json',record),('source.json',draft),('profile.json',profile),('examples.json',examples),('catalog.json',sounds)]:s.write_json(folder/filename,value)
            jobs.append(job)
        s.write_json(STATE/'batches'/(batch+'.json'),{'batch_id':batch,'jobs':jobs,'workers':workers,'style_version':profile['version']})
    # Detached coordinator survives a reconnect; two child processes have isolated OUTPUTS.
    flags=s.CREATE_NO_WINDOW
    with (STATE/'batches'/(batch+'.log')).open('ab') as log:
        subprocess.Popen([sys.executable,str(ROOT/'worker.py'),'batch',batch],stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=flags,env=os.environ.copy())
    return {'batch_id':batch,'jobs':jobs,'status':'queued','workflow':'sfx_and_zoom' if include_zoom else 'sfx_only','writes_to_capcut':False}

def prepare_job(job):
    import context_pipeline as c
    record=job_data(job);folder=job_path(job)
    old_data,old_outputs=s.DATA,s.OUTPUTS
    # Cache shared, per-job style/examples/catalog overrides; no changes to active memory.
    s.OUTPUTS=folder
    original_read=s.read_json
    overrides={str(old_data/'style_profile.json'):folder/'profile.json',str(old_data/'examples.json'):folder/'examples.json',str(old_data/'sound_catalog.json'):folder/'catalog.json'}
    def frozen_read(path):return original_read(overrides.get(str(path),path))
    s.read_json=frozen_read
    try:
        record['status']='preparing';s.write_json(folder/'job.json',record)
        project=s.project_path(record['project']);_,draft,path=s.load_timeline(project,record['timeline_id'])
        if digest(path)!=record['source_hash']:raise ValueError('Source changed while queued; prepare again.')
        _,key=c.context_inputs(project,draft)
        signature=stable_digest(s.video_timing_signature(draft))
        excluded=list({e['timeline'] for e in original_read(folder/'examples.json') if e.get('video_signature')==signature})
        original_compact=s.compact_brief
        def safe_compact(p,t,exclude=None):return original_compact(p,t,list(set((exclude or [])+excluded)))
        s.compact_brief=safe_compact
        import analysis_cache as ac
        try:reused=ac.mapped_report(sys.modules[__name__],ac.find(sys.modules[__name__],project,draft),draft)
        except LookupError:reused=None
        with lock('context:'+key):report=c.prepare(record['project'],record['timeline_id'],progress=lambda m:print(m,flush=True),force_refresh=not bool(reused),analysis_report=reused)
        # Save the canonical human tab name; exclude current media's own examples.
        brief=s.read_json(folder/'enhanced_brief.json');brief['timeline']=record['timeline'];brief['source_hash']=record['source_hash']
        brief['job_id']=job;brief['source_sfx_policy']='Existing target SFX are excluded from input; apply requires a clean target.'
        brief['plan_requirements']={'schema_version':record.get('plan_schema_version',1),'timing_anchor':'Every cue needs a specific indexed speech word, caption reaction or inspected exact frame. get_context supplies global word indices. Caption/ASR disagreement is not a verified onset.','creative_review':'Resolve the evaluated object, delivery and appraisal; consult latest manual substitutions and retimes. A positive word alone does not establish approval.',
            'workflow':'sfx_and_zoom' if record.get('zoom_required') else 'sfx_only','zoom_review_required':bool(record.get('zoom_required'))}
        feedback,rules=scene_memory_for_video(s.read_json(folder/'profile.json'),signature)
        brief['user_style']['learned_feedback']=[{k:v for k,v in f.items() if k not in BRIEF_DROP} for f in feedback]
        brief['user_style']['revision_rules']=[{k:v for k,v in r.items() if k not in BRIEF_DROP} for r in rules]
        density=sfx_density()
        if density:
            target=round(density['manual_per_minute']*record['duration']/60)
            brief['plan_requirements']['sfx_density']={**density,'target_for_this_video':target,'guidance':(
                f"In {density['manual_had_more']}/{density['revisions']} past revisions the user's final video had more SFX than the plan "
                f"(user added {density['user_added']}, removed {density['user_removed']}). Plans averaged {density['planned_per_minute']}/min; "
                f"finished videos {density['manual_per_minute']}/min. Aim for about {target} SFX here. Calibration, not a quota: "
                "every SFX still needs a real spoken/visual cue, but when a clear reaction cue fits a learned sound, include it rather than omit it.")}
        brief['user_style']['mix_preferences']=s.read_json(folder/'profile.json').get('mix_preferences',{})
        brief['user_style']['dialogue_level_references']=s.read_json(folder/'profile.json').get('dialogue_level_references',[])
        brief['user_style']['background_level_references']=s.read_json(folder/'profile.json').get('background_level_references',[])
        if (STATE/'data'/'zoom_style.json').exists():
            brief['zoom_style']=s.read_json(STATE/'data'/'zoom_style.json')
        s.write_json(folder/'enhanced_brief.json',brief)
        s.write_json(folder/'compact.json',pack(brief))
        report['caption_speech_audit']=timing_audit(brief,report)
        s.write_json(folder/'context_report.json',report)
        if digest(path)!=record['source_hash']:raise ValueError('Source changed during context preparation; prepare again.')
        record.update(status='ready',seconds=report['seconds'],cache_key=key,analysis_reused=report.get('analysis_reused',False),analysis_expires_at=report['analysis_created_at']+ac.TTL)
        s.write_json(folder/'job.json',record);ac.register(sys.modules[__name__],job)
    except Exception as exc:record.update(status='failed',error=str(exc));raise
    finally:
        if 'original_compact' in locals():s.compact_brief=original_compact
        s.read_json=original_read;s.DATA=old_data;s.OUTPUTS=old_outputs;s.write_json(folder/'job.json',record)
    return record

def timing_audit(brief,report):
    from difflib import SequenceMatcher
    def norm(text):return re.sub(r'[^a-z0-9 ]','',text.lower()).split()
    warnings=[]
    for caption in brief['captions']:
        a=caption['start'];text=norm(caption['text']);candidates=[]
        if not text:continue
        # Compare caption words to local word sequences, never to the start of
        # a long ASR sentence that may contain several unrelated reactions.
        for track in report['tracks']:
            words=[w for row in track['speech'] for w in row.get('words',[]) if a-4<=w['start']<=a+4]
            for i,word in enumerate(words):
                for length in range(max(1,len(text)-1),len(text)+2):
                    window=words[i:i+length]
                    if len(window)!=length:continue
                    tokens=[token for w in window for token in norm(w['text'])]
                    score=SequenceMatcher(None,text,tokens).ratio()
                    candidates.append((score,word['start'],track['role']))
        if candidates:
            score,at,role=max(candidates,key=lambda x:(x[0],-abs(x[1]-a)));delta=at-a
            if score>=.7 and abs(delta)>.15:warnings.append({'caption':caption['text'],'caption_at':a,'speech_at':at,'offset':round(delta,3),'role':role,'kind':'word_caption_offset'})
            elif score<.7:warnings.append({'caption':caption['text'],'caption_at':a,'kind':'unmatched_reaction','note':'ASR did not reliably align this caption. Inspect the reaction/audio; do not invent a word time.'})
    return {'policy':'Word-sequence offsets are review hints, not auditory verification. Captions and ASR are both retained, especially eww/nonverbal reactions.', 'warnings':warnings}

def status(batch_id:str):
    batch=batch_data(batch_id)
    rows=[{k:v for k,v in job_data(job).items() if k in ('job_id','project','timeline','status','seconds','error','has_existing_sfx')} for job in batch['jobs']]
    return {'batch_id':batch_id,'jobs':rows}

def get_brief(job_id:str,full:bool=False):
    record=job_data(job_id)
    if record['status'] not in ('ready','staged','applied'):raise ValueError('Context is not ready. Check batch status.')
    brief=s.read_json(job_path(job_id)/'enhanced_brief.json')
    return brief if full else pack(brief)

def shared_fields(rows):
    result={}
    for key in rows[0]:
        if not all(key in r for r in rows):continue
        values=[r[key] for r in rows]
        if all(v==values[0] for v in values):result[key]=copy.deepcopy(values[0])
        elif all(isinstance(v,dict) for v in values):
            shared=shared_fields(values)
            if shared:result[key]=shared
    return result

def difference(row,common):
    result={}
    for key,value in row.items():
        if key not in common:result[key]=copy.deepcopy(value)
        elif isinstance(value,dict) and isinstance(common[key],dict):
            delta=difference(value,common[key])
            if delta:result[key]=delta
        elif value!=common[key]:result[key]=copy.deepcopy(value)
    return result

def merge(common,delta):
    result=copy.deepcopy(common)
    for key,value in delta.items():
        result[key]=merge(result[key],value) if key in result and isinstance(value,dict) and isinstance(result[key],dict) else copy.deepcopy(value)
    return result

def get_batch_briefs(batch_id:str):
    batch=batch_data(batch_id);rows=[get_brief(job,True) for job in batch['jobs']];common=shared_fields(rows)
    result={'$shared':pack(common),'$jobs':[{'job_id':job,'$delta':pack(difference(row,common))} for job,row in zip(batch['jobs'],rows)]}
    for row,part in zip(rows,result['$jobs']):assert merge(unpack(result['$shared']),unpack(part['$delta']))==row
    return result

def get_context(job_id:str,start:float,end:float):
    record=job_data(job_id)
    if not 0<=start<end<=record['duration'] or end-start>12:raise ValueError('Choose a context window no longer than 12 seconds inside the timeline.')
    report=s.read_json(job_path(job_id)/'context_report.json');brief=get_brief(job_id,True)
    speech=[]
    for track in report['tracks']:
        rows=[];index=0
        for row in track['speech']:
            words=[{**word,'word_index':index+i} for i,word in enumerate(row.get('words',[]))];index+=len(words)
            if row['start']<end and row['end']>start:rows.append({**row,'words':words})
        speech.append({'role':track['role'],'rows':rows})
    return {'captions':[{**r,'caption_index':i} for i,r in enumerate(brief['captions']) if r['start']<end and r['end']>start],
        'speech':speech,
        'timing_audit':report['caption_speech_audit'], 'note':'Source stream words, not a rendered CapCut composite.'}


def get_context_batch(job_id:str,windows:list[dict]):
    """Pool identical complete rows once; reconstruct EVERY get_context result."""
    if not 1<=len(windows)<=64:raise ValueError('Choose 1–64 cue windows.')
    contexts=[get_context(job_id,w['start'],w['end']) for w in windows]
    rows=[];captions=[];row_ids={};caption_ids={};mapped=[]
    for window,context in zip(windows,contexts):
        item={'start':window['start'],'end':window['end'],'speech':[],'caption_ids':[]}
        for stream in context['speech']:
            refs=[]
            for row in stream['rows']:
                value={'role':stream['role'],'row':row};key=stable_digest(value)
                if key not in row_ids:row_ids[key]=len(rows);rows.append(value)
                refs.append(row_ids[key])
            item['speech'].append({'role':stream['role'],'row_ids':refs})
        for caption in context['captions']:
            key=stable_digest(caption)
            if key not in caption_ids:caption_ids[key]=len(captions);captions.append(caption)
            item['caption_ids'].append(caption_ids[key])
        mapped.append(item)
    result={'speech_rows':rows,'captions':captions,'windows':mapped,'timing_audit':contexts[0]['timing_audit'],'note':contexts[0]['note']}
    for expected,window in zip(contexts,mapped):
        actual={'speech':[{'role':stream['role'],'rows':[rows[i]['row'] for i in stream['row_ids']]} for stream in window['speech']],
            'captions':[captions[i] for i in window['caption_ids']],'timing_audit':result['timing_audit'],'note':result['note']}
        assert actual==expected,'Batched cue evidence changed.'
    return pack(result)

def exact_frame(job_id:str,role:str,at:float):
    import context_pipeline as c
    record=job_data(job_id)
    if not 0<=at<record['duration']:raise ValueError('Frame time outside video.')
    project=s.project_path(record['project']);_,draft,path=s.load_timeline(project,record['timeline_id'])
    if digest(path)!=record['source_hash']:raise ValueError('Timeline changed; prepare again.')
    inputs,_=c.context_inputs(project,draft);track=next(t for t in inputs['tracks'] if t['role']==role)
    clip=next((v for v in track['clips'] if v['start']<=at<v['start']+v['duration']),None)
    if clip is None:raise ValueError('No source clip at this time.')
    relative=at-clip['start']
    if clip['reverse']:relative=clip['duration']-relative
    source_at=clip['source_start']+relative*clip['speed'];dest=job_path(job_id)/f'frame-{role}-{at:.3f}.jpg'
    c.run_ffmpeg(['-ss',str(source_at),'-i',clip['path'],'-frames:v','1','-vf','scale=640:-2','-y',str(dest)])
    return {'path':str(dest),'at':at,'role':role,'note':'Exact decoded source frame. CapCut overlays/effects/crops are not included.'}

def frame_sheet(job_id:str,times:list[float],roles:list[str]|None=None):
    """Both streams x 1-4 times in one labelled image; each frame is also saved as its exact_frame artifact."""
    import context_pipeline as c
    from PIL import Image,ImageDraw
    if not 1<=len(times)<=4:raise ValueError('frame_sheet takes 1-4 times.')
    record=job_data(job_id);project=s.project_path(record['project']);_,draft,_=s.load_timeline(project,record['timeline_id'])
    roles=roles or [t['role'] for t in c.context_inputs(project,draft)[0]['tracks'] if t['role'].startswith('video')]
    tile=320;cells=[]
    for role in roles:
        for at in times:
            try:cells.append((role,at,Image.open(exact_frame(job_id,role,at)['path']).convert('RGB')))
            except ValueError as error:
                if not str(error).startswith(('No source clip','Frame time outside')):raise  # job-level errors fail the whole sheet
                cells.append((role,at,str(error)))
    n=len(times);rows=[cells[r*n:(r+1)*n] for r in range(len(roles))]
    heights=[max([round(img.height*tile/img.width) for _,_,img in row if not isinstance(img,str)] or [60])+22 for row in rows]
    tops=[sum(heights[:r]) for r in range(len(rows))]
    sheet=Image.new('RGB',(tile*n,sum(heights)),'black');draw=ImageDraw.Draw(sheet)
    for i,(role,at,img) in enumerate(cells):
        x,y=(i%n)*tile,tops[i//n]
        draw.text((x+4,y+4),f'{role} @ {at:.3f}s',fill='yellow')
        if isinstance(img,str):draw.text((x+4,y+30),img[:40],fill='red')
        else:sheet.paste(img.resize((tile,round(img.height*tile/img.width))),(x,y+22))
    dest=job_path(job_id)/f'sheet-{"-".join(f"{t:.3f}" for t in times)}.jpg';sheet.save(dest,quality=88)
    return {'path':str(dest),'times':times,'roles':roles,'note':'Columns are times, rows are streams. Exact decoded source frames at 320px; CapCut overlays not included. Use exact_frame for fine detail.'}

@contextmanager
def frozen_job(job):
    folder=job_path(job);original=s.read_json
    paths={str(s.DATA/'style_profile.json'):folder/'profile.json',str(s.DATA/'examples.json'):folder/'examples.json',str(s.DATA/'sound_catalog.json'):folder/'catalog.json'}
    s.read_json=lambda p:original(paths.get(str(p),p))
    try:yield folder
    finally:s.read_json=original

def validate_timing_anchor(folder,record,effect):
    anchor=effect.get('timing_anchor')
    if not anchor:
        if record.get('plan_schema_version',1)>=2:raise ValueError('Every new cue needs an evidence-backed timing_anchor; fetch get_context or exact_frame.')
        return
    role=anchor.get('role');kind=anchor.get('kind');at=anchor.get('at')
    if role not in ('video_track_1','video_track_2') or not isinstance(at,(int,float)) or not math.isfinite(at) or not 0<=at<record['duration']:
        raise ValueError('Invalid timing anchor role/time.')
    if kind=='speech_word':
        report=s.read_json(folder/'context_report.json');track=next((t for t in report['tracks'] if t['role']==role),{})
        words=[w for row in track.get('speech',[]) for w in row.get('words',[])];index=anchor.get('word_index')
        if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(words):raise ValueError('Timing anchor needs a real global word_index from get_context.')
        word=words[index]
        if anchor.get('text')!=word['text'] or abs(at-word['start'])>.002:raise ValueError(f"Timing anchor does not match the frozen speech word: {role} word_index {index} is {word['text']!r} at {word['start']}.")
    elif kind=='caption_reaction':
        captions=s.read_json(folder/'enhanced_brief.json')['captions'];index=anchor.get('caption_index')
        if role!='video_track_1' or isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(captions):raise ValueError('Caption anchor needs a real reaction caption_index.')
        caption=captions[index]
        if anchor.get('text')!=caption['text'] or abs(at-caption['start'])>.002:raise ValueError('Caption anchor does not match the frozen reaction caption.')
    elif kind=='visual_reveal':
        if not (folder/f'frame-{role}-{at:.3f}.jpg').is_file() or len(anchor.get('text',''))<8:raise ValueError('Visual timing anchor needs an exact_frame artifact and observable action.')
    else:raise ValueError('Timing anchor kind must be speech_word, caption_reaction or visual_reveal.')
    if abs(effect['start']-at)>.15 and len(anchor.get('offset_reason',''))<15:
        raise ValueError('An onset offset over 150ms needs a deliberate lead/lag reason; do not silently guess timing.')

def stage_plan(job_id:str,effects:list[dict],quality_notes:dict,zooms:list[dict]|None=None,zoom_quality_notes:dict|None=None,hook_plan:dict|None=None,hook_quality_notes:dict|None=None):
    """No automatic creative placements: require exact cue, intent and evidence."""
    record=job_data(job_id);folder=job_path(job_id)
    if record['status'] not in ('ready','staged'):raise ValueError('Job must have ready context.')
    if record['has_existing_sfx']:raise ValueError('Target contains user SFX. Choose a new clean timeline; do not erase revisions.')
    if record.get('zoom_required') and zooms is None and not record.get('zoom_job_id'):
        raise ValueError('Default workflow requires contextual SFX + zoom review in this same analysis. Pass zooms and zoom_quality_notes; an explicit reviewed empty list is valid silence.')
    if record.get('hook_required') and hook_plan is None:
        raise ValueError('Full combo requires a text-hook plan or explicit keep_existing review.')
    if not quality_notes.get('whole_video_reviewed') or not quality_notes.get('silence_reviewed'):
        raise ValueError('Read both streams for the whole video and explicitly review where silence is appropriate.')
    if quality_notes.get('unresolved'):raise ValueError('Resolve uncertain cue choices using audio/context/frames before staging.')
    balance=quality_notes.get('dialogue_balance',{})
    if balance:
        if len(quality_notes.get('dialogue_balance_reason',''))<15:raise ValueError('Explain a deliberate per-speaker balance change.')
        tracks=ra.video_tracks(s.read_json(folder/'source.json'))
        allowed={f'video_track_{i+1}' for i in range(len(tracks))}
        if any(role not in allowed or not isinstance(gain,(int,float)) or not math.isfinite(gain) or not 0<=gain<=4 for role,gain in balance.items()):
            raise ValueError('Invalid per-speaker gain multiplier.')
    effects=copy.deepcopy(effects);catalog={a['name']:a for a in s.read_json(folder/'catalog.json')};examples=s.read_json(folder/'examples.json')
    profile=s.read_json(folder/'profile.json');learned_levels=profile.get('mix_preferences',{}).get('sound_levels',{})
    def check(e):
        validate_timing_anchor(folder,record,e)
        if not e.get('dialogue') or not e.get('function') or len(e.get('reason',''))<12:
            raise ValueError('Every selected cue needs dialogue/visual anchor, function and a contextual reason.')
        if e.get('confidence') not in ('high','medium'):raise ValueError('Inspect uncertain cues, then omit or resolve them.')
        if e.get('user_reviewed'):raise ValueError('Only actual manual feedback can mark user_reviewed; do not bypass checks.')
        if e['sound'] not in catalog:raise ValueError('Unknown library sound.')
        choices=[(i,a) for i,a in enumerate(examples) if a['sound']==e['sound']]
        if not choices:raise ValueError('No native reference template for sound; import an actual manual example first.')
        index,example=choices[0];e['example_index']=index
        learned=learned_levels.get(e['sound']);tier=e.get('gain_tier','normal')
        if tier not in ('soft','normal','emphasis'):raise ValueError('gain_tier must be soft, normal or emphasis.')
        if learned and e.get('level_source')!='explicit_override':
            if 'volume' in e:e['requested_volume_before_learning']=e['volume']
            e['volume']=learned[tier+'_gain'];e['level_source']='manual_revision_reference'
            e.setdefault('duration',min(learned['median_duration'],(catalog[e['sound']]['duration']-float(e.get('source_start',0)))/float(e.get('speed',1))))
            refs=learned['references'];closest=min(refs,key=lambda r:abs(r['gain']-e['volume']))
            if closest.get('gain_envelope') and len(closest['gain_envelope'])>1 and 'gain_envelope' not in e:
                # Preserve the approved relative attack/body envelope, scaled in time.
                length=float(e.get('duration',learned['median_duration']));factor=length/closest['duration']
                e['gain_envelope']=[{**p,'offset':p['offset']*factor,'duration':p['duration']*factor,**({'source_offset':p['source_offset']*factor} if 'source_offset' in p else {})} for p in closest['gain_envelope']]
            for k in ('fade_in','fade_out'):e.setdefault(k,learned.get(k,example.get(k,.005 if k=='fade_in' else .08)))
        elif e.get('level_source')=='explicit_override' and len(e.get('level_reason',''))<15:
            raise ValueError('A deliberate override of learned levels needs a specific level_reason.')
        for key,value in [('source_start',0),('speed',1),('volume',example['volume']),('fade_in',.005),('fade_out',.08)]:e.setdefault(key,value)
        e.setdefault('duration',min(learned['median_duration'] if learned else example['duration'],catalog[e['sound']]['duration']))
        for part in e.get('gain_envelope',[]):
            if 'source_offset' in part and (not isinstance(part['source_offset'],(int,float)) or not math.isfinite(part['source_offset']) or part['source_offset']<0):raise ValueError('Invalid envelope source offset.')
            if not all(isinstance(part.get(k),(int,float)) and math.isfinite(part[k]) for k in ('offset','duration','gain')) or part['offset']<0 or part['duration']<=0 or not 0<=part['gain']<=1 or part['offset']+part['duration']>e['duration']+.002:
                raise ValueError('Invalid learned gain envelope.')
    # Collect every effect/hook/zoom problem in one pass: one retry instead of many
    # full-plan resends.
    errors=[]
    for i,e in enumerate(effects):
        try:check(e)
        except ValueError as err:errors.append(f"effect {i} {e.get('sound')}@{e.get('start')}: {err}")
    plan={'project':record['project'],'timeline':record['timeline_id'],'source_hash':record['source_hash'],'duration':record['duration'],
        'style_profile_version':record['style_version'],'effects':effects,'quality_notes':quality_notes,'job_id':job_id}
    if not errors:
        try:
            with frozen_job(job_id):s.validate_plan(ra.render_plan(plan),s.read_json(s.DATA/'sound_catalog.json'))
        except ValueError as err:errors.append(f'effects: {err}')
    if hook_plan is not None:
        import hooks
        if not record.get('hook_job_id'):
            child=hooks.prepare(sys.modules[__name__],[{'project':record['project'],'timeline':record['timeline_id'],'analysis_job_id':job_id}]);record['hook_job_id']=child['jobs'][0]
            s.write_json(folder/'job.json',record)
        try:hooks.stage(sys.modules[__name__],record['hook_job_id'],hook_plan,hook_quality_notes or {})
        except ValueError as err:errors.append(f'hook: {err}')
    if zooms is not None:
        if not record.get('zoom_job_id'):
            linked=prepare_zoom_batch([{'project':record['project'],'timeline':record['timeline_id'],'analysis_job_id':job_id}])
            record['zoom_job_id']=linked['jobs'][0];s.write_json(folder/'job.json',record)
        try:stage_zoom_plan(record['zoom_job_id'],zooms,zoom_quality_notes or {})
        except ValueError as err:errors.append(f'zooms: {err}')
    if errors:raise ValueError(f'{len(errors)} problem(s), nothing staged for SFX; fix all then retry: '+' || '.join(errors))
    s.write_json(folder/'plan.json',plan);record['status']='staged';s.write_json(folder/'job.json',record)
    return {'job_id':job_id,'cues':len(effects),'plan_hash':digest(folder/'plan.json'),'zoom_job_id':record.get('zoom_job_id'),
        'hook_job_id':record.get('hook_job_id'),'writes_to_capcut':False,'next':'audit_mix and linked zoom/hook previews, then preflight_batch/apply_batch'}

def audit_mix(job_id:str):
    """48k stereo preview with source clip levels, source speed and SFX trims."""
    import numpy as np, wave
    import context_pipeline as c
    folder=job_path(job_id);plan=s.read_json(folder/'plan.json');record=job_data(job_id)
    project=s.project_path(record['project']);_,draft,path=s.load_timeline(project,record['timeline_id'])
    if digest(path)!=record['source_hash']:raise ValueError('Source changed; prepare again.')
    rate=48000;count=round(plan['duration']*rate);mix=np.zeros((count,2),dtype=np.float32);sfx_mix=np.zeros((count,2),dtype=np.float32);voice_mix=np.zeros((count,2),dtype=np.float32)
    cache_dir=folder/'audio_cache';cache_dir.mkdir(exist_ok=True);memo={}
    def decode(path,source_start,length):
        # Decoded PCM is cached per job: a re-audit after set_mix skips ffmpeg.
        st=Path(path).stat();key=stable_digest([str(path),st.st_size,st.st_mtime_ns,round(source_start,6),round(length,6),rate])[:24]
        if key in memo:return memo[key]
        cached=cache_dir/(key+'.npy')
        if cached.is_file():source=np.load(cached)
        else:
            raw=c.run_ffmpeg(['-ss',str(source_start),'-i',str(path),'-t',str(length),'-vn','-ac','2','-ar',str(rate),'-f','f32le','-'])
            source=np.frombuffer(raw,dtype='<f4').reshape(-1,2);np.save(cached,source)
        memo[key]=source;return source
    def put(path,start,duration,source_start,speed,gain,reverse=False,fade_in=0,fade_out=0,target=None):
        target=mix if target is None else target
        source=decode(path,source_start,duration*speed+.05)
        positions=np.arange(round(duration*rate))*speed
        if reverse:positions=positions[::-1]
        audio=np.column_stack([np.interp(positions,np.arange(len(source)),source[:,ch],left=0,right=0) for ch in range(2)]).astype(np.float32)*gain
        fi=min(len(audio),round(min(fade_in,duration/3)*rate));fo=min(len(audio),round(min(fade_out,duration/3)*rate))
        if fi:audio[:fi]*=np.linspace(0,1,fi)[:,None]
        if fo:audio[-fo:]*=np.linspace(1,0,fo)[:,None]
        lo=round(start*rate);hi=min(count,lo+len(audio));target[lo:hi]+=audio[:hi-lo]
    unsupported=[]
    voice_index=0
    for track in draft['tracks']:
        if track.get('type') not in ('video','audio'):continue
        balance_gain=1
        if track['type']=='video' and track.get('segments'):
            voice_index+=1;balance_gain=plan.get('quality_notes',{}).get('dialogue_balance',{}).get(f'video_track_{voice_index}',1)
        kind='videos' if track['type']=='video' else 'audios';mats={m['id']:m for m in draft['materials'].get(kind,[])}
        for seg in track.get('segments',[]):
            if not seg.get('visible',True):continue
            volume=float(seg.get('volume',1))*balance_gain
            if not volume:continue
            mat=mats.get(seg['material_id']);target=seg['target_timerange'];source=seg.get('source_timerange') or target
            audio_keys=[k for k in seg.get('common_keyframes',[]) if 'audio' in k.get('property_type','').lower() or 'volume' in k.get('property_type','').lower()]
            if not mat or not mat.get('path') or audio_keys:
                unsupported.append(seg['id']);continue
            # Active sound processing has to be reviewed in CapCut; do not certify an inaccurate mix.
            refs=set(seg.get('extra_material_refs',[]))
            fx=[m for k,arr in draft['materials'].items() if k in ('audio_effects','vocal_beautifys','sound_channel_mappings') for m in arr if m.get('id') in refs and m.get('effect_id')]
            if fx:unsupported.append(seg['id']);continue
            fades=[f for f in draft['materials'].get('audio_fades',[]) if f['id'] in refs]
            fi=fades[0].get('fade_in_duration',0)/s.MICRO if fades else 0;fo=fades[0].get('fade_out_duration',0)/s.MICRO if fades else 0
            put(s.resolve_path(mat['path'],project),target['start']/s.MICRO,target['duration']/s.MICRO,source['start']/s.MICRO,float(seg.get('speed') or 1),volume,seg.get('reverse',False),fi,fo,target=voice_mix if track['type']=='video' else None)
    catalog={a['name']:a for a in s.read_json(folder/'catalog.json')}
    for e in ra.render_plan(plan)['effects']:
        if e.get('enabled',True):put(catalog[e['sound']]['path'],e['start'],e['duration'],e['source_start'],e['speed'],e['volume'],fade_in=e['fade_in'],fade_out=e['fade_out'],target=sfx_mix)
    if unsupported:raise ValueError('Preview cannot faithfully model compound audio/effects/keyframes. Resolve/render these segments before applying: '+str(unsupported[:5]))
    other_mix=mix.copy();mix+=voice_mix+sfx_mix
    peak=float(np.max(np.abs(mix))) if count else 0;gain=min(1,.891/max(peak,1e-8));dest=folder/'preview.wav'
    # Srijon's 2026-10-14 rule: keep learned SFX audible; lower the loud dialogue
    # video tracks instead of uniform attenuation. Find that dialogue factor.
    suggestion=None
    if gain<.999999 and float(np.max(np.abs(sfx_mix+other_mix)))<.891:
        lo_k,hi_k=0.0,1.0
        for _ in range(30):
            k=(lo_k+hi_k)/2
            if float(np.max(np.abs(voice_mix*k+other_mix+sfx_mix)))<=.891:lo_k=k
            else:hi_k=k
        current=plan.get('quality_notes',{}).get('dialogue_balance',{})
        roles=[f'video_track_{i+1}' for i in range(len(ra.video_tracks(s.read_json(folder/'source.json'))))]
        suggestion={'source_factor':round(lo_k,4),'source_factor_db':round(20*math.log10(max(lo_k,1e-9)),2),
            'dialogue_balance':{r:round(current.get(r,1)*lo_k,4) for r in roles},
            'note':'Scaling the dialogue video tracks by source_factor (SFX and other audio untouched) reaches 0.891. Apply with set_mix(dialogue_balance=..., reason) then audit again.'}
    with wave.open(str(dest),'wb') as wav:
        wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes((np.clip(mix*gain,-1,1)*32767).astype('<i2').tobytes())
    # Human-approved levels must not silently be reduced again on installation.
    learned_mix=s.read_json(folder/'profile.json').get('mix_preferences',{})
    explicit=plan.get('quality_notes',{}).get('headroom_mode')=='uniform_attenuation'
    if explicit and len(plan['quality_notes'].get('headroom_reason',''))<15:raise ValueError('Explain the deliberate whole-mix attenuation decision.')
    needs_review=bool(learned_mix and gain<.999999 and not explicit)
    plan['master_gain']=1 if needs_review else gain;s.write_json(folder/'plan.json',plan)
    report={'job_id':job_id,'preview':str(dest),'master_gain':gain,'peak_before':peak,'peak_after':peak*gain,'plan_hash':digest(folder/'plan.json'),
        'headroom_review_required':needs_review,'preview_attenuation':gain,'planned_master_gain':plan['master_gain'],'suggested_source_lowering':suggestion,
        'policy':'Preview attenuation protects this WAV. With learned levels, applying attenuation to every dialogue/SFX clip requires an explicit headroom_mode and reason; otherwise adjust the mix and audit again. Sample peaks do not establish perceived loudness.'}
    s.write_json(folder/'mix.json',report);return report

def set_mix(job_id:str,dialogue_balance:dict|None=None,dialogue_balance_reason:str='',headroom_mode:str|None=None,headroom_reason:str=''):
    """Change only mix notes of a staged plan (no effect/zoom/hook resend); audit must rerun."""
    folder=job_path(job_id);record=job_data(job_id)
    if record['status']!='staged':raise ValueError('Stage the plan first.')
    plan=s.read_json(folder/'plan.json');notes=copy.deepcopy(plan['quality_notes'])
    if dialogue_balance is not None:
        if dialogue_balance and len(dialogue_balance_reason)<15:raise ValueError('Explain a deliberate per-speaker balance change.')
        allowed={f'video_track_{i+1}' for i in range(len(ra.video_tracks(s.read_json(folder/'source.json'))))}
        if any(r not in allowed or not isinstance(g,(int,float)) or isinstance(g,bool) or not math.isfinite(g) or not 0<=g<=4 for r,g in dialogue_balance.items()):
            raise ValueError('Invalid per-speaker gain multiplier.')
        notes['dialogue_balance']=dialogue_balance;notes['dialogue_balance_reason']=dialogue_balance_reason
        if not dialogue_balance:notes.pop('dialogue_balance');notes.pop('dialogue_balance_reason',None)
    if headroom_mode is not None:
        if headroom_mode not in ('uniform_attenuation','none'):raise ValueError('headroom_mode must be uniform_attenuation or none.')
        if headroom_mode=='none':notes.pop('headroom_mode',None);notes.pop('headroom_reason',None)
        else:
            if len(headroom_reason)<15:raise ValueError('Explain the deliberate whole-mix attenuation decision.')
            notes['headroom_mode']=headroom_mode;notes['headroom_reason']=headroom_reason
    plan['quality_notes']=notes;plan['master_gain']=1;s.write_json(folder/'plan.json',plan)
    (folder/'mix.json').unlink(missing_ok=True)
    return {'job_id':job_id,'quality_notes':{k:notes[k] for k in ('dialogue_balance','headroom_mode') if k in notes},'writes_to_capcut':False,'next':'audit_mix again'}

def build_changes(job):
    """Prepare changes entirely in memory; caller checks every batch before mutation."""
    record=job_data(job);folder=job_path(job);plan=s.read_json(folder/'plan.json')
    for key,value in [('project',record['project']),('timeline',record['timeline_id']),('source_hash',record['source_hash']),('duration',record['duration']),('style_profile_version',record['style_version'])]:
        if plan.get(key)!=value:raise ValueError('Plan identity/source/style does not match its frozen job.')
    if record['status']!='staged':raise ValueError('Every target must have a staged plan.')
    if record.get('zoom_required') and not record.get('zoom_job_id'):raise ValueError('Default SFX + zoom plan is missing its zoom review.')
    if record.get('hook_required') and not record.get('hook_job_id'):raise ValueError('Full combo is missing text-hook review.')
    if s.read_json(s.DATA/'style_profile.json')['version']!=record['style_version']:raise ValueError('Style changed since preparation. Re-evaluate against the latest revision.')
    mix=s.read_json(folder/'mix.json')
    if mix['plan_hash']!=digest(folder/'plan.json'):raise ValueError('Plan changed after audio audit. Audit again.')
    if mix.get('headroom_review_required'):raise ValueError('Do not silently reduce all learned sound/dialogue levels. Resolve the peak/headroom decision and audit again.')
    project=s.project_path(record['project']);timeline,current,path=s.load_timeline(project,record['timeline_id'])
    if digest(path)!=record['source_hash']:raise ValueError('Source changed after planning. Prepare again.')
    with frozen_job(job):
        sounds=s.read_json(s.DATA/'sound_catalog.json');rendered=ra.render_plan(plan);s.validate_plan(rendered,sounds)
        for sound in sounds:
            if sound['name'] not in {e['sound'] for e in plan['effects'] if e.get('enabled',True)}:continue
            stat=Path(sound['path']).stat()
            if 'mtime' in sound and (stat.st_mtime_ns!=sound['mtime'] or stat.st_size!=sound['size']):raise ValueError('A selected sound file changed; prepare and audit again.')
        if list(s.flatten_sfx(current,sounds,project)):raise ValueError('Target already contains local SFX; user edits are protected.')
        draft=copy.deepcopy(current)
        voice_index=0
        for track in draft['tracks']:
            if track.get('type')=='video' and track.get('segments'):
                voice_index+=1;factor=plan.get('quality_notes',{}).get('dialogue_balance',{}).get(f'video_track_{voice_index}',1)
                if factor!=1:
                    for seg in track['segments']:
                        seg['volume']=float(seg.get('volume',1))*factor;seg['last_nonzero_volume']=float(seg.get('last_nonzero_volume',1))*factor
        s.add_effects(draft,rendered,s.read_json(s.DATA/'examples.json'),sounds)
    gain=plan.get('master_gain',1)
    if record.get('cache_key'):
        import context_pipeline as c
        if c.context_inputs(project,current)[1]!=record['cache_key']:raise ValueError('Source video files changed; prepare again.')
    if not 0<gain<=1:raise ValueError('Invalid master gain.')
    for track in draft['tracks']:
        if track.get('type') in ('video','audio'):
            for seg in track.get('segments',[]):
                seg['volume']=float(seg.get('volume',1))*gain;seg['last_nonzero_volume']=float(seg.get('last_nonzero_volume',1))*gain
    s.validate_draft(draft)
    meta_path=project/'draft_meta_info.json';meta=s.read_json(meta_path)
    group=next((g for g in meta.get('draft_materials',[]) if g.get('type')==0),None)
    if group is None:group={'type':0,'value':[]};meta.setdefault('draft_materials',[]).append(group)
    known={m.get('file_Path') for m in group['value']};catalog={a['name']:a for a in sounds}
    for e in plan['effects']:
        if not e.get('enabled',True):continue
        sound=catalog[e['sound']];audio_path=Path(sound['path']).as_posix()
        if audio_path in known:continue
        duration=round(sound['duration']*s.MICRO)
        group['value'].append({'id':s.uid(),'file_Path':audio_path,'extra_info':sound['name'],'metetype':'music','type':0,'duration':duration,'width':0,'height':0,'md5':'',
            'create_time':0,'import_time':0,'import_time_ms':0,'roughcut_time_range':{'start':0,'duration':duration},'sub_time_range':{'start':-1,'duration':-1},'item_source':1,'enter_from':0})
        known.add(audio_path)
    now=int(time.time()*s.MICRO);meta.update(tm_duration=draft['duration'],tm_draft_modified=now)
    index_path=project/'Timelines'/'project.json'
    index=s.read_json(index_path);index['main_timeline_id']=timeline['id'];index['update_time']=now
    if record.get('zoom_job_id'):
        import zoom as z
        draft=z.validated_native(sys.modules[__name__],record['zoom_job_id'],draft)
    if record.get('hook_job_id'):
        import hooks
        draft=hooks.validated(sys.modules[__name__],record['hook_job_id'],draft)
    return {path:draft,s.draft_file(project):draft,meta_path:meta,index_path:index}

def batch_changes(batch):
    result={}
    for job in batch['jobs']:
        changes=build_changes(job)
        for path,value in changes.items():
            if path in result:
                # Multiple timelines in a project share media metadata; merge registrations.
                if path.name=='draft_meta_info.json':
                    old=result[path];known={m.get('file_Path') for g in old.get('draft_materials',[]) for m in g.get('value',[])}
                    for g in value.get('draft_materials',[]):
                        existing=next((x for x in old['draft_materials'] if x['type']==g['type']),None)
                        if existing is None:old['draft_materials'].append(g);continue
                        for m in g.get('value',[]):
                            if m.get('file_Path') not in known:existing['value'].append(m);known.add(m.get('file_Path'))
                    old['tm_draft_modified']=value['tm_draft_modified'];continue
                if path.name not in ('project.json','draft_content.json','draft_info.json'):raise ValueError('Unexpected batch write collision.')
            result[path]=value
    return result

def preflight_batch(batch_id:str):
    batch=batch_data(batch_id)
    with lock('state'),lock('zoom-style'),lock('hook-style'):
        changes=batch_changes(batch)
    return {'batch_id':batch_id,'valid':True,'targets':len(batch['jobs']),'files':len(changes),'writes_to_capcut':False,
        'capcut_running':s.capcut_running(),'auto_close_on_apply':True,
        'note':'Preflight validates files/timing/style annotations and audio audit; creative correctness requires listening/review.'}

def close_for_apply(auto_close=True):
    import app_lifecycle
    return app_lifecycle.ensure_closed(s.capcut_running,auto_close)

def apply_batch(batch_id:str,auto_close:bool=True):
    batch=batch_data(batch_id)
    with lock('state'),lock('zoom-style'),lock('hook-style'),lock('capcut-write'):
        if not auto_close:close_for_apply(False)
        # Validate every plan/audit before asking the application to exit.
        batch_changes(batch)
        closure=close_for_apply(auto_close)
        # Revalidate after final autosave; never rebase a stale plan blindly.
        changes=batch_changes(batch);previous={p:p.read_bytes() for p in changes}
        if s.capcut_running() or any(p.read_bytes()!=data for p,data in previous.items()):raise ValueError('Project changed during preflight.')
        try:
            for path,value in changes.items():
                if s.capcut_running():raise ValueError('CapCut reopened during apply; rolling back.')
                s.write_json(path,value)
        except Exception:
            for path,data in previous.items():path.write_bytes(data)
            raise
        for job in batch['jobs']:
            record=job_data(job);record['status']='applied';record['applied_at']=time.time();s.write_json(job_path(job)/'job.json',record)
            if record.get('zoom_job_id'):
                import zoom as z
                zr=z.data(sys.modules[__name__],record['zoom_job_id']);zr.update(status='applied',applied_at=time.time())
                s.write_json(z.folder(sys.modules[__name__],record['zoom_job_id'])/'job.json',zr)
            if record.get('hook_job_id'):
                import hooks
                hr=hooks.record(sys.modules[__name__],record['hook_job_id']);hr.update(status='applied',applied_at=time.time())
                s.write_json(hooks.path(sys.modules[__name__],record['hook_job_id'])/'job.json',hr)
    return {'installed':True,'targets':len(batch['jobs']),'saved_backups':False,'project_copies':False,'capcut_close':closure,
        'note':'All targets validated before serialized writes. RAM rollback handles errors; power loss is not transactionally recoverable without saved backups.'}

def revision_diff(predicted,manual,tolerance=.75):
    """Maximum-cardinality exact-sound matching; unmatched cues remain explicit."""
    edges={i:sorted([j for j,b in enumerate(manual) if a['sound']==b['sound'] and abs(a['start']-b['start'])<=tolerance],key=lambda j:abs(a['start']-manual[j]['start'])) for i,a in enumerate(predicted)}
    owner={}
    def visit(i,seen):
        for j in edges[i]:
            if j in seen:continue
            seen.add(j)
            if j not in owner or visit(owner[j],seen):owner[j]=i;return True
        return False
    for i in sorted(edges,key=lambda i:len(edges[i])):visit(i,set())
    pairs=[{'old':i,'manual':j,'delta':round(manual[j]['start']-predicted[i]['start'],3)} for j,i in owner.items()]
    used_old=set(owner.values());used_new=set(owner)
    strict=[pair for pair in pairs if abs(pair['delta'])<=.15]
    retimed=[pair for pair in pairs if abs(pair['delta'])>1/30+.000001]
    candidates=[{'old':i,'manual':j,'delta':round(b['start']-a['start'],3),'kind':'possible_retime' if a['sound']==b['sound'] else 'possible_substitution','requires_context_review':True}
        for i,a in enumerate(predicted) if i not in used_old for j,b in enumerate(manual) if j not in used_new and abs(a['start']-b['start'])<=3]
    return {'matches':pairs,'removed':[i for i in range(len(predicted)) if i not in used_old],'added':[j for j in range(len(manual)) if j not in used_new],
        'timing':{'strict_tolerance':.15,'strict_matches':strict,'strict_precision':len(strict)/len(predicted) if predicted else None,'strict_recall':len(strict)/len(manual) if manual else None,'retimed_matches':retimed,'median_abs_error':ra.statistics.median(abs(p['delta']) for p in pairs) if pairs else None},'review_candidates':candidates,
        'precision':len(pairs)/len(predicted) if predicted else None,'recall':len(pairs)/len(manual) if manual else None,'tolerance':tolerance,
        'interpretation':'One frozen video compared to manual placements. Not a future accuracy guarantee; deletion vs distant retiming can be ambiguous.'}

def _learn_sfx_revision(job_id:str,revision_project:str,revision_timeline:str,rule_updates:list[dict]|None=None):
    folder=job_path(job_id);record=job_data(job_id);source=s.read_json(folder/'source.json');plan=s.read_json(folder/'plan.json')
    project=s.project_path(revision_project);timeline,manual,path=s.load_timeline(project,revision_timeline);manual_hash=digest(path)
    mapping=ra.TimelineMap(source,manual)
    with lock('state'):
        evidence_id=stable_digest({'job':job_id,'hash':manual_hash});history=STATE/'history'/(evidence_id+'.json')
        active=s.read_json(STATE/'memory.json') if (STATE/'memory.json').exists() else {}
        if evidence_id in active.get('receipts',[]):return {'already_learned':True,'report':str(history),'version':s.read_json(s.DATA/'style_profile.json')['version']}
        sounds=s.read_json(s.DATA/'sound_catalog.json');segments=list(s.flatten_sfx(manual,sounds,project))
        old=[];trimmed=[]
        for e in plan['effects']:
            if not e.get('enabled',True):continue
            at=mapping.new_time(0,e['start'])
            if at is None:trimmed.append(e);continue
            old.append({**e,'start':at})
        truth=ra.logical_events(segments,envelope_references=old)
        diff=revision_diff(old,truth)
        brief=get_brief(job_id,True);profile=s.read_json(s.DATA/'style_profile.json');examples=s.read_json(s.DATA/'examples.json')
        signature=stable_digest(s.video_timing_signature(source))
        # Current manual truth supersedes earlier versions of this same video.
        # History retains the old observations; don't train a contradictory duplicate.
        examples=[e for e in examples if e.get('video_signature')!=signature]
        profile['learned_feedback']=[f for f in profile.get('learned_feedback',[]) if f.get('video_signature')!=signature]
        feedback=[]
        for i in diff['removed']:
            e=old[i];feedback.append({'decision':'omit_or_changed','sound':e['sound'],'cue':e['dialogue'],'context':s.context_at(brief['captions'],e['start']),
                'scope':'This video/scene only; nearby additions may be replacements or retimings. Do not infer a global ban.'})
        report_context=s.read_json(folder/'context_report.json') if (folder/'context_report.json').exists() else {}
        for e in truth:
            old_at=mapping.old_time(0,e['start']);speech=ra.word_context(report_context,0,old_at)
            pair=next((p for p in diff['matches'] if truth[p['manual']] is e),None)
            caption_context=s.context_at(brief['captions'],old_at)
            # Never inherit the label of a nearby different sound or a distant
            # prediction. Keep manual evidence separate from the model's guess.
            cue=old[pair['old']]['dialogue'] if pair and abs(pair['delta'])<=.15 else (speech or caption_context)
            if not cue:cue=s.context_at(s.caption_rows(manual),e['start'])
            feedback.append({'decision':'manual_choice','sound':e['sound'],'cue':cue,'start':round(e['start'],3),'duration':round(e['duration'],3),'volume':round(e['volume'],6),
                'gain_envelope':e['gain_envelope'],'gain_basis':'actual final effective gain with compound parents',
                'scope':'Observed example; exact intent requires both dialogue streams and visual context.',
                'caption_context':caption_context,'cue_source':'matched_same_sound_prediction' if pair and abs(pair['delta'])<=.15 else 'mapped_manual_source_context'})
            for role,stream in enumerate(brief.get('source_dialogue',[])):
                context=ra.word_context(report_context,role,mapping.old_time(role,e['start']))
                if context:feedback[-1].setdefault('dialogue_streams',{})[stream['role']]=context
            referenced=set(e['segment'].get('extra_material_refs',[]))
            fade=next((f for f in e['materials'].get('audio_fades',[]) if f.get('id') in referenced),{})
            e['fade_in']=fade.get('fade_in_duration',0)/s.MICRO;e['fade_out']=fade.get('fade_out_duration',0)/s.MICRO
            e['extras']={k:[copy.deepcopy(m) for m in arr if isinstance(m,dict) and m.get('id') in referenced] for k,arr in e.pop('materials').items() if isinstance(arr,list)}
            e['extras']={k:arr for k,arr in e['extras'].items() if arr}
            e.update(project=project.name,timeline=timeline['name'],anchor_text=cue,context_text=cue,feedback_source=evidence_id,
                video_signature=signature,manual_level_reference=True,source_timeline_id=timeline['id'])
            examples.append(e)
        updates=rule_updates or []
        for u in updates:
            if u.get('authority') not in ('explicit_user','scene_inference') or not u.get('rule') or not u.get('evidence') or not u.get('scope'):
                raise ValueError('Rule updates need rule, evidence, scope, and explicit_user/scene_inference authority.')
            if u['authority']=='scene_inference' and u['scope']!='scene_only':raise ValueError('One inferred example cannot establish a global rule.')
        if digest(path)!=manual_hash:raise ValueError('Revision changed while reading. Save then retry.')
        new_version=profile['version']+1
        for f in feedback:f.update(reference=evidence_id,learned_version=new_version,video_signature=signature)
        profile.setdefault('learned_feedback',[]).extend(feedback)
        profile.setdefault('revision_rules',[]).extend([{**u,'learned_version':new_version,'reference':evidence_id,'video_signature':signature} for u in updates])
        profile['version']=new_version
        profile.setdefault('dialogue_level_references',[])
        profile['dialogue_level_references']=[r for r in profile['dialogue_level_references'] if r['timeline_id']!=timeline['id']]
        profile['dialogue_level_references'].append({'project':project.name,'timeline':timeline['name'],'timeline_id':timeline['id'],
            'roles':[{'role':f'video_track_{i+1}','gain_spans':clips} for i,clips in enumerate(ra.level_spans(manual))],
            'policy':'Observed per-role gains; keep foreground/narrator balance distinct. Raw slider gains cannot be blindly generalized to another recording.'})
        profile['background_level_references']=[r for r in profile.get('background_level_references',[]) if r['timeline_id']!=timeline['id']]
        profile['background_level_references'].append({'project':project.name,'timeline':timeline['name'],'timeline_id':timeline['id'],
            'audio':ra.background_references(s,manual,sounds,project)})
        for e in truth:
            if 'fah' in e['sound'].lower() and e['sound'] not in profile['authoritative_user_rules']['comic_line']:
                profile['authoritative_user_rules']['comic_line'].append(e['sound'])
            if e['sound'] not in profile['preferred_sounds']:profile['preferred_sounds'].append(e['sound'])
        ra.update_levels(profile,examples)
        levels=[]
        for pair in diff['matches']:
            predicted=old[pair['old']];manual_e=truth[pair['manual']];installed=predicted['volume']*plan.get('master_gain',1)
            levels.append({'sound':predicted['sound'],'cue':predicted['dialogue'],'start':manual_e['start'],'installed_gain':installed,
                'manual_peak_gain':manual_e['volume'],'manual_energy_gain':manual_e['energy_gain'],
                'peak_gain_change_db':round(ra.db(manual_e['volume']/installed),2),'gain_parts':manual_e['gain_parts'],
                'old_duration':predicted['duration'],'manual_duration':manual_e['duration'],'fade_in':manual_e['fade_in'],'fade_out':manual_e['fade_out']})
        report={'job_id':job_id,'reference':evidence_id,'revision_project':project.name,'revision_timeline_id':timeline['id'],'revision_hash':manual_hash,
            'diff':diff,'old_cues':len(old),'manual_cues':len(truth),'native_sfx_pieces':len(segments),'trimmed_predictions':trimmed,
            'rule_updates':updates,'new_style_version':new_version,'saved_project_backup':False,'sound_level_changes':levels,
            'level_policy':'Compare installed old volume = planned volume times old master_gain. Learn revised effective gain including compound parents and attack/body envelope; do not treat the earlier master attenuation as a new user preference.'}
        # One durable memory bundle makes revision commits recoverable/idempotent.
        s.write_json(history,{'report':report,'previous_profile':s.read_json(s.DATA/'style_profile.json'),'new_profile':profile,'examples':examples})
        s.write_json(STATE/'memory.json',{'profile':profile,'examples':examples,'receipts':active.get('receipts',[])+[evidence_id]})
        s.write_json(s.DATA/'style_profile.json',profile);s.write_json(s.DATA/'examples.json',examples)
    return report

def learn_revision(job_id:str,revision_project:str,revision_timeline:str,rule_updates:list[dict]|None=None):
    result=_learn_sfx_revision(job_id,revision_project,revision_timeline,rule_updates)
    linked=job_data(job_id).get('zoom_job_id')
    if linked:
        import zoom
        record=zoom.data(sys.modules[__name__],linked)
        project=s.project_path(revision_project);timeline,_,_=s.load_timeline(project,revision_timeline)
        if (record['project'],record['timeline_id'])!=(project.name,timeline['id']):
            raise ValueError('Linked zoom revision is a different timeline; use learn_zoom_revision for the applied tab.')
        result['zoom_revision']=learn_zoom_revision(linked)
    hook=job_data(job_id).get('hook_job_id')
    if hook:result['hook_revision']=learn_hook_revision(hook)
    return result


def memory():
    with lock('state'):profile=s.read_json(s.DATA/'style_profile.json')
    return pack(profile)


def learn_zoom_style(references:list[dict]):
    import zoom
    return zoom.learn_style(sys.modules[__name__],references)

def prepare_zoom_batch(targets:list[dict]):
    import zoom
    return zoom.prepare(sys.modules[__name__],targets)

def get_zoom_briefs(batch_id:str):
    import zoom
    return zoom.briefs(sys.modules[__name__],batch_id)

def get_zoom_context(job_id:str,start:float,end:float):
    import zoom
    return zoom.context(sys.modules[__name__],job_id,start,end)

def stage_zoom_plan(job_id:str,zooms:list[dict],quality_notes:dict):
    import zoom
    return zoom.stage(sys.modules[__name__],job_id,zooms,quality_notes)

def preview_zoom_plan(job_id:str):
    import zoom
    return zoom.preview(sys.modules[__name__],job_id)

def apply_zoom_batch(batch_id:str,auto_close:bool=True):
    import zoom
    return zoom.apply_batch(sys.modules[__name__],batch_id,auto_close)

def learn_zoom_revision(job_id:str):
    import zoom
    return zoom.learn_revision(sys.modules[__name__],job_id)

def prepare_edit_batch(targets:list[dict],mode:str='full_combo',workers:int=2):
    import edit_modes
    return edit_modes.prepare(sys.modules[__name__],targets,mode,workers)
def get_edit_briefs(batch_id:str):
    import edit_modes
    return edit_modes.briefs(sys.modules[__name__],batch_id)
def apply_edit_batch(batch_id:str,auto_close:bool=True):
    import edit_modes
    return edit_modes.apply(sys.modules[__name__],batch_id,auto_close)
def learn_hook_style(references:list[dict],preferred_timeline:str|None=None):
    import hooks
    return hooks.learn_style(sys.modules[__name__],references,preferred_timeline)
def stage_hook_plan(job_id:str,hook:dict,quality_notes:dict):
    import hooks
    return hooks.stage(sys.modules[__name__],job_id,hook,quality_notes)
def preview_hook_plan(job_id:str):
    import hooks
    return hooks.preview(sys.modules[__name__],job_id)
def learn_hook_revision(job_id:str):
    import hooks
    return hooks.learn_revision(sys.modules[__name__],job_id)
def analysis_cache_status():
    import analysis_cache
    return analysis_cache.info(sys.modules[__name__])
def learn_edit_revision(batch_id:str):
    import edit_modes
    return edit_modes.learn(sys.modules[__name__],batch_id)

initialize()
