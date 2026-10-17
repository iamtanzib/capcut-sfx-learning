"""Ingest the four authorized manual revisions; never write a CapCut draft."""
import json,sys,statistics
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'plugins/capcut-sfx-learning'))
import service as api

def rule(text,evidence):
    return {'rule':text,'evidence':evidence,'scope':'scene_only','authority':'scene_inference'}

targets=[
('de75ea7cac714aa9',[
 rule('In this job-punishment scene, I need the job is a dry plea with awkward, not a funny-confession FAH.','User replaced FAH5.36s with awkward5.20s.'),
 rule('The thats-evil reaction has a specific short tindeck cartoon cue; it is not forced silence just because the line lacks a joke keyword.','User added tindeck_1.mp3 at12.466666s, gain0.226951.'),
 rule('Nail-bed refusal uses a long doom bell here; the later snow-duration reaction uses a short boom instead of the predicted bell. Do not generalize danger wording to one asset.','User replaced error23.15s with Undertaker23.166666s; removed bell41.43s and added vine41.766666s.'),
 rule('The illegal-punishment reaction carries a quiet Among texture in this scene, separately from the snow-duration boom.','User added Among38.0s for4.633333s, effective gain0.201876.'),
 rule('The torture suspense leads the voice attack rather than waiting at the old ASR/caption anchor.','User moved suspense34.33s to34.033333s; not-alive FAH47.95s to47.833333s.')]),
('7bd393afde57469e',[
 rule('Resolve the completed grass-blanket comfortable appraisal after the initial hesitation: the user added MMM rather than leaving it silent.','New MMM20.666666s at that-look-comfortable; awkward grass recognition retained and retimed16.6s to16.9s.'),
 rule('Blanket suspense belongs to the grass/insect what-the reaction before the spiderweb-name read.','User moved suspense24.05s to22.9s, leading the actual what reaction around22.94s.'),
 rule('The return-to-tortilla choice stays quiet here even though initial tortilla approval uses MMM. Do not sound every accepted-choice repeat.','User removed MMM47.34s; kept MMM9.8s.'),
 rule('Sandpaper reveal receives a separate short impact ahead of the later rejection error; these are distinct selected beats.','Added vine40.9s; error43.83s retained. Whole-blanket FAH moved37.25s to37.1s; cooked FAH54.78s to54.633333s.')]),
('f9d86591573b4c82',[
 rule('Teeth as currency is an observed Among scene, rather than a dry acquisition-question cue alone.','User replaced awkward26.84s with Among25.766666s for4.633334s, gain0.286832.'),
 rule('The suspicious teeth sequence builds suspense on the later who-I-got-them-from turn, then rejection on no.','Suspense moved28.55s to30.533333s; error31.2s to31.766666s. Do not call these deletions just because a move exceeds750ms.'),
 rule('Use the actual reaction attack rather than immutable caption starts for short oh/eww. These observed leads do not establish a fixed global delay.','ooooo35.28s became34.8s; ewww47.47s became47.066666s; save-my-nails FAH43.28s became43.133333s.'),
 rule('The battery objection is dry and the nail-saving punchline is stronger; retain separate manual asset levels.','Awkward10.95s moved10.766666s, gain0.359299; nail FAH gain0.468592 retained with a new onset.')]),
('94bc2d878df64d54',[
 rule('Hairstyle lowkey-tough is a dry awkward response here, not automatic MMM from positive wording.','MMM44.78s replaced by awkward44.333333s, gain0.676875.'),
 rule('The time-freeze reaction uses impressed anime-wow after the initial surprise, rather than the predicted short boom.','Vine74.6s removed; anime-wow75.833333s added for4.233333s, gain0.286832.'),
 rule('October stretching/Luffy preference gets a quiet tf_nemesis bed across the trade plea, not a standalone trade-February FAH.','FAH87.83s removed; tf_nemesis84.933333s added for4.0s, gain0.079123.'),
 rule('Specific farting-pill and reverse-gravity beats have distinct user-selected punctuation; they are not automatic cues on every option.','Added dry-fart18.666666s for0.366667s; suspense32.233333s for1.433333s. Fart reveal vine moved18.24s to17.666666s.'),
 rule('Repeated teleportation enthusiasm can have separate expressive hits in this scene; do not globally mute every repeat.','Added Patrick-yeah61.166666s and yeahoo64.233333s. Teleport MMM59.866666s has a source-continuous short tail at60.933333s; it is one logical event.'),
 rule('The pickle refusal has a long comic-doom bell here, despite the earlier rejection error. This is a scoped manual exception, not a literal-danger requirement or all-refusal rule.','Added Undertaker55.1s for4.233333s at wouldnt-take-that-pill; error51.433333s retained.'),
 rule('Short impacts may lead spoken surprise here; do not wait for a late or misaligned ASR word.','Food-duplication vine90.42s moved89.766666s; giant-hands vine66.58s moved66.433333s.')])]

