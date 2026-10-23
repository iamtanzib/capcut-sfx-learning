"""Ranking videos: ranked clip -> Kevin reaction cuts with B&W tail replays, learned from rendered references.
The host chooses item/reaction boundaries; this module measures, validates, previews and writes native CapCut segments."""
from __future__ import annotations
import copy,hashlib,json,math,re,shutil,statistics,subprocess,time,uuid,wave
from pathlib import Path

FPS=30;MICRO=1_000_000
FAMILIES={'shocked-sound-effect.mp3':'vine boom','vine-boom (20).mp3':'vine boom','fahhhh.mp3':'fah','faaah (7).mp3':'fah','fahhhhhhhhhhhhhh.mp3':'fah',
    'fahhh_KcgAXfs.mp3':'fah','53b1bab6-a8c3-4a1a-82db-7110ce1c29ef_6KNDGWD.mp3':'among us','among-us-role-reveal-sound.mp3':'among us',
    'anime-wow-sound-effect.mp3':'anime wow','wow-anime-voice-accent.mp3':'anime wow','core-sound-effect.mp3':'whoosh'}
# Preferred file per family when a reference match is ambiguous (same audio, several library copies).
CANONICAL={'vine boom':'vine-boom (20).mp3','fah':'fahhhh.mp3','among us':'among-us-role-reveal-sound.mp3','anime wow':'anime-wow-sound-effect.mp3','whoosh':'core-sound-effect.mp3'}
WHOOSH='core-sound-effect.mp3'
# Template media/extra materials safe to clone into a clean cut; transitions/animations stay the user's choice.
CLONE_KINDS=('speeds','placeholder_infos','canvases','sound_channel_mappings','vocal_separations','material_colors','beats')
RULES=[
    'Open directly on ranked item #1 of the source (its baked title and rank list are the hook). Never use Kevin\'s slate ("one of the ranking videos...", "best sea lion moments").',
    'Strictly alternate: ranked item -> Kevin\'s reaction to that item -> next item. Every reference ends on Kevin\'s reaction to the final item.',
    'Items play in source order, each from its first frame through its payoff and rank-label/price reveal; trim only dead frames. Never cut the payoff or the source\'s own punch SFX.',
    'Kevin records the reactions in item order in one take. Map each reaction to the item it talks about by content, not by counting pauses.',
    'Reactions are tight jump cuts: start on the first word, end right after the last word, no dead air. Drop slates, retakes, stumbles and repeated lines.',
    'B&W replay: when a reaction runs long and Kevin points back at the clip ("that", "them", "in there", "like that", naming the object/event), cover the later part of the reaction with the LAST part of that same item replayed in black and white at 1x, zoomed about 1.1x, muted; Kevin\'s voice continues underneath.',
    'Show Kevin\'s face first (at least about 1s, median 1.6s) before the B&W. The B&W lasts about 0.9-2.1s (median 1.4s) and usually runs to the cut into the next item; sometimes the face returns for a short final exclamation ("Oh my god").',
    'Each reference used B&W on 4 of 6 reactions. Opinion/hypothetical reactions and usually the final reaction stay on Kevin\'s face. The count is calibration, not a quota.',
    'SFX go on Kevin only: 1-3 per reaction, first usually 0.7-1.5s in on the punch word. Error is the most common (disbelief), FAH often lands right at the B&W start, plus vine boom, among us, mac-quack, ceeday-huh, undertaker bell, rizz, movie_1.',
    'Ranked items already carry the source creator\'s SFX (vine boom, ding, correct, roblox death). Never add SFX over item clips.',
    'Transition whoosh: core-sound-effect.mp3 starts about 0.33s before every reaction -> next-item cut (20/20 in references); none at item -> reaction cuts.',
    'The user adds CapCut transitions, music and captions. Keep all cuts on the main track so default transitions can be placed between them.',
    'Kevin sits about 4-5 dB above the item clips in the references.',
    'Srijon revisions (2026-10-22, 4 videos): item starts about 3 frames later (skips the source whip-blur), reaction starts 0.1-0.27s later (drops lead-ins like "Oh", "Yeah,"), ends kept, all 14 B&W replays kept.']
DEFAULTS={'kevin_volume':.63,'ranking_volume':.5,'bw_zoom':1.1,'bw_face_first':.6,'gap_split':.45,'whoosh_lead':.33,'start_pad':.04,'end_pad':.06}

def folder(api,job):return api.STATE/'ranking_jobs'/api.safe_id(job)
def record(api,job):return api.s.read_json(folder(api,job)/'job.json')
def batch_record(api,batch):return api.s.read_json(api.STATE/'ranking_batches'/(api.safe_id(batch)+'.json'))
def style_path(api):return api.STATE/'data'/'ranking_style.json'
def registry_path(api):return api.STATE/'data'/'ranking_registry.json'
def style(api):
    path=style_path(api)
    if not path.exists():
        seed=api.ROOT/'seed'/'ranking_style.json'
        if not seed.exists():raise ValueError('Learn the ranking style from rendered references first (learn_ranking_style).')
        api.s.write_json(path,api.s.read_json(seed))
    return api.s.read_json(path)

def tool(name):
    found=shutil.which(name) or str(Path.home()/'.local/bin'/name)
    if not Path(found).is_file():raise ValueError(f'{name} is required.')
    return found
def ff(args,timeout=900):
    proc=subprocess.run([tool('ffmpeg'),'-nostdin','-v','error',*args],stdin=subprocess.DEVNULL,capture_output=True,timeout=timeout)
    if proc.returncode:raise ValueError(proc.stderr.decode(errors='replace')[-800:])
    return proc.stdout
