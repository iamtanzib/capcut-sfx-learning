"""Birth-month cars, following the user's latest no-filler and spoken-eww rules."""
import hashlib
import time
import soundpilot as s

p=s.project_path('test 1');_,draft,path=s.load_timeline(p,'test 3')
examples=s.read_json(s.DATA/'examples.json');sounds=s.read_json(s.DATA/'sound_catalog.json');catalog={a['name']:a for a in sounds}
choices=[
 (3.40,'vine-boom (20).mp3',.34,'impact_or_emphasis','Forever?','Emphasis on the permanent-car challenge, analogous to the skeptical opening keyword.'),
 (8.40,'ewww.mp3',.27,'explicit_disgust','eww bro what the','Explicit user rule: spoken eww gets ewww.mp3. Caption timestamp is used because ASR omitted the exclamation.'),
 (15.47,'fahhhh.mp3',.458,'comic_line','someone about to lick your bumper','The concrete tongue-car licking joke, not a generic negative keyword.'),
 (17.10,'ooooo.mp3',.40,'excited_positive_reaction','oh Ferrari','Short excited recognition of the Ferrari.'),
 (20.83,'MMMMMM.mp3',.30,'approval','yes sir','Approves the Ferrari; distinct from the initial excited reveal.'),
 (28.93,'MMMMMM.mp3',.30,'approval','March, supercar','Accepts the Koenigsegg option.'),
 (32.27,'fahhhh.mp3',.458,'comic_line','just do not let January lick you','The explicit roast about the earlier tooth/tongue car.'),
 (33.73,'error_CDOxCYm.mp3',.60,'confusion_or_rejection','oh heck nah','Rejects the tiny bubble car.'),
 (38.10,'MMMMMM.mp3',.28,'approval','it is not bad','The subsequent qualified acceptance is a separate beat.'),
 (40.77,'vine-boom (20).mp3',.34,'impact_or_emphasis','oh','Impact on the visibly huge monster-truck reveal.'),
 (47.70,'fahhhh.mp3',.458,'comic_line','May, you are getting arrested','A roast tied to the monster-truck driving-over-everything scene.'),
 (50.13,'MMMMMM.mp3',.29,'approval','that is fire','Initial approval of the next option, before the confused reversal.'),
 (52.27,'error_CDOxCYm.mp3',.58,'confusion_or_rejection','bro what','Confusion after seeing how tiny the mini-mobile actually is.'),
 (55.20,'fahhhh.mp3',.458,'comic_line','you are cooked','Comic roast of the tiny car with no practical space; no automatic doom bell.'),
 (56.73,'ooooo.mp3',.40,'excited_positive_reaction','a Supra, yo','Excited recognition of the Supra.'),
 (63.43,'MMMMMM.mp3',.31,'approval','I will trade you that, please','Explicit preference and acceptance of the Supra.'),
 (65.47,'vine-boom (20).mp3',.34,'impact_or_emphasis','what the','Impact on the ridiculous banana-shaped car reveal.'),
 (71.47,'among-us-role-reveal-sound.mp3',.21,'dubious_or_ironic','if she would like the banana car','The ironic attempt to sell a banana-shaped date car as attractive; supported by the physical car and the date dialogue.'),
 (79.03,'fahhhh.mp3',.458,'comic_line','September, you are a menace','Direct roast; no extra generic sting on the preceding oh.'),
 (80.60,'sudden-suspense-sound-effect.mp3',.58,'unexpected_or_tense','what the','Unexpected toilet-car reveal and disbelieving reaction.'),
 (87.70,'fahhhh.mp3',.458,'comic_line','poop and drive','The specific toilet-car punchline. No extra eww is forced where he does not say it.'),
 (90.73,'anime-wow-sound-effect.mp3',.38,'visual_admiration','an SVJ, yo','The striking Lamborghini reveal and sustained impressed reaction.'),
 (100.70,'MMMMMM.mp3',.30,'approval','that is fire / I would love that','One approval cue for the final pink-car choice; the next positive line is not auto-filled.'),
]
effects=[]
for at,name,volume,function,cue,reason in choices:
    candidates=[(i,e) for i,e in enumerate(examples) if e['sound']==name]
    index,_=next(((i,e) for i,e in candidates if e['timeline'] in {'Srijon version','test 2 - SFX v2'}),candidates[0])
    at=round(at*draft['fps'])/draft['fps'];length=min(catalog[name]['duration'],draft['duration']/s.MICRO-at)
    if name=='among-us-role-reveal-sound.mp3':length=min(length,2.45)
    e={'start':round(at,6),'duration':length,'source_start':0,'speed':1,'sound':name,'volume':volume,'function':function,
        'dialogue':cue,'reason':reason,'enabled':True,'review':True,'example_index':index,'alternatives':[],
        'fade_in':.003,'fade_out':.14 if length<catalog[name]['duration']-.1 else .035}
    if name=='among-us-role-reveal-sound.mp3':
        e['context_evidence']={'kind':'visual_context','strength':'high','cue':'A literal banana-shaped car, a date complaint, then if she would like the banana car',
            'why_this_sound':'The absurd date-car claim and the attempted ironic positive spin resemble the learned dubious/ironic use, rather than a generic confession or a palette quota.'}
    effects.append(e)
plan={'project':'test 1','timeline':'test 3','output_timeline':'test 3 Auto SFX','duration':draft['duration']/s.MICRO,
    'source_hash':hashlib.sha256(path.read_bytes()).hexdigest(),'created':time.time(),'effects':effects,'captions':s.caption_rows(draft),
    'style_profile_version':5,'master_gain':1,'engine':'Latest revised Srijon conventions, reaction word timing, source-story context and local frame review',
    'skipped_cues':['No automatic opening movie on okay/lets-see.', 'No doom bell merely for cooked/arrested.',
        'No creepy layer on ordinary car criticism.', 'No extra cue for every car noun, oh, yo or repeated positive line.'],
    'limitations':'User preference agreement is not yet measured on this new video; final CapCut playback needs review.'}
s.validate_plan(plan,sounds)
out=s.OUTPUTS/'test3';out.mkdir(exist_ok=True)
s.write_json(out/'reviewed_plan.json',plan);s.write_json(out/'source_snapshot.json',draft)
r=s.export_copy(plan);s.write_json(out/'export.json',r)
lines=['# test 3 SFX plan','',f'{len(effects)} selected cues across {plan["duration"]:.1f}s; no palette quota.','',
    '| Time | Sound | Reaction | Reason |','|---:|---|---|---|']
for e in effects:lines.append(f'| {e["start"]:.2f}s | {e["sound"]} | {e["dialogue"]} | {e["reason"]} |')
(out/'PLAN.md').write_text('\n'.join(lines),encoding='utf-8')
print('PREPARED',len(effects),'cues; explicit EWWW at 8.40s')
