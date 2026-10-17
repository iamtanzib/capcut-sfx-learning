"""Codex-reviewed example using the two Timeline 11 videos and local sounds."""
import hashlib
import statistics
import time
import soundpilot as s

project=s.project_path('0928'); _,draft,path=s.load_timeline(project,'Timeline 11')
examples=s.read_json(s.DATA/'examples.json'); sounds=s.read_json(s.DATA/'sound_catalog.json')
catalog={a['name']:a for a in sounds}
# Selections reviewed against dialogue and both video tracks in the storyboard.
# These are new creative choices, not a claimed blind benchmark.
choices=[
    (2.40,'vine-boom (20).mp3',1.333,.40,'really','Emphasize the skeptical opening reaction.'),
    (8.90,'anime-wow-sound-effect.mp3',1.55,.32,'oh ho ho','The mansion reveal gets an impressed reaction.'),
    (11.65,'MMMMMM.mp3',1.10,.35,"oh that's nice",'Short approving sound under his smile.'),
    (15.90,'correct.mp3',.85,.32,"that's perfect",'A light positive confirmation before the reversal.'),
    (18.20,'sudden-suspense-sound-effect.mp3',1.433,.35,'bro what','The unexpected gift changes the mood.'),
    (24.35,'error_CDOxCYm.mp3',1.033,.42,'I mean nah','Reject the crocodile gift with a short error cue.'),
    (28.35,'among-us-role-reveal-sound.mp3',3.30,.24,'pickles','Suspicious cue for the crocodile named Pickles.'),
    (33.65,'vine-boom (20).mp3',1.333,.34,'oh wait what','The castle reveal reverses the previous dismissive reaction.'),
    (36.40,'MMMMMM.mp3',1.10,.35,"I'm taking the castle",'His approval lands during the castle choice.'),
    (39.80,'error_CDOxCYm.mp3',1.033,.40,'oh no never mind','Punctuate the quick change of mind.'),
    (48.60,'awkward-moment.mp3',1.50,.48,"what if it's a rock",'Brief awkward anticipation before the tiny money gift.'),
    (50.35,'vine-boom (20).mp3',1.333,.40,'a $1','Accent the one-dollar punchline.'),
    (55.00,'fahhhh.mp3',1.70,.30,"it's the thought that counts",'Small comic disappointment, timed under his ironic acceptance.'),
    (58.15,'anime-wow-sound-effect.mp3',1.55,.34,'is that a Pokemon','Positive reveal cue for the Pokemon cards.'),
    (62.10,'MMMMMM.mp3',1.10,.35,"yo I'm doing that",'Finish on his approving selection.'),
]
effects=[]
for at,name,length,volume,dialogue,reason in choices:
    same=[(i,e) for i,e in enumerate(examples) if e['sound']==name]
    index,template=same[0] if same else next((i,e) for i,e in enumerate(examples) if e['sound']=='vine-boom (20).mp3')
    effects.append({'start':at,'duration':min(length,catalog[name]['duration'],draft['duration']/s.MICRO-at),'source_start':0,'speed':1,
        'sound':name,'volume':volume,'dialogue':dialogue,'reason':reason,'review':False,'enabled':True,'example_index':index,'alternatives':[]})
plan={'project':'0928','timeline':'Timeline 11','output_timeline':'Timeline 12 Auto SFX','duration':draft['duration']/s.MICRO,
    'source_hash':hashlib.sha256(path.read_bytes()).hexdigest(),'created':time.time(),'engine':'Codex scene review + local placement',
    'limitations':'Reviewed using captions and sampled frames of both video tracks. Final playback and artistic preferences still need review.',
    'effects':effects,'captions':s.caption_rows(draft),'existing_sfx':14,'excluded_reference':None}
s.validate_plan(plan,sounds)
s.write_json(s.OUTPUTS/'demo_plan.json',plan); s.write_json(s.OUTPUTS/'latest_plan.json',plan)
report=s.export_copy(plan,replace_existing=True)
print(report)