def probe(path):
    proc=subprocess.run([tool('ffprobe'),'-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True,text=True,timeout=60)
    info=json.loads(proc.stdout or '{}');video=next((x for x in info.get('streams',[]) if x.get('codec_type')=='video'),None)
    if proc.returncode or not video:raise ValueError(f'No readable video stream: {path}')
    w,h=int(video['width']),int(video['height']);rotation=int(float((video.get('tags') or {}).get('rotate',0) or 0))
    for side in video.get('side_data_list',[]):
        if 'rotation' in side:rotation=int(float(side['rotation']))
    if abs(rotation)%180==90:w,h=h,w
    num,den=(video.get('avg_frame_rate') or '30/1').split('/');stat=Path(path).stat()
    return {'path':str(path),'duration':float(info['format']['duration']),'width':w,'height':h,'fps':round(float(num)/float(den),3) if float(den) else 30.0,
        'has_audio':any(x.get('codec_type')=='audio' for x in info['streams']),'size':stat.st_size,'mtime':stat.st_mtime_ns}
def frames(path,fps,w,h,start=None,duration=None):
    import numpy as np
    pre=['-ss',f'{start:.3f}'] if start is not None else [];post=['-t',f'{duration:.3f}'] if duration is not None else []
    raw=ff([*pre,'-i',str(path),*post,'-an','-vf',f'fps={fps},scale={w}:{h}','-f','rawvideo','-pix_fmt','bgr24','-'])
    return np.frombuffer(raw,np.uint8).reshape(-1,h,w,3)
def pcm(path,rate=16000):
    import numpy as np
    return np.frombuffer(ff(['-i',str(path),'-vn','-ac','1','-ar',str(rate),'-f','f32le','-']),'<f4').astype(np.float64)
def scene_cuts(path,threshold=.25):
    proc=subprocess.run([tool('ffmpeg'),'-nostdin','-hide_banner','-i',str(path),'-an','-vf',f"scale=270:480,select='gt(scene,{threshold})',showinfo",'-f','null','-'],
        stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=900)
    return [round(float(x),3) for x in re.findall(r'pts_time:([0-9.]+)',proc.stderr)]
def snap(t):return round(t*FPS)
def us(frame):return round(frame*MICRO/FPS)

def transcribe(api,path,work):
    """Kevin's raw take, words with global indices; cached per job folder."""
    import numpy as np
    import context_pipeline as c
    wav=work/'kevin.wav'
    if not wav.exists():
        audio=pcm(path)
        with wave.open(str(wav),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000);out.writeframes((np.clip(audio,-1,1)*32767).astype('<i2').tobytes())
    report=c.transcribe(wav,api.s.config()['speech_model'],lambda _:None)
    words=[{'i':0,'start':w['start'],'end':w['end'],'text':w['text']} for row in report['rows'] for w in row['words'] if w['text'].strip()]
    for i,w in enumerate(words):w['i']=i
    return words
def envelope(path):
    """10 ms RMS in dBFS of a 16 kHz mono WAV."""
    import numpy as np
    with wave.open(str(path),'rb') as f:a=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(np.float64)/32768
    n=len(a)//160;frame=a[:n*160].reshape(n,160)
    return 20*np.log10(np.sqrt((frame**2).mean(1))+1e-9)

def catalog(api):
    path=api.s.DATA/'sound_catalog.json'
    return api.s.read_json(path) if path.exists() else api.s.scan_library(progress=lambda _:None)
def library_hits(api,signal,rate=8000,threshold=.55):
    """Normalized cross-correlation of each short library sound against a mix; gain is the matched amplitude scale."""
    import numpy as np
    from numpy.fft import rfft,irfft
    x=signal-signal.mean();n=len(x);hits=[]
    cs=np.concatenate([[0],np.cumsum(x*x)])
    for sound in catalog(api):
        if sound.get('role')!='sfx' or sound['duration']>6:continue
        a=pcm(sound['path'],rate);w=int(rate*.35)
        if len(a)<rate*.15:continue
        offset=0
        if len(a)>w:energy=np.convolve(a*a,np.ones(w),'valid');offset=int(np.argmax(energy));a=a[offset:offset+w]
        t=a-a.mean();norm=float(np.linalg.norm(t))
        if norm<1e-3 or len(t)>=n:continue
        size=1<<int(math.ceil(math.log2(n+len(t))));c=irfft(rfft(x,size)*np.conj(rfft(t,size)),size)[:n-len(t)+1]
        ncc=c/(np.sqrt(np.maximum(cs[len(t):]-cs[:-len(t)],1e-12))*norm)
        taken=[]
        for i in np.argsort(ncc)[::-1][:400]:
            if ncc[i]<threshold:break
            if all(abs(i-j)>rate*.5 for j in taken):taken.append(int(i))
        for i in taken:hits.append({'sound':sound['name'],'family':FAMILIES.get(sound['name'],sound['name']),'start':round(i/rate-offset/rate,3),
            'score':round(float(ncc[i]),3),'gain':round(float(c[i]/(norm*norm)),4)})
    best=[]
    for h in sorted(hits,key=lambda h:-h['score']):
        if h['start']<-.05 or any(abs(h['start']-b['start'])<.45 and h['family']==b['family'] for b in best):continue
        if h['family'] in CANONICAL:
            same=[o for o in hits if o['family']==h['family'] and abs(o['start']-h['start'])<.45]
            canon=next((o for o in same if o['sound']==CANONICAL[h['family']] and o['score']>=h['score']-.08),None)
            h=dict(canon or h)
        best.append(h)
    return sorted(best,key=lambda h:h['start'])

def classify(frame):
    """B = desaturated replay (a zoomed one may crop the title band), K = Kevin (no dark title band), R = colour ranking clip."""
    import numpy as np,cv2
    h=frame.shape[0];hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
    if float(np.median(hsv[int(h*.2):int(h*.88),:,1]))<25:return 'B'
    return 'K' if float(np.median(hsv[int(h*.01):int(h*.09),:,2]))>70 else 'R'
def runs(labels,step):
    out=[]
    for i,l in enumerate(labels):
        if out and out[-1][0]==l:out[-1][2]=i+1
        else:out.append([l,i,i+1])
    clean=[]
    for r in out:
        if r[2]-r[1]<3 and clean:clean[-1][2]=r[2]
        elif clean and clean[-1][0]==r[0]:clean[-1][2]=r[2]
        else:clean.append(r)
    return [[l,round(a*step,2),round(b*step,2)] for l,a,b in clean]
def replay_match(gray,bw_index,candidates):
    """Best colour frame for a B&W frame, with zoom (B&W is a zoomed copy). Returns (score, frame index, zoom)."""
    import numpy as np,cv2
    g=gray[bw_index];H,W=g.shape;ch,cw=int(H*.45),int(W*.6);y,x=(H-ch)//2+H//20,(W-cw)//2;crop=g[y:y+ch,x:x+cw];best=(-1.0,None,1.0)
    for z in np.arange(1.0,1.61,.05):
        tpl=cv2.resize(crop,(int(cw/z),int(ch/z)))
        for j in candidates:
            score=float(cv2.matchTemplate(gray[j],tpl,cv2.TM_CCOEFF_NORMED).max())
            if score>best[0]:best=(score,j,round(float(z),2))
    return best

def analyze_reference(api,path,work):
    import numpy as np,cv2
    step=.1;F=frames(path,10,216,384);gray=[cv2.cvtColor(f,cv2.COLOR_BGR2GRAY) for f in F];labels=[classify(f) for f in F]
    segments=runs(labels,step)
    # A grey colour scene is not a replay: a B&W replay follows Kevin's face and matches the preceding item.
    for _ in range(3):
        changed=False
        for k,(l,a,b) in enumerate(segments):
            if l!='B':continue
            prev=next((s for s in reversed(segments[:k]) if s[0]=='R'),None)
            score=-1 if prev is None or k==0 or segments[k-1][0]!='K' else replay_match(gray,int((a+b)/2/step),range(int(prev[1]/step),int(prev[2]/step)))[0]
            if score<.6:
                for i in range(int(a/step),int(b/step)):labels[i]='R'
                changed=True
        if not changed:break
        segments=runs(labels,step)
    words=[]
    report=api.s.read_json(work/'asr.json') if (work/'asr.json').exists() else None
    if report is None:
        import context_pipeline as c
        audio=pcm(path)
        with wave.open(str(work/'audio.wav'),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000);out.writeframes((np.clip(audio,-1,1)*32767).astype('<i2').tobytes())
        report=c.transcribe(work/'audio.wav',api.s.config()['speech_model'],lambda _:None);api.s.write_json(work/'asr.json',report)
    words=[{'start':w['start'],'end':w['end'],'text':w['text']} for r in report['rows'] for w in r['words']]
    duration=len(F)*step;hits=library_hits(api,pcm(path,8000));api.s.write_json(work/'hits.json',hits)
    items=[s for s in segments if s[0]=='R'];reactions=[]
    for i,item in enumerate(items):
        end=items[i+1][1] if i+1<len(items) else duration
        span=[s for s in segments if item[2]-.01<=s[1] and s[2]<=end+.01 and s[0]!='R'];start=item[2]
        bw=next((s for s in span if s[0]=='B'),None);entry={'item':i,'start':start,'end':round(end,2),'duration':round(end-start,2),
            'words':' '.join(w['text'] for w in words if start-.1<=w['start']<end),
            'first_word_offset':next((round(w['start']-start,2) for w in words if w['start']>=start-.8),None)}
        if bw:
            mid=replay_match(gray,int((bw[1]+bw[2])/2/step),range(int(item[1]/step),int(item[2]/step)))
            last=replay_match(gray,max(int(bw[1]/step),int(bw[2]/step)-2),range(int(item[1]/step),int(item[2]/step)))
            entry['bw']={'start':bw[1],'end':bw[2],'duration':round(bw[2]-bw[1],2),'face_before':round(bw[1]-start,2),
                'position':'end' if bw[2]>=end-.15 else 'middle','zoom':mid[2],'match_score':round(mid[0],2),
                'source_end_offset_from_item_end':round((last[1] or 0)*step+.2-item[2],2),'words':' '.join(w['text'] for w in words if bw[1]-.05<=w['start']<bw[2])}
        entry['sfx']=[{**h,'offset':round(h['start']-start,2),'bw_offset':round(h['start']-bw[1],2) if bw else None,
            'near_word':min(words,key=lambda w:abs(w['start']-h['start']))['text'] if words else ''} for h in hits if start-.1<=h['start']<end-.45 and h['family']!='whoosh']
        reactions.append(entry)
    whoosh=[{'start':h['start'],'cut':nxt[1],'offset':round(h['start']-nxt[1],2)} for h in hits if h['family']=='whoosh' for nxt in items[1:] if abs(h['start']-nxt[1])<.9]
    signal=pcm(path)
    def level(kind):
        parts=[signal[int((s[1]+.3)*16000):int((s[2]-.3)*16000)] for s in segments if s[0]==kind and s[2]-s[1]>.8]
        return round(float(np.median([20*np.log10(np.sqrt(np.mean(p**2))+1e-9) for p in parts])),1) if parts else None
    stat=Path(path).stat()
    return {'name':Path(path).name,'path':str(path),'size':stat.st_size,'duration':round(duration,2),'segments':segments,
        'items':[{'start':s[1],'end':s[2],'duration':round(s[2]-s[1],2)} for s in items],'reactions':reactions,'whoosh':whoosh,
        'item_sfx':[h for h in hits if any(s[1]<=h['start']<s[2]-.45 for s in items) and h['family']!='whoosh'],
        'levels_db':{'item':level('R'),'kevin':level('K'),'bw':level('B')}}

def statistics_for(refs):
    med=lambda v:round(statistics.median(v),2) if v else None
    reactions=[r for ref in refs for r in ref['reactions']];bws=[r['bw'] for r in reactions if r.get('bw')]
    sfx=[x for r in reactions for x in r['sfx']];families={}
    for x in sfx:families[x['family']]=families.get(x['family'],0)+1
    return {'videos':len(refs),'items_per_video':[len(r['items']) for r in refs],'item_seconds':{'median':med([i['duration'] for r in refs for i in r['items']]),
            'min':min((i['duration'] for r in refs for i in r['items']),default=None),'max':max((i['duration'] for r in refs for i in r['items']),default=None)},
        'reaction_seconds':{'median':med([r['duration'] for r in reactions]),'min':min((r['duration'] for r in reactions),default=None),'max':max((r['duration'] for r in reactions),default=None)},
        'bw_per_video':[sum(bool(x.get('bw')) for x in r['reactions']) for r in refs],'bw_seconds':{'median':med([b['duration'] for b in bws]),'min':min((b['duration'] for b in bws),default=None),'max':max((b['duration'] for b in bws),default=None)},
        'face_before_bw':{'median':med([b['face_before'] for b in bws]),'min':min((b['face_before'] for b in bws),default=None)},
        'bw_zoom_median':med([b['zoom'] for b in bws]),'bw_position':{p:sum(b['position']==p for b in bws) for p in ('end','middle')},
        'bw_source_end_offset_median':med([b['source_end_offset_from_item_end'] for b in bws]),
        'final_reaction_has_bw':[bool(r['reactions'][-1].get('bw')) for r in refs if r['reactions']],
        'kevin_sfx_per_reaction':med([len(r['sfx']) for r in reactions]),'kevin_sfx_families':dict(sorted(families.items(),key=lambda kv:-kv[1])),
        'first_sfx_offset_median':med([r['sfx'][0]['offset'] for r in reactions if r['sfx']]),
        'fah_offset_from_bw_start':[x['bw_offset'] for x in sfx if x['family']=='fah' and x['bw_offset'] is not None],
        'whoosh':{'cuts':sum(len(r['items'])-1 for r in refs),'with_whoosh':sum(len(r['whoosh']) for r in refs),'lead_median':med([-w['offset'] for r in refs for w in r['whoosh']])},
        'level_gap_db_kevin_minus_item':med([r['levels_db']['kevin']-r['levels_db']['item'] for r in refs if r['levels_db']['kevin'] is not None and r['levels_db']['item'] is not None]),
        'first_word_offset_median':med([r['first_word_offset'] for r in reactions if r['first_word_offset'] is not None])}

def add_sound_templates(api,refs):
    """Sounds used by the references but never placed manually get a native audio template so stage_plan can install them."""
    with api.lock('state'):
        active=api.s.read_json(api.STATE/'memory.json') if (api.STATE/'memory.json').exists() else None
        examples=active['examples'] if active else api.s.read_json(api.s.DATA/'examples.json')
        known={e['sound'] for e in examples};sounds={x['name']:x for x in catalog(api)};added=[]
        base=next((e for e in examples if e['sound']=='vine-boom (20).mp3'),examples[0] if examples else None)
        if base is None:return []
        # Calibrate matched amplitude to slider gain with sounds that do have manual levels.
        observed=[(x['sound'],x['gain']) for r in refs for rx in r['reactions'] for x in rx['sfx']]+[(WHOOSH,h['gain']) for r in refs for h in api.s.read_json(Path(r['work'])/'hits.json') if h['family']=='whoosh']
        ratios=[]
        for name,gain in observed:
            manual=[e['volume'] for e in examples if e['sound']==name]
            if manual and gain>0:ratios.append(statistics.median(manual)/gain)
        factor=statistics.median(ratios) if ratios else 1.0
        for name in sorted({n for n,_ in observed}-known):
            if name not in sounds:continue
            gains=[g for n,g in observed if n==name and g>0];volume=round(min(1.0,max(.05,statistics.median(gains)*factor)),4) if gains else base['volume']
            e=copy.deepcopy(base);e.update(sound=name,path='',start=0.0,duration=round(sounds[name]['duration'],3),source_start=0.0,speed=1.0,volume=volume,compound=[],
                timeline='ranking references',project='ranking_reference_audio_match',caption_timing_source='',context='rendered ranking reference (audio-matched, no CapCut segment)',
                anchor_text='',anchor_edge='start',anchor_offset=0.0,video_signature='ranking-reference-template',template_only=True)
            examples.append(e);added.append({'sound':name,'volume':volume})
        if added:
            if active is not None:active['examples']=examples;active['receipts']=active.get('receipts',[])+['ranking-templates-'+time.strftime('%Y%m%d%H%M%S')];api.s.write_json(api.STATE/'memory.json',active)
            api.s.write_json(api.s.DATA/'examples.json',examples)
        return added

def learn_style(api,references):
    """Analyse 1-8 rendered ranking videos; store structure, B&W replay, SFX and level evidence plus the rules."""
    if not 1<=len(references)<=8:raise ValueError('Give one to eight rendered ranking reference videos.')
    api.initialize();refs=[]
    for path in references:
        p=Path(path)
        if not p.is_file():raise ValueError(f'Missing reference: {path}')
        work=api.STATE/'ranking_references'/hashlib.sha256(f'{p}:{p.stat().st_size}:{p.stat().st_mtime_ns}'.encode()).hexdigest()[:16];work.mkdir(parents=True,exist_ok=True)
        cached=work/'analysis.json'
        ref=api.s.read_json(cached) if cached.exists() else analyze_reference(api,p,work)
        if not (work/'hits.json').exists():api.s.write_json(work/'hits.json',library_hits(api,pcm(p,8000)))
        ref['work']=str(work);api.s.write_json(cached,ref);refs.append(ref)
    previous=api.s.read_json(style_path(api)) if style_path(api).exists() else {}
    value={'version':previous.get('version',0)+1,'type':'ranking_video','updated_at':time.time(),'rules':RULES,'defaults':{**DEFAULTS,**previous.get('defaults',{})},
        'stats':statistics_for(refs),'references':[{k:v for k,v in r.items() if k!='work'} for r in refs],
        'revisions':previous.get('revisions',[]),'learned_adjustments':previous.get('learned_adjustments',{})}
    stats=value['stats']
    if stats['bw_zoom_median']:value['defaults']['bw_zoom']=stats['bw_zoom_median']
    if stats['whoosh']['lead_median']:value['defaults']['whoosh_lead']=stats['whoosh']['lead_median']
    added=add_sound_templates(api,refs)
    with api.lock('ranking-style'):api.s.write_json(style_path(api),value)
    seed=api.ROOT/'seed'/'ranking_style.json'
    try:api.s.write_json(seed,value)
    except OSError:pass
    return {'version':value['version'],'references':len(refs),'stats':stats,'sound_templates_added':added,'rules':len(RULES)}

def content_signature(api,project,draft):
    """What the user can see/hear: track segments (media, ranges, volume, framing) and text. CapCut's exit save rewrites trivial
    material fields, so a whole-file hash would block a plan made while CapCut was open; real edits still change this."""
    mats={m['id']:m for arr in draft.get('materials',{}).values() if isinstance(arr,list) for m in arr if isinstance(m,dict) and 'id' in m}
    rows=[]
    for t in draft.get('tracks',[]):
        segs=[]
        for s in sorted(t.get('segments',[]),key=lambda x:x['target_timerange']['start']):
            m=mats.get(s.get('material_id'),{})
            segs.append([str(api.s.resolve_path(m['path'],project)) if m.get('path') else m.get('content') or m.get('type'),s['target_timerange'],s.get('source_timerange'),
                round(float(s.get('volume',1)),4),s.get('visible',True),(s.get('clip') or {}).get('scale'),(s.get('clip') or {}).get('transform')])
        rows.append([t.get('type'),segs])
    return api.stable_digest({'duration':draft.get('duration'),'tracks':rows})

def source_kind(path):
    """Ranking sources carry a dark baked title band; Kevin's raw takes do not."""
    import numpy as np
    sample=frames(path,1,216,384,duration=6)
    return 'ranking' if np.mean([classify(f)!='K' for f in sample])>.5 else 'kevin'
def video_paths(api,project,draft):
    mats={m['id']:m for m in draft['materials'].get('videos',[])};paths=[]
    for t in draft.get('tracks',[]):
        if t.get('type')!='video':continue
        for seg in t.get('segments',[]):
            m=mats.get(seg['material_id'])
            if m and m.get('path'):
                p=str(api.s.resolve_path(m['path'],project))
                if p not in paths:paths.append(p)
    return paths
def find_template(api,project,draft,path):
    """A native segment + material + extras to clone: this timeline first, then the project's other timelines."""
    def scan(d,same):
        mats={m['id']:m for m in d['materials'].get('videos',[])}
        index={m['id']:(k,m) for k,arr in d['materials'].items() if isinstance(arr,list) for m in arr if isinstance(m,dict) and 'id' in m}
        found=None
        for t in d.get('tracks',[]):
            if t.get('type')!='video':continue
            for seg in t.get('segments',[]):
                m=mats.get(seg['material_id'])
                if not m:continue
                extras={}
                for ref in seg.get('extra_material_refs',[]):
                    kind,mat=index.get(ref,(None,None))
                    if kind in CLONE_KINDS:extras.setdefault(kind,[]).append(mat)
                entry={'segment':seg,'material':m,'extras':extras,'same_timeline':same,'same_media':str(api.s.resolve_path(m.get('path',''),project))==str(path)}
                if entry['same_media']:return entry
                found=found or entry
        return found
    best=scan(draft,True)
    if best and best['same_media']:return best
    for t in api.s.timelines(project):
        folder=Path(project)/'Timelines'/t['id']
        if not folder.exists():continue
        other=scan(api.s.read_json(api.s.draft_file(folder)),False)
        if other and other['same_media']:return other
        best=best or other
    if best is None:raise ValueError('No native video segment in this project to clone. Drop both raw files into the timeline once, save, then prepare again.')
    return best

def contact_sheets(path,info,work,prefix,fps=2,cols=10,rows=4):
    import numpy as np,cv2
    F=frames(path,fps,144,256);out=[];per=cols*rows
    for k in range(0,len(F),per):
        sheet=np.zeros((rows*256,cols*144,3),np.uint8)
        for j,f in enumerate(F[k:k+per]):
            f=f.copy();cv2.rectangle(f,(0,0),(70,18),(0,0,0),-1);cv2.putText(f,f'{(k+j)/fps:.1f}s',(3,14),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,255,255),1,cv2.LINE_AA)
            sheet[(j//cols)*256:(j//cols+1)*256,(j%cols)*144:(j%cols+1)*144]=f
        name=work/f'{prefix}_sheet_{len(out)+1}.jpg';cv2.imwrite(str(name),sheet,[cv2.IMWRITE_JPEG_QUALITY,82]);out.append(str(name))
    return out
def label_onsets(path):
    """Rank-list labels persist to the end once shown: report when new persistent white text appears on the left side."""
    import numpy as np,cv2
    F=frames(path,5,270,480);hsv=np.stack([cv2.cvtColor(f,cv2.COLOR_BGR2HSV) for f in F])[:,70:400,0:125]
    white=(hsv[...,2]>215)&(hsv[...,1]<50);T=len(white);notwhite=~white
    last=np.where(notwhite.any(0),T-np.argmax(notwhite[::-1],0),0);onset=last[white[-1]]
    counts=np.convolve(np.bincount(onset,minlength=T),[1,1,1],'same');peaks=[]
    for i in np.argsort(counts)[::-1]:
        if counts[i]<30:break
        if all(abs(i-j)>3 for j,_ in peaks):peaks.append((int(i),int(counts[i])))
    return [{'at':round(i/5,2),'pixels':c} for i,c in sorted(peaks)]

def analyze_job(api,job):
    rec=record(api,job);work=folder(api,job)
    import numpy as np
    words=transcribe(api,rec['kevin']['path'],work);env=envelope(work/'kevin.wav');np.save(work/'kevin_rms.npy',env)
    phrases=[]
    for w in words:
        if phrases and w['start']-words[w['i']-1]['end']<.6:phrases[-1].update(to_word=w['i'],end=w['end'],text=phrases[-1]['text']+' '+w['text'])
        else:phrases.append({'from_word':w['i'],'to_word':w['i'],'start':w['start'],'end':w['end'],'gap_before':round(w['start']-words[w['i']-1]['end'],2) if w['i'] else round(w['start'],2),'text':w['text']})
    ranking=rec['ranking']['path'];cuts=scene_cuts(ranking);onsets=label_onsets(ranking)
    builtin=library_hits(api,pcm(ranking,8000),threshold=.6);sheets=contact_sheets(ranking,rec['ranking'],work,'ranking')
    starts=[0.0]
    for o in onsets:
        # The list often re-lays out during the intro; no first item is that short.
        if o['at']<2.0:continue
        near=[c for c in cuts if o['at']-1.5<=c<=o['at']+.3];start=max(near) if near else o['at']
        if start-starts[-1]>1.0:starts.append(start)
    items=[{'start':round(a,3),'end':round(b,3)} for a,b in zip(starts,starts[1:]+[rec['ranking']['duration']])]
    slate=re.compile(r'\b(ranking|moments|part|video|one of the)\b',re.I)
    usable=[p for k,p in enumerate(phrases) if not (k==0 and p['start']<4 and slate.search(p['text']))]
    groups=[]
    if usable and items:
        gaps=sorted(range(1,len(usable)),key=lambda k:-usable[k]['gap_before'])[:len(items)-1];bounds=[0]+sorted(gaps)+[len(usable)]
        groups=[{'from_word':usable[a]['from_word'],'to_word':usable[b-1]['to_word'],'text':' '.join(p['text'] for p in usable[a:b])} for a,b in zip(bounds,bounds[1:]) if b>a]
    st=style(api)
    brief={'job_id':job,'project':rec['project'],'timeline':rec['timeline'],'timeline_id':rec['timeline_id'],'kevin':rec['kevin'],'ranking':rec['ranking'],
        'kevin_words':{'$columns':['i','start','end','text'],'$rows':[[w['i'],w['start'],w['end'],w['text']] for w in words]},'kevin_phrases':phrases,
        'ranking_analysis':{'scene_cuts':cuts,'label_onsets':onsets,'builtin_sfx':[{k:h[k] for k in ('sound','start','score')} for h in builtin],'contact_sheets':sheets,'sheet_fps':2},
        'proposal':{'note':'Automatic draft only. Verify every item boundary on frames and every reaction mapping by content.','items':items,'reactions':groups},
        'style':{'version':st['version'],'rules':st['rules'],'defaults':st['defaults'],'stats':st['stats'],'learned_adjustments':st.get('learned_adjustments',{}),
            'recent_revisions':st.get('revisions',[])[-6:],'reference_reactions':[{'video':r['name'],'reactions':[{'words':x['words'],'duration':x['duration'],
                'bw':{k:x['bw'][k] for k in ('face_before','duration','position','words')} if x.get('bw') else None,
                'sfx':[[s['sound'],s['offset'],s['near_word']] for s in x['sfx']]} for x in r['reactions']]} for r in st['references']]},
        'plan_schema':'stage_ranking_plan(job_id, items=[{start,end,rank,label,reason}], reactions=[{item,about,pieces:[{from_word,to_word}],tighten?,bw?:{at_word,duration|until_end,tail_end?,zoom?,reason}}], quality_notes, volumes?). See references/ranking.md.'}
    api.s.write_json(work/'words.json',words);api.s.write_json(work/'brief.json',brief)
    rec.update(status='ready',prepared_at=time.time());api.s.write_json(work/'job.json',rec)
    return rec

def prepare(api,targets):
    api.initialize()
    if not 1<=len(targets)<=5:raise ValueError('Choose one to five project/timeline pairs.')
    st=style(api);batch=api.ident();jobs=[];seen=set()
    for target in targets:
        project=api.s.project_path(target['project']);tl,draft,path=api.s.load_timeline(project,target['timeline'])
        if (str(project),tl['id']) in seen:raise ValueError('Duplicate target in batch.')
        seen.add((str(project),tl['id']))
        sounds=api.s.read_json(api.s.DATA/'sound_catalog.json') if (api.s.DATA/'sound_catalog.json').exists() else []
        if list(api.s.flatten_sfx(draft,sounds,project)):raise ValueError(f'{tl["name"]} already holds SFX; ranking cuts need a raw or empty timeline.')
        present=video_paths(api,project,draft);explicit=[target.get('kevin'),target.get('ranking')]
        if all(explicit):kevin,ranking=map(str,explicit)
        else:
            if len(present)!=2:raise ValueError(f'{tl["name"]}: put exactly Kevin\'s take and the ranking source in the timeline, or pass kevin/ranking file paths.')
            kinds={p:source_kind(p) for p in present}
            if sorted(kinds.values())!=['kevin','ranking']:raise ValueError(f'{tl["name"]}: could not tell Kevin\'s take from the ranking source; pass kevin/ranking paths.')
            kevin=next(p for p,k in kinds.items() if k=='kevin');ranking=next(p for p,k in kinds.items() if k=='ranking')
        other=[p for p in present if p not in (kevin,ranking)]
        if other:raise ValueError(f'{tl["name"]} has other video media ({Path(other[0]).name}); ranking cuts rebuild only raw/empty timelines.')
        job=api.ident();work=folder(api,job);work.mkdir(parents=True)
        rec={'job_id':job,'batch_id':batch,'project':project.name,'timeline':tl['name'],'timeline_id':tl['id'],'source_hash':api.digest(path),'source_signature':content_signature(api,project,draft),
            'kevin':probe(kevin),'ranking':probe(ranking),'style_version':st['version'],'status':'preparing','created_at':time.time(),'existing_video_paths':present}
        api.s.write_json(work/'job.json',rec);api.s.write_json(work/'source.json',draft);api.s.write_json(work/'style.json',st);jobs.append(job)
    (api.STATE/'ranking_batches').mkdir(parents=True,exist_ok=True)
    api.s.write_json(api.STATE/'ranking_batches'/(batch+'.json'),{'batch_id':batch,'jobs':jobs,'created_at':time.time()})
    results=[]
    for job in jobs:
        try:analyze_job(api,job);results.append({'job_id':job,'status':'ready'})
        except Exception as exc:
            rec=record(api,job);rec.update(status='failed',error=str(exc));api.s.write_json(folder(api,job)/'job.json',rec);results.append({'job_id':job,'status':'failed','error':str(exc)})
    return {'batch_id':batch,'jobs':results,'writes_to_capcut':False,'next':'get_ranking_briefs, read every contact sheet, then ranking_frames for exact boundaries.'}

def briefs(api,batch):
    rec=batch_record(api,batch);rows=[api.s.read_json(folder(api,j)/'brief.json') for j in rec['jobs']]
    shared=rows[0]['style']
    return {'batch_id':batch,'style':shared,'jobs':[{k:v for k,v in r.items() if k!='style'} for r in rows]}

def frame_image(api,job,role,times):
    """Exact source frames (seconds in that source) tiled with labels: role kevin, ranking or bw (B&W preview of ranking)."""
    import numpy as np,cv2
    rec=record(api,job)
    if role not in ('kevin','ranking','bw'):raise ValueError('role must be kevin, ranking or bw.')
    if not 1<=len(times)<=8:raise ValueError('Give one to eight times.')
    src=rec['kevin' if role=='kevin' else 'ranking'];tiles=[]
    for t in times:
        if not 0<=t<src['duration']:raise ValueError(f'{t} is outside the {role} source.')
        raw=ff(['-ss',f'{t:.3f}','-i',src['path'],'-frames:v','1','-an','-vf','scale=270:480'+(',hue=s=0' if role=='bw' else ''),'-f','rawvideo','-pix_fmt','bgr24','-'])
        f=np.frombuffer(raw,np.uint8).reshape(480,270,3).copy();cv2.rectangle(f,(0,0),(120,22),(0,0,0),-1)
        cv2.putText(f,f'{role} {t:.2f}s',(4,16),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,255,255),1,cv2.LINE_AA);tiles.append(f)
    image=np.concatenate(tiles,1);name=folder(api,job)/f'frames-{role}-{"-".join(f"{t:.2f}" for t in times)}.jpg'
    cv2.imwrite(str(name),image,[cv2.IMWRITE_JPEG_QUALITY,85]);return {'path':str(name)}

def loud_span(env,w,hi,lo_bound=0.0,hi_bound=None):
    """First/last 10 ms frame inside a word (ASR spans can stretch over silence) that is clearly speech: 30 ms sustained, so a breath or click does not count."""
    import numpy as np
    a=max(int(max(w['start']-.05,lo_bound)*100),0);b=min(int(((w['end']+.1) if hi_bound is None else min(w['end']+.1,hi_bound))*100),len(env))
    loud=env[a:b]>hi;sustained=loud[:-2]&loud[1:-1]&loud[2:] if len(loud)>2 else loud
    idx=np.nonzero(sustained)[0]
    return (a+int(idx[0]),a+int(idx[-1])+min(2,len(loud)-1)) if len(idx) else None
def piece_bounds(words,env,a,b,pad):
    """Start/end of a word span at the audible syllable edges, never into a neighbouring word's real (loud) span."""
    import numpy as np
    floor=float(np.percentile(env,10));hi=max(floor+25,float(env.max())-30);lo=hi-10
    prev=loud_span(env,words[a-1],hi) if a>0 else None;nxt=loud_span(env,words[b+1],hi) if b+1<len(words) else None
    lo_limit=(prev[1]+1)/100+.02 if prev else 0.0;hi_limit=nxt[0]/100-.02 if nxt else len(env)/100
    first=loud_span(env,words[a],hi,lo_bound=lo_limit,hi_bound=hi_limit);last=loud_span(env,words[b],hi,lo_bound=lo_limit,hi_bound=hi_limit)
    f=first[0] if first else int(words[a]['start']*100);g=last[1]+1 if last else int(words[b]['end']*100)
    stop=max(int(lo_limit*100),f-20)
    while f>stop and env[f-1]>lo:f-=1
    stop=min(int(hi_limit*100),g+25,len(env))
    while g<stop and env[g]>lo:g+=1
    return max(lo_limit,f/100-pad['start_pad']),min(hi_limit,g/100+pad['end_pad'])

def stage(api,job,items,reactions,quality_notes,volumes=None):
    import numpy as np
    rec=record(api,job);work=folder(api,job)
    if rec['status'] not in ('ready','staged'):raise ValueError('Prepare must finish first.')
    for key in ('item_boundaries_checked_on_frames','reaction_mapping_reviewed','dropped_speech_reviewed'):
        if quality_notes.get(key) is not True:raise ValueError(f'quality_notes.{key} must be true after actually reviewing it.')
    words=api.s.read_json(work/'words.json');env=np.load(work/'kevin_rms.npy');st=api.s.read_json(work/'style.json');d={**DEFAULTS,**st.get('defaults',{})}
    brief=api.s.read_json(work/'brief.json');cuts=brief['ranking_analysis']['scene_cuts'];rdur=rec['ranking']['duration'];kdur=rec['kevin']['duration']
    errors=[];warnings=[];last=-1.0;snapped=[]
    # The user's revisions move starts later (items skip the source's whip-blur frames, reactions drop lead-ins);
    # apply their median once at least two revised videos agree.
    adj=st.get('learned_adjustments',{});use=adj.get('revisions',0)>=2
    item_lead=min(.3,max(0.0,adj.get('item_start_delta') or 0)) if use else 0.0
    piece_lead=min(.3,max(-.1,adj.get('piece_start_delta') or 0)) if use else 0.0
    if len(items)<2:errors.append('A ranking video needs at least two items.')
    for i,it in enumerate(items):
        try:
            a,b=float(it['start']),float(it['end'])
            for name,t in (('start',a),('end',b)):
                near=min(cuts,key=lambda c:abs(c-t),default=None);near=near if near is not None and abs(near-t)<=.12 else t
                # An end (snapped cut or host time) is the next shot's first frame: stop just before it.
                value=near if name=='start' else round(near-.01,3)
                if value!=t:snapped.append([i,name,t,value])
                a,b=(value,b) if name=='start' else (a,value)
            if a>0 and item_lead and not it.get('keep_start'):a=round(a+item_lead,3)
            if not (0<=a<b<=rdur+1e-3):raise ValueError('outside the ranking source')
            if b-a<.6:raise ValueError('shorter than 0.6s')
            if a<last-1e-3:raise ValueError('overlaps or precedes the previous item; items play in source order')
            if len(str(it.get('reason','')))<10:raise ValueError('needs a reason naming the payoff/reveal')
            it.update(start=round(a,3),end=round(b,3));last=b
        except (KeyError,TypeError,ValueError) as err:errors.append(f'item {i}: {err}')
    if len(reactions)!=len(items):errors.append('Give exactly one reaction per item, in item order.')
    used=-1;planned=[]
    for k,r in enumerate(reactions):
        try:
            if r.get('item')!=k:raise ValueError('reaction item index must match its position')
            if len(str(r.get('about','')))<10:raise ValueError('about must say what Kevin reacts to')
            pieces=[]
            for p in r.get('pieces') or []:
                a,b=int(p['from_word']),int(p['to_word'])
                if not 0<=a<=b<len(words):raise ValueError(f'word range {a}-{b} is invalid')
                if a<=used:raise ValueError('pieces must move forward through the take without reuse')
                split=[a]+[i+1 for i in range(a,b) if r.get('tighten',True) and words[i+1]['start']-words[i]['end']>d['gap_split']]
                for x,y in zip(split,split[1:]+[b+1]):
                    s0,s1=piece_bounds(words,env,x,y-1,d)
                    if x==a and 'start_adjust' in p:s0+=float(p['start_adjust'])
                    elif piece_lead:s0=min(s0+piece_lead,(words[x]['start']+words[x]['end'])/2)
                    if y-1==b and 'end_adjust' in p:s1+=float(p['end_adjust'])
                    pieces.append({'from_word':x,'to_word':y-1,'start':round(max(0,s0),3),'end':round(min(kdur,s1),3),'text':' '.join(w['text'] for w in words[x:y])})
                if ('start_adjust' in p or 'end_adjust' in p) and (len(str(p.get('adjust_reason','')))<10 or max(abs(float(p.get('start_adjust',0))),abs(float(p.get('end_adjust',0))))>.5):
                    raise ValueError('adjustments need adjust_reason and stay within 0.5s')
                used=b
            if not pieces:raise ValueError('needs at least one piece')
            planned.append({**r,'pieces':pieces})
        except (KeyError,TypeError,ValueError) as err:errors.append(f'reaction {k}: {err}')
    if errors:raise ValueError(f'{len(errors)} problem(s), nothing staged; fix all then retry: '+' || '.join(errors))
    vol={'kevin':d['kevin_volume'],'ranking':d['ranking_volume'],**(volumes or {})}
    if not all(isinstance(v,(int,float)) and 0<=v<=2 for v in vol.values()):raise ValueError('Volumes must be 0..2.')
    segments=[];overlays=[];frame=0;timeline=[];spans=[]
    for k,(it,r) in enumerate(zip(items,planned)):
        # Whole frames rounded down, so an item never reaches past its end into the next shot.
        n=max(1,math.floor((it['end']-it['start'])*FPS+1e-6));segments.append({'role':'ranking','index':k,'source_start':it['start'],'frames':n,'target_frame':frame})
        timeline.append([round(frame/FPS,3),round((frame+n)/FPS,3),'item',str(it.get('label') or it.get('rank') or k+1)]);frame+=n;rstart=frame;placed=[]
        for p in r['pieces']:
            n=max(1,snap(p['end']-p['start']));segments.append({'role':'kevin','index':k,'source_start':p['start'],'frames':n,'target_frame':frame})
            placed.append((frame,n,p));timeline.append([round(frame/FPS,3),round((frame+n)/FPS,3),'kevin',p['text']]);frame+=n
        spans.append([rstart,frame])
        bw=r.get('bw')
        if bw:
            try:
                at=int(bw['at_word']);host=next(((f0,n,p) for f0,n,p in placed if p['from_word']<=at<=p['to_word']),None)
                if host is None:raise ValueError('at_word must be inside this reaction')
                f0=host[0]+snap(max(0,words[at]['start']-.03-host[2]['start']))
                if f0-rstart<snap(d['bw_face_first']):raise ValueError(f'show Kevin\'s face at least {d["bw_face_first"]}s before the B&W')
                f1=frame if bw.get('until_end') else min(frame,f0+max(1,snap(float(bw['duration']))))
                # Default tail stops 0.05s before the cut: nearest-frame rendering at the cut time shows the next shot.
                length=(f1-f0)/FPS;tail=float(bw.get('tail_end',it['end']-.05));zoom=float(bw.get('zoom',d['bw_zoom']))
                if not .5<=length<=2.6:raise ValueError(f'B&W length {length:.2f}s; keep 0.5-2.6s')
                if not (it['start']-1e-3<=tail-length and tail<=it['end']+1e-3):raise ValueError('tail must be the last part of this same item')
                if not 1.0<=zoom<=1.6:raise ValueError('zoom 1.0-1.6')
                if len(str(bw.get('reason','')))<12:raise ValueError('B&W needs a reason (what Kevin points back at)')
                under=[w['text'] for pf,_,p in placed for w in words[p['from_word']:p['to_word']+1] if f0<=pf+snap(w['start']-p['start'])<f1]
                overlays.append({'reaction':k,'target_frame':f0,'frames':f1-f0,'source_start':round(tail-length,3),'zoom':zoom,'reason':bw['reason'],'under_words':' '.join(under)})
                timeline.append([round(f0/FPS,3),round(f1/FPS,3),'bw',overlays[-1]['under_words']])
            except (KeyError,TypeError,ValueError) as err:errors.append(f'reaction {k} bw: {err}')
    if errors:raise ValueError(f'{len(errors)} problem(s), nothing staged; fix all then retry: '+' || '.join(errors))
    stats=st.get('stats',{});typical=statistics.median(stats.get('bw_per_video') or [0]) if stats.get('bw_per_video') else None
    if typical is not None and abs(len(overlays)-typical*len(items)/6)>2:warnings.append(f'{len(overlays)} B&W replays; references used about {typical:g} per 6 reactions (calibration, not a quota).')
    if overlays and overlays[-1]['reaction']==len(items)-1 and sum(stats.get('final_reaction_has_bw',[]))<len(stats.get('final_reaction_has_bw',[]))/2:warnings.append('Final reaction ends on B&W; most references end on Kevin\'s face.')
    for k,(a,b) in enumerate(spans):
        if (b-a)/FPS>7:warnings.append(f'reaction {k} lasts {(b-a)/FPS:.1f}s; references max {stats.get("reaction_seconds",{}).get("max")}s.')
    used_words={i for r in planned for p in r['pieces'] for i in range(p['from_word'],p['to_word']+1)}
    dropped=[];run=[]
    for w in words:
        if w['i'] in used_words:
            if run:dropped.append(' '.join(run));run=[]
        else:run.append(w['text'])
    if run:dropped.append(' '.join(run))
    whoosh=[round(segments[k]['target_frame']/FPS-d['whoosh_lead'],3) for k in range(len(segments)) if segments[k]['role']=='ranking' and segments[k]['index']>0]
    plan={'job_id':job,'project':rec['project'],'timeline':rec['timeline_id'],'source_hash':rec['source_hash'],'style_version':rec['style_version'],
        'items':items,'reactions':planned,'segments':segments,'overlays':overlays,'volumes':vol,'total_frames':frame,'whoosh_cues':whoosh,'quality_notes':quality_notes}
    api.s.write_json(work/'plan.json',plan);rec['status']='staged';rec['plan_hash']=api.digest(work/'plan.json');rec.pop('preview',None);api.s.write_json(work/'job.json',rec)
    return {'job_id':job,'duration':round(frame/FPS,2),'items':len(items),'kevin_pieces':sum(len(r['pieces']) for r in planned),'bw':len(overlays),
        'learned_start_offsets':{'item':item_lead,'reaction_piece':piece_lead},
        'timeline':sorted(timeline),'snapped_to_scene_cut':snapped,'dropped_speech':dropped,'warnings':warnings,'writes_to_capcut':False,'next':'preview_ranking_plan, inspect the sheet, then apply_ranking_batch'}

def render_piece(src,start,frames_,out,w=360,h=640,bw=False,zoom=1.0,audio=True):
    # Exactly frames_ video frames and the same audio length, so concatenated parts never drift by a frame.
    vf=f'scale={int(w*zoom)}:{int(h*zoom)}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS},setsar=1'+(',hue=s=0' if bw else '')+f',tpad=stop_mode=clone:stop_duration=0.2,setpts=N/({FPS}*TB)'
    args=['-ss',f'{start:.3f}','-i',src,'-vf',vf,'-frames:v',str(frames_)]
    args+=['-af','aresample=44100,apad,asetpts=N/SR/TB','-t',f'{frames_/FPS:.4f}','-ac','2','-c:a','aac','-b:a','128k'] if audio else ['-an']
    ff([*args,'-c:v','libx264','-preset','veryfast','-crf','26','-pix_fmt','yuv420p','-y',str(out)])

def preview(api,job):
    """Low-resolution render of the staged cut (hard cuts, B&W overlays, both audio sources) plus a boundary sheet."""
    import numpy as np,cv2
    rec=record(api,job);work=folder(api,job);plan=api.s.read_json(work/'plan.json')
    if rec['status']!='staged' or api.digest(work/'plan.json')!=rec['plan_hash']:raise ValueError('Stage the plan first.')
    tmp=work/'preview';shutil.rmtree(tmp,ignore_errors=True);tmp.mkdir();parts=[]
    for i,sg in enumerate(plan['segments']):
        src=rec[sg['role']];out=tmp/f'{i:03d}.mp4'
        silent=not src['has_audio']
        render_piece(src['path'],sg['source_start'],sg['frames'],out,audio=not silent)
        if silent:ff(['-i',str(out),'-f','lavfi','-i','anullsrc=r=44100:cl=stereo','-shortest','-c:v','copy','-c:a','aac','-y',str(out.with_suffix('.a.mp4'))]);out=out.with_suffix('.a.mp4')
        parts.append(out)
    # Concat filter, not the demuxer: parts from 60 and 30 fps sources carry different timebases and the demuxer drifts.
    main=tmp/'main.mp4';inputs=[x for p in parts for x in ('-i',str(p))]
    graph=''.join(f'[{i}:v][{i}:a]' for i in range(len(parts)))+f'concat=n={len(parts)}:v=1:a=1[v][a]'
    ff([*inputs,'-filter_complex',graph,'-map','[v]','-map','[a]','-r',str(FPS),'-c:v','libx264','-preset','veryfast','-crf','24','-c:a','aac','-b:a','128k','-y',str(main)])
    final=work/'preview.mp4'
    if plan['overlays']:
        inputs=['-i',str(main)];chain='[0:v]';graph=[]
        for k,ov in enumerate(plan['overlays']):
            clip=tmp/f'bw{k}.mp4';render_piece(rec['ranking']['path'],ov['source_start'],ov['frames'],clip,bw=True,zoom=ov['zoom'],audio=False);inputs+=['-i',str(clip)]
            t0=ov['target_frame']/FPS;graph.append(f"[{k+1}:v]setpts=PTS-STARTPTS+{t0:.4f}/TB[b{k}];{chain}[b{k}]overlay=eof_action=repeat:enable='between(t,{t0-.5/FPS:.4f},{t0+(ov['frames']-.5)/FPS:.4f})'[v{k}]");chain=f'[v{k}]'
        ff([*inputs,'-filter_complex',';'.join(graph),'-map',chain,'-map','0:a','-c:v','libx264','-preset','veryfast','-crf','26','-c:a','copy','-y',str(final)])
    else:shutil.copyfile(main,final)
    # Boundary sheet: last frame before and first frame after every cut, plus each B&W midpoint.
    marks=[]
    for sg in plan['segments'][1:]:t=sg['target_frame']/FPS;marks+=[(t-1/FPS-.005,'before cut'),(t-.005,f"after: {sg['role']}")]
    marks+=[((ov['target_frame']+ov['frames']/2)/FPS,'B&W mid') for ov in plan['overlays']]
    tiles=[]
    for t,label in sorted(marks):
        raw=ff(['-ss',f'{max(0,t):.3f}','-i',str(final),'-frames:v','1','-vf','scale=180:320','-f','rawvideo','-pix_fmt','bgr24','-'])
        if len(raw)!=180*320*3:continue
        f=np.frombuffer(raw,np.uint8).reshape(320,180,3).copy();cv2.rectangle(f,(0,0),(180,30),(0,0,0),-1)
        cv2.putText(f,f'{t:.2f}s',(3,12),cv2.FONT_HERSHEY_SIMPLEX,.38,(0,255,255),1,cv2.LINE_AA);cv2.putText(f,label[:24],(3,26),cv2.FONT_HERSHEY_SIMPLEX,.36,(255,255,255),1,cv2.LINE_AA);tiles.append(f)
    if not tiles:raise ValueError('Preview render produced no frames.')
    cols=8;rows=[np.concatenate(tiles[i:i+cols]+[np.zeros_like(tiles[0])]*(cols-len(tiles[i:i+cols])),1) for i in range(0,len(tiles),cols)]
    sheet=work/'preview_sheet.jpg';cv2.imwrite(str(sheet),np.concatenate(rows,0),[cv2.IMWRITE_JPEG_QUALITY,82])
    heard=listen(api,final,work,plan,rec['plan_hash'])
    rec['preview']={'plan_hash':rec['plan_hash'],'video':str(final),'sheet':str(sheet)};api.s.write_json(work/'job.json',rec)
    shutil.rmtree(tmp,ignore_errors=True)
    return {'job_id':job,'video':str(final),'sheet':str(sheet),'heard':heard,
        'note':'Preview uses hard cuts at 360x640; CapCut transitions/music are the user\'s. Read the sheet and compare planned vs heard words before apply.'}

def listen(api,video,work,plan,key):
    """Transcribe the rendered preview so clipped or leaked syllables at each cut show up as planned-vs-heard text."""
    import numpy as np
    import context_pipeline as c
    wav=work/f'preview-{key[:12]}.wav'
    if not wav.exists():
        audio=pcm(video)
        with wave.open(str(wav),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000);out.writeframes((np.clip(audio,-1,1)*32767).astype('<i2').tobytes())
    heard=[w for row in c.transcribe(wav,api.s.config()['speech_model'],lambda _:None)['rows'] for w in row['words']];out=[]
    for sg in plan['segments']:
        a=sg['target_frame']/FPS;b=a+sg['frames']/FPS;r=plan['reactions'][sg['index']]
        planned=next((p['text'] for p in r['pieces'] if abs(p['start']-sg['source_start'])<1e-3),'') if sg['role']=='kevin' else ''
        out.append({'at':round(a,2),'role':sg['role'],'planned':planned,'heard':' '.join(w['text'] for w in heard if a-.05<=(w['start']+w['end'])/2<b)})
    return out

def bw_media(api,job,plan,rec):
    """Full-resolution desaturated tail clips; deterministic names so a re-apply reuses them."""
    out=api.STATE/'ranking_media'/job;out.mkdir(parents=True,exist_ok=True);made=[]
    for k,ov in enumerate(plan['overlays']):
        key=hashlib.sha256(f"{rec['ranking']['path']}:{rec['ranking']['size']}:{ov['source_start']}:{ov['frames']}".encode()).hexdigest()[:10]
        path=out/f"bw_{k+1:02d}_{key}.mp4"
        if not path.exists():
            tmp=path.with_name(path.stem+'.writing.mp4')
            ff(['-ss',f"{ov['source_start']:.3f}",'-i',rec['ranking']['path'],'-t',f"{ov['frames']/FPS+2/FPS:.4f}",'-an','-vf',
                f'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={FPS},hue=s=0,setsar=1','-c:v','libx264','-preset','medium','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart','-y',str(tmp)])
            tmp.replace(path)
        info=probe(path)
        if info['duration']+1e-3<ov['frames']/FPS:raise ValueError('Rendered B&W clip is shorter than planned.')
        made.append(info)
    return made

def clone_segment(api,draft,template,patch=None,reset_clip=False):
    seg=copy.deepcopy(template['segment']);mat=copy.deepcopy(template['material']);mapping={mat['id']:api.s.uid()};mat['id']=mapping[template['material']['id']]
    if patch:mat.update(patch)
    draft['materials'].setdefault('videos',[]).append(mat)
    for kind,items in template['extras'].items():
        for m in items:
            c=copy.deepcopy(m);c['id']=mapping.setdefault(m['id'],api.s.uid());draft['materials'].setdefault(kind,[]).append(c)
            if kind=='speeds':c['speed']=1.0;c['curve_speed']=None
    seg.update(id=api.s.uid(),material_id=mat['id'],extra_material_refs=[mapping[r] for r in template['segment'].get('extra_material_refs',[]) if r in mapping],
        speed=1.0,reverse=False,keyframe_refs=[],common_keyframes=[],group_id='',raw_segment_id='',visible=True)
    if reset_clip or not template['same_timeline']:
        seg['clip']={'scale':{'x':1.0,'y':1.0},'rotation':0.0,'transform':{'x':0.0,'y':0.0},'flip':{'vertical':False,'horizontal':False},'alpha':1.0};seg['uniform_scale']={'on':True,'value':1.0}
    return seg,mat
def media_patch(info,has_audio=None):
    name=Path(info['path']).name
    return {'path':Path(info['path']).as_posix(),'material_name':name,'duration':round(info['duration']*MICRO),'width':info['width'],'height':info['height'],
        'has_audio':info['has_audio'] if has_audio is None else has_audio,'local_material_id':str(uuid.uuid4()),'media_path':'','origin_material_id':'','request_id':'','unique_id':'',
        'crop':{'upper_left_x':0.0,'upper_left_y':0.0,'upper_right_x':1.0,'upper_right_y':0.0,'lower_left_x':0.0,'lower_left_y':1.0,'lower_right_x':1.0,'lower_right_y':1.0},
        'crop_ratio':'free','crop_scale':1.0,'audio_fade':None,'reverse_path':'','intensifies_path':'','reverse_intensifies_path':'','intensifies_audio_path':'','cartoon_path':''}

def build(api,job,media=None):
    """Whole new draft in memory: main track alternates items/reaction pieces, an overlay track carries muted B&W tails."""
    rec=record(api,job);work=folder(api,job);plan=api.s.read_json(work/'plan.json')
    if rec['status'] not in ('staged','applied') or api.digest(work/'plan.json')!=rec.get('plan_hash'):raise ValueError('Stage the plan first.')
    if (rec.get('preview') or {}).get('plan_hash')!=rec['plan_hash']:raise ValueError('Preview the staged plan and read its sheet before apply.')
    project=api.s.project_path(rec['project']);tl,current,path=api.s.load_timeline(project,rec['timeline_id'])
    if content_signature(api,project,current)!=rec['source_signature']:raise ValueError('Timeline content changed after preparation (user edit). Prepare again.')
    for role in ('kevin','ranking'):
        stat=Path(rec[role]['path']).stat()
        if stat.st_size!=rec[role]['size'] or stat.st_mtime_ns!=rec[role]['mtime']:raise ValueError(f'The {role} source file changed; prepare again.')
    draft=copy.deepcopy(current);templates={role:find_template(api,project,current,rec[role]['path']) for role in ('kevin','ranking')}
    media=media if media is not None else bw_media(api,job,plan,rec)
    old_video=[t for t in draft['tracks'] if t.get('type')=='video'];position=draft['tracks'].index(old_video[0]) if old_video else 0
    draft['tracks']=[t for t in draft['tracks'] if t.get('type')!='video']
    gone={s['material_id'] for t in old_video for s in t.get('segments',[])}|{r for t in old_video for s in t.get('segments',[]) for r in s.get('extra_material_refs',[])}
    still={s['material_id'] for t in draft['tracks'] for s in t.get('segments',[])}|{r for t in draft['tracks'] for s in t.get('segments',[]) for r in s.get('extra_material_refs',[])}
    for kind,arr in draft['materials'].items():
        if isinstance(arr,list):draft['materials'][kind]=[m for m in arr if not (isinstance(m,dict) and m.get('id') in gone-still)]
    main={'id':api.s.uid(),'type':'video','segments':[],'flag':0,'attribute':0,'name':'','is_default_name':True}
    for sg in plan['segments']:
        t=templates[sg['role']];patch=None if t['same_media'] else media_patch(rec[sg['role']])
        seg,_=clone_segment(api,draft,t,patch)
        start=us(sg['target_frame']);length=us(sg['target_frame']+sg['frames'])-start;src=round(sg['source_start']*MICRO)
        if src+length>round(rec[sg['role']]['duration']*MICRO)+2000:raise ValueError(f"{sg['role']} segment runs past its source.")
        seg.update(source_timerange={'start':src,'duration':length},target_timerange={'start':start,'duration':length},volume=float(plan['volumes'][sg['role']]),
            last_nonzero_volume=float(plan['volumes'][sg['role']]) or 1.0,render_index=0,track_render_index=0)
        main['segments'].append(seg)
    tracks=[main];layer=max((s.get('track_render_index',0) for t in draft['tracks'] for s in t.get('segments',[])),default=0)+1
    if plan['overlays']:
        overlay={'id':api.s.uid(),'type':'video','segments':[],'flag':2,'attribute':0,'name':'','is_default_name':True}
        for ov,info in zip(plan['overlays'],media):
            seg,_=clone_segment(api,draft,templates['ranking'],media_patch(info,has_audio=False),reset_clip=True)
            start=us(ov['target_frame']);length=us(ov['target_frame']+ov['frames'])-start
            seg.update(source_timerange={'start':0,'duration':length},target_timerange={'start':start,'duration':length},volume=0.0,last_nonzero_volume=1.0,render_index=1,track_render_index=layer)
            seg['clip']['scale']={'x':ov['zoom'],'y':ov['zoom']};overlay['segments'].append(seg)
        tracks.append(overlay)
    draft['tracks'][position:position]=tracks
    draft['duration']=us(plan['total_frames'])
    if rec['ranking']['height']>rec['ranking']['width']:draft['canvas_config']={**draft.get('canvas_config',{}),'ratio':'original','width':1080,'height':1920}
    api.s.validate_draft(draft)
    changes={path:draft}
    if api.s.is_main_timeline(project,tl):changes[api.s.draft_file(project)]=draft
    meta_path=project/'draft_meta_info.json'
    if meta_path.exists():
        meta=api.s.read_json(meta_path);group=next((g for g in meta.get('draft_materials',[]) if g.get('type')==0),None)
        if group is None:group={'type':0,'value':[]};meta.setdefault('draft_materials',[]).append(group)
        known={m.get('file_Path') for m in group['value']}
        for info in [rec['kevin'],rec['ranking'],*media]:
            p=Path(info['path']).as_posix()
            if p in known:continue
            duration=round(info['duration']*MICRO)
            group['value'].append({'id':api.s.uid(),'file_Path':p,'extra_info':Path(p).name,'metetype':'video','type':0,'duration':duration,'width':info['width'],'height':info['height'],'md5':'',
                'create_time':0,'import_time':0,'import_time_ms':0,'roughcut_time_range':{'start':0,'duration':duration},'sub_time_range':{'start':-1,'duration':-1},'item_source':1,'enter_from':0});known.add(p)
        if api.s.is_main_timeline(project,tl):meta.update(tm_duration=draft['duration'])
        meta['tm_draft_modified']=int(time.time()*MICRO);changes[meta_path]=meta
    return changes,media

def apply_batch(api,batch,auto_close=True):
    rec=batch_record(api,batch)
    with api.lock('ranking-style'),api.lock('capcut-write'):
        def collect(media=None):
            out={};made={}
            for job in rec['jobs']:
                changes,m=build(api,job,(media or {}).get(job));made[job]=m
                for p,v in changes.items():
                    if p in out and p.name=='draft_meta_info.json':
                        known={x.get('file_Path') for g in out[p].get('draft_materials',[]) for x in g.get('value',[])}
                        group=next(g for g in out[p]['draft_materials'] if g.get('type')==0)
                        for g in v.get('draft_materials',[]):
                            for x in g.get('value',[]):
                                if x.get('file_Path') not in known:group['value'].append(x);known.add(x.get('file_Path'))
                        continue
                    if p in out and p.name!='draft_info.json':raise ValueError('Unexpected batch write collision.')
                    out[p]=v
            return out,made
        if not auto_close:api.close_for_apply(False)
        _,media=collect();closure=api.close_for_apply(auto_close)
        changes,_=collect(media);previous={p:p.read_bytes() for p in changes}
        try:
            for p,value in changes.items():
                if api.s.capcut_running():raise ValueError('CapCut reopened; rolling back ranking writes.')
                api.s.write_json(p,value)
        except Exception:
            for p,data in previous.items():p.write_bytes(data)
            raise
        registry=api.s.read_json(registry_path(api)) if registry_path(api).exists() else {}
        for job in rec['jobs']:
            r=record(api,job);plan=api.s.read_json(folder(api,job)/'plan.json');project=api.s.project_path(r['project'])
            _,_,path=api.s.load_timeline(project,r['timeline_id']);r.update(status='applied',applied_at=time.time(),applied_hash=api.digest(path),media=[m['path'] for m in media[job]])
            api.s.write_json(folder(api,job)/'job.json',r)
            registry[r['timeline_id']]={'job_id':job,'project':r['project'],'timeline':r['timeline'],'applied_at':r['applied_at'],'applied_hash':r['applied_hash']}
        api.s.write_json(registry_path(api),registry)
    return {'installed':True,'targets':len(rec['jobs']),'files_written':len(changes),'capcut_close':closure,'saved_backups':False,
        'next':'Open CapCut and review. For SFX on Kevin\'s reactions run prepare_edit_batch(mode=just_sfx) on the same timelines; the brief then carries the ranking cut map and rules.'}

def annotate_brief(api,record_,brief,draft):
    """Add the ranking cut map and learned ranking SFX rules to a normal SFX brief for a timeline this module cut.
    The map is read from the saved timeline, so user moves/trims after apply are respected."""
    path=registry_path(api)
    if not path.exists():return
    entry=api.s.read_json(path).get(record_['timeline_id'])
    if not entry or entry['project']!=record_['project']:return
    st=style(api);rec=record(api,entry['job_id']);project=api.s.project_path(rec['project']);main,over=observed(api,rec,draft,project)
    builtin=api.s.read_json(folder(api,entry['job_id'])/'brief.json')['ranking_analysis']['builtin_sfx'];rows=[];item_sfx=[];item=-1
    for x in main:
        if x['role']=='ranking':item+=1
        kind={'ranking':'item','kevin':'reaction'}.get(x['role'],'other');end=x['start']+x['duration']
        rows.append({'kind':kind,'item_or_reaction':item,'start':round(x['start'],3),'end':round(end,3)})
        if x['role']=='ranking':
            a=x['source_start'];item_sfx+=[{'sound':h['sound'],'timeline_at':round(x['start']+h['start']-a,2)} for h in builtin if a<=h['start']<a+x['source_duration']]
    lead=st['defaults']['whoosh_lead'];cuts=[r['start'] for k,r in enumerate(rows) if r['kind']=='item' and k>0 and rows[k-1]['kind']!='item']
    brief['ranking']={'video_type':'ranking_video','cut_map':rows,'bw_overlays':[{'start':round(x['start'],3),'end':round(x['start']+x['duration'],3)} for x in over if x['role'] in ('bw','ranking')],
        'whoosh_cues':[{'sound':WHOOSH,'at':round(c-lead,3),'cut':c} for c in cuts],'item_clip_builtin_sfx':item_sfx,
        'rules':[r for r in st['rules'] if any(k in r for k in ('SFX','whoosh','B&W','Kevin sits'))],
        'reference_sfx_stats':{k:st['stats'].get(k) for k in ('kevin_sfx_per_reaction','kevin_sfx_families','first_sfx_offset_median','fah_offset_from_bw_start','whoosh')},
        'reference_reactions':[{'video':r['name'],'reactions':[{'words':x['words'],'bw_words':(x.get('bw') or {}).get('words'),'sfx':[[s['sound'],s['offset'],s['near_word']] for s in x['sfx']]} for x in r['reactions']]} for r in st['references']]}
    brief.setdefault('plan_requirements',{})['ranking']=('Ranking video: place SFX only on Kevin reaction spans (cut_map kind=reaction, including B&W overlays where his voice continues). '
        'Item clips already contain the source creator\'s SFX (item_clip_builtin_sfx): never add over them. Add the transition whoosh at each whoosh_cues time with a visual_reveal anchor '
        'on an inspected frame at the cut. The general sfx_density target does not apply; use the reference ranking stats instead.')
    if brief['plan_requirements'].get('sfx_density'):brief['plan_requirements']['sfx_density']['guidance']+=' Not applicable to ranking videos: see plan_requirements.ranking.'

def observed(api,rec,draft,project):
    """Main-track sequence and overlays of a saved (possibly user-revised) ranking timeline, mapped to sources."""
    mats={m['id']:m for m in draft['materials'].get('videos',[])};media=set(rec.get('media',[]));main=[];over=[]
    tracks=[t for t in draft['tracks'] if t.get('type')=='video']
    for n,t in enumerate(tracks):
        for seg in sorted(t.get('segments',[]),key=lambda s:s['target_timerange']['start']):
            p=str(api.s.resolve_path(mats.get(seg['material_id'],{}).get('path',''),project))
            role='ranking' if p==rec['ranking']['path'] else 'kevin' if p==rec['kevin']['path'] else 'bw' if p in media else 'other'
            row={'role':role,'path':p,'start':seg['target_timerange']['start']/MICRO,'duration':seg['target_timerange']['duration']/MICRO,
                'source_start':(seg.get('source_timerange') or {}).get('start',0)/MICRO,'source_duration':(seg.get('source_timerange') or {}).get('duration',0)/MICRO,
                'volume':seg.get('volume'),'scale':(seg.get('clip') or {}).get('scale',{}).get('x')}
            (main if n==0 else over).append(row)
    return main,over

def learn_revision(api,job):
    """Compare the applied cut with the user's saved revision; keep the corrections as ranking evidence (no CapCut writes)."""
    rec=record(api,job);plan=api.s.read_json(folder(api,job)/'plan.json')
    if rec['status']!='applied':raise ValueError('Only an applied ranking cut can be compared with a revision.')
    project=api.s.project_path(rec['project']);_,draft,path=api.s.load_timeline(project,rec['timeline_id'])
    main,over=observed(api,rec,draft,project)
    def overlap(a0,a1,b0,b1):return max(0.0,min(a1,b1)-max(a0,b0))
    def compare(planned,seen):
        matches=[];used=set()
        for i,(a,b) in enumerate(planned):
            best=max(((overlap(a,b,s,s+d),j) for j,(s,d) in enumerate(seen) if j not in used),default=(0,None))
            if best[0]>0:
                j=best[1];used.add(j);s,d=seen[j];matches.append({'planned':i,'start_delta':round(s-a,3),'end_delta':round(s+d-b,3)})
        return matches,[i for i in range(len(planned)) if i not in {m['planned'] for m in matches}],[j for j in range(len(seen)) if j not in used]
    # Compare with what was written (whole frames), not the requested boundaries.
    written=lambda role:[(sg['source_start'],round(sg['source_start']+sg['frames']/FPS,4)) for sg in plan['segments'] if sg['role']==role]
    items=written('ranking');pieces=written('kevin')
    im,ir,ia=compare(items,[(x['source_start'],x['source_duration']) for x in main if x['role']=='ranking'])
    pm,pr,pa=compare(pieces,[(x['source_start'],x['source_duration']) for x in main if x['role']=='kevin'])
    bw_seen=[x for x in over if x['role'] in ('bw','ranking')];kept=[];changed=[]
    for k,ov in enumerate(plan['overlays']):
        t0=ov['target_frame']/FPS;match=min((x for x in bw_seen if abs(x['start']-t0)<1.5 or Path(x['path']).name.startswith(f'bw_{k+1:02d}_')),key=lambda x:abs(x['start']-t0),default=None)
        if match is None:continue
        kept.append(k);changed.append({'planned':k,'duration_delta':round(match['duration']-ov['frames']/FPS,3),'zoom':match['scale'],'start_shift':round(match['start']-t0,3)})
    report={'job_id':job,'timeline':rec['timeline'],'revision_hash':api.digest(path),'unchanged':api.digest(path)==rec.get('applied_hash'),
        'items':{'matched':len(im),'removed':ir,'added':len(ia),'changes':[m for m in im if abs(m['start_delta'])>.05 or abs(m['end_delta'])>.05]},
        'kevin_pieces':{'matched':len(pm),'removed':pr,'added':len(pa),'changes':[m for m in pm if abs(m['start_delta'])>.05 or abs(m['end_delta'])>.05]},
        'bw':{'planned':len(plan['overlays']),'kept':kept,'removed':[k for k in range(len(plan['overlays'])) if k not in kept],'added':max(0,len(bw_seen)-len(kept)),'changes':changed},
        'main_track_other_media':sum(x['role']=='other' for x in main),'learned_at':time.time()}
    if report['unchanged']:return {**report,'learned':False,'note':'Timeline still matches the applied cut; save the revision in CapCut first.'}
    with api.lock('ranking-style'):
        st=style(api);st['revisions']=[r for r in st.get('revisions',[]) if r['job_id']!=job]+[report]
        med=lambda v:round(statistics.median(v),3) if v else None;revs=st['revisions']
        st['learned_adjustments']={'revisions':len(revs),
            'item_start_delta':med([c['start_delta'] for r in revs for c in r['items']['changes']]),'item_end_delta':med([c['end_delta'] for r in revs for c in r['items']['changes']]),
            'piece_start_delta':med([c['start_delta'] for r in revs for c in r['kevin_pieces']['changes']]),'piece_end_delta':med([c['end_delta'] for r in revs for c in r['kevin_pieces']['changes']]),
            'bw_kept':sum(len(r['bw']['kept']) for r in revs),'bw_removed':sum(len(r['bw']['removed']) for r in revs),'bw_added':sum(r['bw']['added'] for r in revs),
            'bw_duration_delta':med([c['duration_delta'] for r in revs for c in r['bw']['changes']]),'bw_zoom':med([c['zoom'] for r in revs for c in r['bw']['changes'] if c['zoom']])}
        st['version']+=1;api.s.write_json(style_path(api),st)
        hist=api.STATE/'ranking_history';hist.mkdir(exist_ok=True);api.s.write_json(hist/f'{job}-{int(time.time())}.json',{'report':report,'plan':plan,'observed':{'main':main,'overlays':over}})
    return {**report,'learned':True,'style_version':st['version'],'learned_adjustments':st['learned_adjustments']}
