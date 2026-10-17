"""Build the complete private Windows recovery snapshot without project writes."""
import os,sys,json,shutil,hashlib,subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent;PLUGIN=BASE/'plugins/capcut-sfx-learning'
OLD=BASE/'outputs/SoundPilot-Recovery-2026-10-09';DEST=BASE/'outputs/SoundPilot-MASTER-2026-10-10'
if DEST.exists():raise ValueError('Use a fresh destination; do not mix archive generations.')
DEST.mkdir()
sys.path.insert(0,str(PLUGIN));import service as a
SKIP={'__pycache__','.git','.venv','node_modules'}
def copytree(src,dst):
    for p in Path(src).rglob('*'):
        rel=p.relative_to(src)
        if not p.is_file() or any(x in SKIP for x in rel.parts) or p.suffix in ('.pyc','.pyo','.log','.writing'):continue
        target=Path(dst)/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
print('Copying latest plugin, offline runtime and models...',flush=True)
copytree(PLUGIN,DEST/'plugins/capcut-sfx-learning')
copytree(OLD/'runtime',DEST/'runtime');copytree(OLD/'models',DEST/'models')
shutil.copy2(OLD/'RUNTIME_PACKAGES.txt',DEST/'RUNTIME_PACKAGES.txt')
print('Capturing consistent SFX + zoom memory and complete cached state...',flush=True)
with a.lock('state'),a.lock('zoom-style'):
    memory=a.s.read_json(a.STATE/'memory.json');zoom=a.s.read_json(a.s.DATA/'zoom_style.json');cfg=a.s.config()
    for top in ('memory.json','data','history','jobs','batches','zoom_jobs','zoom_batches'):
        p=a.STATE/top
        if p.is_file():target=DEST/'state'/top;target.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(p,target)
        elif p.is_dir():copytree(p,DEST/'state'/top)
    for name,value in [('style_profile.json',memory['profile']),('examples.json',memory['examples']),('zoom_style.json',zoom)]:
        value=json.loads(json.dumps(value))
        if name=='examples.json':
            for e in value:
                e['path']=''
                if isinstance(e.get('material'),dict):e['material']['path']=''
                e.pop('source_file',None)
        a.s.write_json(DEST/'plugins/capcut-sfx-learning/seed'/name,value)
print('Packing all local sound media and available used external audio...',flush=True)
library=Path(cfg['library']);audio=DEST/'plugins/capcut-sfx-learning/library';copytree(library,audio)
asset_map={str(p):p.relative_to(library).as_posix() for p in library.rglob('*') if p.is_file()}
# Keep the previous archive's distinct external audio, even if its source moved.
old_info=a.s.read_json(OLD/'BACKUP_INFO.json')
for path,rel in old_info['asset_map'].items():
    src=OLD/'plugins/capcut-sfx-learning/library'/rel;dst=audio/rel
    if src.is_file() and not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    if dst.is_file():asset_map.setdefault(path,rel)
external=[]
def add_audio(draft,project):
    linked_ids={m.get('id') for m in draft['materials'].get('drafts',[])}
    compounds={s['material_id'] for t in draft['tracks'] if t['type']=='audio' for s in t.get('segments',[]) if linked_ids.intersection(s.get('extra_material_refs',[]))}
    for mat in draft['materials'].get('audios',[]):
        if mat.get('id') in compounds or not mat.get('path'):continue
        src=a.s.resolve_path(mat['path'],project)
        if not src.is_file() or str(src) in asset_map:continue
        digest=sha(src);same=next((p for p in audio.rglob('*') if p.is_file() and p.name.casefold()==src.name.casefold() and sha(p)==digest),None)
        rel=same.relative_to(audio) if same else Path('external-imports')/src.name;dst=audio/rel
        if dst.exists() and sha(dst)!=digest:rel=Path('external-imports')/(digest[:8]+'-'+src.name);dst=audio/rel
        if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
        asset_map[str(src)]=rel.as_posix();external.append(rel.as_posix())
    for mat in draft['materials'].get('drafts',[]):
        if mat.get('draft'):add_audio(mat['draft'],project)
for project_info in a.s.list_projects():
    project=a.s.project_path(project_info['name'])
    for tl in project_info['timelines']:
        _,draft,_=a.s.load_timeline(project,tl['id']);add_audio(draft,project)
# Equal filenames with different bytes must not make runtime catalog ambiguous.
names={};aliases={}
for p in sorted(audio.rglob('*.mp3'),key=lambda p:'external-imports' in p.parts):
    name=p.name.casefold()
    if name not in names:names[name]=p;continue
    new=p.with_name('ARCHIVED-'+sha(p)[:8]+'-'+p.name);old_rel=p.relative_to(audio).as_posix();rel=new.relative_to(audio).as_posix()
    p.rename(new);aliases[old_rel]=rel
    for key,value in list(asset_map.items()):
        if value==old_rel:asset_map[key]=rel
