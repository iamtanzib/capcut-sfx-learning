"""Prepare authorized zoom targets from already-existing SFX analyses."""
import sys,json
from pathlib import Path
BASE=Path(__file__).resolve().parent;sys.path.insert(0,str(BASE/'plugins/capcut-sfx-learning'))
import service as a
refs={'Day 7.3':'a1c942f5b10f472c','Day 7.4':'7f054b42880d4633','Day 7.5':'965e2fa694c24212','Day 7.6':'1ae7d2f210584a20'}
targets={'Day 1.3':'de75ea7cac714aa9','Day 1.4':'7bd393afde57469e','Day 1.5':'f9d86591573b4c82','Day 1.6':'94bc2d878df64d54'}
out=BASE/'outputs/zoom-feature';out.mkdir(exist_ok=True)
print(json.dumps(a.learn_zoom_style([{'project':'test 1','timeline':n,'analysis_job_id':j} for n,j in refs.items()])))
batch=a.prepare_zoom_batch([{'project':'test 1','timeline':n,'analysis_job_id':j} for n,j in targets.items()])
a.s.write_json(out/'BATCH.json',batch)
print(json.dumps(batch))
brief=a.get_zoom_briefs(batch['batch_id']);a.s.write_json(out/'BATCH_BRIEFS.json',brief)
import zoom
for zid in batch['jobs']:
    r=zoom.data(a,zid);b=a.s.read_json(zoom.folder(a,zid)/'brief.json')
    words=[w for row in b['dialogue']['tracks'][0]['speech'] for w in row['words']]
    print(json.dumps({'timeline':r['timeline'],'job':zid,'words':[[w['word_index'],w['start'],w['end'],w['text']] for w in words]},ensure_ascii=False))
