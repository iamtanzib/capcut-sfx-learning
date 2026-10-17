"""Inventory every saved timeline's native text and available cached intro."""
import sys,json
from pathlib import Path
BASE=Path(__file__).resolve().parent;sys.path.insert(0,str(BASE/'plugins/capcut-sfx-learning'))
import service as a
import zoom
out=[]
for pr in a.s.list_projects():
    project=a.s.project_path(pr['name'])
    for tl in pr['timelines']:
        _,d,path=a.s.load_timeline(project,tl['id']);mats={m['id']:m for m in d['materials'].get('texts',[])};texts=[]
        for tr in d['tracks']:
            if tr['type']!='text':continue
            for seg in tr['segments']:
                mat=mats.get(seg['material_id'],{});raw=mat.get('content','')
                try:content=json.loads(raw)
                except (ValueError,TypeError):content={}
                texts.append({'segment':seg,'material':mat,'text':content.get('text',''),'parsed':content})
        candidates=[t for t in texts if t['segment']['target_timerange']['duration']>d['duration']*.5]
        item={'project':project.name,'timeline':tl['name'],'timeline_id':tl['id'],'duration':d['duration']/1e6,'hash':a.digest(path),'text_segments':len(texts),'long_text':candidates}
        try:
            job,mapping,report=zoom.cached(a,project,tl,d)
            item.update(analysis_job_id=job,cached_intro=[{'role':t['role'],'speech':[r for r in t['speech'] if r['start']<12]} for t in report['tracks']])
        except (ValueError,FileNotFoundError) as exc:item['cache_missing']=str(exc)
        out.append(item)
        print(json.dumps({'project':project.name,'timeline':tl['name'],'text_segments':len(texts),'hooks':[{'text':t['text'],'clip':t['segment'].get('clip'),'flags':{k:t['material'].get(k) for k in ('type','recognize_type','font_path','font_id','text_size')}} for t in candidates],'cached':item.get('analysis_job_id'),'intro':item.get('cached_intro',[])},ensure_ascii=False))
folder=BASE/'outputs/text-hook-feature';folder.mkdir(exist_ok=True)
a.s.write_json(folder/'TIMELINE_INVENTORY.json',out)
chosen=next((x for x in out if x['timeline']=='Day 1.6'),None)
if chosen:print(json.dumps({'reference_native_hook':chosen['long_text']},ensure_ascii=False))
