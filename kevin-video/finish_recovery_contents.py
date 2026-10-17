"""Complete caches/docs and make duplicate external audio names unambiguous."""
import sys,json,shutil,hashlib
from pathlib import Path
BASE=Path(__file__).resolve().parent;DEST=BASE/'outputs/SoundPilot-Recovery-2026-10-09';PLUGIN=DEST/'plugins/capcut-sfx-learning'
sys.path.insert(0,str(BASE/'plugins/capcut-sfx-learning'));import service as api
with api.lock('state'):
    for top in ('memory.json','data','history','jobs','batches'):
        src=api.STATE/top
        files=[src] if src.is_file() else src.rglob('*')
        for file in files:
            if not file.is_file() or file.suffix in ('.log','.writing'):continue
            target=DEST/'state'/file.relative_to(api.STATE);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
info=json.loads((DEST/'BACKUP_INFO.json').read_text(encoding='utf-8'));library=PLUGIN/'library'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
names={};renamed={}
for path in sorted(library.rglob('*.mp3'),key=lambda p:'external-imports' in p.parts):
    if path.name.casefold() not in names:names[path.name.casefold()]=path;continue
    new=path.with_name('ARCHIVED-'+sha(path)[:8]+'-'+path.name);old_rel=path.relative_to(library).as_posix();new_rel=new.relative_to(library).as_posix()
    path.rename(new);renamed[old_rel]=new_rel
    for key,value in list(info['asset_map'].items()):
        if value==old_rel:info['asset_map'][key]=new_rel
