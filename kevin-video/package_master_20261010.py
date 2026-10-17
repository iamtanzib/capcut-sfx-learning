"""Finalize full master ZIP with streaming CRC/SHA and original audio checks."""
import json,hashlib,zipfile,zlib
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE/'outputs/SoundPilot-MASTER-2026-10-10'
DEST=BASE/'outputs/SoundPilot-MASTER-FULL-2026-10-10-v0.1.10.zip'
if DEST.exists():raise ValueError('Preserve existing archives; choose a new filename.')
tested=json.loads((ROOT/'RESTORE_TEST_RESULTS.json').read_text(encoding='utf-8'));assert tested['offline_preparation']=='ready' and tested['actual_mcp_22_tools_verified']
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def files():return sorted(p for p in ROOT.rglob('*') if p.is_file() and not any(x in ('__pycache__','.git','node_modules') for x in p.relative_to(ROOT).parts)
    and p.suffix not in ('.pyc','.pyo','.log','.writing') and p.name!='SHA256_FILES.json')
paths=files();forbidden={'auth.json','credentials.json','.env','.claude.json'}
assert not any(p.name.lower() in forbidden for p in paths),'Authentication/config secret file in package.'
print(f'Hashing complete payload ({len(paths)} files)...',flush=True)
manifest={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
(ROOT/'SHA256_FILES.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');paths.append(ROOT/'SHA256_FILES.json')
info=json.loads((ROOT/'BACKUP_INFO.json').read_text(encoding='utf-8'))
for original,relative in info['asset_map'].items():
    p=Path(original)
    if p.is_file():assert sha(p)==manifest['plugins/capcut-sfx-learning/library/'+relative],str(p)
print('Writing complete ZIP (source/media/runtime/models/memory)...',flush=True)
with zipfile.ZipFile(DEST,'w',zipfile.ZIP_DEFLATED,compresslevel=4,allowZip64=True) as z:
    for i,p in enumerate(paths):
        z.write(p,(Path(ROOT.name)/p.relative_to(ROOT)).as_posix())
        if i and i%2000==0:print(f'Packed {i}/{len(paths)}',flush=True)
print('Checking every archived file CRC and SHA-256...',flush=True)
with zipfile.ZipFile(DEST) as z:
    for i,entry in enumerate(z.infolist()):
        h=hashlib.sha256();crc=0
        with z.open(entry) as f:
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block);crc=zlib.crc32(block,crc)
        assert crc&0xffffffff==entry.CRC,entry.filename
        relative=entry.filename[len(ROOT.name)+1:]
        expected=sha(ROOT/'SHA256_FILES.json') if relative=='SHA256_FILES.json' else manifest[relative]
        assert h.hexdigest()==expected,entry.filename
        if i and i%2500==0:print(f'Verified {i}/{len(paths)}',flush=True)
digest=sha(DEST);DEST.with_suffix('.zip.sha256').write_text(digest+'  '+DEST.name+'\n',encoding='utf-8')
report={'zip':str(DEST),'sha256':digest,'bytes':DEST.stat().st_size,'size_mib':round(DEST.stat().st_size/1048576,1),'files':len(paths),
    'plugin_version':info['plugin_version'],'sfx_memory_version':info['style_version'],'sfx_examples':info['reference_examples'],
    'zoom_memory_version':info['zoom_style_version'],'zoom_reference_events':info['zoom_reference_events'],'mp3_files':info['library_mp3_files'],'mp4_files':info['library_mp4_files'],
    'all_archive_crc_and_sha256_verified':True,'available_original_audio_bytes_verified':True,'portable_restore_test_passed':True,
    'real_capcut_projects_modified':False,'credentials_included':False,'original_capcut_projects_and_source_videos_included':False}
(BASE/'outputs/SoundPilot-MASTER-FULL-2026-10-10-REPORT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