out=BASE/'outputs/day1-revision';out.mkdir(exist_ok=True)
reports=[];before={}
for job,rules in targets:
    rec=api.job_data(job);project=api.s.project_path('test 1');_,draft,path=api.s.load_timeline(project,rec['timeline_id']);before[str(path)]=api.digest(path)
    report=api.learn_revision(job,'test 1',rec['timeline_id'],rules)
    if report.get('already_learned'):report=api.s.read_json(report['report'])['report']
    reports.append({'timeline':rec['timeline'],**report})
    print(json.dumps({'timeline':rec['timeline'],'style_version':report['new_style_version'],'old':report['old_cues'],'manual':report['manual_cues'],'strict_150ms':len(report['diff']['timing']['strict_matches']),'associated_750ms':len(report['diff']['matches']),'retimed_over_one_frame':len(report['diff']['timing']['retimed_matches'])}),flush=True)
assert all(api.digest(p)==h for p,h in before.items()),'Saved manual timeline changed while learning; inspect its latest saved version.'
profile=api.s.read_json(api.s.DATA/'style_profile.json')
result={'batch_id':'2fa25db946fd4806','style_version':profile['version'],'reports':reports,'manual_timelines_unchanged':True,'logical_manual_cues':sum(r['manual_cues'] for r in reports),'original_predictions':sum(r['old_cues'] for r in reports),'native_manual_pieces':sum(r['native_sfx_pieces'] for r in reports),'strict_150ms_matches':sum(len(r['diff']['timing']['strict_matches']) for r in reports),'loose_750ms_associations':sum(len(r['diff']['matches']) for r in reports),'retimed_matches':sum(len(r['diff']['timing']['retimed_matches']) for r in reports)}
api.s.write_json(out/'LEARNED.json',result)
lines=['# Day 1.3–1.6 manual revision learning','',f"Style version {profile['version']}. Original predictions stay frozen. Manual timeline hashes unchanged.",'','The ±750ms association score is not precise timing accuracy. Strict ±150ms sound/onset matching, moves larger than a 30fps frame, asset substitutions and final gain changes are reported separately. This is a retrospective comparison with saved revisions, not a future accuracy claim. No auditory verification of masking/delivery was performed.','','| Timeline | Original cues | Manual logical cues | Strict ±150ms P / R | Loose ±750ms P / R | Retimed >1 frame |','|---|---:|---:|---|---|---:|']
for r in reports:
    d=r['diff'];t=d['timing'];lines.append(f"| {r['timeline']} | {r['old_cues']} | {r['manual_cues']} | {t['strict_precision']:.1%} / {t['strict_recall']:.1%} | {d['precision']:.1%} / {d['recall']:.1%} | {len(t['retimed_matches'])} |")
lines+=['',f"Totals: {result['original_predictions']} predictions, {result['logical_manual_cues']} revised logical cues, {result['native_manual_pieces']} native pieces. {result['strict_150ms_matches']} strict matches, {result['loose_750ms_associations']} loose associations, {result['retimed_matches']} associated cues moved more than one frame.",'','Short source-continuous MMM tail is one event; its 100ms timeline gap and exact source offset remain represented. Nearby different-family/distant prediction labels are no longer copied into new manual anchors. User-selected new assets and final gains are retained.','','## Scene corrections','']
for r in reports:
    lines+=['### '+r['timeline'],'']
    for u in r['rule_updates']:lines+=['- '+u['rule']+' Evidence: '+u['evidence']]
    lines+=['','### Matched gain corrections','', '| Sound | Installed gain | Revised peak gain | Change |','|---|---:|---:|---:|']
    for c in r['sound_level_changes']:
        if abs(c['peak_gain_change_db'])>.1:lines.append(f"| {c['sound']} | {c['installed_gain']:.4f} | {c['manual_peak_gain']:.4f} | {c['peak_gain_change_db']:+.2f} dB |")
    lines+=['']
(out/'REVISION_NOTES.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='reports'},indent=2))