info['external_audio_imports']=[renamed.get(r,r) for r in info['external_audio_imports']]
info['duplicate_audio_aliases']=renamed;info['library_mp3_files']=len(list(library.rglob('*.mp3')));info['library_mp4_files']=len(list(library.rglob('*.mp4')))
info['scope']='Plugin, all sound-library media and used available external audio, full learned memory/history/jobs/cached review context, usage/adoption reports and Windows runtime/models. Original full-resolution source videos and authentication files are separate.'
(DEST/'BACKUP_INFO.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
for src,name in [('recovery_restore_memory.py','restore_memory.py'),('recovery_master.ps1','MASTER.ps1'),('recovery_health_check.py','health_check.py')]:shutil.copy2(BASE/src,DEST/name)
(DEST/'examples').mkdir(exist_ok=True)
(DEST/'examples/prepare.json').write_text(json.dumps({'targets':[{'project':'YOUR PROJECT','timeline':'YOUR NEW TIMELINE'}],'workers':2},indent=2))
(DEST/'examples/learn.json').write_text(json.dumps({'job_id':'RETURNED_JOB_ID','revision_project':'YOUR PROJECT','revision_timeline':'YOUR REVISED TIMELINE','rule_updates':[]},indent=2))
(DEST/'USAGE.txt').write_text('''SoundPilot / CapCut SFX Learning - complete personal recovery

QUICK RESTORE
1. Extract the ENTIRE ZIP to a permanent Windows x64 folder.
2. Double-click MASTER.bat; choose 1 (install/restore).
3. Open a new Codex chat; use capcut-sfx-learning.
4. To restore old Documents/Sidebar audio paths too, choose S. Missing
   sounds are copied; different existing files are preserved.

CURRENT ADOPTION
Plugin 0.1.4, memory v12, 201 reference placements.
Four latest manual revisions: 60 logical cues / 64 native audio pieces.
Learned meaning/selection/timing, all compound parent gains, per-asset
soft/normal/emphasis levels, attack/body ducking, voice/background balance.
All library audio plus available used external music/audio is included.
Full memory.json, receipts/history, job snapshots, speech-word reports,
cached preview audio/images/proxies and historical usage notes are included.

USING CODEX
Tell Codex: "Read RESTORE_WITH_CODEX.md and restore this SFX system."
After install: "Use capcut-sfx-learning on project X timelines A,B,C,D,E.
Read both streams and my learned sound levels, then apply when CapCut closes."
For feedback: "I revised timeline A; compare it with its applied job and learn."
MASTER prepares local context and provides controls; Codex/Claude makes
the contextual artistic sound choices. It does not fabricate an automatic
perfect plan without the host model.

COMMAND EXAMPLES (PowerShell/CMD)
MASTER.bat install
MASTER.bat install -DraftRoot "D:\\CapCutDrafts"
MASTER.bat check
MASTER.bat memory
MASTER.bat projects
MASTER.bat prepare -InputFile "C:\\path\\targets.json"
MASTER.bat status -BatchId RETURNED_BATCH_ID
MASTER.bat apply -BatchId AUTHORIZED_AUDITED_BATCH_ID
MASTER.bat learn -InputFile "C:\\path\\revision.json"
MASTER.bat restore-sounds

BEHAVIOR
- Existing newer memory is kept; older/missing memory is restored.
- -ForceMemory deliberately selects the archived memory and preserves the
  previous memory bundle in restore-preserved.
- No CapCut project file is modified by install/check/learning.
- Applying requires a clean target, stable source/style, audited plan,
  a resolved headroom decision and CapCut closed. No saved project backup
  or project copy is made by apply, following the user's preference.
- Peak checks do not certify perceived loudness or creative accuracy.
- Prior uninstalled/queued plans are marked needs_refresh after restore;
  prepare again before applying. Applied job history remains available.

WHAT IS SEPARATE
Codex/Claude app installation and account sign-in are separate. No API keys,
ChatGPT/Claude auth files or browser profiles are inside this ZIP.
Original full-resolution CapCut videos and the CapCut project checkout
are separate; keep their own backup. This archive stores the SFX system,
its sound assets, learned memory and generated review context.
On a new PC, point -DraftRoot at the saved CapCut project directory and
relink original footage in CapCut if its drive/username changed.
The bundled runtime/dependencies/models work offline on Windows x64;
the host ChatGPT/Claude still needs its normal app/account access.
ChatGPT web additionally needs a supported secure local MCP tunnel.

Keep this WHOLE folder together: moving it is supported (MASTER rebases
runtime/state paths); deleting it after install removes its bundled runtime.
The ZIP is a dated snapshot. New revisions after this backup need a fresh
backup of the active SoundPilotLearning state and any newly added sounds.
Historical usage/API-equivalent notes are in reports; they are not bills.
''',encoding='utf-8')
(DEST/'RESTORE_WITH_CODEX.md').write_text('''# Restore the complete SFX system

The user requests installation from this archive. Read `USAGE.txt` and `BACKUP_INFO.json` first. Preserve other plugins, auth files, CapCut projects and newer learned memory.

1. Extract the complete folder to a stable writable Windows x64 location. Do not execute a single BAT extracted alone.
2. Run `MASTER.bat install`. The script rebases its bundled Python environment, restores the archive's state if missing/older, scans included audio, sets the offline model root and registers only this owned plugin via Codex's supported CLI. It removes/replaces only this SFX plugin's prior registrations; other marketplaces/plugins remain unchanged.
3. If the draft root differs, pass `-DraftRoot "absolute CapCut draft directory"`. To validate without changing host registration, use `-NoRegister`; use a separate `-StateRoot` for tests. Do not use `-ForceMemory` unless the user specifically wants the archived memory over a newer one.
4. Run `MASTER.bat check`. Verify the reported Python/base paths live within this extracted folder, bundled FFmpeg is detected, base.en loads offline, and memory has the expected version/reference count. A preserved newer memory may exceed the snapshot's values.
5. Open a fresh Codex chat and perform a read-only project-list or style-memory tool call. The plugin is `capcut-sfx-learning@srijon-sfx-recovery`. Runtime/memory restoration alone does not prove artistic accuracy.
6. If Codex CLI is absent, install/sign into Codex separately and rerun install. This archive contains no account credentials. Claude Code can use the included skill and `launch.ps1`; a Desktop config snippet may be generated without overwriting existing servers.

`MASTER.bat restore-sounds` copies missing media into the Documents/Sidebar sound library for old path compatibility, preserving different existing files. The plugin itself uses the integrated packaged library. External audio with duplicate filenames is preserved under an ARCHIVED hash alias; `BACKUP_INFO.json` maps every original audio path to its included copy.

Do not restore old queued/staged plans directly. They need fresh preparation/source hashes after relocation; the installer marks them needs_refresh. Original full-resolution media and CapCut project checkouts are not inside this SFX archive; generated review proxies/audio/context are included. Avoid claiming those original projects were recovered by this installer.
''',encoding='utf-8')
print(json.dumps({'mp3_files':info['library_mp3_files'],'mp4_files':info['library_mp4_files'],'aliases':renamed,'state_files':sum(p.is_file() for p in (DEST/'state').rglob('*'))},ensure_ascii=False))
