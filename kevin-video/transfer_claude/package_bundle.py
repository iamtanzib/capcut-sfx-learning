"""Finalize the tested private Claude transfer; verify all ZIP bytes."""
from __future__ import annotations
import hashlib, json, shutil, zipfile, zlib, datetime
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE/'outputs/CapCut-SFX-Learning-Claude-Code-FULL-2026-10-13-v0.1.15'
DEST=ROOT.parent/(ROOT.name+'.zip')
if DEST.exists(): raise RuntimeError('Preserve existing ZIP; choose a new generation.')
tests=json.loads((ROOT/'TRANSFER_TEST_RESULTS.json').read_text(encoding='utf-8'))
if not (tests.get('passed') or tests.get('ok')): raise RuntimeError('Portable migration verification must pass before packaging.')

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

for p in (BASE/'transfer_claude').glob('*.py'):
    q=ROOT/'development-source/migration-build'/p.name; q.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,q)
# Retain the exact installed source alongside the Claude-adapted runtime copy.
source=BASE/'plugins/capcut-sfx-learning'
for p in source.rglob('*'):
    rel=p.relative_to(source)
    if not p.is_file() or '__pycache__' in rel.parts or p.suffix in ('.pyc','.pyo','.log','.writing'): continue
    q=ROOT/'development-source/installed-plugin-source'/rel
    q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
# Installer rebases only this file on extraction; ship its original clean template.
shutil.copy2(ROOT/'runtime/ORIGINAL_PYVENV.txt',ROOT/'runtime/env/pyvenv.cfg')
required=['README_BN.md','CLAUDE.md','INSTALL_CLAUDE_CODE.bat','INSTALL_CLAUDE_CODE.ps1',
          'VERIFY.ps1','CALL_TOOL.ps1','migration/health_check.py','migration/restore_state.py',
          'plugins/capcut-sfx-learning/skills/capcut-sfx-learning/SKILL.md','BUNDLE_INFO.json']
for rel in required:
    if not (ROOT/rel).is_file(): raise RuntimeError('Missing required bundle file: '+rel)
forbidden={'auth.json','credentials.json','.env','.claude.json','settings.local.json'}
paths=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name!='SHA256_FILES.json'
             and not any(part in ('__pycache__','.git','local-install','node_modules','locks','.locks') for part in p.relative_to(ROOT).parts)
             and p.suffix not in ('.pyc','.pyo','.log','.writing'))
assert not any(p.name.lower() in forbidden for p in paths),'Authentication file in bundle.'
print(f'Hashing {len(paths)} files...',flush=True)
manifest={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
(ROOT/'SHA256_FILES.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
paths.append(ROOT/'SHA256_FILES.json')
info=json.loads((ROOT/'BUNDLE_INFO.json').read_text(encoding='utf-8'))
for original,relative in info['asset_map'].items():
    if Path(original).is_file(): assert sha(Path(original))==manifest[relative],original
print(f'Creating ZIP from {sum(p.stat().st_size for p in paths)/1048576:.1f} MiB...',flush=True)
with zipfile.ZipFile(DEST,'w',zipfile.ZIP_DEFLATED,compresslevel=4,allowZip64=True) as z:
    for i,p in enumerate(paths):
        z.write(p,(Path(ROOT.name)/p.relative_to(ROOT)).as_posix())
        if i and i%2500==0: print(f'Packed {i}/{len(paths)}',flush=True)
print('Verifying every ZIP entry CRC and SHA-256...',flush=True)
with zipfile.ZipFile(DEST) as z:
    seen=set()
    for i,item in enumerate(z.infolist()):
        relative=item.filename[len(ROOT.name)+1:]
        assert relative not in seen,relative
        seen.add(relative); h=hashlib.sha256();crc=0
        with z.open(item) as f:
            for block in iter(lambda:f.read(1024*1024),b''): h.update(block);crc=zlib.crc32(block,crc)
        assert crc&0xffffffff==item.CRC,item.filename
        expected=sha(ROOT/'SHA256_FILES.json') if relative=='SHA256_FILES.json' else manifest[relative]
        assert h.hexdigest()==expected,item.filename
        if i and i%2500==0: print(f'Verified {i}/{len(paths)}',flush=True)
    assert seen==set(manifest)|{'SHA256_FILES.json'}
digest=sha(DEST)
DEST.with_suffix('.zip.sha256').write_text(digest+'  '+DEST.name+'\n',encoding='utf-8')
report={'zip':str(DEST),'sha256':digest,'bytes':DEST.stat().st_size,'size_mib':round(DEST.stat().st_size/1048576,1),
        'files':len(paths),'plugin_version':info['plugin_version'],
        'sfx_style_version':info['sfx_style_version'],'sfx_examples':info['sfx_examples'],
        'zoom_style_version':info['zoom_style_version'],'zoom_reference_events':info['zoom_reference_events'],
        'hook_style_version':info['hook_style_version'],'hook_references':info['hook_references'],
        'all_archive_crc_and_sha256_verified':True,'available_original_sound_asset_bytes_verified':True,
        'portable_migration_tests_passed':True,'credentials_included':False,
        'original_source_footage_included':False,'creative_cross_host_equivalence_measured':False,
        'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(ROOT.parent/(ROOT.name+'-REPORT.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
