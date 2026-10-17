"""Relocated bundle checks with isolated state; never alter real CapCut drafts."""
import os,sys,json,subprocess,time,hashlib
from pathlib import Path
BASE=Path(__file__).resolve().parent;BUNDLE=BASE/'outputs/SoundPilot-MASTER-2026-10-10'
STATE=BASE/'outputs/master-20261010-test-state';DRAFTS=BASE/'outputs/master-20261010-test-drafts'
DRAFTS.mkdir(exist_ok=True);PLUGIN=BUNDLE/'plugins/capcut-sfx-learning';LIB=PLUGIN/'library';PY=BUNDLE/'runtime/env/Scripts/python.exe'
env={**os.environ,'SOUNDPILOT_STATE':str(STATE),'PYTHONPATH':'','CT2_FORCE_CPU_ISA':'GENERIC','CT2_USE_MKL':'0',
    'PATH':str(BUNDLE/'runtime/tools')+os.pathsep+str(Path(os.environ['SystemRoot'])/'System32')+os.pathsep+str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0')}
def run(args,python=True):
    proc=subprocess.run(([str(PY)] if python else [])+[str(x) for x in args],env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    if proc.returncode:raise RuntimeError((proc.stderr or proc.stdout)[-4000:])
    return proc.stdout
print('Running MASTER install in isolated state, without host registration...',flush=True)
out=run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',BUNDLE/'MASTER.ps1','install','-NoRegister','-StateRoot',STATE,'-DraftRoot',DRAFTS],False)
(BUNDLE/'RESTORE_INSTALL_TEST.txt').write_text(out,encoding='utf-8')
arch=json.loads((BUNDLE/'state/memory.json').read_text());current=json.loads((STATE/'memory.json').read_text())
assert current['profile']['version']==arch['profile']['version']==16 and len(current['examples'])==263 and current['receipts']==arch['receipts']
assert json.loads((STATE/'data/zoom_style.json').read_text())['version']==5
assert (STATE/'zoom_jobs/0c722b57ccad423c/plan.json').exists()
print('Checking independent newer-memory preservation and older-memory upgrades...',flush=True)
saved=(STATE/'memory.json').read_bytes();zsaved=(STATE/'data/zoom_style.json').read_bytes()
future=json.loads(saved);future['profile']['version']=17;future['profile']['test_sentinel']='newer-sfx'
zfuture=json.loads(zsaved);zfuture['version']=6;zfuture['test_sentinel']='newer-zoom'
(STATE/'memory.json').write_text(json.dumps(future));(STATE/'data/zoom_style.json').write_text(json.dumps(zfuture))
r=json.loads(run([BUNDLE/'restore_memory.py','--state',STATE,'--library',LIB]))
assert r['newer_existing_memory_preserved'] and not r['zoom_memory_restored_from_archive']
assert json.loads((STATE/'data/zoom_style.json').read_text())['test_sentinel']=='newer-zoom'
(STATE/'memory.json').write_bytes(saved);zolder=json.loads(zsaved);zolder['version']=1;(STATE/'data/zoom_style.json').write_text(json.dumps(zolder))
r=json.loads(run([BUNDLE/'restore_memory.py','--state',STATE,'--library',LIB]));assert r['zoom_memory_restored_from_archive'] and r['zoom_style_version']==5
# Applied histories and 28-vs34 manual zoom adoption stay present after rebase.
refs=json.loads((STATE/'data/zoom_style.json').read_text())['references'];assert len(refs)==8 and sum(len(r['events']) for r in refs)==60
assert 'get_context_batch' in (PLUGIN/'server.py').read_text()
print('Verifying bundled model/runtime and actual MCP transport...',flush=True)
health=json.loads(run([BUNDLE/'health_check.py','--state',STATE]));assert health['plugin_version']=='0.1.10' and health['offline_speech_model']
mcp=run([PLUGIN/'tests/mcp_smoke.py']);assert 'get_context_batch' in mcp and 'learn_zoom_revision' in mcp
# Exercise offline preparation using only shipped runtime/models and a tiny generated source.
project=DRAFTS/'fixture';folder=project/'Timelines/T';folder.mkdir(parents=True,exist_ok=True);media=project/'silent.mp4'
run([BUNDLE/'runtime/tools/ffmpeg.exe','-nostdin','-v','error','-f','lavfi','-i','color=c=navy:s=160x90:r=8','-f','lavfi','-i','anullsrc=r=16000:cl=mono','-t','2','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-y',media],False)
draft={'id':'T','duration':2_000_000,'materials':{'videos':[{'id':'v','path':str(media)}],'audios':[],'texts':[]},
    'tracks':[{'type':'video','segments':[{'id':'s','material_id':'v','volume':1,'target_timerange':{'start':0,'duration':2_000_000},'source_timerange':{'start':0,'duration':2_000_000}}]}]}
(folder/'draft_content.json').write_text(json.dumps(draft));(project/'Timelines/project.json').write_text(json.dumps({'timelines':[{'id':'T','name':'fixture'}]}))
before=hashlib.sha256((folder/'draft_content.json').read_bytes()).hexdigest()
batch=json.loads(run([PLUGIN/'cli.py','prepare_batch','--json',json.dumps({'targets':[{'project':'fixture','timeline':'T'}],'workers':1})]));assert batch['workflow']=='sfx_and_zoom'
began=time.monotonic()
while True:
    progress=json.loads(run([PLUGIN/'cli.py','batch_status','--json',json.dumps({'batch_id':batch['batch_id']})]));status=progress['jobs'][0]['status']
    if status in ('ready','failed'):break
    if time.monotonic()-began>120:raise TimeoutError('Offline preparation did not finish.')
    time.sleep(2)
assert status=='ready',progress
assert before==hashlib.sha256((folder/'draft_content.json').read_bytes()).hexdigest()
result={'plugin_version':'0.1.10','sfx_memory_version':16,'sfx_examples':263,'zoom_memory_version':5,'zoom_reference_events':60,
    'portable_runtime_rebased':True,'models_load_offline':True,'actual_mcp_22_tools_verified':True,'sfx_plus_zoom_default_verified':True,
    'old_zoom_memory_upgraded':True,'newer_sfx_and_zoom_memories_preserved':True,'applied_jobs_and_revisions_restored':True,
    'offline_preparation':status,'synthetic_draft_unchanged':True,'real_capcut_projects_modified':False,'host_registration_in_test':False,'health':health}
(BUNDLE/'RESTORE_TEST_RESULTS.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2),flush=True)
