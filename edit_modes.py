"""User-facing edit modes share one local analysis, with isolated component plans."""
import copy,time
def mode(value):
    key=' '.join(value.lower().replace('_',' ').replace('-',' ').split())
    aliases={'full combo':'full_combo','full combo edit':'full_combo','full':'full_combo',
        'just sfx':'just_sfx','just sfz':'just_sfx','sfx only':'just_sfx',
        'just zoom':'just_zoom','just zoom line':'just_zoom','zoom only':'just_zoom',
        'just text hook':'just_text_hook','text hook only':'just_text_hook'}
    if key not in aliases:raise ValueError('Use just sfx, just zoom, just text hook, or full combo edit.')
    return aliases[key]
def load(api,batch):return api.s.read_json(api.STATE/'edit_batches'/(api.safe_id(batch)+'.json'))
def prepare(api,targets,edit_mode='full_combo',workers=2):
    chosen=mode(edit_mode);analysis=api.prepare_batch(targets,workers,include_zoom=chosen=='full_combo',include_hook=chosen=='full_combo')
    record={'batch_id':analysis['batch_id'],'mode':chosen,'analysis_batch_id':analysis['batch_id'],'targets':targets,'analysis_jobs':analysis['jobs']}
    (api.STATE/'edit_batches').mkdir(exist_ok=True);api.s.write_json(api.STATE/'edit_batches'/(record['batch_id']+'.json'),record)
    return {**analysis,'mode':chosen,'next':'batch_status then get_edit_briefs. One analysis is shared by all selected components.'}
def briefs(api,batch,lean=0):
    import hooks,zoom
    rec=load(api,batch);records=[api.job_data(j) for j in rec['analysis_jobs']]
    if any(r['status'] not in ('ready','staged','applied') for r in records):raise ValueError('Wait for all analysis jobs; inspect batch_status failures.')
    targets=[{'project':r['project'],'timeline':r['timeline_id'],'analysis_job_id':r['job_id']} for r in records]
    if rec['mode'] in ('full_combo','just_text_hook') and not rec.get('hook_batch_id'):
        child=hooks.prepare(api,targets);rec.update(hook_batch_id=child['batch_id'],hook_jobs=child['jobs'])
        if rec['mode']=='full_combo':
            for j,h in zip(rec['analysis_jobs'],child['jobs']):
                r=api.job_data(j);r['hook_job_id']=h;api.s.write_json(api.job_path(j)/'job.json',r)
    if rec['mode']=='just_zoom' and not rec.get('zoom_batch_id'):
        child=zoom.prepare(api,targets);rec.update(zoom_batch_id=child['batch_id'],zoom_jobs=child['jobs'])
    api.s.write_json(api.STATE/'edit_batches'/(batch+'.json'),rec)
    if rec['mode']=='just_text_hook':return {'mode':rec['mode'],'hook_batch_id':rec['hook_batch_id'],**hooks.briefs(api,rec['hook_batch_id'])}
    if rec['mode']=='just_zoom':return {'mode':rec['mode'],'zoom_batch_id':rec['zoom_batch_id'],**zoom.briefs(api,rec['zoom_batch_id'])}
    rows=[api.get_brief(j,True) for j in rec['analysis_jobs']]
    if rec['mode']=='full_combo':
        for row,j in zip(rows,rec['hook_jobs']):row['text_hook']=api.s.read_json(hooks.path(api,j)/'brief.json');row['hook_job_id']=j
    import lean as ln
    rows=ln.apply(rows,lean);common=api.shared_fields(rows)
    value={'mode':rec['mode'],'$shared':api.pack(common),'$jobs':[{'job_id':j,'$delta':api.pack(api.difference(r,common))} for j,r in zip(rec['analysis_jobs'],rows)]}
    for row,part in zip(rows,value['$jobs']):assert api.merge(api.unpack(value['$shared']),api.unpack(part['$delta']))==row,'Edit briefing evidence changed.'
    return value
def apply(api,batch,auto_close=True):
    import hooks,zoom
    rec=load(api,batch)
    if rec['mode'] in ('full_combo','just_sfx'):return api.apply_batch(rec['analysis_batch_id'],auto_close)
    if rec['mode']=='just_zoom':return api.apply_zoom_batch(rec['zoom_batch_id'],auto_close)
    return apply_hooks(api,rec['hook_jobs'],auto_close)
def apply_hooks(api,jobs,auto_close=True):
    import hooks
    with api.lock('hook-style'),api.lock('capcut-write'):
        def build():
            result={}
            for j in jobs:
                rec=hooks.record(api,j);pr=api.s.project_path(rec['project']);tl,current,path=api.s.load_timeline(pr,rec['timeline_id'])
                updated=hooks.validated(api,j,current)
                if updated==current:continue
                result[path]=updated
                if api.s.is_main_timeline(pr,tl):result[api.s.draft_file(pr)]=updated
            return result
        changes=build()
        closure={'auto_close_requested':False,'not_needed':True}
        if changes:
            closure=api.close_for_apply(auto_close)
            changes=build()
        previous={p:p.read_bytes() for p in changes}
        try:
            for p,value in changes.items():
                if api.s.capcut_running():raise ValueError('CapCut reopened; rollback hook writes.')
                if p.read_bytes()!=previous[p]:raise ValueError('Timeline changed during text-hook apply.')
                api.s.write_json(p,value)
        except Exception:
            for p,value in previous.items():p.write_bytes(value)
            raise
        for j in jobs:
            r=hooks.record(api,j);r.update(status='applied',applied_at=time.time());api.s.write_json(hooks.path(api,j)/'job.json',r)
            parent=api.job_data(r['analysis_job_id']);parent['hook_job_id']=j;api.s.write_json(api.job_path(r['analysis_job_id'])/'job.json',parent)
    return {'installed':True,'targets':len(jobs),'files_written':len(changes),'manual_filled_hooks_preserved':True,'saved_backups':False,'capcut_close':closure}

def learn(api,batch):
    rec=load(api,batch);reports=[]
    for i,j in enumerate(rec['analysis_jobs']):
        r=api.job_data(j)
        if rec['mode'] in ('full_combo','just_sfx'):report=api.learn_revision(j,r['project'],r['timeline_id'])
        elif rec['mode']=='just_zoom':report=api.learn_zoom_revision(rec['zoom_jobs'][i])
        else:report=api.learn_hook_revision(rec['hook_jobs'][i])
        reports.append({'timeline':r['timeline'],'report':report})
    return {'mode':rec['mode'],'reports':reports,'writes_to_capcut':False}
