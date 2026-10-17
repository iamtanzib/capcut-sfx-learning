"""Learn the manual car-video revision without editing any CapCut timeline."""
import collections
import hashlib
import soundpilot as s

out=s.OUTPUTS/'test3_revision';out.mkdir(exist_ok=True)
project=s.project_path('test 1');_,manual,path=s.load_timeline(project,'test 3')
before_hash=hashlib.sha256(path.read_bytes()).hexdigest()
truth=sorted(s.flatten_sfx(manual,s.read_json(s.DATA/'sound_catalog.json'),project),key=lambda e:e['start'])
old=s.read_json(s.OUTPUTS/'test3'/'reviewed_plan.json')['effects']
pairs=[];used_old=set();used_new=set()
edges=sorted((abs(a['start']-b['start']),i,j) for i,a in enumerate(old) for j,b in enumerate(truth) if a['sound']==b['sound'])
for delta,i,j in edges:
    if delta<=1.0 and i not in used_old and j not in used_new:
        used_old.add(i);used_new.add(j);pairs.append((i,j,delta))
kept=[];retimed=[]
for i,j,delta in pairs:
    e={'sound':old[i]['sound'],'old_start':old[i]['start'],'manual_start':round(truth[j]['start'],3),'cue':old[i]['dialogue']}
    (kept if delta<.08 else retimed).append(e)
replaced=[]
edges=sorted((abs(a['start']-b['start']),i,j) for i,a in enumerate(old) if i not in used_old
    for j,b in enumerate(truth) if j not in used_new and abs(a['start']-b['start'])<=1.0)
for delta,i,j in edges:
    if i not in used_old and j not in used_new:
        used_old.add(i);used_new.add(j)
        replaced.append({'old_sound':old[i]['sound'],'manual_sound':truth[j]['sound'],'old_start':old[i]['start'],
            'manual_start':round(truth[j]['start'],3),'cue':old[i]['dialogue']})
added=[{'sound':e['sound'],'start':round(e['start'],3),'duration':round(e['duration'],3),'volume':round(e['volume'],3)} for j,e in enumerate(truth) if j not in used_new]
removed=[{'sound':e['sound'],'start':e['start']} for i,e in enumerate(old) if i not in used_old]
matching=sum(delta<=.75 for _,_,delta in pairs)
report={'old_predictions':len(old),'manual_placements':len(truth),'kept':kept,'retimed':retimed,'replaced':replaced,'added':added,'removed':removed,
    'matches_750ms':matching,'precision':matching/len(old),'recall':matching/len(truth),'reference_sha256':before_hash,
    'policy':'Frozen previous prediction vs manual revision, before this revision is indexed. Same-video retraining must not be called new-video accuracy.'}
s.write_json(out/'DIFF.json',report);s.write_json(out/'manual_snapshot.json',manual)
profile=s.read_json(s.DATA/'style_profile.json');profile['version']=6
profile['latest_revised_reference']={'project':'test 1','timeline':'test 3','placements':len(truth),'sha256':before_hash}
profile['car_revision_examples']=[
    {'cue':'Ferrari reveal','time':16.767,'sound':'anime-wow-sound-effect.mp3','function':'visual_admiration','replaces':'ooooo.mp3'},
    {'cue':'Koenigsegg reveal / naming the car','time':24.367,'sound':'vine-boom (20).mp3','function':'keyword_emphasis'},
    {'cue':'exceptional Koenigsegg reveal','time':23.767,'sound':'heavenly-music-gaming-sound-effect-hd-mp3cut.mp3','function':'exceptional_good_reveal'},
    {'cue':'Supra recognition','time':56.4,'sound':'vine-boom (20).mp3','function':'keyword_emphasis','replaces':'ooooo.mp3'},
    {'cue':'deadpan banana-car what-the','time':65.433,'sound':'awkward-moment.mp3','function':'dry_or_awkward','replaces':'vine-boom (20).mp3'},
    {'cue':'banana car forever / date consequence','time':70.667,'sound':'undertakers-bell_2UwFCIe.mp3','function':'dramatic_comic_consequence','replaces':'among-us-role-reveal-sound.mp3','interpretation':'Specific observed choice; do not generalize every dating or banana line.'},
    {'cue':'hype/transition at yo after Lamborghini','time':94.367,'sound':'movie_1.mp3','function':'dramatic_punctuation'},
    {'cue':'mild oh recognition of pink Acura','time':97.767,'sound':'ooooo.mp3','function':'mild_reaction_lift'},
]
profile['additional_timing_and_selection_rules'] += [
    'Excitement has levels: Ferrari/Lamborghini admiration can use anime-wow; a mild oh can use ooooo; a named-car impact can use vine boom.',
    'Specific exceptional-car beauty can support a heavenly bed plus a short reveal hit and later spoken approval. Distinct functions justify those layers; palette variety does not.',
    'Banana-car deadpan confusion used awkward, not a shock boom; the lifelong absurd-car consequence used Undertaker, not inferred romantic Among Us.',
    'The user added a short movie punctuation beat near 94.37s after the Lamborghini hype. Movie is not globally banned and is not an automatic intro.',
    'Spoken-eww determines the sound file, not an immutable caption-start time: the user moved ewww from 8.40s to 7.97s to lead the disgust beat.',
    'Approval and funny-line mappings remain primary. Respect user volume corrections per asset; do not make all wow sounds equally loud.'
]
for rule in profile['rules']:
    if rule['sound']=='anime-wow-sound-effect.mp3':rule['rule']='Stronger impressed visual admiration, such as mansion/rare card/Ferrari/Lamborghini. A mild oh/recognition can instead use ooooo. The car revision replaced Ferrari ooooo with anime-wow.'
    if rule['sound']=='ooooo.mp3':rule['rule']='Mild reaction lift, anticipation or recognition. Not every excited iconic reveal: Ferrari became anime-wow, Supra became a boom, and a mild December oh used ooooo.'
    if rule['sound']=='undertakers-bell_2UwFCIe.mp3':rule['rule']+=' Also observed on the specific lifelong absurd banana-car consequence at 70.67s. Context is broader than literal physical danger, but cooked/habit words alone remain insufficient.'
    if rule['sound']=='movie_1.mp3':rule['rule']+=' Also a short dramatic punctuation/transition near a hype yo after Lamborghini; not only opening setup.'
    if rule['sound']=='heavenly-music-gaming-sound-effect-hd-mp3cut.mp3':
        rule['rule']='A selective exceptional-good reveal: chocolate caramel egg after bad snacks, and the Koenigsegg car reveal. Can be a quiet longer bed with a short reveal hit and a later approval cue.'
        rule['evidence_strength']='medium'
    if rule['sound']=='among-us-role-reveal-sound.mp3':rule['rule']+=' The banana/date conditional-positive cue was replaced by Undertaker in test 3; do not infer innuendo/suspicion from fruit/date wording alone.'
