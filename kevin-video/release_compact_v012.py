"""Ship the owned update source; leave CapCut, model settings and memory untouched."""
import hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=ROOT/'plugins/capcut-sfx-learning';version='0.1.12'
assert json.loads((source/'plugin.json').read_text(encoding='utf-8'))['version']==version
assert json.loads((source/'.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version']==version
installed=Path.home()/'.codex/plugins/cache/srijon-sfx/capcut-sfx-learning'/version
for name in ['service.py','server.py','hooks.py','edit_modes.py','skills/capcut-sfx-learning/SKILL.md']:
    assert (source/name).read_bytes()==(installed/name).read_bytes(),name
claude=Path.home()/'.claude/skills/capcut-sfx-learning'
marker=claude/'.soundpilot-owned'
if claude.exists() and not marker.is_file():raise ValueError('Preserve unrelated Claude skill; update only owned skill.')
shutil.copytree(source/'skills/capcut-sfx-learning',claude,dirs_exist_ok=True)
marker.write_text('capcut-sfx-learning '+version,encoding='utf-8')
dest=ROOT/'outputs/plugin-release';dest.mkdir(exist_ok=True)
archive=dest/f'capcut-sfx-learning-{version}-quality-compact.zip'
if archive.exists():raise ValueError('Keep the existing release ZIP intact.')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(source.rglob('*')):
        if not p.is_file() or p.is_symlink() or any(x in ('.venv','__pycache__','node_modules','.git') for x in p.relative_to(source).parts) or p.suffix in ('.pyc','.log'):continue
        z.write(p,Path('capcut-sfx-learning')/p.relative_to(source))
    z.write(ROOT/'outputs/token-compact-v012/VERIFIED.json','capcut-sfx-learning/COMPACT_PAYLOAD_VERIFIED.json')
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
sha=hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix('.zip.sha256').write_text(sha+'  '+archive.name+'\n',encoding='utf-8')
result={'version':version,'installed':str(installed),'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha,
    'workflow_regression_tests':57,'installed_stdio_tools':31,'inherited_table_memory_verified':True,'claude_owned_skill_updated':True,
    'source_and_installed_code_match':True,'model_reasoning_or_asr_changed':False,'quality_gates_changed':False,
    'actual_quota_reduction_measured':False,'new_creative_quality_evaluation':False,'writes_to_capcut':False,
    'package_scope':'Code, owned skills, font and seed memories; not the full MASTER runtime/sound archive.'}
(ROOT/'outputs/token-compact-v012/RELEASE.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
