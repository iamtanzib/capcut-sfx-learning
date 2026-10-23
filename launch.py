"""Same engine/state as the PowerShell launcher; protocol stdout stays clean."""
import json, os, subprocess, sys
from pathlib import Path
root = Path(__file__).resolve().parent
session = root.parents[1] / 'local-install/claude-session.json'
if not os.environ.get('SOUNDPILOT_STATE') and session.exists():
    os.environ['SOUNDPILOT_STATE'] = json.loads(session.read_text(encoding='utf-8-sig'))['state']
state = Path(os.environ.get('SOUNDPILOT_STATE', str(Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'SoundPilotLearning')))
runtime = state / 'runtime.json'
if not runtime.exists():
    print('Run setup.py first (Windows: INSTALL_CLAUDE_CODE.bat).', file=sys.stderr); sys.exit(1)
settings = json.loads(runtime.read_text(encoding='utf-8-sig'))
python = Path(settings['python'])
if not python.is_file():
    print('Configured Python moved. Rerun the installer.', file=sys.stderr); sys.exit(1)
if settings.get('ffmpeg_bin'):
    os.environ['PATH'] = settings['ffmpeg_bin'] + os.pathsep + os.environ.get('PATH', '')
sys.exit(subprocess.run([str(python), str(root/'server.py'), *sys.argv[1:]], env=os.environ.copy()).returncode)
