"""Native reaction punch-ins; reuse frozen analyses, never transcribe again.

Creative selection belongs to the host. This module only learns observed native
edits, maps cached evidence, splits safe constant-speed clips and validates writes.
"""
from __future__ import annotations
import copy, json, math, statistics, time
from pathlib import Path


def tracks(draft):
    videos={m['id']:m for m in draft['materials'].get('videos',[])}
    return [t for t in draft['tracks'] if t.get('type')=='video' and any(
        videos.get(s.get('material_id'),{}).get('path') and s.get('visible',True) for s in t.get('segments',[]))]


def extract(draft):
    """Observe piecewise constant transforms relative to the time-weighted baseline."""
    result=[]
    for i,track in enumerate(tracks(draft)):
        groups={}
        for seg in track['segments']:
            clip=seg.get('clip') or {}
            if not clip.get('scale'):continue
            key=json.dumps(clip,sort_keys=True)
            groups.setdefault(key,[clip,0])[1]+=seg['target_timerange']['duration']
        if not groups:continue
        base=max(groups.values(),key=lambda x:x[1])[0]
        for seg in track['segments']:
            clip=seg.get('clip') or {}
            sx=clip.get('scale',{}).get('x',1)/base.get('scale',{}).get('x',1)
            sy=clip.get('scale',{}).get('y',1)/base.get('scale',{}).get('y',1)
            if max(sx,sy)<=1.05:continue
            tr=seg['target_timerange']
            result.append({'role':f'video_track_{i+1}','start':tr['start']/1e6,'end':(tr['start']+tr['duration'])/1e6,
                'scale':sx,'scale_y':sy,'dx':clip['transform']['x']-base['transform']['x'],
                'dy':clip['transform']['y']-base['transform']['y'],'native_clip':copy.deepcopy(clip),
                'animated':bool(seg.get('common_keyframes') or seg.get('keyframe_refs'))})
    return result


def folder(api,job):return api.STATE/'zoom_jobs'/api.safe_id(job)
def data(api,job):return api.s.read_json(folder(api,job)/'job.json')
def style(api):
    path=api.STATE/'data'/'zoom_style.json'
    if not path.exists():raise ValueError('Learn saved manual zoom references first.')
    return api.s.read_json(path)


def refresh_statistics(value):
    events=[e for r in value['references'] for e in r['events']]
    scales=[e['scale'] for e in events];durations=[e['end']-e['start'] for e in events]
    value['statistics']={'events':len(events),'median_scale':statistics.median(scales) if scales else None,
        'scale_range':[min(scales),max(scales)] if scales else [],'median_duration':statistics.median(durations) if durations else None,
        'duration_range':[min(durations),max(durations)] if durations else []}


def revision_diff(predicted,observed):
    """Associate same-role intervals without confusing retention with accuracy."""
    def distance(a,b):return abs(a['start']-b['start'])+abs(a['end']-b['end'])
    edges={i:sorted([j for j,b in enumerate(observed) if a.get('role','video_track_1')==b['role'] and
        (abs(a['start']-b['start'])<=.75 or max(a['start'],b['start'])<min(a['end'],b['end']))],key=lambda j:distance(a,observed[j])) for i,a in enumerate(predicted)}
    owner={}
    def visit(i,seen):
        for j in edges[i]:
            if j in seen:continue
            seen.add(j)
            if j not in owner or visit(owner[j],seen):owner[j]=i;return True
        return False
    for i in sorted(edges,key=lambda i:len(edges[i])):visit(i,set())
    matches=[]
    for j,i in sorted(owner.items(),key=lambda p:p[1]):
        p,m=predicted[i],observed[j]
        delta={k:round(m.get(k,0)-p.get(k,0),6) for k in ('start','end','scale','dx','dy')}
        matches.append({'predicted_index':i,'manual_index':j,'delta':delta,'retimed':max(abs(delta['start']),abs(delta['end']))>1/30+.000002,
            'reframed':max(abs(delta[k]) for k in ('scale','dx','dy'))>.005})
    return {'matches':matches,'added':[j for j in range(len(observed)) if j not in owner],
        'removed_or_distant_move':[i for i in range(len(predicted)) if i not in set(owner.values())],
        'retained_without_material_change':sum(not m['retimed'] and not m['reframed'] for m in matches),
        'interpretation':'Retrospective interval association, not an independent creative accuracy score. Unmatched distant moves need contextual review.'}


