"""Learn the four saved revisions, keeping all CapCut project files read-only."""
import sys,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'plugins/capcut-sfx-learning'))
import service as a
rules={
'Day 7.3':[
 {'rule':'In this school-ownership scene, I wanna get school was treated as dry recognition with awkward, not active approval with MMM.', 'evidence':'Manual revision replaces MMM 9.94s with awkward 9.633s.', 'scope':'scene_only','authority':'scene_inference'},
 {'rule':'Strong teleport-bed/pocket-option acceptance received a louder MMM than the quieter reflection-work acknowledgment.', 'evidence':'Final MMM gains: 0.4213 at29.5s and0.4381 at53.633s versus0.2277 at23.8s.', 'scope':'scene_only','authority':'scene_inference'},
 {'rule':'Add reaction hits on the bed-reveal what at25.733s and the talking-dog oh at38.033s; suspense leads the gold-phone problem at44.767s.', 'evidence':'The user added two vine booms and a suspense cue; retained the later comic FAH.', 'scope':'scene_only','authority':'scene_inference'}],
'Day 7.4':[
 {'rule':'In this rumor video, suspense leads the feet-consequence question around12.133s; the later nest reaction uses vine at18.867s.', 'evidence':'The original nest suspense at16.15s was moved/replaced; the new feet suspense and nest boom are observed.', 'scope':'scene_only','authority':'scene_inference'},
 {'rule':'Pickle-tears not-bad acceptance uses emphasized MMM, while the later gnome-army MMM stays softer.', 'evidence':'Effective MMM gains0.4144 at29.467s versus0.1961 at53.5s.', 'scope':'scene_only','authority':'scene_inference'},
 {'rule':'The free-eggs irony cue starts earlier at39.667s with stronger Among gain0.4658.', 'evidence':'Manual Among moved from40.48s to39.667s and raised gain by about8.3dB.', 'scope':'scene_only','authority':'scene_inference'}],
'Day 7.5':[
 {'rule':'The death-book bell has a strong short attack followed by a much quieter body under the reactors refusal.', 'evidence':'One logical bell:14.833s attack gain0.7276 for0.333s, then0.2270 for1.767s.', 'scope':'scene_only','authority':'scene_inference'},
 {'rule':'In this locker sequence, backpack recognition oh is left quiet; future-phone suspense aligns with the reactors comment around38.433s rather than the earlier narration warning.', 'evidence':'User removed ooooo27.24s and moved the suspense from34.91s to38.433s.', 'scope':'scene_only','authority':'scene_inference'},
 {'rule':'Keep the initial human-teeth Eww cue; the second moving-teeth gross commentary is a stronger FAH punchline in this scene.', 'evidence':'Ewww41.5s remains, while the second ewww45.66s became FAH46.1s gain0.5914.', 'scope':'scene_only','authority':'scene_inference'},
 {'rule':'The miniature-house creepy sound begins52.767s and continues as one event with a ducked middle, rather than ending after a short flat bed.', 'evidence':'Native pieces join continuously: gain0.2606, then0.1264 during54.1–56.7s, then0.2606 tail.', 'scope':'scene_only','authority':'scene_inference'}],
'Day 7.6':[
 {'rule':'In this toothpaste sequence the initial bro-what/questioning-best reaction uses awkward/suspense; the later direct September-best statement still uses MMM.', 'evidence':'User removed early MMM12.94s, added awkward10.1s and suspense12.033s, retained MMM80.167s.', 'scope':'scene_only','authority':'scene_inference'},
 {'rule':'The charcoal brushing scene has a quiet creepy texture at27.7s; the ordinary later rejection error at31.86s was removed in this scene.', 'evidence':'Manual creepy gain0.1364 over4.2s, MMM28.1s retained, old error absent.', 'scope':'scene_only','authority':'scene_inference'},
 {'rule':'Short specific punctuation is allowed: huh23.0s, pumpkin-name boom34.033s and strawberry reaction movie42.167s are user-selected scene beats.', 'evidence':'These three exact local sounds were manually added; not a general rule to cue every noun or transition.', 'scope':'scene_only','authority':'scene_inference'},
 {'rule':'The diamond boom belongs to the reactors surprised what at97.967s here, ahead of the later resale FAH, rather than only the narrated price.', 'evidence':'User moved vine from99.02s to97.967s; selling FAH100.667s remains.', 'scope':'scene_only','authority':'scene_inference'},
 {'rule':'Use the user-selected alternate FAH variant for the hot-sauce cooked burst and a restrained Among texture under the garlic ending in this scene.', 'evidence':'fahhh_KcgAXfs69.567s and Among91.833s were added with effective gains1.1220 and0.3480.', 'scope':'scene_only','authority':'scene_inference'}]
}
project=a.s.project_path('test 1');before={str(p):a.digest(p) for p in project.rglob('*.json')}
batch=a.s.read_json(ROOT/'outputs/day7-batch/INSTALL_RESULT.json');reports=[]
for row in batch['rows']:
    record=a.job_data(row['job_id']);report=a.learn_revision(row['job_id'],'test 1',record['timeline_id'],rules[row['timeline']]);reports.append(report)
    print(json.dumps({'timeline':row['timeline'],'old_cues':report.get('old_cues'),'manual_cues':report.get('manual_cues'),'native_pieces':report.get('native_sfx_pieces'),'version':report.get('new_style_version'),'already_learned':report.get('already_learned',False)}),flush=True)
