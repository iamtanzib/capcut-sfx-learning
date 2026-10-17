"""Restore all components, retain newer memory, never write native CapCut drafts."""
import argparse, copy, json, os, shutil, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(); p.add_argument('--state', required=True); p.add_argument('--draft-root', required=True); a = p.parse_args()
state = Path(a.state).resolve(); payload = ROOT/'state'; state.mkdir(parents=True, exist_ok=True)
info = json.loads((ROOT/'BUNDLE_INFO.json').read_text(encoding='utf-8'))
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True); temp = path.with_name(path.name+'.migration-writing')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8'); os.replace(temp, path)
old_values = {}
for relative in ('memory.json', 'data/style_profile.json', 'data/examples.json', 'data/zoom_style.json', 'data/hook_style.json', 'config.json'):
    q = state/relative
    if q.exists():
        try: old_values[relative] = read(q)
        except (ValueError, OSError):
            saved = state/'migration-preserved'/str(time.time_ns())/relative
            saved.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(q, saved)
            # Quarantine corrupt committed memory before service.initialize reads it.
            if relative == 'memory.json': q.rename(q.with_name('memory.corrupt-'+str(time.time_ns())+'.json'))
asset_map = {k.replace('\\', '/').casefold(): str(ROOT/v) for k, v in info['asset_map'].items()}
prefixes = [(info['old_state_root'], str(state)), (info['old_model_root'], str(ROOT/'models')), (info['old_library_root'], str(ROOT/'library'))]
def rebase(value):
    if isinstance(value, dict): return {k: rebase(v) for k, v in value.items()}
    if isinstance(value, list): return [rebase(v) for v in value]
    if not isinstance(value, str): return value
    normalized = value.replace('\\', '/'); key = normalized.casefold()
    if key in asset_map: return asset_map[key]
    for old, new in prefixes:
        old = old.replace('\\', '/')
        if key == old.casefold() or key.startswith(old.casefold()+'/'): return new+normalized[len(old):]
    return value
os.environ['SOUNDPILOT_STATE'] = str(state); sys.path.insert(0, str(ROOT/'plugins/capcut-sfx-learning')); import service as api
report = {}; skipped = {'runtime.json', 'config.json', 'memory.json', 'data/style_profile.json', 'data/examples.json', 'data/zoom_style.json', 'data/hook_style.json', 'data/sound_catalog.json'}
with api.lock('state'), api.lock('zoom-style'), api.lock('hook-style'), api.lock('analysis-index'):
    archived = read(payload/'memory.json'); current = old_values.get('memory.json')
    if current is None and 'data/style_profile.json' in old_values and 'data/examples.json' in old_values:
        current = {'profile': old_values['data/style_profile.json'], 'examples': old_values['data/examples.json'], 'receipts': []}
    take = current is None or current.get('profile', {}).get('version', -1) < archived['profile']['version']
    active = rebase(archived if take else current)
    write(state/'memory.json', active); write(state/'data/style_profile.json', active['profile']); write(state/'data/examples.json', active['examples'])
    report['sfx_restored'] = take; report['sfx_version'] = active['profile']['version']
    for relative, label in [('data/zoom_style.json', 'zoom'), ('data/hook_style.json', 'hook')]:
        archived = read(payload/relative); current = old_values.get(relative)
        take = current is None or current.get('version', -1) < archived['version']
        active = rebase(archived if take else current); write(state/relative, active)
        report[label+'_restored'] = take; report[label+'_version'] = active['version']
    restored = 0
    for source in payload.rglob('*'):
        if not source.is_file(): continue
        rel = source.relative_to(payload)
        if rel.as_posix() in skipped: continue
        target = state/rel
        if target.exists(): continue
        if source.suffix == '.json':
            value = rebase(read(source))
            if rel.name == 'job.json' and value.get('status') not in ('applied', 'failed'):
                value['archived_status'] = value.get('status'); value['status'] = 'needs_refresh'
            write(target, value)
        else:
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        restored += 1
    cfg = copy.deepcopy(old_values.get('config.json', info['original_config']))
    cfg.update(draft_root=str(Path(a.draft_root).resolve()), library=str(ROOT/'library'), model_root=str(ROOT/'models'), sidebar_settings='')
    write(state/'config.json', cfg)
    write(state/'migration-config-input.json', {k: cfg[k] for k in ('draft_root', 'library', 'model_root')})
    report.update(history_cache_files_restored=restored, capcut_project_writes=False)
write(state/'migration-restore-report.json', report)
print(json.dumps(report, ensure_ascii=False))