def cached(api,project,timeline,draft,job_id=None):
    import analysis_cache as ac
    try:
        found=ac.find(api,project,draft,job_id)
        return found['job_id'],found['mapping'],found['report']
    except LookupError as exc:raise ValueError(str(exc)) from exc


def historical_cached(api,project,timeline,draft,job_id=None):
    """Verify the media-stat key for frozen footage, then map edits to its speech."""
    import context_pipeline as c
    candidates=[api.job_path(job_id)] if job_id else sorted((api.STATE/'jobs').iterdir(),key=lambda p:p.stat().st_mtime,reverse=True)
    errors=[]
    for path in candidates:
        if not (path/'context_report.json').exists() or not (path/'source.json').exists():continue
        record=api.s.read_json(path/'job.json')
        if record.get('project')!=project.name or record.get('timeline_id')!=timeline['id']:continue
        old=api.s.read_json(path/'source.json')
        try:
            mapping=api.ra.TimelineMap(old,draft)
            report=api.s.read_json(path/'context_report.json')
            if c.context_inputs(project,old)[1]!=report['cache_key']:
                raise ValueError('Cached source media/config changed; no silent analysis reuse.')
            return path.name,mapping,report
        except ValueError as exc:errors.append(str(exc))
    raise ValueError('No compatible saved analysis. '+('; '.join(errors[:2]) or 'Prepare SFX once before zoom.'))


def map_report(mapping,report):
    """Keep every mapped word and both streams; old indices remain stable."""
    result=[]
    for role,track in enumerate(report['tracks']):
        rows=[];index=0
        for row in track['speech']:
            words=[]
            for word in row.get('words',[]):
                start=mapping.new_time(role,word['start'])
                end=mapping.new_time(role,max(word['start'],word['end']-1e-6))
                if start is not None and end is not None:
                    words.append({**word,'start':round(start,6),'end':round(end+1e-6,6),'word_index':index})
                index+=1
            if words:rows.append({'start':words[0]['start'],'end':words[-1]['end'],'text':row['text'] if len(words)==len(row.get('words',[])) else ' '.join(w['text'] for w in words),'words':words})
        result.append({'role':track['role'],'speech':rows})
    return {'tracks':result,'note':'Cached source speech mapped to current timeline; captions/ASR can drift. No new inference.'}


def learn_style(api,references):
    if not 1<=len(references)<=5:raise ValueError('Choose 1–5 manual zoom references.')
    observed=[]
    for ref in references:
        project=api.s.project_path(ref['project']);tl,draft,path=api.s.load_timeline(project,ref['timeline'])
        job,mapping,report=cached(api,project,tl,draft,ref.get('analysis_job_id'))
        events=extract(draft)
        if any(e['animated'] for e in events):raise ValueError('Animated reference needs a separate keyframe implementation.')
        for e in events:
            e['contexts']=[{'role':t['role'],'text':api.ra.word_context(report,i,mapping.old_time(i,e['start']))} for i,t in enumerate(report['tracks'])]
            e.pop('native_clip');e.pop('animated')
        observed.append({'project':project.name,'timeline':tl['name'],'timeline_id':tl['id'],'source_hash':api.digest(path),'analysis_job_id':job,'events':events})
    events=[e for ref in observed for e in ref['events']]
    if not events:raise ValueError('References contain no observed punch-ins.')
    with api.lock('zoom-style'):
        dest=api.STATE/'data'/'zoom_style.json';old=api.s.read_json(dest) if dest.exists() else {'version':0,'references':[]}
        by_id={(r['project'],r['timeline_id']):r for r in old['references']}
        for ref in observed:by_id[(ref['project'],ref['timeline_id'])]=ref
        refs=list(by_id.values())
        if refs==old['references']:return {'version':old['version'],'already_learned':True,'events':len(events)}
        all_events=[e for r in refs for e in r['events']];scales=[e['scale'] for e in all_events];durations=[e['end']-e['start'] for e in all_events]
        value={'version':old['version']+1,'references':refs,'statistics':{'events':len(all_events),'median_scale':statistics.median(scales),'scale_range':[min(scales),max(scales)],
            'median_duration':statistics.median(durations),'duration_range':[min(durations),max(durations)]},
            'policy':'Observed hard-cut reaction punch-ins then baseline reset. Select meaningful reaction phrases, not every SFX, option, keyword or fixed quota. Position for THIS face/layout. Reference offsets/times are examples, not target timestamps.'}
        api.s.write_json(dest,value)
    return {'version':value['version'],'references':len(refs),'statistics':value['statistics'],'writes_to_capcut':False}


