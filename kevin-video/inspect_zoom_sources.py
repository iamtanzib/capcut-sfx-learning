"""Read-only inspect saved native transforms and cached job correspondence."""
import json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'plugins/capcut-sfx-learning'))
import service as a
project=a.s.project_path('test 1')
report={'timelines':[],'jobs':[],'capcut_running':a.s.capcut_running()}
for name in [f'Day {day}.{i}' for day in (7,1) for i in range(3,7)]:
    tl,d,path=a.s.load_timeline(project,name)
    item={'name':name,'id':tl['id'],'path':str(path),'hash':a.digest(path),'duration':d['duration']/1e6,'video_tracks':[]}
    for track in d['tracks']:
        if track['type']!='video':continue
        segs=[]
        for seg in track['segments']:
            v=next((v for v in d['materials']['videos'] if v['id']==seg['material_id']),{})
            segs.append({k:seg.get(k) for k in ('id','material_id','target_timerange','source_timerange','clip','common_keyframes','keyframe_refs','extra_material_refs','uniform_scale','is_loop','enable_adjust','render_index')})
            segs[-1]['name']=v.get('material_name',v.get('path',''))
        item['video_tracks'].append({'id':track['id'],'segments':segs})
    item['keyframe_materials']={k:v for k,v in d['materials'].items() if 'anim' in k or 'keyframe' in k}
    report['timelines'].append(item)
for folder in sorted((a.STATE/'jobs').iterdir()):
    if not (folder/'job.json').exists():continue
    r=a.s.read_json(folder/'job.json')
    if r.get('timeline') in [x['name'] for x in report['timelines']]:
        report['jobs'].append({**r,'files':[f.name for f in folder.iterdir() if f.is_file()]})
out=BASE/'outputs/zoom-feature';out.mkdir(exist_ok=True)
a.s.write_json(out/'SOURCE_INSPECTION.json',report)
for tl in report['timelines']:
    print(json.dumps({'name':tl['name'],'duration':tl['duration'],'tracks':[{'segments':len(t['segments']),'transforms':[{'start':s['target_timerange']['start']/1e6,'duration':s['target_timerange']['duration']/1e6,'name':Path(s['name']).name,'clip':s['clip'],'keyframes':s['common_keyframes'],'refs':s['keyframe_refs']} for s in t['segments']]} for t in tl['video_tracks']]},ensure_ascii=False))
print(json.dumps({'jobs':[{'job_id':r['job_id'],'timeline':r['timeline'],'status':r['status'],'files':r['files']} for r in report['jobs']],'capcut_running':report['capcut_running']},ensure_ascii=False))
