"""Read the user's revision as positive AND negative evidence; no CapCut writes."""
import collections
import hashlib
import json
import soundpilot as s

out=s.OUTPUTS/'test2_revision';out.mkdir(exist_ok=True)
project=s.project_path('test 1');_,draft,path=s.load_timeline(project,'test 2 - SFX v2')
source_hash=hashlib.sha256(path.read_bytes()).hexdigest()
sounds=s.read_json(s.DATA/'sound_catalog.json');truth=sorted(s.flatten_sfx(draft,sounds,project),key=lambda e:e['start'])
old=s.read_json(s.OUTPUTS/'test2v2'/'reviewed_plan.json')['effects']
edges=sorted((abs(a['start']-b['start']),i,j) for i,a in enumerate(old) for j,b in enumerate(truth) if a['sound']==b['sound'])
used_old=set();used_new=set();kept=[];moved=[]
for delta,i,j in edges:
    if i in used_old or j in used_new or delta>4:continue
    used_old.add(i);used_new.add(j)
    row={'sound':old[i]['sound'],'old_start':old[i]['start'],'manual_start':round(truth[j]['start'],3),'delta':round(truth[j]['start']-old[i]['start'],3),
        'cue':old[i]['dialogue']}
    (kept if delta<.08 else moved).append(row)
removed=[{'start':e['start'],'sound':e['sound'],'cue':e['dialogue'],'old_reason':e['reason']} for i,e in enumerate(old) if i not in used_old]
added=[{'start':round(e['start'],3),'sound':e['sound'],'volume':round(e['volume'],3)} for i,e in enumerate(truth) if i not in used_new]
# The actual matched pairs distinguish retiming from a removed cue.
within_tolerance=len(kept)+sum(abs(e['delta'])<=.75 for e in moved)
report={'original_cues':len(old),'manual_cues':len(truth),'unchanged':kept,'retimed':moved,'removed':removed,'added':added,
    'exact_sound_onset_matches_750ms':within_tolerance,'precision':within_tolerance/len(old),'recall':within_tolerance/len(truth),
    'reference_sha256':source_hash,'policy':'This is agreement with the user revision, measured before training on it. Deleted cues are negative evidence, not invitations to substitute another sound.'}
s.write_json(out/'DIFF.json',report);s.write_json(out/'manual_snapshot.json',draft)
profile=s.read_json(s.DATA/'style_profile.json');profile['version']=5
profile['latest_revised_reference']={'project':'test 1','timeline':'test 2 - SFX v2','placements':len(truth),'sha256':source_hash}
profile['selection_policy']={
    'primary_goal':'Match meaningful reaction beats; silence is a valid decision.',
    'palette_quota':False,'automatic_intro_cue':False,'automatic_negative_word_music':False,
    'default_for_uncertain_event':'omit',
    'rare_context_sounds':['undertakers-bell_2UwFCIe.mp3','among-us-role-reveal-sound.mp3','Creepy Sound Effect.mp3','movie_1.mp3'],
    'rare_sound_requirement':'Require a specific supported scene/intent and exact cue; a negative word, mood label, or desire for variety is insufficient.',
    'timing':'Anchor the intended beat. Do not choose the first oh or always place sounds after a sentence.'}
