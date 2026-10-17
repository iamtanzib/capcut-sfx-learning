"""Restore archived owned state with portable paths; never write CapCut drafts."""
import argparse,hashlib,json,os,shutil,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--state');p.add_argument('--library');p.add_argument('--force-memory',action='store_true');p.add_argument('--copy-sounds-to');a=p.parse_args()
payload=ROOT/'state';manifest=json.loads((ROOT/'BACKUP_INFO.json').read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.restore-writing');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,path)
if a.copy_sounds_to:
    destination=Path(a.copy_sounds_to).resolve();destination.mkdir(parents=True,exist_ok=True);copied=0;conflicts=[]
    for source in (ROOT/'plugins/capcut-sfx-learning/library').rglob('*'):
        if not source.is_file():continue
        relative=source.relative_to(ROOT/'plugins/capcut-sfx-learning/library');target=destination/relative
        if target.exists():
            if sha(target)!=sha(source):conflicts.append(str(relative))
            continue
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);copied+=1
    print(json.dumps({'missing_files_restored':copied,'existing_files_overwritten':False,'different_existing_files_preserved':conflicts},ensure_ascii=False));raise SystemExit(0)
if not a.state or not a.library:raise ValueError('State and library are required.')
state=Path(a.state).resolve();library=Path(a.library).resolve();state.mkdir(parents=True,exist_ok=True)
had_profile=(state/'data/style_profile.json').exists();had_examples=(state/'data/examples.json').exists()
had_zoom=(state/'data/zoom_style.json').exists()
current_path=state/'memory.json'
if current_path.exists():
    try:
        probe=json.loads(current_path.read_text(encoding='utf-8-sig'));assert isinstance(probe['profile']['version'],int)
    except (UnicodeError,json.JSONDecodeError,KeyError,TypeError,AssertionError):
        current_path.rename(state/('memory.corrupt-'+str(time.time_ns())+'.json'))
os.environ['SOUNDPILOT_STATE']=str(state)
import sys;sys.path.insert(0,str(ROOT/'plugins/capcut-sfx-learning'));import service as api
archive=json.loads((payload/'memory.json').read_text(encoding='utf-8-sig'))
asset_map=manifest['asset_map']
prefixes=[(manifest['old_state_root'],str(state)),(manifest['old_model_root'],str(ROOT/'models'))]
def rebase(value):
    if isinstance(value,dict):return {k:rebase(v) for k,v in value.items()}
    if isinstance(value,list):return [rebase(v) for v in value]
    if not isinstance(value,str):return value
    normalized=value.replace('\\','/')
    for old,relative in asset_map.items():
        if normalized.lower()==old.replace('\\','/').lower():return str(library/relative)
    old_library=manifest['old_library_root'].replace('\\','/')
    if normalized.lower().startswith(old_library.lower()+'/'):return str(library/normalized[len(old_library)+1:])
    for old,new in prefixes:
        old=old.replace('\\','/')
        if normalized.lower()==old.lower() or normalized.lower().startswith(old.lower()+'/'):return new+normalized[len(old):]
    return value # Original source videos remain external; don't rewrite user footage paths.
with api.lock('state'),api.lock('zoom-style'):
    current_path=state/'memory.json';current=None
    if current_path.exists():
        try:current=json.loads(current_path.read_text(encoding='utf-8-sig'))
        except (UnicodeError,json.JSONDecodeError):
            saved=current_path.with_name('memory.corrupt-'+str(time.time_ns())+'.json');shutil.copy2(current_path,saved)
    from_derived=False
    if current is None and had_profile and had_examples:
        try:current={'profile':json.loads((state/'data/style_profile.json').read_text(encoding='utf-8-sig')),'examples':json.loads((state/'data/examples.json').read_text(encoding='utf-8-sig')),'receipts':[]}
        except (UnicodeError,json.JSONDecodeError):pass
        else:from_derived=True
    use_archive=a.force_memory or current is None or current['profile']['version']<archive['profile']['version'] or (from_derived and current['profile']['version']==archive['profile']['version'])
    if use_archive:
        if current is not None and a.force_memory:write(state/'restore-preserved'/('memory-'+str(time.time_ns())+'.json'),current)
        active=rebase(archive);write(current_path,active)
    else:active=rebase(current);write(current_path,active)
    write(state/'data/style_profile.json',active['profile']);write(state/'data/examples.json',active['examples'])
    zoom_restored=False
    if (payload/'data/zoom_style.json').exists():
        archived_zoom=json.loads((payload/'data/zoom_style.json').read_text(encoding='utf-8-sig'));zoom_path=state/'data/zoom_style.json';current_zoom=None
        if had_zoom and zoom_path.exists():
            try:
                current_zoom=json.loads(zoom_path.read_text(encoding='utf-8-sig'));assert isinstance(current_zoom['version'],int)
            except (UnicodeError,json.JSONDecodeError,KeyError,TypeError,AssertionError):
                shutil.copy2(zoom_path,state/('zoom-memory.corrupt-'+str(time.time_ns())+'.json'));current_zoom=None
        zoom_restored=a.force_memory or current_zoom is None or current_zoom['version']<archived_zoom['version']
        if a.force_memory and current_zoom is not None:write(state/'restore-preserved'/('zoom-memory-'+str(time.time_ns())+'.json'),current_zoom)
        active_zoom=rebase(archived_zoom if zoom_restored else current_zoom);write(zoom_path,active_zoom)
    restored=0
    for source in payload.rglob('*'):
        if not source.is_file():continue
        rel=source.relative_to(payload)
        if rel.as_posix() in ('memory.json','data/style_profile.json','data/examples.json','data/zoom_style.json'):continue
        if rel.name in ('runtime.json','config.json','sound_catalog.json'):continue
        target=state/rel
        if target.exists():continue
        if source.suffix!='.json':
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);restored+=1;continue
        value=rebase(json.loads(source.read_text(encoding='utf-8-sig')))
        if rel.name=='job.json' and value.get('status') not in ('applied','failed'):
            value['archived_status']=value.get('status');value['status']='needs_refresh'
        write(target,value);restored+=1
print(json.dumps({'memory_restored_from_archive':use_archive,'style_version':active['profile']['version'],'examples':len(active['examples']),
    'zoom_memory_restored_from_archive':zoom_restored,'zoom_style_version':active_zoom['version'] if 'active_zoom' in locals() else None,
    'history_job_files_restored':restored,'newer_existing_memory_preserved':not use_archive,'capcut_project_writes':False}))
