"""Lossless Windows recovery archive: code, real audio, memory/history and runtime."""
import os,sys,json,shutil,hashlib,time,zipfile,subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent;PLUGIN=BASE/'plugins/capcut-sfx-learning'
DEST=BASE/'outputs/SoundPilot-Recovery-2026-10-09';DEST.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PLUGIN));import service as api
SKIP={'__pycache__','.git','.venv','node_modules'}
def copy_tree(source,destination,extra_skip=()):
    source=Path(source);destination=Path(destination)
    for path in source.rglob('*'):
        rel=path.relative_to(source)
        if any(part in SKIP or part in extra_skip for part in rel.parts):continue
        if path.is_dir():continue
        if path.suffix in ('.pyc','.pyo','.log'):continue
        target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
print('Copying plugin + complete learned state...',flush=True)
copy_tree(PLUGIN,DEST/'plugins/capcut-sfx-learning')
with api.lock('state'):
    cfg=api.s.config();memory=api.s.read_json(api.STATE/'memory.json');source_state=api.STATE
    for top in ('memory.json','data','history','jobs','batches'):
        root=source_state/top
        files=[root] if root.is_file() else list(root.rglob('*'))
        for file in files:
            if not file.is_file() or file.suffix in ('.log','.writing'):continue
            relative=file.relative_to(source_state);target=DEST/'state'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
    # Capture this exact consistent generation for portable initialization too.
    for name,data in [('style_profile.json',memory['profile']),('examples.json',memory['examples'])]:
        value=json.loads(json.dumps(data))
        if name=='examples.json':
            for e in value:e['path']='';e['material']['path']='';e.pop('source_file',None)
        (DEST/'plugins/capcut-sfx-learning/seed'/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print('Copying actual sound library...',flush=True)
library=Path(cfg['library']);audio_dest=DEST/'plugins/capcut-sfx-learning/library';copy_tree(library,audio_dest)
asset_map={str(p):p.relative_to(library).as_posix() for p in library.rglob('*') if p.is_file()}
# Include used external leaf audio when it is available, avoiding compound renders.
project=api.s.project_path('test 1');external=[]
def add_audio(draft):
    linked_ids={m.get('id') for m in draft['materials'].get('drafts',[])}
    linked_mats={seg['material_id'] for track in draft['tracks'] if track.get('type')=='audio' for seg in track.get('segments',[]) if linked_ids.intersection(seg.get('extra_material_refs',[]))}
    for mat in draft['materials'].get('audios',[]):
        if mat.get('id') in linked_mats or not mat.get('path'):continue
        source=api.s.resolve_path(mat['path'],project)
        if not source.is_file():continue
        if str(source) in asset_map:continue
        same=next((p for p in audio_dest.rglob('*') if p.is_file() and p.name==source.name and sha(p)==sha(source)),None)
        relative=same.relative_to(audio_dest) if same else Path('external-imports')/source.name
        target=audio_dest/relative
        if target.exists() and sha(target)!=sha(source):relative=Path('external-imports')/(sha(source)[:8]+'-'+source.name);target=audio_dest/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copy2(source,target)
        asset_map[str(source)]=relative.as_posix();external.append(relative.as_posix())
    for m in draft['materials'].get('drafts',[]):
        if m.get('draft'):add_audio(m['draft'])
for name in ('Day 7.3','Day 7.4','Day 7.5','Day 7.6'):
    _,draft,_=api.s.load_timeline(project,name);add_audio(draft)
print('Copying portable Python and installed dependencies...',flush=True)
base_python=Path(sys.base_prefix);env_python=Path(sys.prefix)
for name in ('python.exe','pythonw.exe','python3.dll','python312.dll','vcruntime140.dll','vcruntime140_1.dll','LICENSE.txt'):
    source=base_python/name
    if source.exists():target=DEST/'runtime/python'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
copy_tree(base_python/'DLLs',DEST/'runtime/python/DLLs')
copy_tree(base_python/'Lib',DEST/'runtime/python/Lib',extra_skip=('site-packages',))
copy_tree(env_python/'Lib/site-packages',DEST/'runtime/env/Lib/site-packages')
for name in ('python.exe','pythonw.exe'):
    target=DEST/'runtime/env/Scripts'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(env_python/'Scripts'/name,target)
(DEST/'runtime/env/pyvenv.cfg').write_text('include-system-site-packages = false\nversion = 3.12.14\n',encoding='utf-8')
tools=DEST/'runtime/tools';tools.mkdir(parents=True,exist_ok=True)
for name in ('ffmpeg','ffprobe'):shutil.copy2(shutil.which(name),tools/(name+'.exe'))
ff_root=Path(shutil.which('ffmpeg')).parents[1]
for name in ('LICENSE','README.txt'):
    if (ff_root/name).exists():shutil.copy2(ff_root/name,tools/(name+'.ffmpeg' if name=='LICENSE' else name))
subprocess.run([sys.executable,'-m','pip','freeze'],stdout=(DEST/'RUNTIME_PACKAGES.txt').open('w',encoding='utf-8'),check=True)
print('Copying local offline models...',flush=True)
copy_tree(Path(cfg['model_root']),DEST/'models',extra_skip=('.locks','.cache'))
for original,name in [('recovery_master.ps1','MASTER.ps1'),('recovery_restore_memory.py','restore_memory.py'),('recovery_health_check.py','health_check.py')]:shutil.copy2(BASE/original,DEST/name)
(DEST/'MASTER.bat').write_bytes(b'@echo off\r\nsetlocal\r\nchcp 65001 >nul\r\npowershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0MASTER.ps1" %*\r\nset "sfxExit=%errorlevel%"\r\nif "%~1"=="" pause\r\nexit /b %sfxExit%\r\n')
# Launchers must find bundled FFmpeg even when Codex starts outside this BAT's environment.
launcher=DEST/'plugins/capcut-sfx-learning/launch.ps1'
source=launcher.read_text(encoding='utf-8');source=source.replace("$sfxRuntimeFile = Join-Path $sfxState 'runtime.json'", "$sfxRuntimeFile = Join-Path $sfxState 'runtime.json'\nif (Test-Path -LiteralPath $sfxRuntimeFile) {\n    $sfxRuntimeConfig = Get-Content -LiteralPath $sfxRuntimeFile -Raw | ConvertFrom-Json\n    if ($sfxRuntimeConfig.ffmpeg_bin) { $env:PATH = \"$($sfxRuntimeConfig.ffmpeg_bin);$env:PATH\" }\n}")
launcher.write_text(source,encoding='utf-8')
launcher=DEST/'plugins/capcut-sfx-learning/launch.py';source=launcher.read_text();source=source.replace("result=subprocess.run", "if runtime.exists():\n    settings=json.loads(runtime.read_text(encoding='utf-8-sig'))\n    if settings.get('ffmpeg_bin'):os.environ['PATH']=settings['ffmpeg_bin']+os.pathsep+os.environ.get('PATH','')\nresult=subprocess.run").replace("runtime.read_text(encoding='utf-8')","runtime.read_text(encoding='utf-8-sig')");launcher.write_text(source)
market=DEST/'.agents/plugins/marketplace.json';market.parent.mkdir(parents=True,exist_ok=True)
market.write_text(json.dumps({'name':'srijon-sfx-recovery','plugins':[{'name':'capcut-sfx-learning','source':{'source':'local','path':'./plugins/capcut-sfx-learning'},'policy':{'installation':'AVAILABLE','authentication':'ON_INSTALL'},'category':'Productivity'}]},indent=2))
reports=DEST/'reports';reports.mkdir(exist_ok=True)
patterns=('*.md','*DIFF*.json','*STYLE_PROFILE*.json','*CHAT_TOKEN_USAGE*.json','*LEARNED*.json','*USAGE_SNAPSHOT*.json','API_EQUIVALENT.json','INSTALL_RESULT.json')
picked=set()
for pattern in patterns:
    for file in (BASE/'outputs').glob('**/'+pattern):
        rel=file.relative_to(BASE/'outputs')
        if rel.parts[0] in (DEST.name,'plugin-release') or 'timeline-install-backup' in str(rel) or file in picked:continue
        picked.add(file);target=reports/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
info={'created_local_date':'2026-10-09','platform':'Windows x64','plugin_version':'0.1.4','style_version':memory['profile']['version'],'reference_examples':len(memory['examples']),
    'old_state_root':str(source_state),'old_library_root':str(library),'old_model_root':cfg['model_root'],'asset_map':asset_map,
    'library_mp3_files':len(list(audio_dest.rglob('*.mp3'))),'library_mp4_files':len(list(audio_dest.rglob('*.mp4'))),'external_audio_imports':sorted(set(external)),
    'scope':'Plugin, local sound media, curated memory, full revision history, jobs and cached review context, usage/adoption reports, Python dependencies, FFmpeg and offline models. No authentication files, CapCut project checkout or original full-resolution reaction/source videos outside the sound library.'}
(DEST/'BACKUP_INFO.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'staging':str(DEST),'style_version':info['style_version'],'references':info['reference_examples'],'mp3_files':info['library_mp3_files'],'external_audio':info['external_audio_imports']},ensure_ascii=False),flush=True)
