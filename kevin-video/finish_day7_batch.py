"""Refresh only proven-equivalent saved drafts, audit and apply authorized batch."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'plugins/capcut-sfx-learning'))
import service as a
import context_pipeline as c
OLD='a1e16077faa34a5c';NEW='45752ff3da4344b7'
old_batch=a.batch_data(OLD);new_batch=a.batch_data(NEW)
out=ROOT/'outputs/day7-batch';out.mkdir(exist_ok=True)
results=[]
for old,new in zip(old_batch['jobs'],new_batch['jobs']):
    record=a.job_data(new)
    if record['status']!='ready':raise ValueError('Wait for refreshed context: '+new)
    project=a.s.project_path(record['project']);old_draft=a.s.read_json(a.job_path(old)/'source.json');new_draft=a.s.read_json(a.job_path(new)/'source.json')
    assert c.context_inputs(project,old_draft)[0]==c.context_inputs(project,new_draft)[0],'Meaningful source change needs new decisions.'
    plan=a.s.read_json(a.job_path(old)/'plan.json');notes=plan['quality_notes'];notes['refresh_reason']='Only CapCut metadata normalization; media, edits, duration and captions verified equal.';notes['prior_job']=old
    a.stage_plan(new,plan['effects'],notes)
    if (a.job_path(old)/'alignment_check.json').exists():
        a.s.write_json(a.job_path(new)/'alignment_check.json',a.s.read_json(a.job_path(old)/'alignment_check.json'))
    mix=a.audit_mix(new);results.append({'timeline':record['timeline'],'job_id':new,'cues':len(plan['effects']),'master_gain':mix['master_gain']})
    print(json.dumps(results[-1]),flush=True)
preflight=a.preflight_batch(NEW);print(json.dumps(preflight),flush=True)
project=a.s.project_path('test 1');target_ids={a.job_data(j)['timeline_id'] for j in new_batch['jobs']}
others={str(path):a.digest(path) for t in a.s.timelines(project) if t['id'] not in target_ids for path in [a.s.load_timeline(project,t['id'])[2]]}
install=a.apply_batch(NEW)
for path,sha in others.items():assert a.digest(path)==sha,'An unrelated timeline changed.'
catalog=a.s.read_json(a.s.DATA/'sound_catalog.json')
for row in results:
    _,draft,path=a.s.load_timeline(project,a.job_data(row['job_id'])['timeline_id'])
    actual=list(a.s.flatten_sfx(draft,catalog,project));a.s.validate_draft(draft)
    assert len(actual)==row['cues'],'Installed cue count differs.'
    planned=[e for e in a.s.read_json(a.job_path(row['job_id'])/'plan.json')['effects'] if e.get('enabled',True)]
    pairs=sorted(actual,key=lambda e:(e['start'],e['sound'])),sorted(planned,key=lambda e:(e['start'],e['sound']))
    for actual_e,planned_e in zip(*pairs):
        assert actual_e['sound']==planned_e['sound'] and abs(actual_e['start']-planned_e['start'])<.00001
    row['installed_verified']=True
result={'batch_id':NEW,'rows':results,'total_cues':sum(r['cues'] for r in results),'unrelated_timelines_unchanged':True,'unrelated_timeline_count':len(others),'install':install}
a.s.write_json(out/'INSTALL_RESULT.json',result)
lines=['# Day 7.3–7.6 SFX batch','',f'Installed {result["total_cues"]} selected cues. {len(others)} other timelines unchanged. No saved project backup/copy created.','',
    '| Timeline | Cues | Verified |','|---|---:|---|']
for row in results:lines.append(f'| {row["timeline"]} | {row["cues"]} | yes |')
lines+=['','Day 7.6 selected onsets use raw-source speech, confirmed by a second short-window pass. Existing captions were preserved despite their timing mismatch.',
    '', 'Sample-peak mix checks passed with shared per-timeline attenuation. Playback listening is unverified in this text-only host; creative accuracy requires user review.','',
    'Clear approval uses MMM; smelly-feet and toothpaste-drinking confessions use FAH; explicit eww uses ewww. Doom/creepy/Among cues have specific scene evidence, with no palette quota.']
(out/'REVIEW.md').write_text('\n'.join(lines),encoding='utf-8');print(json.dumps(result,indent=2),flush=True)
