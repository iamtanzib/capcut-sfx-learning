"""Shopping-cart reaction plan. No saved source backup or duplicate project."""
import hashlib
import time
import soundpilot as s

p=s.project_path('test 1');_,draft,path=s.load_timeline(p,'test 4')
sounds=s.read_json(s.DATA/'sound_catalog.json');catalog={a['name']:a for a in sounds};examples=s.read_json(s.DATA/'examples.json')
choices=[
 (3.07,'vine-boom (20).mp3',.34,'impact_or_emphasis','24 hours','Emphasis on the duration challenge, not a forced intro sting.'),
 (5.53,'error_CDOxCYm.mp3',.58,'confusion_or_rejection','bro what','The immediate objection to having no choice.'),
 (7.40,'awkward-moment.mp3',.40,'dry_or_awkward','where are my rights','Dry rhetorical complaint; no arbitrary rare music layer.'),
 (9.10,'ooooo.mp3',.36,'mild_reaction_lift','oh, gaming shopping cart','Recognition/interest in the gaming cart.'),
 (12.23,'MMMMMM.mp3',.30,'approval','that is fire','Clear approval; no additional cue on the repeated fire/I-would-too thought.'),
 (18.07,'MMMMMM.mp3',.28,'approval','that is comfortable','Approves the plushy cart. The subsequent I-dont-mind-that is left quiet.'),
 (25.17,'sudden-suspense-sound-effect.mp3',.53,'unexpected_or_tense','bro what, glass cart','Shock at the plainly uncomfortable glass cart.'),
 (28.60,'MMMMMM.mp3',.24,'approval','it does not at all','Agreement with the narrator that it does not look comfortable, distinct from the initial shock.'),
 (31.60,'fahhhh.mp3',.458,'comic_line','you are cooked','Direct roast of the 24-hour glass-cart sleeper, without a doom bell.'),
 (33.33,'ooooo.mp3',.34,'mild_reaction_lift','oh, ball pit','Short recognition of the ball-pit option.'),
 (38.23,'MMMMMM.mp3',.29,'approval','that is not bad','Accepts the ball-pit option after seeing it in use.'),
 (46.97,'awkward-moment.mp3',.36,'dry_or_awkward','that is not ...','A brief dry ending on the unfinished/skeptical response; no invented strong praise or horror.'),
]
effects=[]
for at,name,volume,function,cue,reason in choices:
    candidates=[(i,e) for i,e in enumerate(examples) if e['sound']==name]
    index,_=next(((i,e) for i,e in candidates if e['timeline'] in {'test 3','Srijon version','test 2 - SFX v2'}),candidates[0])
    at=round(at*draft['fps'])/draft['fps'];length=min(catalog[name]['duration'],draft['duration']/s.MICRO-at)
    effects.append({'start':round(at,6),'duration':length,'source_start':0,'speed':1,'sound':name,'volume':volume,
        'function':function,'dialogue':cue,'reason':reason,'enabled':True,'review':True,'example_index':index,'alternatives':[],
        'fade_in':.003,'fade_out':.12 if length<catalog[name]['duration']-.1 else .035})
plan={'project':'test 1','timeline':'test 4','duration':draft['duration']/s.MICRO,'source_hash':hashlib.sha256(path.read_bytes()).hexdigest(),
    'created':time.time(),'effects':effects,'style_profile_version':6,'master_gain':1,'save_backup':False,'create_project_copy':False,
    'engine':'Revised Srijon context-first cues, with silence for repeated or unclear statements',
    'skipped_cues':['No automatic movie on the choice-list opening.','No extra cue on repeated approvals.',
        'No rare atmosphere just because a glass cart is bad.','No forced heavenly/wow on the teddy cart without a clear approving reaction.'],
    'limitations':'Cue choices await user review. The last sentence is truncated, so its neutral cue should be reviewed.'}
s.validate_plan(plan,sounds)
out=s.OUTPUTS/'test4';out.mkdir(exist_ok=True)
s.write_json(out/'reviewed_plan.json',plan)
lines=['# test 4 sound plan','',f'{len(effects)} selected cues. No original-project backup or duplicate project is created.','',
    '| Time | Sound | Reaction | Reason |','|---:|---|---|---|']
for e in effects:lines.append(f'| {e["start"]:.2f}s | {e["sound"]} | {e["dialogue"]} | {e["reason"]} |')
(out/'PLAN.md').write_text('\n'.join(lines),encoding='utf-8')
print('PREPARED',len(effects),'cues; no saved backup/project copy')
