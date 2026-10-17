"""Offline bootstrap verification; no CapCut project mutation."""
import argparse,json,os,sys,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--memory-only',action='store_true');p.add_argument('--verify-files',action='store_true');a=p.parse_args()
os.environ['SOUNDPILOT_STATE']=a.state;sys.path.insert(0,str(ROOT/'plugins/capcut-sfx-learning'))
import service as api
profile=api.s.read_json(api.s.DATA/'style_profile.json');examples=api.s.read_json(api.s.DATA/'examples.json')
info={'python':sys.executable,'python_prefix':sys.prefix,'python_base_prefix':sys.base_prefix,'style_version':profile['version'],'reference_examples':len(examples),
    'revised_sound_assets':len(profile.get('mix_preferences',{}).get('sound_levels',{})),'revision_history_files':len(list((api.STATE/'history').glob('*.json')))}
if (api.s.DATA/'zoom_style.json').exists():
    zoom=api.s.read_json(api.s.DATA/'zoom_style.json');info.update(zoom_style_version=zoom['version'],zoom_reference_timelines=len(zoom['references']),zoom_reference_events=sum(len(r['events']) for r in zoom['references']))
info['plugin_version']=api.s.read_json(ROOT/'plugins/capcut-sfx-learning/plugin.json')['version']
if not a.memory_only:
    import context_pipeline,numpy,mcp,cv2,tiktoken
    assert numpy.__version__=='1.26.4'
    from faster_whisper import WhisperModel
    model=WhisperModel('base.en',device='cpu',compute_type='int8',cpu_threads=2,num_workers=1,download_root=str(ROOT/'models/speech'),local_files_only=True)
    cfg=api.s.config();catalog=api.s.read_json(api.s.DATA/'sound_catalog.json')
    assert all(Path(s['path']).is_file() for s in catalog)
    info.update(ffmpeg=shutil.which('ffmpeg'),ffprobe=shutil.which('ffprobe'),library=cfg['library'],mp3_catalog=len(catalog),offline_speech_model=True)
    assert info['ffmpeg'] and info['ffprobe'];assert str(ROOT/'runtime/tools').lower() in info['ffmpeg'].lower()
    assert Path(sys.prefix).resolve()==(ROOT/'runtime/env').resolve();assert Path(sys.base_prefix).resolve()==(ROOT/'runtime/python').resolve()
if a.verify_files:
    expected=json.loads((ROOT/'SHA256_FILES.json').read_text())
    for relative,sha in expected.items():
        if relative=='runtime/env/pyvenv.cfg':continue # Bootstrap rebases this file intentionally.
        path=ROOT/relative;assert path.is_file(),relative
        h=hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        assert h.hexdigest()==sha,relative
    info['file_hashes_verified']=len(expected)-1
print(json.dumps(info,ensure_ascii=False,indent=2))
