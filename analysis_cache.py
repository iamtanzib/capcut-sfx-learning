"""Seven-day media analysis reuse, independent of SFX/zoom/text/style edits."""
import copy,time,json
from pathlib import Path
TTL=7*24*3600

def index(api):
    p=api.STATE/'data/analysis_index.json'
    return api.s.read_json(p) if p.exists() else {'schema':1,'ttl_days':7,'entries':{}}

def register(api,job_id):
    import context_pipeline as c
    folder=api.job_path(job_id);rec=api.job_data(job_id)
    if not (folder/'context_report.json').exists():return None
    report=api.s.read_json(folder/'context_report.json');source=api.s.read_json(folder/'source.json')
    project=api.s.project_path(rec['project']);inputs,key=c.context_inputs(project,source)
    if report.get('cache_key')!=key:raise ValueError('Cached source media/config fingerprint is stale.')
    if report.get('model',api.s.config()['speech_model'])!=api.s.config()['speech_model']:raise ValueError('Cached speech model differs.')
    created=report.get('analysis_created_at')
    if created is None:
        root=Path(report.get('cache_folder',''));files=list(root.glob('*.json')) if root.is_dir() else []
        created=min([p.stat().st_mtime for p in files] or [rec.get('created_at',(folder/'context_report.json').stat().st_mtime)])
    value={'job_id':job_id,'project':rec['project'],'source_input_key':key,'created_at':created,'expires_at':created+TTL,
        'signature':api.stable_digest(api.s.video_timing_signature(source)),'roles':len(inputs['tracks'])}
    with api.lock('analysis-index'):
        data=index(api);data['entries'][job_id]=value;api.s.write_json(api.STATE/'data/analysis_index.json',data)
    return value

def backfill(api):
    known=index(api)['entries'];added=0
    for path in (api.STATE/'jobs').glob('*/context_report.json'):
        job=path.parent.name
        if job in known:continue
        try:register(api,job);added+=1
        except (ValueError,KeyError,OSError):continue
    return added

def find(api,project,draft,job_id=None,allow_expired=False):
    """Validate file stats/model, then map original words to current footage."""
    import context_pipeline as c
    import zoom
    if job_id:register(api,job_id)
    else:backfill(api)
    entries=index(api)['entries'];rows=[entries[job_id]] if job_id in entries else list(entries.values())
    rows.sort(key=lambda e:e['created_at'],reverse=True)
    for entry in rows:
        if not allow_expired and time.time()>=entry['expires_at']:continue
        try:
            folder=api.job_path(entry['job_id']);source=api.s.read_json(folder/'source.json');old_project=api.s.project_path(entry['project'])
            if c.context_inputs(old_project,source)[1]!=entry['source_input_key']:continue
            report=api.s.read_json(folder/'context_report.json')
            if report.get('model',api.s.config()['speech_model'])!=api.s.config()['speech_model']:continue
            before=copy.deepcopy(source);after=copy.deepcopy(draft)
            for document,root in ((before,old_project),(after,project)):
                for mat in document['materials'].get('videos',[]):
                    if mat.get('path'):mat['path']=str(api.s.resolve_path(mat['path'],root).resolve())
            mapping=api.ra.TimelineMap(before,after)
            for track in mapping.after:
                for i,left in enumerate(track):
                    for right in track[i+1:]:
                        if left['path']==right['path'] and max(left['source_start'],right['source_start'])<min(left['source_start']+left['duration']*left['speed'],right['source_start']+right['duration']*right['speed'])-2e-6:
                            raise ValueError('Repeated source samples need fresh analysis.')
            if len(zoom.tracks(draft))!=entry['roles']:continue
            return {'entry':entry,'mapping':mapping,'report':report,'source':source,'job_id':entry['job_id']}
        except (ValueError,KeyError,OSError):continue
    raise LookupError('No verified, compatible seven-day analysis. Prepare this video once; no stale evidence was used.')

def mapped_report(api,result,draft):
    import zoom
    report=copy.deepcopy(result['report']);mapping=result['mapping'];mapped=zoom.map_report(mapping,report)
    for old,new in zip(report['tracks'],mapped['tracks']):old['speech']=new['speech'];old['cached']=True;old.setdefault('loud_moments',[]);old.setdefault('transcription_seconds',0)
    same=api.s.video_timing_signature(result['source'])==api.s.video_timing_signature(draft)
    if not same:
        scenes=[]
        for role,group in enumerate(report.get('scenes',[])):
            rows=[]
            for row in group['scenes']:
                for old in mapping.before[role]:
                    lo=max(row['start'],old['start']);hi=min(row['end'],old['start']+old['duration'])
                    if hi<=lo:continue
                    src_lo=old['source_start']+(lo-old['start'])*old['speed'];src_hi=old['source_start']+(hi-old['start'])*old['speed']
                    for current in mapping.after[role]:
                        if current['path']!=old['path']:continue
                        a=max(src_lo,current['source_start']);b=min(src_hi,current['source_start']+current['duration']*current['speed'])
                        if b>a:rows.append({'start':current['start']+(a-current['source_start'])/current['speed'],'end':current['start']+(b-current['source_start'])/current['speed']})
            rows.sort(key=lambda x:x['start'])
            scenes.append({'role':group['role'],'scenes':rows})
        report['scenes']=scenes;report['keyframes']=[];report['visual_refresh_required']=True
    report.update(analysis_reused=True,reused_analysis_job_id=result['job_id'],analysis_created_at=result['entry']['created_at'],analysis_expires_at=result['entry']['expires_at'])
    return report

def info(api):
    backfill(api);rows=list(index(api)['entries'].values());now=time.time()
    return {'ttl_days':7,'active':sum(e['expires_at']>now for e in rows),'expired':sum(e['expires_at']<=now for e in rows),
        'policy':'Reusable media analysis expires after seven days; learned rules and revision history remain durable. Source changes/model changes invalidate reuse. Reads do not extend expiry.'}
