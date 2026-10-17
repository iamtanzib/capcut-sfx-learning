"""Read-only feedback learning; no saved project backup is created."""
import hashlib
import json
import statistics
import soundpilot as s

out=s.OUTPUTS/'test4_revision';out.mkdir(exist_ok=True)
project=s.project_path('test 1');_,manual,path=s.load_timeline(project,'test 4')
digest=hashlib.sha256(path.read_bytes()).hexdigest()
truth=sorted(s.flatten_sfx(manual,s.read_json(s.DATA/'sound_catalog.json'),project),key=lambda e:e['start'])
old=s.read_json(s.OUTPUTS/'test4'/'reviewed_plan.json')['effects']
used_old=set();used_new=set();kept=[];moved=[];matches=0
edges=sorted((abs(a['start']-b['start']),i,j) for i,a in enumerate(old) for j,b in enumerate(truth) if a['sound']==b['sound'])
for delta,i,j in edges:
    if delta>1 or i in used_old or j in used_new:continue
    used_old.add(i);used_new.add(j)
    if delta<=.75:matches+=1
    row={'sound':old[i]['sound'],'old_start':old[i]['start'],'manual_start':round(truth[j]['start'],3),'cue':old[i]['dialogue']}
    (kept if delta<.08 else moved).append(row)
removed=[{'sound':e['sound'],'start':e['start'],'cue':e['dialogue']} for i,e in enumerate(old) if i not in used_old]
added=[{'sound':e['sound'],'start':round(e['start'],3),'duration':round(e['duration'],3),'volume':round(e['volume'],3)} for i,e in enumerate(truth) if i not in used_new]
report={'old_cues':len(old),'manual_cues':len(truth),'kept':kept,'retimed':moved,'removed':removed,'added':added,
    'matches_750ms':matches,'precision':matches/len(old),'recall':matches/len(truth),'reference_sha256':digest,
    'policy':'Frozen previous plan vs user revision before retraining. This is a single-video comparison, not a guarantee for future videos.',
    'saved_project_backup_created':False}
s.write_json(out/'DIFF.json',report)
profile=s.read_json(s.DATA/'style_profile.json');profile['version']=7
profile['latest_revised_reference']={'project':'test 1','timeline':'test 4','placements':len(truth),'sha256':digest}
profile['shopping_cart_revision_examples']=[
    {'cue':'oh, the gaming shopping cart','decision':'silence','removed_sound':'ooooo.mp3','function':'conversational_recognition'},
    {'cue':'I would too','sound':'awkward-moment.mp3','time':15.467,'function':'dry_assent','interpretation':'Observed dry echo in this scene; not a universal rule for this phrase.'},
    {'cue':'glass cart reveal / bro what','sound':'sudden-suspense-sound-effect.mp3','time':24.9,'function':'unexpected_or_tense'},
    {'cue':'you are cooked, glass-cart roast','sound':'fahhhh.mp3','time':31.367,'function':'comic_line'},
    {'cue':'isolated oh at ball-pit reveal','sound':'ooooo.mp3','time':33.167,'function':'mild_reaction_lift'},
]
profile['negative_examples'].append({'sound':'ooooo.mp3','cue':'conversational oh, the gaming shopping cart','decision':'omit',
    'lesson':'Reading/noticing an option name does not automatically require a reaction-lift sound. The next explicit that-is-fire approval already has MMMMMM.'})
profile['additional_timing_and_selection_rules'] += [
    'Distinguish conversational recognition from an expressive isolated oh. The gaming-cart ooooo was removed, while ball-pit ooooo was retained.',
    'Positive sentence meaning alone does not identify the sound: I-would-too used awkward as a dry echo in this scene, while active that-is-fire approval retained MMMMMM.',
    'The glass-cart suspense was moved to 24.90s to follow the actual reveal rather than waiting until the later spoken objection.',
    'Place funny-word attacks around the salient syllable: user moved cooked FAHH to 31.37s and the ball-pit oh lift to 33.17s.',
    'The teddy-cart ending remained a restrained awkward cue; do not invent stronger admiration solely from a cozy-looking prop.'
]
for rule in profile['rules']:
    notes={'ooooo.mp3':'Distinguish a real reaction lift from conversationally reading an option name: gaming-cart recognition was left quiet, isolated ball-pit oh retained ooooo.',
        'MMMMMM.mp3':'Positive wording alone is insufficient: the user gave I-would-too a dry awkward cue in the shopping-cart scene.',
        'awkward-moment.mp3':'Can also punctuate a dry conversational assent/echo (I would too), not only negative/hesitant wording.'}
    note=notes.get(rule['sound'])
    if note and note not in rule['rule']:rule['rule']+=' '+note
profile['additional_timing_and_selection_rules']=list(dict.fromkeys(profile['additional_timing_and_selection_rules']))
profile['negative_examples']=list({json.dumps(e,sort_keys=True):e for e in profile['negative_examples']}.values())
s.write_json(s.DATA/'style_profile.json',profile)
cfg=s.read_json(s.BASE/'config.json')
ref={'project':'test 1','timeline':'test 4','timeline_id':manual['id']}
if not any(r['project']=='test 1' and r['timeline']=='test 4' for r in cfg['additional_reference_sources']):cfg['additional_reference_sources'].append(ref)
s.write_json(s.BASE/'config.json',cfg)
trained=s.Planner().train();examples=s.read_json(s.DATA/'examples.json')
for rule in profile['rules']:
    rows=[e for e in examples if e['sound']==rule['sound']]
    rule['count']=len(rows)
    rule['median_volume']=round(statistics.median(e['volume'] for e in rows),3)
    rule['median_duration']=round(statistics.median(e['duration'] for e in rows),3)
s.write_json(s.DATA/'style_profile.json',profile);s.write_json(out/'STYLE_PROFILE_V7.json',profile)
unchanged=hashlib.sha256(path.read_bytes()).hexdigest()==digest
assert unchanged,'Reference changed during learning; recheck the latest saved version.'
lines=['# test 4 manual revision','',
    f'{len(old)} proposed cues; {len(truth)} revised cues. {len(kept)} unchanged, {len(moved)} retimed, {len(removed)} removed, {len(added)} added.','',
    '- Removed ooooo at 9.10s on reading the gaming-cart option.',
    '- Added awkward at 15.47s on the dry I-would-too response.',
    '- Suspense: 25.17 → 24.90s. FAHH: 31.60 → 31.37s. Ball-pit ooooo: 33.33 → 33.17s.','',
    f'Exact sound within ±0.75s: {matches}/{len(old)} precision ({report["precision"]*100:.1f}%); {matches}/{len(truth)} recall ({report["recall"]*100:.1f}%). Timing refinements still matter; this is not a future-video guarantee.','',
    f'{trained["examples"]} reference placements across {len(trained["summary"])} sources. The revised CapCut timeline was not edited and no saved project backup was made.']
(out/'REVISION_NOTES.md').write_text('\n'.join(lines),encoding='utf-8')
print({'kept':len(kept),'retimed':moved,'removed':removed,'added':added,'matches':matches,'precision':report['precision'],
    'reference_placements':trained['examples'],'reference_unchanged':unchanged,'project_backup_created':False})