def prepare(api,targets):
    if not 1<=len(targets)<=5:raise ValueError('Choose one to five zoom targets.')
    learned=style(api);batch=api.ident();jobs=[];seen=set()
    for target in targets:
        project=api.s.project_path(target['project']);tl,draft,path=api.s.load_timeline(project,target['timeline'])
        pair=(project.name,tl['id'])
        if pair in seen:raise ValueError('Duplicate zoom target.')
        seen.add(pair)
        job,mapping,report=cached(api,project,tl,draft,target.get('analysis_job_id'))
        if extract(draft):raise ValueError('Target already has punch-ins; manual zooms are protected.')
        zid=api.ident();dest=folder(api,zid);dest.mkdir(parents=True)
        record={'job_id':zid,'batch_id':batch,'project':project.name,'timeline':tl['name'],'timeline_id':tl['id'],'source_hash':api.digest(path),
            'analysis_job_id':job,'style_version':learned['version'],'duration':draft['duration']/1e6,'status':'ready'}
        catalogue=api.s.read_json(api.job_path(job)/'catalog.json')
        sounds=api.ra.logical_events(list(api.s.flatten_sfx(draft,catalogue,project)))
        brief={'job_id':zid,'timeline':tl['name'],'duration':record['duration'],'dialogue':map_report(mapping,report),
            'captions':api.s.caption_rows(draft),'sfx':[{'start':e['start'],'end':e['start']+e['duration'],'sound':e['sound']} for e in sounds],
            'layout':[{'role':f'video_track_{i+1}','track_id':t.get('id'),'segments':[{'id':s['id'],'start':s['target_timerange']['start']/1e6,'end':(s['target_timerange']['start']+s['target_timerange']['duration'])/1e6,'clip':s.get('clip')} for s in t['segments']]} for i,t in enumerate(tracks(draft))],
            'zoom_style':learned,'analysis_reused':True}
        for name,value in [('job.json',record),('source.json',draft),('brief.json',brief)]:api.s.write_json(dest/name,value)
        jobs.append(zid)
    (api.STATE/'zoom_batches').mkdir(exist_ok=True)
    api.s.write_json(api.STATE/'zoom_batches'/(batch+'.json'),{'batch_id':batch,'jobs':jobs})
    return {'batch_id':batch,'jobs':jobs,'analysis_reused':True,'transcription_runs':0,'writes_to_capcut':False}


def briefs(api,batch_id):
    batch=api.s.read_json(api.STATE/'zoom_batches'/(api.safe_id(batch_id)+'.json'))
    rows=[api.s.read_json(folder(api,j)/'brief.json') for j in batch['jobs']];common=api.shared_fields(rows)
    value={'$shared':api.pack(common),'$jobs':[{'job_id':j,'$delta':api.pack(api.difference(r,common))} for j,r in zip(batch['jobs'],rows)]}
    for row,part in zip(rows,value['$jobs']):assert api.merge(api.unpack(value['$shared']),api.unpack(part['$delta']))==row
    return value