for src,dst in [('recovery_master.ps1','MASTER.ps1'),('recovery_restore_memory.py','restore_memory.py'),('recovery_health_check.py','health_check.py')]:shutil.copy2(BASE/src,DEST/dst)
(DEST/'MASTER.bat').write_bytes((OLD/'MASTER.bat').read_bytes());(DEST/'VERIFY.bat').write_bytes((OLD/'VERIFY.bat').read_bytes())
launcher=DEST/'plugins/capcut-sfx-learning/launch.ps1';text=launcher.read_text(encoding='utf-8')
text=text.replace("$sfxRuntimeFile = Join-Path $sfxState 'runtime.json'", "$sfxRuntimeFile = Join-Path $sfxState 'runtime.json'\nif (Test-Path -LiteralPath $sfxRuntimeFile) {\n    $sfxRuntimeConfig = Get-Content -LiteralPath $sfxRuntimeFile -Raw | ConvertFrom-Json\n    if ($sfxRuntimeConfig.ffmpeg_bin) { $env:PATH = \"$($sfxRuntimeConfig.ffmpeg_bin);$env:PATH\" }\n}")
launcher.write_text(text,encoding='utf-8')
launcher=DEST/'plugins/capcut-sfx-learning/launch.py';text=launcher.read_text(encoding='utf-8')
text=text.replace("runtime.read_text(encoding='utf-8')","runtime.read_text(encoding='utf-8-sig')")
text=text.replace('result=subprocess.run',"if runtime.exists():\n    settings=json.loads(runtime.read_text(encoding='utf-8-sig'))\n    if settings.get('ffmpeg_bin'):os.environ['PATH']=settings['ffmpeg_bin']+os.pathsep+os.environ.get('PATH','')\nresult=subprocess.run")
launcher.write_text(text,encoding='utf-8')
market=DEST/'.agents/plugins/marketplace.json';market.parent.mkdir(parents=True)
market.write_text(json.dumps({'name':'srijon-sfx-recovery','plugins':[{'name':'capcut-sfx-learning','source':{'source':'local','path':'./plugins/capcut-sfx-learning'},'policy':{'installation':'AVAILABLE','authentication':'ON_INSTALL'},'category':'Productivity'}]},indent=2),encoding='utf-8')
reports=DEST/'reports';reports.mkdir()
for folder in ('zoom-feature','day1-revision','day7-revisions','usage-audit','day7-batch','plugin-benchmark'):
    src=BASE/'outputs'/folder
    if not src.exists():continue
    for p in src.rglob('*'):
        if p.is_file() and p.suffix in ('.json','.md','.txt'):
            target=reports/folder/p.relative_to(src);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
# Prior historical reports remain available; new same-path reports take precedence.
for p in (OLD/'reports').rglob('*'):
    if p.is_file():
        target=reports/p.relative_to(OLD/'reports')
        if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
info={'created_local_date':'2026-10-10','platform':'Windows x64','plugin_version':a.s.read_json(PLUGIN/'plugin.json')['version'],
    'style_version':memory['profile']['version'],'reference_examples':len(memory['examples']),'zoom_style_version':zoom['version'],
    'zoom_reference_timelines':len(zoom['references']),'zoom_reference_events':sum(len(r['events']) for r in zoom['references']),
    'default_workflow':'sfx_and_zoom','mcp_tools':22,'old_state_root':str(a.STATE),'old_library_root':str(library),'old_model_root':cfg['model_root'],
    'asset_map':asset_map,'library_mp3_files':len(list(audio.rglob('*.mp3'))),'library_mp4_files':len(list(audio.rglob('*.mp4'))),
    'external_audio_imports':sorted(set(external)),'duplicate_audio_aliases':aliases,
    'scope':'Private Windows recovery: latest plugin, sound library, SFX/zoom memory/history/jobs/cached review context, reports, portable Python dependencies/FFmpeg and offline models. Authentication and original CapCut project/source footage are separate.'}
a.s.write_json(DEST/'BACKUP_INFO.json',info)
(DEST/'examples').mkdir()
for name,value in [('prepare.json',{'targets':[{'project':'YOUR PROJECT','timeline':'YOUR NEW TIMELINE'}],'workers':2,'include_zoom':True}),
    ('prepare-sfx-only.json',{'targets':[{'project':'YOUR PROJECT','timeline':'YOUR NEW TIMELINE'}],'workers':2,'include_zoom':False}),
    ('zoom-prepare.json',{'targets':[{'project':'YOUR PROJECT','timeline':'YOUR SFX TIMELINE','analysis_job_id':'EXISTING_ANALYSIS_JOB_ID'}]}),
    ('learn.json',{'job_id':'APPLIED_SFX_JOB_ID','revision_project':'YOUR PROJECT','revision_timeline':'YOUR REVISED TIMELINE','rule_updates':[]})]:a.s.write_json(DEST/'examples'/name,value)
