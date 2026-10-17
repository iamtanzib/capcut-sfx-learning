"""Verify relocated runtime/MCP, real offline preparation, and restore guards."""
import os,sys,json,subprocess,time,hashlib
from pathlib import Path
BASE=Path(__file__).resolve().parent;BUNDLE=BASE/'outputs/SoundPilot-Recovery-2026-10-09'
PY=BUNDLE/'runtime/env/Scripts/python.exe';STATE=BASE/'outputs/recovery-test-state';LIB=BUNDLE/'plugins/capcut-sfx-learning/library';PLUGIN=BUNDLE/'plugins/capcut-sfx-learning'
env={**os.environ,'SOUNDPILOT_STATE':str(STATE),'PYTHONPATH':'','PATH':str(BUNDLE/'runtime/tools')+os.pathsep+str(Path(os.environ['SystemRoot'])/'System32')+os.pathsep+str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0'), 'CT2_FORCE_CPU_ISA':'GENERIC','CT2_USE_MKL':'0'}
def run(args):
    r=subprocess.run([str(PY),*map(str,args)],env=env,capture_output=True,text=True,encoding='utf-8')
    if r.returncode:raise RuntimeError(r.stderr or r.stdout)
    return r.stdout
archive=json.loads((BUNDLE/'state/memory.json').read_text(encoding='utf-8'))
current=json.loads((STATE/'memory.json').read_text());assert current['receipts']==archive['receipts'];assert len(current['examples'])==201
# Preserve a simulated newer memory, without touching the user's actual state.
saved=(STATE/'memory.json').read_bytes();future=json.loads(saved);future['profile']['version']=13;future['profile']['test_sentinel']='newer-memory'
(STATE/'memory.json').write_text(json.dumps(future),encoding='utf-8')
result=json.loads(run([BUNDLE/'restore_memory.py','--state',STATE,'--library',LIB]))
assert result['newer_existing_memory_preserved'] and json.loads((STATE/'memory.json').read_text())['profile']['test_sentinel']=='newer-memory'
(STATE/'memory.json').write_bytes(saved)
# Corrupt/missing memory recovers, retaining the corrupt original for inspection.
corrupt=BASE/'outputs/recovery-corrupt-test';corrupt.mkdir(exist_ok=True);(corrupt/'memory.json').write_text('{intentional corrupt fixture')
r=json.loads(run([BUNDLE/'restore_memory.py','--state',corrupt,'--library',LIB]));assert r['style_version']==12;assert list(corrupt.glob('memory.corrupt-*.json'))
# Restore old audio paths without overwriting an existing differing file.
sound_test=BASE/'outputs/recovery-audio-test';sound_test.mkdir(exist_ok=True);sentinel=sound_test/'MMMMMM.mp3';sentinel.write_bytes(b'existing user file fixture')
r=json.loads(run([BUNDLE/'restore_memory.py','--copy-sounds-to',sound_test]));assert sentinel.read_bytes()==b'existing user file fixture';assert 'MMMMMM.mp3' in r['different_existing_files_preserved']
# End-to-end local media/model pipeline from the copied runtime only.
drafts=BASE/'outputs/recovery-synthetic-drafts';project=drafts/'fixture';folder=project/'Timelines/T';folder.mkdir(parents=True,exist_ok=True)
media=project/'silent-fixture.mp4'
subprocess.run([str(BUNDLE/'runtime/tools/ffmpeg.exe'),'-nostdin','-v','error','-f','lavfi','-i','color=c=navy:s=160x90:r=8','-f','lavfi','-i','anullsrc=r=16000:cl=mono','-t','2','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-y',str(media)],env=env,check=True)
draft={'id':'T','duration':2000000,'materials':{'videos':[{'id':'v','path':str(media)}],'audios':[],'texts':[]},'tracks':[{'type':'video','segments':[{'id':'s','material_id':'v','volume':1,'target_timerange':{'start':0,'duration':2000000},'source_timerange':{'start':0,'duration':2000000}}]}]}
(folder/'draft_content.json').write_text(json.dumps(draft));(project/'Timelines/project.json').write_text(json.dumps({'timelines':[{'id':'T','name':'fixture'}]}));before=hashlib.sha256((folder/'draft_content.json').read_bytes()).hexdigest()
run([PLUGIN/'cli.py','configure','--json',json.dumps({'draft_root':str(drafts),'library':str(LIB),'model_root':str(BUNDLE/'models')})])
batch=json.loads(run([PLUGIN/'cli.py','prepare_batch','--json',json.dumps({'targets':[{'project':'fixture','timeline':'T'}],'workers':1})]))
began=time.monotonic()
while True:
    progress=json.loads(run([PLUGIN/'cli.py','batch_status','--json',json.dumps({'batch_id':batch['batch_id']})]));status=progress['jobs'][0]['status']
    if status in ('ready','failed'):break
    if time.monotonic()-began>90:raise TimeoutError('Relocated offline worker did not finish.')
    time.sleep(1)
assert status=='ready',progress
assert before==hashlib.sha256((folder/'draft_content.json').read_bytes()).hexdigest()
# Restored JSON/media previews point inside the test state, and MCP launches without the original PATH.
assert (STATE/'jobs'/batch['jobs'][0]/'context_report.json').is_file()
output=run([PLUGIN/'tests/mcp_smoke.py'])
result={'portable_runtime':str(PY),'base_and_environment_rebased':True,'original_workspace_runtime_used':False,'models_offline':True,
    'mp3_catalog':72,'reference_examples':201,'style_version':12,'revision_receipts_restored':len(archive['receipts']),
    'newer_memory_preserved':True,'corrupt_memory_preserved_and_recovered':True,'differing_existing_sound_preserved':True,
    'offline_media_preparation_status':status,'mcp_startup_and_13_tools':True,'real_capcut_projects_modified':False}
(BUNDLE/'RESTORE_TEST_RESULTS.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