def context(api,job,start,end):
    r=data(api,job)
    if not 0<=start<end<=r['duration'] or end-start>12:raise ValueError('Use an in-video context window <=12 seconds.')
    b=api.s.read_json(folder(api,job)/'brief.json')
    return {'tracks':[{'role':t['role'],'speech':[r for r in t['speech'] if r['start']<end and r['end']>start]} for t in b['dialogue']['tracks']],
        'captions':[r for r in b['captions'] if r['start']<end and r['end']>start]}


def stage(api,job,zooms,quality_notes):
    r=data(api,job);dest=folder(api,job);b=api.s.read_json(dest/'brief.json');draft=api.s.read_json(dest/'source.json')
    if r['status']=='applied':raise ValueError('Already applied; learn the revision instead.')
    if not quality_notes.get('whole_video_reviewed') or not quality_notes.get('silence_reviewed') or quality_notes.get('unresolved'):
        raise ValueError('Review whole video, silence and unresolved zoom decisions.')
    fps=float(draft.get('fps',30));normalized=[];errors=[]
    # Report every invalid zoom in one pass so the host fixes all in one retry.
    for e in sorted(copy.deepcopy(zooms),key=lambda x:x.get('start',0)):
        try:normalized.append(_check_zoom(e,b,r,fps,normalized))
        except ValueError as err:errors.append(f"zoom @{e.get('start')}: {err}")
    if errors:raise ValueError(' | '.join(errors))
    plan={'job_id':job,'source_hash':r['source_hash'],'style_version':r['style_version'],'zooms':normalized,'quality_notes':quality_notes}
    # Build now to reject unsupported segments/materials before preview or any write.
    apply_native(api,draft,plan)
    api.s.write_json(dest/'plan.json',plan);r['status']='staged';api.s.write_json(dest/'job.json',r)
    return {'job_id':job,'zooms':len(normalized),'plan_hash':api.digest(dest/'plan.json'),'writes_to_capcut':False,'next':'preview_zoom_plan, inspect all images, then apply'}

def _check_zoom(e,b,r,fps,normalized):
        if not all(isinstance(e.get(k),(int,float)) and not isinstance(e[k],bool) and math.isfinite(e[k]) for k in ('start','end','scale')):
            raise ValueError('Zoom requires finite start/end/scale.')
        e.setdefault('role','video_track_1');e.setdefault('dx',0.0);e.setdefault('dy',0.0)
        if not 1.05<=e['scale']<=1.7 or not .2<=e['end']-e['start']<=4.5:raise ValueError('Zoom exceeds verified reaction scale/duration limits.')
        if not all(isinstance(e[k],(int,float)) and math.isfinite(e[k]) and abs(e[k])<=.3 for k in ('dx','dy')):raise ValueError('Invalid native transform offset.')
        if len(e.get('reason',''))<20 or len(e.get('dialogue',''))<2:raise ValueError('Every zoom needs an actual contextual reaction (dialogue >=2 chars) and reason (>=20 chars).')
        anchor=e.get('timing_anchor') or {}
        track=next((t for t in b['dialogue']['tracks'] if t['role']==anchor.get('role')),None)
        word=next((w for row in (track or {}).get('speech',[]) for w in row['words'] if w['word_index']==anchor.get('word_index')),None)
        if not word or abs(word['start']-anchor.get('at',-999))>2e-6 or word['text']!=anchor.get('text'):raise ValueError('Zoom needs a verified cached speech_word anchor (caption anchors are not accepted; use the nearest word plus offset_reason)'+(f"; word_index {anchor.get('word_index')} is {word['text']!r} at {word['start']}" if word else '')+'.')
        if anchor.get('kind')!='speech_word' or e['role']!=anchor['role']:raise ValueError('Reaction role must match speech anchor.')
        if abs(e['start']-word['start'])>.15 and len(anchor.get('offset_reason',''))<20:raise ValueError('Zoom onset >150ms from anchor needs a specific delivery/visual reason.')
        e['start']=round(round(e['start']*fps)/fps,6);e['end']=round(round(e['end']*fps)/fps,6)
        if not 0<=e['start']<e['end']<=r['duration']+.000002:raise ValueError('Zoom outside video.')
        if any(p['role']==e['role'] and p['end']>e['start'] for p in normalized):raise ValueError('Overlapping zooms.')
        return e


