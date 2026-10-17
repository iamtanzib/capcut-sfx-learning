"""Varied second design; keeps original test 2 and Srijon version intact."""
import hashlib
import time
import soundpilot as s

project=s.project_path('test 1');_,draft,path=s.load_timeline(project,'test 2')
source_snapshot=draft
sounds=s.read_json(s.DATA/'sound_catalog.json');catalog={a['name']:a for a in sounds}
examples=s.read_json(s.DATA/'examples.json')
# Existing approved test 2 is the input. Its video gains are already normalized.
# Keep retained SFX near their prior audible levels and introduce soft contextual layers.
choices=[
 (2.73,'vine-boom (20).mp3',.19,'impact_or_emphasis','Banned?','Short emphasis on the challenge keyword.'),
 (5.85,'movie_1.mp3',.235,'dramatic_setup','okay / choice list','Opening setup on the hesitation before the options.'),
 (10.27,'MMMMMM.mp3',.15,'approval',"that's easy",'Genuine early confidence; keep the accepted approval convention.'),
 (12.03,'error_CDOxCYm.mp3',.30,'confusion_or_rejection','yes ... oh shoot','The accidental banned-word slip.'),
 (13.55,'undertakers-bell_2UwFCIe.mp3',.23,'doom_or_danger',"I'm cooked",'One doom bell on the cooked consequence, rather than another error pulse.'),
 (18.33,'awkward-moment.mp3',.34,'dry_or_awkward',"I can't do that",'A dry inability/hesitation beat on the sorry choice.'),
 (20.70,'fahhhh.mp3',.216,'comic_line','I apologize, I apologize','The over-formal repeated workaround is the comic line; keep it short.'),
 (23.47,'MMMMMM.mp3',.16,'approval',"that's easy",'Accepts the workaround, distinct from the earlier joke.'),
 (28.27,'error_CDOxCYm.mp3',.30,'confusion_or_rejection','bro','Quick mistake cue on saying the banned word.'),
 (29.33,'fahhhh.mp3',.216,'comic_line','I lost two','The learned funny-failure/self-roast beat.'),
 (31.05,'among-us-role-reveal-sound.mp3',.15,'dubious_or_ironic','I say it every day','An ironic self-incrimination layer after losing twice, not a cue on choosing a word.'),
 (33.73,'sudden-suspense-sound-effect.mp3',.32,'unexpected_or_tense','oh ... oh','The greeting ban starts the unsettled reaction.'),
 (36.48,'Creepy Sound Effect.mp3',.095,'unsettling','this is bad','Soft unsettling tail for losing ordinary greetings; below the dialogue.'),
 (39.10,'MMMMMM.mp3',.165,'approval',"I'm gonna do yes",'Clear selection of the option.'),
 (44.43,'awkward-moment.mp3',.32,'dry_or_awkward',"that's bad",'The social awkwardness of being unable to thank someone.'),
 (47.10,'MMMMMM.mp3',.137,'approval','exactly','Explicit agreement.'),
 (49.80,'vine-boom (20).mp3',.19,'impact_or_emphasis','okay ... oh shit','A punchy realization, varied from the earlier error cue.'),
 (51.18,'undertakers-bell_2UwFCIe.mp3',.18,'doom_or_danger','okay is in every conversation','A quiet short consequence sting after the slip; not a long competing music bed.'),
 (55.80,'MMMMMM.mp3',.15,'approval',"alright, it's not bad",'Approves the all-right alternative.'),
 (57.53,'vine-boom (20).mp3',.185,'impact_or_emphasis','like','Emphasize the echoed option word.'),
 (61.47,'awkward-moment.mp3',.30,'dry_or_awkward','like is in every sentence','Dry realization of the habit, without a forced FAHH.'),
 (65.53,'vine-boom (20).mp3',.185,'impact_or_emphasis','what','The skeptical final word echo.'),
 (69.17,'error_CDOxCYm.mp3',.305,'confusion_or_rejection','nah nah bro','Ordinary closing rejection.'),
]
effects=[]
for at,name,volume,function,cue,reason in choices:
    candidates=[(i,e) for i,e in enumerate(examples) if e['sound']==name]
    index,_=next(((i,e) for i,e in candidates if e['timeline']=='Srijon version'),candidates[0])
    at=round(at*draft['fps'])/draft['fps']
    length=min(catalog[name]['duration'],draft['duration']/s.MICRO-at)
    if name=='undertakers-bell_2UwFCIe.mp3':length=min(length,2.0)
    if name=='among-us-role-reveal-sound.mp3':length=min(length,2.7)
    if name=='Creepy Sound Effect.mp3':length=min(length,2.2)
    if at==round(20.7*draft['fps'])/draft['fps']:length=min(length,1.35)
    effects.append({'start':round(at,6),'duration':length,'source_start':0,'speed':1,'sound':name,'volume':volume,
        'function':function,'dialogue':cue,'reason':reason,'enabled':True,'review':True,'example_index':index,'alternatives':[],
        'fade_in':.015 if name=='Creepy Sound Effect.mp3' else .003,
        'fade_out':.18 if length<catalog[name]['duration']-.1 else .035})
plan={'project':'test 1','timeline':'test 2','output_timeline':'test 2 - SFX v2','duration':draft['duration']/s.MICRO,
    'source_hash':hashlib.sha256(path.read_bytes()).hexdigest(),'effects':effects,'captions':s.caption_rows(draft),
    'created':time.time(),'master_gain':1,'style_profile_version':4,
    'engine':'Varied Srijon palette, retained approval cues and contextual consequence layers',
    'limitations':'The added rare-sound interpretations are creative choices for user review; no accuracy percentage is claimed.'}
s.validate_plan(plan,sounds)
out=s.OUTPUTS/'test2v2';out.mkdir(exist_ok=True)
s.write_json(out/'reviewed_plan.json',plan);s.write_json(out/'source_snapshot.json',source_snapshot)
report=s.export_copy(plan,replace_existing=True);s.write_json(out/'export.json',report)
lines=['# test 2 — varied SFX design v2','',f'{len(effects)} cues using {len({e["sound"] for e in effects})} sound files. Original test 2 and Srijon version are preserved.','',
    '| Time | Sound | Cue | Reason |','|---:|---|---|---|']
for e in effects:lines.append(f'| {e["start"]:.2f}s | {e["sound"]} | {e["dialogue"]} | {e["reason"]} |')
(out/'PLAN.md').write_text('\n'.join(lines),encoding='utf-8')
print('V2_READY',len(effects),'cues',len({e['sound'] for e in effects}),'sounds',report['path'])
