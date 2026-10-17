"""Apply the authorized plan in place without creating a backup or project copy."""
import copy
import hashlib
import time
import soundpilot as s


def apply(plan):
    if s.capcut_running():raise ValueError('Close CapCut first so autosave cannot overwrite this change.')
    sounds=s.read_json(s.DATA/'sound_catalog.json');s.validate_plan(plan,sounds)
    project=s.project_path(plan['project']);timeline,current,path=s.load_timeline(project,plan['timeline'])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=plan['source_hash']:
        raise ValueError('Source changed after planning. Recheck the current saved edit.')
    if list(s.flatten_sfx(current,sounds,project)):
        raise ValueError('The target already contains local SFX. Do not replace user edits with this clean-input operation.')
    draft=copy.deepcopy(current)
    lanes=s.add_effects(draft,plan,s.read_json(s.DATA/'examples.json'),sounds)
    gain=float(plan.get('master_gain',1))
    if not 0<gain<=1:raise ValueError('Invalid master gain.')
    if gain!=1:
        for track in draft['tracks']:
            if track.get('type') in ('video','audio'):
                for seg in track.get('segments',[]):
                    seg['volume']=float(seg.get('volume',1))*gain
                    seg['last_nonzero_volume']=float(seg.get('last_nonzero_volume',1))*gain
    s.validate_draft(draft)
    meta=s.read_json(project/'draft_meta_info.json')
    group=next((g for g in meta.get('draft_materials',[]) if g.get('type')==0),None)
    if group is None:group={'type':0,'value':[]};meta.setdefault('draft_materials',[]).append(group)
    known={m.get('file_Path') for m in group['value']};catalog={a['name']:a for a in sounds}
    for effect in plan['effects']:
        if not effect.get('enabled',True):continue
        sound=catalog[effect['sound']];audio_path=s.Path(sound['path']).as_posix()
        if audio_path in known:continue
        duration=round(sound['duration']*s.MICRO)
        group['value'].append({'id':s.uid(),'file_Path':audio_path,'extra_info':sound['name'],'metetype':'music','type':0,
            'duration':duration,'width':0,'height':0,'md5':'','create_time':0,'import_time':0,'import_time_ms':0,
            'roughcut_time_range':{'start':0,'duration':duration},'sub_time_range':{'start':-1,'duration':-1},'item_source':1,'enter_from':0})
        known.add(audio_path)
    now=int(time.time()*s.MICRO);meta.update(tm_duration=draft['duration'],tm_draft_modified=now)
    index_path=project/'Timelines'/'project.json';index=s.read_json(index_path)
    index['main_timeline_id']=timeline['id'];index['update_time']=now
    changes={path:draft,s.draft_file(project):draft,project/'draft_meta_info.json':meta,index_path:index}
    # Rollback state is transient memory only, not a saved backup.
    previous={p:p.read_bytes() for p in changes}
    if s.capcut_running() or any(p.read_bytes()!=data for p,data in previous.items()):
        raise ValueError('Project changed while preparing the write. Close CapCut and retry.')
    try:
        for p,value in changes.items():s.write_json(p,value)
    except Exception:
        for p,data in previous.items():p.write_bytes(data)
        raise
    return {'installed':True,'project':plan['project'],'timeline':plan['timeline'],
        'effects':sum(e.get('enabled',True) for e in plan['effects']),'tracks':lanes,'saved_backup_created':False,'project_copy_created':False}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--folder',required=True);args=parser.parse_args()
    out=s.OUTPUTS/args.folder
    if out.resolve().parent!=s.OUTPUTS.resolve():raise ValueError('Choose one output folder name.')
    result=apply(s.read_json(out/'reviewed_plan.json'));s.write_json(out/'install.json',result);print(result)