def check_segment(draft,seg):
    if seg.get('common_keyframes') or seg.get('keyframe_refs') or seg.get('lyric_keyframes'):raise ValueError('Existing keyframes protected; cannot safely split.')
    if seg.get('reverse') or seg.get('is_loop') or float(seg.get('speed',1))<=0:raise ValueError('Reverse/loop footage is unsupported.')
    clip=seg.get('clip') or {}
    if clip.get('rotation',0)!=0 or any(clip.get('flip',{}).values()):raise ValueError('Rotated/flipped footage needs explicit framing support.')
    if seg.get('render_timerange',{}).get('duration',0):raise ValueError('Nonempty render time range cannot be safely split.')
    if seg.get('responsive_layout',{}).get('enable'):raise ValueError('Responsive layout cannot be safely split.')
    if seg.get('group_id') or seg.get('template_id') or seg.get('digital_human_template_group_id'):
        raise ValueError('Grouped/template footage needs explicit split support.')
    video=next((m for m in draft['materials'].get('videos',[]) if m['id']==seg['material_id']),{})
    if video.get('freeze') or video.get('smart_motion') or video.get('surface_trackings') or video.get('video_algorithm',{}).get('algorithms') or video.get('stable',{}).get('stable_level',0):
        raise ValueError('Motion/freeze/stabilization processing needs explicit split support.')
    refs=set(seg.get('extra_material_refs',[]))
    for key,arr in draft['materials'].items():
        if not isinstance(arr,list):continue
        for mat in arr:
            if not isinstance(mat,dict) or mat.get('id') not in refs:continue
            if key=='speeds' and mat.get('curve_speed'):raise ValueError('Speed curves cannot be safely split.')
            if key=='material_animations' and mat.get('animations'):raise ValueError('Clip animations cannot be safely split.')
            if key in ('audio_fades','transitions','masks','video_effects','audio_effects'):
                raise ValueError('Time-dependent fade/transition/mask/effect needs explicit split support.')
            if mat.get('time_range') or mat.get('time_ranges'):raise ValueError('Timed native material needs explicit split support.')


def audio_signature(api,draft):
    return {'video_timing':api.s.video_timing_signature(draft),'video_levels':api.ra.level_spans(draft),
        'other_tracks':[t for t in draft['tracks'] if t.get('type')!='video'],
        'audio_materials':{k:v for k,v in draft['materials'].items() if k in ('audios','drafts','audio_fades','audio_effects')}}


