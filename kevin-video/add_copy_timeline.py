"""Install a prepared copy as a new tab, retaining all existing timelines."""
import copy
import hashlib
import time
import soundpilot as s


def add_copy(export_path,project_name,name):
    if s.capcut_running():raise ValueError('Close CapCut before adding the prepared timeline.')
    project=s.project_path(project_name);export_path=s.Path(export_path)
    report=s.read_json(export_path/'soundpilot_export.json')
    _,_,source_file=s.load_timeline(project,report['source_timeline'])
    if report['source']!=str(project) or hashlib.sha256(source_file.read_bytes()).hexdigest()!=report['source_hash']:
        raise ValueError('The source timeline changed. Rebuild the copy from the saved source.')
    index_path=project/'Timelines'/'project.json';layout_path=project/'timeline_layout.json'
    index=s.read_json(index_path);layout=s.read_json(layout_path)
    if any(t['name'].casefold()==name.casefold() for t in index['timelines']):raise ValueError('Timeline name already exists.')
    old_index=index_path.read_bytes();old_layout=layout_path.read_bytes()
    backup=s.OUTPUTS/f'new-timeline-backup-{time.time_ns()}';backup.mkdir(parents=True)
    (backup/'project.json').write_bytes(old_index);(backup/'timeline_layout.json').write_bytes(old_layout)
    new_id=s.uid();folder=project/'Timelines'/new_id
    # Checked path: this new folder must stay inside the selected project's Timelines.
    if folder.resolve().parent!=(project/'Timelines').resolve():raise ValueError('Unexpected timeline path.')
    folder.mkdir()
    empty=s.read_json(export_path/'draft_content.json');empty.update({'id':new_id,'name':name,'duration':0,'tracks':[]})
    s.write_json(folder/'draft_content.json',empty);s.write_json(folder/'draft_content.json.bak',empty)
    now=int(time.time()*s.MICRO)
    index['timelines'].append({'id':new_id,'name':name,'is_marked_delete':False,'create_time':now,'update_time':now})
    if not layout.get('dockItems'):layout['dockItems']=[{'dockIndex':0,'ratio':1,'timelineIds':[],'timelineNames':[]}]
    layout['dockItems'][0]['timelineIds'].append(new_id);layout['dockItems'][0]['timelineNames'].append(name)
    if s.capcut_running():raise ValueError('CapCut reopened; no project index was changed.')
    try:
        s.write_json(index_path,index);s.write_json(layout_path,layout)
        installed=s.install_into_empty_timeline(export_path,project_name,name)
    except Exception:
        index_path.write_bytes(old_index);layout_path.write_bytes(old_layout)
        raise
    installed['new_tab_index_backup']=str(backup)
    installed['source_preserved']=True
    return installed


if __name__=='__main__':
    out=s.OUTPUTS/'test2v2';r=s.read_json(out/'export.json')
    result=add_copy(r['path'],'test 1','test 2 - SFX v2')
    s.write_json(out/'install.json',result);print(result)
