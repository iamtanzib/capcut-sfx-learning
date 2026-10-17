"""New video: selections reviewed against both dialogue streams and local frames."""
import hashlib
import time
import soundpilot as s

matches=[s.project_path(p['name']) for p in s.list_projects() if s.read_json(s.project_path(p['name'])/'draft_meta_info.json').get('draft_name','').casefold()=='test 1']
if len(matches)!=1:raise ValueError('Expected exactly one project named test 1.')
project=matches[0];_,draft,path=s.load_timeline(project,'Timeline 01')
examples=s.read_json(s.DATA/'examples.json');sounds=s.read_json(s.DATA/'sound_catalog.json')
catalog={a['name']:a for a in sounds}
# No old SFX exists in this target video. Times follow its captions/words and reveals.
choices=[
    (.35,'movie_1.mp3',.72,.22,'Your school is getting a brand new vending machine','Short opening accent; keep the narrator readable.'),
    (5.36,'mac-quack.mp3',.95,.28,'bro','A small comic beat for the skeptical reaction before the choices.'),
    (9.08,'MMMMMM.mp3',.98,.30,'oh heck yeah bro','Approving reaction to the fast-food machine and his smile.'),
    (15.26,'correct.mp3',1.08,.28,'exactly give me some wings','Positive confirmation for the wings choice.'),
    (17.20,'vine-boom (20).mp3',1.23,.34,'oh wait','Accent the unexpected test-answer machine and his immediate rethink.'),
    (20.80,'fahhhh.mp3',1.55,.30,'I failed everything','Land just after the confession, then leave room for the next line.'),
    (27.83,'error_CDOxCYm.mp3',.96,.35,'what the','A short disbelief cue at the candy-machine reaction.'),
    (29.02,'vine-boom (20).mp3',1.23,.30,"that's not even real",'Punctuate the absurd-looking candy reveal after the line.'),
    (33.32,'MMMMMM.mp3',.98,.27,'breakfast','Match the approving breakfast reaction.'),
    (38.28,'ding-sound-effect_2.mp3',1.12,.24,"long as it's free",'A light idea/approval cue on the repeated free condition.'),
    (39.92,'among-us-role-reveal-sound.mp3',1.55,.18,"I'm picking the test answers",'Quiet suspicious cue for choosing the cheating option.'),
    (41.88,'sudden-suspense-sound-effect.mp3',1.27,.27,'oh wait hold on','The supplies reveal changes his mind again.'),
    (48.30,'check-mark_oPG7Xo5.mp3',1.15,.26,"that's perfect",'Confirm that the emergency pencils solve his problem.'),
    (50.33,'awkward-moment.mp3',1.42,.30,'who gonna eat','A short awkward beat after questioning the ice-cream choice.'),
    (54.53,'fahhhh.mp3',1.10,.26,'nobody get no ice cream bro','Short closing comic rejection, ending before the video cuts.'),
]
effects=[]
for at,name,length,volume,dialogue,reason in choices:
    matches=[(i,e) for i,e in enumerate(examples) if e['sound']==name]
    index,_=matches[0] if matches else next((i,e) for i,e in enumerate(examples) if e['sound']=='vine-boom (20).mp3')
    # Snap new clips to the project's 30 fps grid.
    at=round(at*draft['fps'])/draft['fps'];length=min(length,catalog[name]['duration'],draft['duration']/s.MICRO-at)
    effects.append({'start':round(at,6),'duration':length,'source_start':0,'speed':1,'sound':name,'volume':volume,
        'dialogue':dialogue,'reason':reason,'review':False,'enabled':True,'example_index':index,'alternatives':[],
        'fade_in':.005,'fade_out':.14 if catalog[name]['duration']-length>.2 else .06})
plan={'project':project.name,'project_display_name':'test 1','timeline':'Timeline 01','output_timeline':'test 1 Auto SFX',
    'duration':draft['duration']/s.MICRO,'source_hash':hashlib.sha256(path.read_bytes()).hexdigest(),'created':time.time(),
    'engine':'Codex review of new two-track dialogue, word timing and local source frames',
    'effects':effects,'captions':s.caption_rows(draft),'existing_sfx':0,'old_target_sfx_used':False,
    'limitations':'Exact new-video selections, not an artistic accuracy guarantee. Sampled visual frames are coarse; final CapCut playback needs user review.'}
s.validate_plan(plan,sounds)
out=s.OUTPUTS/'test1';out.mkdir(parents=True,exist_ok=True)
s.write_json(out/'reviewed_plan.json',plan)
report=s.export_copy(plan);s.write_json(out/'export.json',report)
ctx=s.read_json(s.OUTPUTS/'context_report.json')
cost={'project':'test 1','folder':project.name,'video_seconds':plan['duration'],'effects':len(effects),
    'external_api_calls':[],'external_api_call_count':0,'external_api_cost_usd':0.0,
    'local_processing_seconds':ctx['seconds'],'local_model':ctx['model'],
    'pricing_method':'No paid inference API was invoked. Transcript/scene preparation and timeline writing ran locally.',
    'not_measured':'Codex chat/account usage in dollars; local electricity cost. These are not included in the $0 API figure.',
    'report_time':time.time()}
s.write_json(out/'cost_report.json',cost)
print(report)
print('EXTERNAL_API_COST_USD',cost['external_api_cost_usd'])