def apply_native(api,draft,plan):
    result=copy.deepcopy(draft);before=audio_signature(api,draft);roles=tracks(result)
    for role,track in enumerate(roles):
        events=[e for e in plan['zooms'] if e['role']==f'video_track_{role+1}'];new=[]
        for seg in track['segments']:
            tr=seg['target_timerange'];start=tr['start'];end=start+tr['duration']
            active=[e for e in events if round(e['start']*1e6)<end and round(e['end']*1e6)>start]
            if not active:new.append(seg);continue
            check_segment(result,seg)
            src=seg['source_timerange'];speed=float(seg.get('speed',1))
            if abs(src['duration']-tr['duration']*speed)>3:raise ValueError('Source/target time ratio mismatch.')
            boundaries=sorted({start,end,*[max(start,min(end,round(e[k]*1e6))) for e in active for k in ('start','end')]})
            for lo,hi in zip(boundaries,boundaries[1:]):
                piece=copy.deepcopy(seg);piece['id']=api.s.uid();piece['target_timerange']={'start':lo,'duration':hi-lo}
                src_lo=src['start']+round((lo-start)*speed);src_hi=src['start']+round((hi-start)*speed)
                if hi==end:src_hi=src['start']+src['duration']
                piece['source_timerange']={'start':src_lo,'duration':src_hi-src_lo}
                # Native editor creates fresh linked material IDs for independent cuts.
                for key,arr in list(result['materials'].items()):
                    if not isinstance(arr,list):continue
                    ids=[piece['material_id']] if key=='videos' else list(piece.get('extra_material_refs',[]))
                    for ref in ids:
                        mat=next((m for m in arr if isinstance(m,dict) and m.get('id')==ref),None)
                        if mat is None:continue
                        clone=copy.deepcopy(mat);clone['id']=api.s.uid();arr.append(clone)
                        if key=='videos':piece['material_id']=clone['id']
                        else:piece['extra_material_refs']=[clone['id'] if x==ref else x for x in piece['extra_material_refs']]
                event=next((e for e in active if round(e['start']*1e6)<=lo and hi<=round(e['end']*1e6)),None)
                if event:
                    piece['clip']['scale']={k:v*event['scale'] for k,v in seg['clip']['scale'].items()}
                    piece['clip']['transform']['x']+=event.get('dx',0);piece['clip']['transform']['y']+=event.get('dy',0)
                new.append(piece)
        track['segments']=new
    if any(e['role'] not in [f'video_track_{i+1}' for i in range(len(roles))] for e in plan['zooms']):raise ValueError('Unknown zoom role.')
    for e in plan['zooms']:
        t=roles[int(e['role'].rsplit('_',1)[1])-1]
        coverage=sum(max(0,min(s['target_timerange']['start']+s['target_timerange']['duration'],round(e['end']*1e6))-max(s['target_timerange']['start'],round(e['start']*1e6))) for s in t['segments'])
        if abs(coverage-round((e['end']-e['start'])*1e6))>2:raise ValueError('Zoom crosses missing/overlapping video coverage.')
    if before!=audio_signature(api,result):raise ValueError('Zoom unexpectedly changed timing/audio/captions; rejected.')
    api.s.validate_draft(result)
    return result


