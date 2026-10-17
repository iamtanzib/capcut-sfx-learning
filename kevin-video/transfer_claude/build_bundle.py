"""Private Claude Code migration: capture current plugin/state without draft writes."""
from __future__ import annotations
import collections, hashlib, json, os, shutil, sys, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SRC = BASE / 'plugins/capcut-sfx-learning'
OLD = BASE / 'outputs/SoundPilot-MASTER-2026-10-10'
DEST = BASE / 'outputs/CapCut-SFX-Learning-Claude-Code-FULL-2026-10-13-v0.1.15'
SKIP = {'__pycache__', '.git', '.venv', 'node_modules', '.locks', 'locks'}
FORBIDDEN = {'auth.json', 'credentials.json', '.env', '.claude.json', 'settings.local.json'}
RESUME='--resume' in sys.argv

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def copytree(src, dst, suffixes=None):
    for p in Path(src).rglob('*'):
        rel = p.relative_to(src)
        if not p.is_file() or any(x in SKIP for x in rel.parts): continue
        if p.suffix in ('.pyc', '.pyo', '.log', '.writing') or p.name.lower() in FORBIDDEN: continue
        if suffixes is not None and p.suffix.lower() not in suffixes: continue
        q = Path(dst) / rel; q.parent.mkdir(parents=True, exist_ok=True)
        if RESUME and q.is_file() and q.stat().st_size==p.stat().st_size and q.stat().st_mtime_ns==p.stat().st_mtime_ns: continue
        shutil.copy2(p, q)

def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def state_inventory(root):
    """Check read-only snapshot consistency without writing live lock sidecars."""
    result = {}
    for p in root.rglob('*'):
        rel = p.relative_to(root)
        if not p.is_file() or any(x in SKIP for x in rel.parts): continue
        if p.suffix in ('.pyc', '.pyo', '.log', '.writing') or p.name.lower() in FORBIDDEN: continue
        stat = p.stat()
        result[rel.as_posix()] = {'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
                                 'sha256': sha(p) if p.suffix == '.json' else None}
    return result

if DEST.exists() and not RESUME: raise RuntimeError('Preserve existing bundle; use a new generation.')
DEST.mkdir(parents=True,exist_ok=RESUME)
# Import file-reading engine only. service.initialize() writes derived memory at
# import time, which is unnecessary for an export of the already active state.
from types import SimpleNamespace
live_state=Path(os.environ.get('SOUNDPILOT_STATE',str(Path(os.environ['LOCALAPPDATA'])/'SoundPilotLearning'))).resolve()
os.environ['SOUNDPILOT_STATE']=str(live_state)
sys.path.insert(0,str(SRC/'engine')); import soundpilot
api=SimpleNamespace(STATE=live_state,s=soundpilot)
cfg = api.s.config(); library = Path(cfg['library'])
print('Capturing plugin 0.1.15 and current SFX/zoom/hook memory...', flush=True)
copytree(SRC, DEST/'plugins/capcut-sfx-learning')
before = state_inventory(api.STATE)
copytree(api.STATE, DEST/'state')
after = state_inventory(api.STATE)
if before != after: raise RuntimeError('Live state changed during snapshot; do not use this generation.')
for rel, metadata in before.items():
    copied = DEST/'state'/rel
    if copied.stat().st_size != metadata['bytes']: raise RuntimeError('Incomplete state copy: '+rel)
    if metadata['sha256'] and sha(copied) != metadata['sha256']: raise RuntimeError('State copy changed: '+rel)
write(DEST/'STATE_SNAPSHOT_PARITY.json', {'source_state_unchanged_during_copy': True,
      'files': before, 'live_state_writes': False})
memory = json.loads((DEST/'state/memory.json').read_text(encoding='utf-8'))
zoom = json.loads((DEST/'state/data/zoom_style.json').read_text(encoding='utf-8'))
hook = json.loads((DEST/'state/data/hook_style.json').read_text(encoding='utf-8'))

print('Copying tested Python, exact installed dependencies, FFmpeg and offline models...', flush=True)
venv_cfg = dict(line.split(' = ', 1) for line in (BASE/'.venv/pyvenv.cfg').read_text().splitlines() if ' = ' in line)
copytree(Path(venv_cfg['home']), DEST/'runtime/python')
# Use the current environment, not the older recovery's dependency snapshot.
copytree(BASE/'.venv', DEST/'runtime/env')
copytree(OLD/'runtime/tools', DEST/'runtime/tools')
for tool in ('ffmpeg', 'ffprobe'):
    actual = Path(shutil.which(tool)); target = DEST/'runtime/tools'/actual.name
    shutil.copy2(actual, target)
copytree(Path(cfg['model_root']), DEST/'models')
import subprocess
packages = subprocess.run([sys.executable, '-m', 'pip', 'freeze', '--all'], capture_output=True, text=True, check=True)
(DEST/'RUNTIME_PACKAGES.txt').write_text(packages.stdout, encoding='utf-8')
shutil.copy2(BASE/'.venv/pyvenv.cfg', DEST/'runtime/ORIGINAL_PYVENV.txt')