s.write_json(s.DATA/'style_profile.json',profile)
cfg=s.read_json(s.BASE/'config.json')
# Original caption-source tabs were deleted by the user. Retain their verified snapshots.
install=s.read_json(s.OUTPUTS/'test1'/'install.json')
for ref in cfg['additional_reference_sources']:
    if ref['timeline']=='Srijon version':
        ref['caption_snapshot']=str(s.Path(install['backup'])/'Timelines'/'38E44388-4CD1-47cc-9385-D82C9CCEEAD6'/'draft_content.json')
    elif ref['timeline']=='test 2 - SFX v2':
        ref['caption_snapshot']=str(s.OUTPUTS/'test2'/'source_snapshot.json')
new={'project':'test 1','timeline':'test 3','timeline_id':manual['id'],'caption_snapshot':str(s.OUTPUTS/'test3'/'source_snapshot.json')}
if not any(r['timeline']=='test 3' and r['project']=='test 1' for r in cfg['additional_reference_sources']):cfg['additional_reference_sources'].append(new)
s.write_json(s.BASE/'config.json',cfg)
trained=s.Planner().train()
events=s.read_json(s.DATA/'examples.json')
for rule in profile['rules']:rule['count']=sum(e['sound']==rule['sound'] for e in events)
s.write_json(s.DATA/'style_profile.json',profile);s.write_json(out/'STYLE_PROFILE_V6.json',profile)
unchanged=hashlib.sha256(path.read_bytes()).hexdigest()==before_hash
assert unchanged,'Reference changed during analysis; review the fresh save before continuing.'
lines=['# test 3 user revision','',
    f'Previous prediction: {len(old)} cues. Manual version: {len(truth)}. Unchanged: {len(kept)}; retimed: {len(retimed)}; replaced: {len(replaced)}; added: {len(added)}.','',
    '| Previous sound | Your sound | Time |','|---|---|---:|']
for e in replaced:lines.append(f'| {e["old_sound"]} | {e["manual_sound"]} | {e["manual_start"]:.2f}s |')
lines.extend(['','## Added cues',*['- '+str(e) for e in added],'','## Timing changes',*['- '+str(e) for e in retimed],'',
    'Precision within ±0.75s: '+f'{matching}/{len(old)} = {report["precision"]*100:.1f}%. Cue coverage/recall: {matching}/{len(truth)} = {report["recall"]*100:.1f}%.',
    'This does not establish 80% overall quality; new added cues and sound replacements remain misses.',
    '',f'{trained["examples"]} placements now indexed across {len(trained["summary"])} references. No CapCut timeline was changed.'])
(out/'REVISION_NOTES.md').write_text('\n'.join(lines),encoding='utf-8')
print({'manual_cues':len(truth),'kept':len(kept),'retimed':len(retimed),'replaced':replaced,'added':added,
    'matching':matching,'precision':report['precision'],'recall':report['recall'],'reference_events':trained['examples'],'manual_unchanged':unchanged})