def preview(api,job):
    """Decode exact cached-footage times for layout QA; no speech or scene inference."""
    import context_pipeline as c
    from PIL import Image,ImageDraw
    r=data(api,job);dest=folder(api,job);plan=api.s.read_json(dest/'plan.json');draft=api.s.read_json(dest/'source.json')
    project=api.s.project_path(r['project']);_,current,path=api.s.load_timeline(project,r['timeline_id'])
    if api.digest(path)!=r['source_hash']:raise ValueError('Timeline changed before visual preview.')
    cached(api,project,{'id':r['timeline_id']},current,r['analysis_job_id'])
    changed=apply_native(api,draft,plan);rows=max(1,len(plan['zooms']));W,H=270,480
    sheet=Image.new('RGB',(W*3,H*rows+30),(25,25,25));draw=ImageDraw.Draw(sheet)
    def render(d,at,tag):
        canvas=Image.new('RGB',(W,H));mats={m['id']:m for m in d['materials']['videos']}
        config=d.get('canvas_config') or {'width':1080,'height':1920};cw,ch=config['width'],config['height']
        for i,track in enumerate(tracks(d)):
            seg=next((s for s in track['segments'] if s['target_timerange']['start']/1e6<=at<(s['target_timerange']['start']+s['target_timerange']['duration'])/1e6),None)
            if not seg:continue
            mat=mats[seg['material_id']];src=seg['source_timerange']['start']/1e6+(at-seg['target_timerange']['start']/1e6)*float(seg.get('speed',1))
            source_path=api.s.resolve_path(mat['path'],project)
            key=api.stable_digest({'path':str(source_path),'mtime':source_path.stat().st_mtime_ns,'source_at':round(src,6)})[:20]
            image_path=dest/f'decoded-{key}.jpg'
            if not image_path.exists():c.run_ffmpeg(['-ss',str(src),'-i',str(api.s.resolve_path(mat['path'],project)),'-frames:v','1','-vf','scale=540:-2','-y',str(image_path)])
            image=Image.open(image_path).convert('RGB');crop=mat.get('crop',{});x0=crop.get('upper_left_x',0);y0=crop.get('upper_left_y',0);x1=crop.get('lower_right_x',1);y1=crop.get('lower_right_y',1)
            image=image.crop((round(x0*image.width),round(y0*image.height),round(x1*image.width),round(y1*image.height)))
            fit=min(W/image.width,H/image.height);clip=seg['clip'];w=round(image.width*fit*clip['scale']['x']);h=round(image.height*fit*clip['scale']['y'])
            image=image.resize((w,h));x=round((W-w)/2+clip['transform']['x']*W/2);y=round((H-h)/2-clip['transform']['y']*H/2)
            canvas.paste(image,(x,y))
        return canvas
    for i,e in enumerate(plan['zooms']):
        for j,(d,at) in enumerate([(draft,(e['start']+e['end'])/2),(changed,e['start']+.04),(changed,max(e['start'],e['end']-.04))]):
            im=render(d,at,f'frame-{i}-{j}');sheet.paste(im,(j*W,i*H+30))
        draw.text((5,i*H+32),f"{e['start']:.2f}-{e['end']:.2f}s  {e['scale']:.2f}x",fill='yellow')
    draw.text((5,6),'Baseline / Zoom onset / Zoom end (layout preview; no captions/effects)',fill='white')
    path=dest/'zoom-preview.jpg';sheet.save(path,quality=88)
    report={'job_id':job,'plan_hash':api.digest(dest/'plan.json'),'image':str(path),'image_hash':api.digest(path),'zooms':len(plan['zooms']),
        'note':'Approximate native scale/position compositing. Captions, effects and color processing omitted. Inspect head/eyes, split boundary and resets; native CapCut rendering remains unverified.'}
    api.s.write_json(dest/'preview.json',report);return report


def validated_native(api,job,draft):
    r=data(api,job);dest=folder(api,job);plan=api.s.read_json(dest/'plan.json')
    if r['status']!='staged':raise ValueError('Every zoom target must be staged.')
    if plan['source_hash']!=r['source_hash'] or plan['style_version']!=style(api)['version']:raise ValueError('Zoom source/style changed; restage.')
    review=api.s.read_json(dest/'preview.json')
    if review['plan_hash']!=api.digest(dest/'plan.json') or review['image_hash']!=api.digest(review['image']):raise ValueError('Zoom plan changed after preview.')
    if not plan['quality_notes'].get('framing_reviewed'):raise ValueError('Inspect all preview frames and mark framing_reviewed before apply.')
    project=api.s.project_path(r['project']);_,current,path=api.s.load_timeline(project,r['timeline_id'])
    if api.digest(path)!=r['source_hash']:raise ValueError('Target changed; manual edits protected.')
    cached(api,project,{'id':r['timeline_id']},current,r['analysis_job_id'])
    return apply_native(api,draft,plan)


def changes(api,batch_id):
    batch=api.s.read_json(api.STATE/'zoom_batches'/(api.safe_id(batch_id)+'.json'));result={}
    for job in batch['jobs']:
        r=data(api,job);pr=api.s.project_path(r['project']);tl,current,path=api.s.load_timeline(pr,r['timeline_id'])
        draft=validated_native(api,job,current);result[path]=draft
        # Keep the active timeline; sync root only if this edited tab is active.
        if api.s.is_main_timeline(pr,tl):result[api.s.draft_file(pr)]=draft
    return batch,result