print('Copying all library files and referenced external SFX/fonts...', flush=True)
audio = DEST/'library'; copytree(library, audio)
asset_map = {str(p): 'library/'+p.relative_to(library).as_posix() for p in library.rglob('*') if p.is_file()}
hash_cache = {}
def h(p):
    key = str(p)
    if key not in hash_cache: hash_cache[key] = sha(p)
    return hash_cache[key]
def add_asset(src, preferred=None):
    src = Path(src)
    if not src.is_file(): return None
    known=asset_map.get(str(src))
    if known and (DEST/known).is_file(): return known
    digest = h(src)
    same = next((p for p in audio.rglob('*') if p.is_file() and p.name.casefold() == src.name.casefold() and h(p) == digest), None)
    if same is None:
        rel = Path(preferred) if preferred else Path('external-imports')/src.name
        same = audio/rel
        if same.exists() and h(same) != digest: same = same.with_name('ARCHIVED-'+digest[:10]+'-'+same.name)
        if not same.exists(): same.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, same)
    relative = 'library/'+same.relative_to(audio).as_posix()
    return relative
old_info = json.loads((OLD/'BACKUP_INFO.json').read_text(encoding='utf-8-sig'))
for original, relative in old_info['asset_map'].items():
    if original in asset_map: continue
    src = Path(original)
    if not src.is_file(): src = OLD/'plugins/capcut-sfx-learning/library'/relative
    dest_relative = add_asset(src, relative)
    if dest_relative: asset_map[original] = dest_relative
missing = set(); footage = {}; fonts = {}; current_projects = api.s.list_projects()
media_ext = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'}
path_keys = {'path', 'file_path', 'local_path', 'video_path', 'source_path', 'source_file', 'font_path', 'path_on_disk', 'original_path'}
def inspect(value, project=None):
    if isinstance(value, dict):
        for key, val in value.items():
            if key in path_keys and isinstance(val, str) and val:
                p = Path(val) if Path(val).is_absolute() else (api.s.resolve_path(val, project) if project else None)
                if p is not None:
                    ext = p.suffix.lower()
                    if p.is_file():
                        if ext in media_ext: asset_map[str(p)] = add_asset(p)
                        elif ext in ('.ttf', '.otf'):
                            if str(p) in fonts: continue
                            target = DEST/'assets/fonts'/p.name
                            if target.exists() and h(target) != h(p): target = target.with_name(h(p)[:10]+'-'+p.name)
                            target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, target)
                            fonts[str(p)] = target.relative_to(DEST).as_posix()
                        elif ext in ('.mp4', '.mov', '.mkv', '.avi'): footage[str(p).casefold()] = {'path': str(p), 'bytes': p.stat().st_size}
                    elif ext in media_ext | {'.ttf', '.otf', '.mov', '.mp4'}: missing.add(str(p))
            else: inspect(val, project)
    elif isinstance(value, list):
        for item in value: inspect(item, project)
for p in (DEST/'state').rglob('*.json'):
    try: inspect(json.loads(p.read_text(encoding='utf-8-sig')))
    except (ValueError, OSError): pass
# Snapshot saved native metadata, avoiding CapCut's 30GB proxy/recycle cache.
for pi in current_projects:
    project = api.s.project_path(pi['name'])
    copytree(project, DEST/'reference-projects'/project.name, {'.json', '.ttf', '.otf'})
    for tl in pi['timelines']:
        _, draft, _ = api.s.load_timeline(project, tl['id']); inspect(draft, project)
asset_map.update(fonts)
# MP3 lookup is filename-based; keep current library names as canonical.
names = {}; aliases = {}
for p in sorted(audio.rglob('*.mp3'), key=lambda p: ('external-imports' in p.parts, str(p))):
    key = p.name.casefold()
    if key not in names: names[key] = p; continue
    old_relative = 'library/'+p.relative_to(audio).as_posix()
    new = p.with_name('ARCHIVED-'+h(p)[:10]+'-'+p.name)
    if new.exists():
        if h(new)!=h(p): raise RuntimeError('Archived audio alias collision: '+str(new))
        # A resumed partial export may already contain this identical alias.
        p.unlink()
    else: p.rename(new)
    new_relative = 'library/'+new.relative_to(audio).as_posix(); aliases[old_relative] = new_relative
    for original, relative in list(asset_map.items()):
        if relative == old_relative: asset_map[original] = new_relative

# Live memory is authoritative; stale v16 seeds are replaced in the transfer copy.
for name, value in [('style_profile.json', memory['profile']), ('examples.json', memory['examples']), ('zoom_style.json', zoom), ('hook_style.json', hook)]:
    write(DEST/'plugins/capcut-sfx-learning/seed'/name, value)
write(DEST/'plugins/capcut-sfx-learning/seed/config.json', {**cfg, 'draft_root': '', 'library': '', 'model_root': '', 'sidebar_settings': ''})

