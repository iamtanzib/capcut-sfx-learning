"""New banned-word video, manually reviewed with the latest Srijon conventions."""
import hashlib
import time
import soundpilot as s

p=s.project_path('test 1');_,draft,path=s.load_timeline(p,'test 2')
sounds=s.read_json(s.DATA/'sound_catalog.json');catalog={a['name']:a for a in sounds}
examples=s.read_json(s.DATA/'examples.json')
# Word times from the reaction stream; cues are deliberately not added to every line.
choices=[
 (2.733,'vine-boom (20).mp3',.392,'impact_or_emphasis','Banned?','Emphasize the skeptical echo of the challenge keyword.'),
 (5.90,'movie_1.mp3',.495,'dramatic_setup','okay / before the choices','Short setup beat, like the user movie cue before the option list.'),
 (10.267,'MMMMMM.mp3',.32,'approval',"that's easy",'The first option initially feels easy; approving word, not its reveal alone.'),
 (12.033,'error_CDOxCYm.mp3',.65,'confusion_or_rejection','yes ... oh shoot','He accidentally says the banned word and realizes the mistake.'),
 (13.567,'fahhhh.mp3',.458,'comic_line',"I'm cooked",'Funny self-roast after the slip, following the user failed-everything FAHH correction.'),
 (18.333,'error_CDOxCYm.mp3',.57,'confusion_or_rejection',"I can't do that",'Ordinary refusal/difficulty with the sorry ban; not a FAHH keyword trigger.'),
 (23.467,'MMMMMM.mp3',.34,'approval',"that's easy",'Accepts the apologize workaround; one approval cue for this whole thought.'),
 (28.267,'error_CDOxCYm.mp3',.65,'confusion_or_rejection','bro','Accidental use of the banned word, before the self-roast.'),
 (29.333,'fahhhh.mp3',.458,'comic_line','I lost two','The clear funny confession, rather than treating every bad/not-good word as a joke.'),
 (33.733,'sudden-suspense-sound-effect.mp3',.72,'unexpected_or_tense','oh ... oh','Alarmed surprise at losing the common greeting, matching the user ooh/what-the suspense pattern.'),
 (39.10,'MMMMMM.mp3',.35,'approval',"I'm gonna do yes",'Actual selection of an option, analogous to giving wings / taking the castle.'),
 (44.433,'error_CDOxCYm.mp3',.62,'confusion_or_rejection',"that's bad",'Rejects the thank-you ban because it would seem rude.'),
 (47.10,'MMMMMM.mp3',.29,'approval','exactly','Brief explicit agreement with the dilemma.'),
 (49.80,'error_CDOxCYm.mp3',.65,'confusion_or_rejection','okay ... oh shit','Realization that okay itself is banned; ordinary acknowledgment is not an approval cue here.'),
 (55.80,'MMMMMM.mp3',.32,'approval',"alright, it's not bad",'Accepts the all-right alternative. Ends before the next repeated word.'),
 (57.533,'vine-boom (20).mp3',.392,'impact_or_emphasis','like','Emphasize the echoed option word, like the user breakfast noun cue.'),
 (65.533,'vine-boom (20).mp3',.392,'impact_or_emphasis','what','The disbelieving echo of the final banned word.'),
 (69.167,'error_CDOxCYm.mp3',.65,'confusion_or_rejection','nah nah bro','Closing rejection; no automatic FAHH for a negative ending.'),
]
effects=[]
for at,name,volume,function,cue,reason in choices:
    candidates=[(i,e) for i,e in enumerate(examples) if e['sound']==name]
    # Prefer the user's newest template for schema/trim conventions when available.
    index,template=next(((i,e) for i,e in candidates if e['timeline']=='Srijon version'),candidates[0])
    at=round(at*draft['fps'])/draft['fps']
    length=min(catalog[name]['duration'],draft['duration']/s.MICRO-at)
    effects.append({'start':round(at,6),'duration':length,'source_start':0,'speed':1,'sound':name,'volume':volume,
        'function':function,'dialogue':cue,'reason':reason,'review':True,'enabled':True,'example_index':index,'alternatives':[],
        'fade_in':.003,'fade_out':.035})
plan={'project':'test 1','timeline':'test 2','output_timeline':'test 2 Auto SFX','duration':draft['duration']/s.MICRO,
    'source_hash':hashlib.sha256(path.read_bytes()).hexdigest(),'created':time.time(),'effects':effects,'captions':s.caption_rows(draft),
    'existing_sfx':0,'style_profile_version':4,'engine':'Latest Srijon style + two-track speech/word timing + local frame review',
    'old_target_sfx_used':False,'skipped_cues':['Apologize repetition shares the workaround approval cue at 23.47s.',
        'I say it every day shares the lost-two comic beat; no extra cue is forced.',
        'Like is in every sentence adds context to the like reveal; no automatic funny-keyword FAHH.'],
    'limitations':'User preference agreement is not yet measured on this new video. Final CapCut playback still needs review.'}
s.validate_plan(plan,sounds)
out=s.OUTPUTS/'test2';out.mkdir(exist_ok=True)
s.write_json(out/'reviewed_plan.json',plan)
s.write_json(out/'source_snapshot.json',draft)
ctx=s.read_json(s.DATA/'context'/'9793a1654469281cff69'/'report-base.en.json')
s.write_json(out/'cost_report.json',{'video':'test 2','seconds':71.3,'local_context_seconds':ctx['seconds'],
    'external_api_call_count':0,'external_api_cost_usd':0.0,'calls':[],
    'note':'Local model and file processing. Codex chat/account usage and electricity are not priced here.'})
report=s.export_copy(plan);s.write_json(out/'export.json',report)
lines=['# test 2 sound plan','', 'New video; latest Srijon correction applied. Every placement needs user review; no 80% score is claimed.','',
    '| Time | Sound | Reaction | Why |','|---:|---|---|---|']
for e in effects:lines.append(f'| {e["start"]:.2f} | {e["sound"]} | {e["dialogue"]} | {e["reason"]} |')
(out/'PLAN.md').write_text('\n'.join(lines),encoding='utf-8')
print('TEST2_READY',len(effects),'effects',report['path'])