profile['negative_examples']=[
    {'sound':'movie_1.mp3','cue':'okay before the choice list','decision':'omit','lesson':'A list setup does not require an intro sting.'},
    {'sound':'undertakers-bell_2UwFCIe.mp3','cue':'I am cooked in a banned-word game','decision':'omit','lesson':'Cooked alone does not justify a doom bell.'},
    {'sound':'undertakers-bell_2UwFCIe.mp3','cue':'okay is in every conversation','decision':'omit','lesson':'Habit regret is not a doom/danger scene.'},
    {'sound':'among-us-role-reveal-sound.mp3','cue':'I say it every day','decision':'omit','lesson':'An ordinary habit/confession does not itself make a suspicious or ironic cue.'},
    {'sound':'Creepy Sound Effect.mp3','cue':'this is bad in a normal greeting game','decision':'omit','lesson':'Bad alone is not a creepy event; suspense can carry the relevant beat without layering creepy.'}
]
profile['revision_timing_examples']=moved
profile['revision_added_examples']=added
profile['additional_timing_and_selection_rules'] += [
    'Do not force Undertaker/Among Us/creepy/movie to satisfy a varied palette. This user revision removed all five such forced placements.',
    'If a cue is removed, preserve silence unless the user supplies a replacement; do not auto-fill the gap.',
    'A mild oh/realization can use ooooo: the user added it at 17.20s.',
    'Suspense moved from 33.73s to 35.93s: use the actual this-is-bad beat, not the first oh.',
    'MMMMMM moved to 47.50s after exactly; awkward moved to 60.97s at the beginning of the like-every-sentence thought.'
]
for rule in profile['rules']:
    if rule['sound']=='undertakers-bell_2UwFCIe.mp3':rule['rule']+=' Do not infer doom from cooked or a banned-word habit alone; both bells were removed in test 2.'
    if rule['sound']=='among-us-role-reveal-sound.mp3':rule['rule']+=' Ordinary I-say-it-every-day is insufficient; that added layer was removed.'
    if rule['sound']=='Creepy Sound Effect.mp3':rule['rule']+=' Require real supported unsettling context; a generic this-is-bad line in the word game was rejected.'
    if rule['sound']=='movie_1.mp3':rule['rule']+=' No automatic opening/list cue; the user removed the added setup sting in test 2.'
s.write_json(s.DATA/'style_profile.json',profile)
cfg=s.config();source={'project':'test 1','timeline':'test 2 - SFX v2','caption_timeline':'test 2'}
raw_cfg=s.read_json(s.BASE/'config.json')
if not any(r['project']==source['project'] and r['timeline']==source['timeline'] for r in raw_cfg.get('additional_reference_sources',[])):
    raw_cfg.setdefault('additional_reference_sources',[]).append(source)
s.write_json(s.BASE/'config.json',raw_cfg)
trained=s.Planner().train()
examples=s.read_json(s.DATA/'examples.json')
for rule in profile['rules']:rule['count']=sum(e['sound']==rule['sound'] for e in examples)
s.write_json(s.DATA/'style_profile.json',profile);s.write_json(out/'STYLE_PROFILE_V5.json',profile)
unchanged=hashlib.sha256(path.read_bytes()).hexdigest()==source_hash
assert unchanged,'User revision changed during learning; recheck before using the snapshot.'
lines=['# test 2 revision: less filler, exact reaction timing','',
    f'Before: {len(old)} cues. User revision: {len(truth)}. Kept unchanged: {len(kept)}; retimed: {len(moved)}; removed: {len(removed)}; added: {len(added)}.','',
    '## Removed cues','| Time | Sound | Previous cue |','|---:|---|---|']
for r in removed:lines.append(f'| {r["start"]:.2f} | {r["sound"]} | {r["cue"]} |')
lines.extend(['','## Retimed cues','| Sound | Previous | User timing |','|---|---:|---:|'])
for r in moved:lines.append(f'| {r["sound"]} | {r["old_start"]:.2f} | {r["manual_start"]:.2f} |')
lines.extend(['','## Added cue',str(added),'',
    '## New selection rules',*['- '+r['lesson'] for r in profile['negative_examples']],
    '- No palette quota. Silence is a valid choice. Removed cues are negative examples, not blank slots to refill.',
    '',f'{trained["examples"]} placements now indexed across {len(trained["summary"])} references. User timeline was not modified.',
    '',f'Prior prediction agreement within ±0.75s: {within_tolerance}/{len(old)} precision ({within_tolerance/len(old)*100:.1f}%), {within_tolerance}/{len(truth)} recall ({within_tolerance/len(truth)*100:.1f}%). These measure this revision only; no new-video accuracy is claimed.'])
(out/'REVISION_NOTES.md').write_text('\n'.join(lines),encoding='utf-8')
print({'before':len(old),'after':len(truth),'kept':len(kept),'retimed':moved,'removed':removed,'added':added,'reference_placements':trained['examples'],'manual_unchanged':unchanged})

if __name__=='__main__':pass
