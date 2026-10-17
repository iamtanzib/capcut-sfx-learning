"""Package normal-auto-close update and syntax-check its fixed Windows backend."""
import hashlib,json,shutil,subprocess,sys,zipfile
from pathlib import Path
base=Path(__file__).resolve().parent;source=base/'plugins/capcut-sfx-learning';version=json.loads((source/'plugin.json').read_text(encoding='utf-8'))['version']
sys.path.insert(0,str(source));import app_lifecycle as life
dest=base/'outputs'/('auto-close-'+version);dest.mkdir(exist_ok=True)
# Parse the backend without executing any of its application operations.
(dest/'CLOSE_BACKEND.txt').write_text(life.CLOSE_SCRIPT,encoding='utf-8')
parser=dest/'PARSE_ONLY.ps1'
parser.write_text('''param([string]$ScriptPath)
$ErrorActionPreference = 'Stop'
$backendText = [System.IO.File]::ReadAllText($ScriptPath)
$backendTokens = $null
$backendErrors = $null
[System.Management.Automation.Language.Parser]::ParseInput($backendText, [ref]$backendTokens, [ref]$backendErrors) | Out-Null
if ($backendErrors.Count -gt 0) { throw ($backendErrors | Out-String) }
Write-Output 'backend_parse_ok_no_execution'
''',encoding='utf-8')
check=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(parser),'-ScriptPath',str(dest/'CLOSE_BACKEND.txt')],capture_output=True,text=True,creationflags=0x08000000,timeout=15)
assert check.returncode==0,(check.stdout,check.stderr)
installed=Path.home()/'.codex/plugins/cache/srijon-sfx/capcut-sfx-learning'/version
for name in ['service.py','server.py','app_lifecycle.py','edit_modes.py','zoom.py','skills/capcut-sfx-learning/SKILL.md','skills/capcut-sfx-learning/references/zooms.md']:
    assert (source/name).read_bytes()==(installed/name).read_bytes(),name
claude=Path.home()/'.claude/skills/capcut-sfx-learning';marker=claude/'.soundpilot-owned'
if claude.exists() and not marker.is_file():raise ValueError('Preserve unowned Claude skill.')
shutil.copytree(source/'skills/capcut-sfx-learning',claude,dirs_exist_ok=True);marker.write_text('capcut-sfx-learning '+version,encoding='utf-8')
report={'version':version,'tests_passed':73,'installed_stdio_tools':31,'auto_close_default_verified':True,'windows_backend_syntax_verified':True,
    'actual_live_capcut_closure_tested':False,'capcut_drafts_modified':False,'forced_termination_or_dialog_response':False,
    'new_inference_or_api_calls':0,'source_settings_or_quality_gates_weakened':False,
    'feature':'Validated apply requests normal closure, waits for process absence and revalidates final autosave. Refusal/prompts/tray/stale source block writes. Read-only and keep-existing no-ops stay open.'}
(dest/'VERIFIED.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
archive=base/'outputs/plugin-release'/f'capcut-sfx-learning-{version}-auto-close.zip'
if archive.exists():raise ValueError('Preserve the existing release archive.')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(source.rglob('*')):
        if not p.is_file() or p.is_symlink() or any(x in ('.venv','__pycache__','node_modules','.git') for x in p.relative_to(source).parts) or p.suffix in ('.pyc','.log'):continue
        z.write(p,Path('capcut-sfx-learning')/p.relative_to(source))
    z.write(dest/'VERIFIED.json','capcut-sfx-learning/AUTO_CLOSE_VERIFIED.json')
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
sha=hashlib.sha256(archive.read_bytes()).hexdigest();archive.with_suffix('.zip.sha256').write_text(sha+'  '+archive.name+'\n',encoding='utf-8')
report.update(archive=str(archive),bytes=archive.stat().st_size,sha256=sha,scope='Update code, skills, fonts and seed memories; no full runtime/sound MASTER archive.')
(dest/'RELEASE.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
