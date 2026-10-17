"""Measure exact table packing only; no inference or CapCut mutation."""
import sys,json,copy,tiktoken
from pathlib import Path
BASE=Path(__file__).resolve().parent;sys.path.insert(0,str(BASE/'plugins/capcut-sfx-learning'))
import service as a
from itertools import groupby
def encode(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def compact(v):
    if isinstance(v,list):
        if v and all(isinstance(x,dict) for x in v):
            keys=list(v[0])
            if all(set(x)==set(keys) for x in v):return {'$columns':keys,'$rows':[[compact(x[k]) for k in keys] for x in v]}
            chunks=[]
            for _,g in groupby(v,key=lambda x:tuple(sorted(x))):
                group=list(g);chunks.append(compact(group))
            ordinary=[compact(x) for x in v];segmented={'$segments':chunks}
            return segmented if len(encode(segmented))+40<len(encode(ordinary)) else ordinary
        return [compact(x) for x in v]
    if isinstance(v,dict):return {k:compact(x) for k,x in v.items()}
    return v
def expand(v):
    if isinstance(v,dict):
        if set(v)=={'$segments'}:return [x for chunk in v['$segments'] for x in expand(chunk)]
        if set(v)=={'$columns','$rows'}:return [dict(zip(v['$columns'],[expand(x) for x in r])) for r in v['$rows']]
        return {k:expand(x) for k,x in v.items()}
    return [expand(x) for x in v] if isinstance(v,list) else v
enc=tiktoken.get_encoding('o200k_base');count=lambda v:len(enc.encode(encode(v)))
sets={}
batch=a.batch_data('2fa25db946fd4806');rows=[a.get_brief(j,True) for j in batch['jobs']]
common=a.shared_fields(rows);sets['saved_sfx_batch']={'$shared':common,'$jobs':[{'job_id':j,'$delta':a.difference(r,common)} for j,r in zip(batch['jobs'],rows)]}
zoom=a.s.read_json('outputs/zoom-feature/BATCH_BRIEFS.json');sets['saved_zoom_batch']=a.unpack(zoom)
style=a.s.read_json(a.s.DATA/'style_profile.json');sets['latest_sfx_memory']=style;sets['latest_zoom_memory']=a.s.read_json(a.s.DATA/'zoom_style.json')
report=[]
for name,value in sets.items():
    old=a.pack(value);new=compact(value);assert expand(new)==value
    baseline=count(old);after=count(new)
    report.append({'dataset':name,'old_tokens':baseline,'new_tokens':after,'saving_pct':round(100*(1-after/baseline),1),'exact_roundtrip':True})
a.s.write_json(BASE/'outputs/zoom-feature/LOSSLESS_CANDIDATE.json',report)
print(json.dumps(report,indent=2))
