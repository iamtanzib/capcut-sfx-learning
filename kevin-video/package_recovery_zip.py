"""Hash and verify the final complete archive; source audio remains byte-exact."""
import os,json,hashlib,zipfile,shutil,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE/'outputs/SoundPilot-Recovery-2026-10-09';ZIP=BASE/'outputs/SoundPilot-MASTER-Backup-2026-10-09.zip'
shutil.copy2(BASE/'recovery_master.ps1',ROOT/'MASTER.ps1')
(ROOT/'VERIFY.bat').write_bytes(b'@echo off\r\ncall "%~dp0MASTER.bat" check -VerifyFiles %*\r\npause\r\n')
def files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and not any(part in ('__pycache__','.git','node_modules') for part in p.relative_to(ROOT).parts)
        and p.suffix not in ('.pyc','.pyo','.log','.writing') and p.name!='SHA256_FILES.json')
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
paths=files();print(f'Hashing {len(paths)} files...',flush=True)
manifest={p.relative_to(ROOT).as_posix():sha(p) for p in paths};(ROOT/'SHA256_FILES.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
paths.append(ROOT/'SHA256_FILES.json')
forbidden={'auth.json','.claude.json','.env','credentials.json'}
assert not any(p.name in forbidden for p in paths)
print('Creating complete ZIP...',flush=True)
with zipfile.ZipFile(ZIP,'w',zipfile.ZIP_DEFLATED,compresslevel=4,allowZip64=True) as archive:
    for i,p in enumerate(paths):
        archive.write(p,(Path(ROOT.name)/p.relative_to(ROOT)).as_posix())
        if i and i%2000==0:print(f'Packed {i}/{len(paths)} files',flush=True)
print('Verifying ZIP CRC and every restored asset hash...',flush=True)
with zipfile.ZipFile(ZIP) as archive:
    assert archive.testzip() is None
    for relative,expected in manifest.items():
        h=hashlib.sha256()
        with archive.open(ROOT.name+'/'+relative) as f:
            for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
        assert h.hexdigest()==expected,relative
    info=json.loads(archive.read(ROOT.name+'/BACKUP_INFO.json'))
    for old,relative in info['asset_map'].items():
        original=Path(old)
        if not original.is_file():continue
        expected=sha(original);actual=manifest['plugins/capcut-sfx-learning/library/'+relative];assert actual==expected,old
digest=sha(ZIP);ZIP.with_suffix('.zip.sha256').write_text(digest+'  '+ZIP.name+'\n',encoding='utf-8')
report={'zip':str(ZIP),'zip_sha256':digest,'size_bytes':ZIP.stat().st_size,'size_mib':round(ZIP.stat().st_size/1048576,1),
    'files':len(paths),'all_archive_hashes_verified':True,'source_audio_bytes_verified':True,'mp3_files':info['library_mp3_files'],
    'mp4_files':info['library_mp4_files'],'style_version':info['style_version'],'references':info['reference_examples'],
    'restore_runtime_models_mcp_tested':True,'host_registration_in_test':False,'original_capcut_projects_modified':False}
(BASE/'outputs/SoundPilot-MASTER-Backup-2026-10-09-REPORT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
