"""Read existing job analyses; extract reference zoom beats without inference."""
import json,sys,statistics
from pathlib import Path
BASE=Path(__file__).resolve().parent;sys.path.insert(0,str(BASE/'plugins/capcut-sfx-learning'))
import service as a
refs={'Day 7.3':'a1c942f5b10f472c','Day 7.4':'7f054b42880d4633','Day 7.5':'965e2fa694c24212','Day 7.6':'1ae7d2f210584a20'}
targets={'Day 1.3':'de75ea7cac714aa9','Day 1.4':'7bd393afde57469e','Day 1.5':'f9d86591573b4c82','Day 1.6':'94bc2d878df64d54'}
project=a.s.project_path('test 1');out={'references':[],'targets':[]}
for name,job in {**refs,**targets}.items():
    tl,d,path=a.s.load_timeline(project,name);cached=a.s.read_json(a.job_path(job)/'source.json');mapping=a.ra.TimelineMap(cached,d)
    r=a.s.read_json(a.job_path(job)/'context_report.json')
    item={'name':name,'job_id':job,'duration':d['duration']/1e6,'sfx':[{'start':e['start'],'duration':e['duration'],'sound':e['sound']} for e in a.ra.logical_events(list(a.s.flatten_sfx(d,a.s.read_json(a.job_path(job)/'catalog.json'),project)))], 'dialogue':[]}
    for track in r['tracks']:
        item['dialogue'].append({'role':track['role'],'sentences':[{'start':row['start'],'end':row['end'],'text':row['text']} for row in track['speech']]})
    if name in refs:
        track=next(t for t in d['tracks'] if t['type']=='video');segs=track['segments'];base=min(segs,key=lambda s:s['clip']['scale']['x'])['clip']
        item['zooms']=[]
        for seg in segs:
            if seg['clip']['scale']['x']<=base['scale']['x']*1.05:continue
            start=seg['target_timerange']['start']/1e6;end=start+seg['target_timerange']['duration']/1e6
            contexts=[]
            for role in range(len(r['tracks'])):
                at=mapping.old_time(role,start)
                contexts.append(a.ra.word_context(r,role,at))
            item['zooms'].append({'start':start,'end':end,'scale':seg['clip']['scale']['x'],'dx':seg['clip']['transform']['x']-base['transform']['x'],'dy':seg['clip']['transform']['y']-base['transform']['y'],'contexts':contexts})
        out['references'].append(item)
        print(json.dumps({k:v for k,v in item.items() if k not in ('dialogue','sfx')},ensure_ascii=False))
    else:
        out['targets'].append(item);print(json.dumps(item,ensure_ascii=False))
a.s.write_json(BASE/'outputs/zoom-feature/CACHED_BRIEFS.json',out)
# First native segment fields are diagnostic data, never instructions.
tl,d,path=a.s.load_timeline(project,'Day 1.3');seg=next(t for t in d['tracks'] if t['type']=='video')['segments'][0]
print(json.dumps({'native_segment':seg,'canvas':d.get('canvas_config'),'duration':d['duration']},ensure_ascii=False))
