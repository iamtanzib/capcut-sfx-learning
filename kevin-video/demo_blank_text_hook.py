"""Use real cached intro/native settings in an isolated blank-field project."""
import json,os,sys,copy
from pathlib import Path
from unittest.mock import patch
BASE=Path(__file__).resolve().parent;LIVE=Path(os.environ['LOCALAPPDATA'])/'SoundPilotLearning'
OUT=BASE/'outputs/text-hook-feature';STATE=OUT/'demo-state';DRAFTS=OUT/'demo-drafts';PR=DRAFTS/'demo';FOLDER=PR/'Timelines/DEMO'
STATE.mkdir(exist_ok=True);FOLDER.mkdir(parents=True,exist_ok=True)
cfg=json.loads((LIVE/'config.json').read_text(encoding='utf-8-sig'));cfg['draft_root']=str(DRAFTS)
(STATE/'config.json').write_text(json.dumps(cfg),encoding='utf-8');os.environ['SOUNDPILOT_STATE']=str(STATE)
sys.path.insert(0,str(BASE/'plugins/capcut-sfx-learning'));import service as a
import hooks,edit_modes,shutil
inventory=json.loads((OUT/'TIMELINE_INVENTORY.json').read_text());ref=next(r for r in inventory if r['timeline']=='Day 1.6')
draft=a.s.read_json(Path(json.loads((LIVE/'config.json').read_text())['draft_root'])/'test 1'/'Timelines'/ref['timeline_id']/'draft_content.json')
for mat in draft['materials']['texts']:
    if mat['id']==ref['long_text'][0]['material']['id']:
        content=hooks.parsed(mat);content['text']=''
        for run in content['styles']:run['range']=[0,0]
        mat['content']=json.dumps(content)
draft['id']='DEMO';a.s.write_json(FOLDER/'draft_content.json',draft);a.s.write_json(PR/'draft_content.json',draft)
a.s.write_json(PR/'Timelines/project.json',{'main_timeline_id':'DEMO','timelines':[{'id':'DEMO','name':'Blank Hook Demo'}]})
job='94bc2d878df64d54';dest=a.job_path(job);dest.mkdir(exist_ok=True)
for filename in ('context_report.json','source.json','catalog.json'):shutil.copy2(LIVE/'jobs'/job/filename,dest/filename)
r=a.s.read_json(LIVE/'jobs'/job/'job.json');r.update(project='demo',timeline='Blank Hook Demo',timeline_id='DEMO');a.s.write_json(dest/'job.json',r)
batch=hooks.prepare(a,[{'project':'demo','timeline':'DEMO','analysis_job_id':job}]);jid=batch['jobs'][0]
hook={'text':'YOUR BIRTH MONTH IS\nYOUR MAGIC PILL\nWHAT DID YOU GET?','highlight_phrases':['MAGIC PILL'],
    'evidence':{'role':'video_track_2','quote':'Your birth month is your new magic pill.'},'reason':'Keep the exact birth-month magic-pill topic and the choice question from the main intro.'}
notes={'intro_reviewed':True,'unresolved':[],'layout_reviewed':True}
hooks.stage(a,jid,hook,notes);preview=hooks.preview(a,jid)
before=copy.deepcopy(draft)
with patch.object(a.s,'capcut_running',return_value=False):applied=edit_modes.apply_hooks(a,[jid])
after=a.s.read_json(FOLDER/'draft_content.json');b=copy.deepcopy(before);d=copy.deepcopy(after)
for doc in (b,d):
    for mat in doc['materials']['texts']:
        if mat['id']==ref['long_text'][0]['material']['id']:mat.pop('content')
assert b==d,'Native settings, captions, audio or zoom edits changed.'
shutil.copy2(preview['image'],OUT/'INTRO_HOOK_DEMO.png')
a.s.write_json(OUT/'DEMO_RESULT.json',{'cached_intro_used':True,'transcription_runs':0,'native_settings_other_tracks_unchanged':True,
    'real_capcut_projects_modified':False,'demo_image':str(OUT/'INTRO_HOOK_DEMO.png'),'result':applied})
print(json.dumps(a.s.read_json(OUT/'DEMO_RESULT.json'),indent=2))