usage=f'''CapCut SFX Learning - FULL MASTER - 2026-10-10

QUICK INSTALL / RESTORE (Windows x64)
1. Extract the ENTIRE ZIP to a permanent writable folder.
2. Double-click MASTER.bat; choose 1 (install/restore).
3. Choose 2 to check portable runtime, offline models, sounds and memory.
4. Start a new Codex chat and use CapCut SFX Learning.

WHAT IS INCLUDED
Plugin {info['plugin_version']}; SFX memory v{info['style_version']} with {info['reference_examples']} examples.
Zoom memory v{info['zoom_style_version']}: {info['zoom_reference_timelines']} reference timelines / {info['zoom_reference_events']} zooms.
SFX + meaningful reaction zooms are DEFAULT. No separate zoom request needed.
One analysis, then SFX followed by zooms in the same session/transaction.
Manual revisions update local sound/zoom style memory, not model weights.
All {info['library_mp3_files']} MP3 + {info['library_mp4_files']} sound-library MP4 files, available used external audio.
Full memory, receipts/history, frozen jobs, mapped word reports and cached review media.
Portable Python 3.12/dependencies, FFmpeg/FFprobe, offline speech/embedding models.
Lossless shared briefs, batched cue timing (52.6% less measured cue-context text;
not a claim of 52.6% less total Codex usage). Model/reasoning/checks retained.

USAGE
Tell Codex: "Use this plugin for project X timelines A,B,C,D."
It designs both SFX and zooms. Explicitly say "SFX only/no zoom" to opt out.
After revisions: "I revised these timelines; learn my SFX and zoom changes."
The host model still makes artistic decisions; MASTER does not invent a perfect
creative plan by itself. Necessary scene/frame/audio checks remain in place.

COMMANDS
MASTER.bat install
MASTER.bat install -DraftRoot "D:\\CapCutDrafts"
MASTER.bat check
VERIFY.bat
MASTER.bat memory
MASTER.bat projects
MASTER.bat prepare -InputFile "C:\\path\\targets.json"
MASTER.bat status -BatchId RETURNED_BATCH_ID
MASTER.bat apply -BatchId AUTHORIZED_AUDITED_BATCH_ID
MASTER.bat learn -InputFile "C:\\path\\revision.json"
MASTER.bat zoom-prepare -InputFile "C:\\path\\zoom-targets.json"
MASTER.bat zoom-apply -BatchId FRAMING_REVIEWED_ZOOM_BATCH
MASTER.bat zoom-learn -JobId APPLIED_ZOOM_JOB
MASTER.bat restore-sounds

RESTORE SAFETY
Newer existing SFX AND zoom memories are preserved independently.
Missing/older memory is upgraded from this snapshot. -ForceMemory explicitly
chooses archived memories and preserves overwritten memory bundles separately.
Install/check/learning do not edit CapCut projects. Apply requires CapCut closed,
unchanged source/style and audited contextual plans. No project backups/copies
by default; write failures use RAM rollback. Power loss is not transactional.
Old queued/staged jobs require refresh after relocation; applied history is retained.
Audio with duplicate filenames is kept under an ARCHIVED hash alias.

WHAT IS SEPARATE
No API keys, Codex/Claude sign-in files or browser profiles are included.
Original CapCut project checkouts and full-resolution source videos outside
the sound library are NOT included; copy/relink those separately on a new PC.
Codex/Claude application/account access is separate; ChatGPT web needs a
supported secure local MCP connection. The local runtime/models work offline.
Keep this extracted folder: installed runtime/sounds depend on it. Run MASTER
again if moving the folder so state/runtime paths are rebased.
This is a private personal snapshot; it includes your learned edits and cached
review clips. Shipping the ZIP does not publish a public marketplace plugin.
New revisions or sounds after this snapshot require a new backup.
'''
(DEST/'USAGE.txt').write_text(usage,encoding='utf-8')
restore=(OLD/'RESTORE_WITH_CODEX.md').read_text(encoding='utf-8').replace('complete SFX system','complete SFX + zoom system')
restore+='\nSnapshot: plugin 0.1.10, SFX memory16 /263 examples, zoom memory5 /8 reference timelines /60 zooms. Newer sound and zoom memories are preserved independently. Default is SFX + zoom; cue context is lossless and batched. See TOKEN_EFFICIENCY.md and ZOOM_REVISION_ADOPTION.md in the plugin.\n'
(DEST/'RESTORE_WITH_CODEX.md').write_text(restore,encoding='utf-8')
print(json.dumps({'staging':str(DEST),'plugin':info['plugin_version'],'sfx_memory':info['style_version'],'examples':info['reference_examples'],'zoom_memory':info['zoom_style_version'],'zoom_events':info['zoom_reference_events'],'mp3':info['library_mp3_files'],'mp4':info['library_mp4_files']},indent=2),flush=True)