def apply_batch(api,batch_id,auto_close=True):
    with api.lock('zoom-style'),api.lock('capcut-write'):
        if not auto_close:api.close_for_apply(False)
        changes(api,batch_id)
        closure=api.close_for_apply(auto_close)
        batch,result=changes(api,batch_id);previous={p:p.read_bytes() for p in result}
        if api.s.capcut_running() or any(p.read_bytes()!=b for p,b in previous.items()):raise ValueError('Project changed during zoom preflight.')
        try:
            for path,value in result.items():
                if api.s.capcut_running():raise ValueError('CapCut reopened; roll back zoom writes.')
                api.s.write_json(path,value)
        except Exception:
            for path,raw in previous.items():path.write_bytes(raw)
            raise
        for job in batch['jobs']:
            r=data(api,job);r.update(status='applied',applied_at=time.time());api.s.write_json(folder(api,job)/'job.json',r)
            # Later SFX revision learning also sees this standalone zoom revision.
            linked=api.job_data(r['analysis_job_id']);linked['zoom_job_id']=job
            api.s.write_json(api.job_path(r['analysis_job_id'])/'job.json',linked)
    return {'installed':True,'targets':len(batch['jobs']),'zooms':sum(len(api.s.read_json(folder(api,j)/'plan.json')['zooms']) for j in batch['jobs']),
        'analysis_reused':True,'transcription_runs':0,'sfx_audio_captions_unchanged':True,'saved_backups':False,'capcut_close':closure}


def learn_revision(api,job):
    r=data(api,job)
    if r['status']!='applied':raise ValueError('Only an applied zoom can be compared with a manual revision.')
    project=api.s.project_path(r['project']);tl,draft,path=api.s.load_timeline(project,r['timeline_id']);manual_hash=api.digest(path);planned=api.s.read_json(folder(api,job)/'plan.json')['zooms']
    # Store the latest manual truth for this footage, including deliberate silence.
    historical_cached(api,project,tl,draft,r['analysis_job_id']);observed=extract(draft)
    mapping=api.ra.TimelineMap(api.s.read_json(api.job_path(r['analysis_job_id'])/'source.json'),draft)
    report=api.s.read_json(api.job_path(r['analysis_job_id'])/'context_report.json')
    for e in observed:
        e['contexts']=[{'role':t['role'],'text':api.ra.word_context(report,i,mapping.old_time(i,e['start']))} for i,t in enumerate(report['tracks'])];e.pop('native_clip')
    diff=revision_diff(planned,observed)
    ref={'project':project.name,'timeline':tl['name'],'timeline_id':tl['id'],'source_hash':manual_hash,'analysis_job_id':r['analysis_job_id'],'events':observed,
        'video_signature':api.stable_digest(api.s.video_timing_signature(draft)),'revision_diff':diff,
        'predicted':planned,
        'scope':'Manual examples and removed/retimed predicted zooms for this scene; no automatic global keyword rule.'}
    with api.lock('zoom-style'):
        value=style(api);existing=next((x for x in value['references'] if x['project']==project.name and x['timeline_id']==tl['id']),None)
        if existing and existing['source_hash']==ref['source_hash']:return {'already_learned':True,'version':value['version']}
        if api.digest(path)!=manual_hash:raise ValueError('Manual zoom revision changed during reading; save then retry.')
        history=api.STATE/'history'/('zoom-'+api.stable_digest({'job':job,'hash':manual_hash})+'.json')
        api.s.write_json(history,{'previous_style':value,'job_id':job,'manual_reference':ref})
        value['references']=[x for x in value['references'] if (x['project'],x['timeline_id'])!=(project.name,tl['id'])]+[ref];value['version']+=1
        refresh_statistics(value)
        api.s.write_json(api.STATE/'data'/'zoom_style.json',value)
    return {'version':value['version'],'predicted':len(planned),'manual':len(observed),'diff':diff,
        'added_contexts':[observed[j] for j in diff['added']],'analysis_reused':True,'scope':ref['scope'],'writes_to_capcut':False}
