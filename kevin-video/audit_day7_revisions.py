"""Read-only actual revision diffs: selection, timing, trims, fades and gain."""
import sys,math,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'plugins/capcut-sfx-learning'))
import service as a
def db(value):return round(20*math.log10(value),2) if value>0 else None
def fades(effect):
    refs=set(effect['segment'].get('extra_material_refs',[]));arr=effect['materials'].get('audio_fades',[])
    f=next((m for m in arr if m.get('id') in refs),{})
    return [f.get('fade_in_duration',0)/1e6,f.get('fade_out_duration',0)/1e6]
batch=a.s.read_json(ROOT/'outputs/day7-batch/INSTALL_RESULT.json');sounds=a.s.read_json(a.s.DATA/'sound_catalog.json');project=a.s.project_path('test 1')
reports=[];all_matched=[]
for row in batch['rows']:
    job=row['job_id'];folder=a.job_path(job);plan=a.s.read_json(folder/'plan.json');record=a.job_data(job)
    timeline,draft,path=a.s.load_timeline(project,record['timeline_id']);before=a.digest(path)
    same_video=a.s.video_timing_signature(a.s.read_json(folder/'source.json'))==a.s.video_timing_signature(draft)
    truth=sorted(a.s.flatten_sfx(draft,sounds,project),key=lambda x:x['start']);pred=[e for e in plan['effects'] if e.get('enabled',True)]
    strict=a.revision_diff(pred,truth,.75);loose=a.revision_diff(pred,truth,3)
    gain=plan.get('master_gain',1);matches=[]
    for pair in loose['matches']:
        old=pred[pair['old']];new=truth[pair['manual']];installed=old['volume']*gain
        fi,fo=fades(new)
        matches.append({'sound':old['sound'],'cue':old['dialogue'],'old_start':old['start'],'manual_start':round(new['start'],3),'time_change':pair['delta'],
            'planned_volume':old['volume'],'installed_volume':round(installed,6),'manual_volume':round(new['volume'],6),
            'installed_db':db(installed),'manual_db':db(new['volume']),'change_db':db(new['volume']/installed),
            'old_duration':old['duration'],'manual_duration':round(new['duration'],3),'old_source_start':old['source_start'],'manual_source_start':round(new['source_start'],3),
            'old_fades':[old['fade_in'],old['fade_out']],'manual_fades':[fi,fo], 'compound':new['compound']})
    mats={m['id']:m for m in draft['materials'].get('videos',[])}
    voices=[{'name':mats.get(seg['material_id'],{}).get('material_name',Path(mats.get(seg['material_id'],{}).get('path','')).name),'start':seg['target_timerange']['start']/1e6,
        'duration':seg['target_timerange']['duration']/1e6,'volume':seg.get('volume',1),'db':db(seg.get('volume',1))} for t in draft['tracks'] if t['type']=='video' for seg in t['segments']]
    report={'job':job,'timeline':timeline['name'],'same_video_timing':same_video,'sha256':before,'old_cues':len(pred),'manual_cues':len(truth),'strict':strict,
        'old_master_gain':gain,'voice_levels':voices,'matched':matches,
        'unmatched_old':[{'sound':pred[i]['sound'],'start':pred[i]['start'],'cue':pred[i]['dialogue']} for i in loose['removed']],
        'unmatched_manual':[{'sound':truth[i]['sound'],'start':round(truth[i]['start'],3),'duration':round(truth[i]['duration'],3),'volume':truth[i]['volume'],'db':db(truth[i]['volume'])} for i in loose['added']]}
    assert a.digest(path)==before,'Revision changed while reading; retry.'
    reports.append(report);all_matched+=matches
summary=[]
for sound in sorted({r['sound'] for r in all_matched}):
    rs=[r for r in all_matched if r['sound']==sound];summary.append({'sound':sound,'matched':len(rs),'volume_changes':sum(abs(r['change_db'] or 0)>.25 for r in rs),
        'median_installed_db':statistics.median(r['installed_db'] for r in rs),'median_manual_db':statistics.median(r['manual_db'] for r in rs),
        'median_change_db':statistics.median(r['change_db'] for r in rs),'manual_volumes':sorted({r['manual_volume'] for r in rs})})
out=ROOT/'outputs/day7-revision';out.mkdir(exist_ok=True);a.s.write_json(out/'DIFF.json',{'timelines':reports,'sound_level_summary':summary,'projects_modified':False})
print(json.dumps({'sound_level_summary':summary,'timelines':reports},ensure_ascii=False,indent=2))
