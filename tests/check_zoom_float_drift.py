"""Self-check: zoom splits must not trip the timing guard through float drift (day 6.4 test 1, 0.991x clip).
Run with SOUNDPILOT_STATE=C:/Users/srijon/AppData/Local/SoundPilotLearning; skips if the job is gone."""
import copy,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import service as a
import zoom

src=Path(os.environ.get('SOUNDPILOT_STATE',''))/'jobs/0ba3b9011e5e4450/source.json'
if not src.is_file():sys.exit(f'skip: {src} missing')
draft=a.s.read_json(src)
Z=[[1.04,2.6],[8.78,10.2],[14.77,17.0],[21.89,23.8],[24.59,27.1],[29.58,31.4],[39.94,41.5],[46.88,49.3],[54.1,56.3]]
frame=lambda t:round(t*30)/30
plan={'zooms':[{'role':r,'start':frame(x),'end':frame(y),'scale':1.1} for r in ('video_track_1','video_track_2') for x,y in Z]}
result=zoom.apply_native(a,draft,plan)
assert zoom.audio_signature(a,draft)==zoom.audio_signature(a,result)
# A real 1-frame timing change must still be rejected.
moved=copy.deepcopy(result);seg=moved['tracks'][[t.get('type') for t in moved['tracks']].index('video')]['segments'][1]
seg['target_timerange']['start']+=33333
assert zoom.audio_signature(a,draft)!=zoom.audio_signature(a,moved)
print('ok')
