"""Portable launcher: prefer the configured tested runtime, otherwise package venv."""
import json,os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
state=Path(os.environ.get('SOUNDPILOT_STATE',Path(os.environ.get('LOCALAPPDATA',Path.home()))/'SoundPilotLearning'))
runtime=state/'runtime.json'
python=Path(json.loads(runtime.read_text(encoding='utf-8'))['python']) if runtime.exists() else root/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if not python.is_file():
    print('Run setup.py with Python 3.12 before connecting the SFX plugin.',file=sys.stderr);sys.exit(1)
result=subprocess.run([str(python),str(root/'server.py'),*sys.argv[1:]],env=os.environ.copy())
sys.exit(result.returncode)
