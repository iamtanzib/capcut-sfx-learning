"""Read frozen evidence only; compare exact candidate transport with 0.1.11."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('plugins/capcut-sfx-learning').resolve()))
import service as a
import tiktoken
enc=tiktoken.get_encoding('o200k_base')
dump=lambda v:json.dumps(v,ensure_ascii=False,separators=(',',':'))
def legacy_pack(v):
    if isinstance(v,list):
        if v and all(isinstance(x,dict) for x in v):
            keys=list(v[0])
            if all(set(x)==set(keys) for x in v):
                return {'$columns':keys,'$rows':[[legacy_pack(x[k]) for k in keys] for x in v]}
            from itertools import groupby
            parts=[legacy_pack(list(g)) for _,g in groupby(v,key=lambda x:tuple(sorted(x)))]
            normal=[legacy_pack(x) for x in v];seg={'$segments':parts}
            return seg if len(dump(seg))+40<len(dump(normal)) else normal
        return [legacy_pack(x) for x in v]
    if isinstance(v,dict):
        out={k:legacy_pack(x) for k,x in v.items()}
        return {'$literal':out} if set(v) in ({'$columns','$rows'},{'$segments'},{'$literal'}) else out
    return v
def batch(rows,jobs,packer):
    common=a.shared_fields(rows)
    return {'$shared':packer(common),'$jobs':[{'job_id':j,'$delta':packer(a.difference(r,common))} for j,r in zip(jobs,rows)]}
if __name__=='__main__':
    rec=a.s.read_json(a.STATE/'edit_batches/4d5daa2a9b234b22.json')
    rows=[a.get_brief(j,True) for j in rec['analysis_jobs']]
    hooks=[a.s.read_json(a.STATE/'hook_jobs'/j/'brief.json') for j in rec['hook_jobs']]
    combo=copy.deepcopy(rows)
    for r,h,j in zip(combo,hooks,rec['hook_jobs']):r['text_hook']=h;r['hook_job_id']=j
    sets={'sfx_batch':(rows,rec['analysis_jobs']),'full_combo_batch':(combo,rec['analysis_jobs']),'hook_only_batch':(hooks,rec['hook_jobs']),
        'sfx_memory':([a.s.read_json(a.STATE/'memory.json')],['memory'])}
    results={}
    dest=Path('outputs/token-compact-v012');dest.mkdir(exist_ok=True)
    for name,(values,ids) in sets.items():
        old=batch(values,ids,legacy_pack);new=batch(values,ids,a.pack)
        for row,part in zip(values,new['$jobs']):
            restored=a.merge(a.unpack(new['$shared']),a.unpack(part['$delta']))
            assert json.dumps(restored,sort_keys=True,ensure_ascii=False)==json.dumps(row,sort_keys=True,ensure_ascii=False)
        before=len(enc.encode(dump(old)));after=len(enc.encode(dump(new)))
        results[name]={'before_tokens':before,'after_tokens':after,'saving_pct':round((1-after/before)*100,2),'exact_json_roundtrip':True}
        (dest/(name+'-evidence.json')).write_text(dump({'rows':values,'jobs':ids}),encoding='utf-8')
    context_rows=[]
    for job in a.batch_data('2fa25db946fd4806')['jobs']:
        record=a.job_data(job);plan=a.s.read_json(a.job_path(job)/'plan.json')
        windows=[{'start':max(0,e['start']-1.2),'end':min(record['duration'],e['start']+2)} for e in plan['effects'] if e.get('enabled',True)]
        compact=a.get_context_batch(job,windows);pooled=a.unpack(compact)
        for window,refs in zip(windows,pooled['windows']):
            restored={'captions':[pooled['captions'][i] for i in refs['caption_ids']],
                'speech':[{'role':s['role'],'rows':[pooled['speech_rows'][i]['row'] for i in s['row_ids']]} for s in refs['speech']],
                'timing_audit':pooled['timing_audit'],'note':pooled['note']}
            assert json.dumps(restored,sort_keys=True)==json.dumps(a.get_context(job,**window),sort_keys=True)
        before=len(enc.encode(dump(legacy_pack(pooled))));after=len(enc.encode(dump(compact)))
        context_rows.append({'timeline':record['timeline'],'windows':len(windows),'before_tokens':before,'after_tokens':after,'exact_each_window_roundtrip':True})
    results={'tokenizer':'o200k_base','scope':'Text payload only; no model/reasoning/vision/quota measurement. Frozen four-video evidence, not a new creative quality evaluation.',
        'datasets':results,'pooled_context_rows':context_rows,'writes_to_capcut':False,'transcription_runs':0}
    (dest/'VERIFIED.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results))
