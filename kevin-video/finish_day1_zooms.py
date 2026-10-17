"""Apply the authorized staged zoom batch only after CapCut is closed."""
import sys,json
from pathlib import Path
BASE=Path(__file__).resolve().parent;sys.path.insert(0,str(BASE/'plugins/capcut-sfx-learning'))
import service as a
import zoom
batch=a.s.read_json(BASE/'outputs/zoom-feature/BATCH.json')
before={}
for project in a.s.list_projects():
    pr=a.s.project_path(project['name'])
    for tl in project['timelines']:
        _,draft,path=a.s.load_timeline(pr,tl['id']);before[str(path)]=a.digest(path)
result=a.apply_zoom_batch(batch['batch_id'])
targets={};changed=[]
for jid in batch['jobs']:
    r=zoom.data(a,jid);pr=a.s.project_path(r['project']);tl,draft,path=a.s.load_timeline(pr,r['timeline_id'])
    source=a.s.read_json(zoom.folder(a,jid)/'source.json')
    assert zoom.audio_signature(a,source)==zoom.audio_signature(a,draft)
    a.s.validate_draft(draft)
    targets[str(path)]={'timeline':tl['name'],'zooms':len(a.s.read_json(zoom.folder(a,jid)/'plan.json')['zooms']),'native_segments':len(zoom.tracks(draft)[0]['segments'])}
for path,h in before.items():
    if a.digest(path)!=h:
        assert path in targets,'Unexpected non-target timeline mutation: '+path
        changed.append(targets[path])
result.update(timelines=changed,non_target_timelines_unchanged=True,visual_layout_preview_reviewed=True,native_capcut_render_reviewed=False)
a.s.write_json(BASE/'outputs/zoom-feature/APPLIED.json',result)
print(json.dumps(result,indent=2))