print('Collecting source, every update archive, historical reports and migration docs...', flush=True)
source_archive = DEST/'development-source'
for p in BASE.iterdir():
    if p.is_file() and p.suffix.lower() in {'.py', '.md', '.txt', '.ps1', '.bat', '.html', '.json'}:
        if p.name.lower() not in FORBIDDEN:
            source_archive.mkdir(parents=True, exist_ok=True); shutil.copy2(p, source_archive/p.name)
for top in ('data', 'tests', 'vendor'):
    copytree(BASE/top, source_archive/top)
copytree(SRC,source_archive/'installed-plugin-source')
copytree(BASE/'.agents', source_archive/'.agents')
for p in (BASE/'transfer_claude').glob('*.py'):
    q=source_archive/'migration-build'/p.name; q.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,q)
copytree(OLD/'reports', DEST/'reports/prior-history')
(DEST/'reports/workspace').mkdir(parents=True,exist_ok=True)
exclude = {p.name for p in (BASE/'outputs').iterdir() if p.name.startswith(('SoundPilot-', 'CapCut-SFX-Learning-Claude-Code-', 'recovery-', 'master-'))}
for p in (BASE/'outputs').iterdir():
    if p.name in exclude or p.name == '__pycache__': continue
    if p.is_dir(): copytree(p, DEST/'reports/workspace'/p.name, {'.json', '.md', '.txt', '.py', '.ps1', '.sha256', '.zip'})
    elif p.suffix in ('.json', '.md', '.txt', '.py'): shutil.copy2(p, DEST/'reports/workspace'/p.name)
copytree(Path(__file__).parent/'files', DEST)

plugin = DEST/'plugins/capcut-sfx-learning'
write(plugin/'.claude-plugin/plugin.json', {'name': 'capcut-sfx-learning', 'version': '0.1.15', 'description': 'Personal CapCut SFX, reaction zooms and native intro hooks with durable revision memory.', 'author': {'name': 'Srijon'}})
write(plugin/'.mcp.json', {'mcpServers': {'capcut-sfx-learning': {'type': 'stdio', 'command': 'powershell.exe', 'args': ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', '${CLAUDE_PLUGIN_ROOT}/launch.ps1']}}})
shutil.copy2(Path(__file__).parent/'files/migration/launch.ps1', plugin/'launch.ps1')
shutil.copy2(Path(__file__).parent/'files/migration/launch.py', plugin/'launch.py')
info = {
    'snapshot_date': '2026-10-13', 'snapshot_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'timezone': 'Asia/Dhaka', 'platform': 'native Windows x64', 'plugin_version': '0.1.15',
    'sfx_style_version': memory['profile']['version'], 'sfx_examples': len(memory['examples']),
    'zoom_style_version': zoom['version'], 'zoom_reference_timelines': len(zoom['references']), 'zoom_reference_events': sum(len(r.get('events', [])) for r in zoom['references']),
    'hook_style_version': hook['version'], 'hook_references': len(hook.get('references', [])), 'mcp_tools_expected': 31,
    'old_state_root': str(api.STATE), 'old_library_root': str(library), 'old_model_root': cfg['model_root'], 'old_workspace_root': str(BASE),
    'old_draft_root': cfg['draft_root'], 'original_config': cfg, 'asset_map': asset_map, 'duplicate_audio_aliases': aliases,
    'sound_files_by_type': dict(collections.Counter(p.suffix.lower() for p in audio.rglob('*') if p.is_file())),
    'cached_state_files': len([p for p in (DEST/'state').rglob('*') if p.is_file()]), 'credentials_included': False,
    'original_source_footage_included': False, 'reference_project_metadata_included': True,
    'creative_cross_host_equivalence_measured': False,
}
installed=Path(os.environ['USERPROFILE'])/'.codex/plugins/cache/srijon-sfx/capcut-sfx-learning/0.1.15'
source_hashes={p.relative_to(SRC).as_posix():sha(p) for p in SRC.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
parity={rel: {'source_sha256':digest, 'installed_sha256':sha(installed/rel) if (installed/rel).is_file() else None}
        for rel,digest in source_hashes.items()}
differences=[rel for rel,record in parity.items() if record['source_sha256'] != record['installed_sha256']]
if differences: raise RuntimeError('Workspace differs from installed plugin: '+', '.join(differences))
info['engine_matches_installed_0_1_15']=True
write(DEST/'BUNDLE_INFO.json', info)
write(DEST/'EXTERNAL_INPUTS.json', {'note': 'Full original footage is input data, not plugin runtime. Keep existing files on this PC; copy/relink them separately on another PC. Cached review audio/frames and complete learned memory ARE included.', 'available_source_footage': sorted(footage.values(), key=lambda x: x['path'].casefold()), 'missing_historical_paths': sorted(missing), 'saved_projects': current_projects})
write(DEST/'SOURCE_PARITY.json', {'all_source_files_match_installed':True,'files':parity,
      'transfer_copy_adaptations':['launch.ps1','launch.py','.mcp.json','.claude-plugin/plugin.json','seed/ (current live memory)']})
print(json.dumps({k: v for k, v in info.items() if k not in ('asset_map', 'original_config')}, ensure_ascii=False, indent=2), flush=True)
