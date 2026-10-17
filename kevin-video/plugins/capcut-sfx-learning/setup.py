"""Install local runtime, configure paths and fetch the selected offline speech model."""
import argparse,json,os,subprocess,sys,venv
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--draft-root',required=True);p.add_argument('--library',required=True);p.add_argument('--model-root',default='');p.add_argument('--reuse-python',default='');p.add_argument('--skip-model-download',action='store_true');a=p.parse_args()
state=Path(os.environ.get('SOUNDPILOT_STATE',Path(os.environ.get('LOCALAPPDATA',Path.home()))/'SoundPilotLearning'));state.mkdir(parents=True,exist_ok=True)
python=Path(a.reuse_python) if a.reuse_python else ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if not a.reuse_python:
    venv.EnvBuilder(with_pip=True).create(ROOT/'.venv');subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'requirements.txt')],check=True)
subprocess.run([str(python),'-c','import mcp, tiktoken, faster_whisper, numpy, scenedetect; assert numpy.__version__=="1.26.4"'],check=True)
state.joinpath('runtime.json').write_text(json.dumps({'python':str(python.resolve())}),encoding='utf-8')
params={'draft_root':a.draft_root,'library':a.library,'model_root':a.model_root}
subprocess.run([str(python),str(ROOT/'cli.py'),'configure','--json',json.dumps(params)],check=True)
if not a.skip_model_download:
    subprocess.run([str(python),'-c', 'import sys;sys.path.insert(0,'+repr(str(ROOT))+');import service as a;import context_pipeline;from faster_whisper import WhisperModel;c=a.s.config();WhisperModel(c["speech_model"],device="cpu",compute_type="int8",cpu_threads=c["speech_threads"],download_root=str(a.Path(c["model_root"])/"speech"))'],check=True)
print('Ready. Connect launch.py using a local MCP host; see INSTALL.md.')