assert before=={str(p):a.digest(p) for p in project.rglob('*.json')},'A saved project changed during the read; check the latest autosave.'
profile=a.s.read_json(a.s.DATA/'style_profile.json');out=ROOT/'outputs/day7-revision';out.mkdir(exist_ok=True)
result={'reports':reports,'style_version':profile['version'],'reference_examples':len(a.s.read_json(a.s.DATA/'examples.json')),'project_files_unchanged':True,
    'logical_manual_cues':sum(r.get('manual_cues',0) for r in reports),'native_pieces':sum(r.get('native_sfx_pieces',0) for r in reports),
    'matched_750ms':sum(len(r.get('diff',{}).get('matches',[])) for r in reports),'old_cues':sum(r.get('old_cues',0) for r in reports),
    'gain_levels':profile['mix_preferences']['sound_levels']}
a.s.write_json(out/'LEARNED.json',result)
lines=['# Day 7.3–7.6 manual revisions','',f'Style memory version {profile["version"]}; {result["reference_examples"]} reference examples. Saved project JSON files unchanged.','',
    'Compound links resolve by material reference even when their audio path is blank. Outer and inner gains multiply. Split pieces of one cue count as one event and retain attack/body level automation.',
    '', '| Timeline | Proposed cues | Manual logical cues | Native pieces | Exact sound within ±0.75s |','|---|---:|---:|---:|---:|']
for row,r in zip(batch['rows'],reports):lines.append(f'| {row["timeline"]} | {r.get("old_cues")} | {r.get("manual_cues")} | {r.get("native_sfx_pieces")} | {len(r.get("diff",{}).get("matches",[]))} |')
lines+=['','These are retrospective selection/timing comparisons; they do not count volume correctness or guarantee future accuracy. Source-time maps preserve context after visual splits and a small real narration trim.',
    '', 'Learned levels use manually approved final effective gains, not old unattenuated plan values or old automatic master attenuation. Normal/soft/emphasis references are separate; voice-role and background gain spans are retained.',
    '', 'New learned plans cannot silently turn down all dialogue/SFX for headroom. A flagged mix needs an explicit headroom decision or revised levels before apply. No playback listening/perceived-loudness certification was performed.',
    '', '| Sound | References | Soft gain | Normal gain | Emphasis gain |','|---|---:|---:|---:|---:|']
for sound,p in profile['mix_preferences']['sound_levels'].items():lines.append(f'| {sound} | {p["count"]} | {p["soft_gain"]:.3f} | {p["normal_gain"]:.3f} | {p["emphasis_gain"]:.3f} |')
(out/'REVISION_NOTES.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('style_version','reference_examples','logical_manual_cues','native_pieces','matched_750ms','old_cues','project_files_unchanged')},indent=2))
