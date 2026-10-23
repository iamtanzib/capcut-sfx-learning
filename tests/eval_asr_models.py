"""Compare speech models on cached timeline audio against CapCut captions (no state writes).

Usage: python tests/eval_asr_models.py OUT_DIR model [model ...]
Copies each job's cached track wavs into OUT_DIR, transcribes with every model (same
settings as production), then scores each model by how well its words line up with the
timeline's captions: matched captions, offset >150 ms, unmatched, median |offset|.
"""
import glob, json, os, re, shutil, statistics, sys, time
from difflib import SequenceMatcher
from pathlib import Path
BUNDLE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, BUNDLE)
import service as S
import context_pipeline as C
JOBS = os.environ.get('ASR_JOBS', '9c0283cc27914b4f 43f6283461ec42fc fc5747556cfb4776 0277b5656793439d 14bae7ad87744687').split()
out = Path(sys.argv[1]); models = sys.argv[2:]
def norm(t): return re.sub(r'[^a-z0-9 ]', '', t.lower()).split()
def score(captions, tracks):
    offs, unmatched = [], 0
    for cap in captions:
        text = norm(cap['text']); a = cap['start']; best = None
        if not text: continue
        for words in tracks:
            near = [w for w in words if a - 4 <= w['start'] <= a + 4]
            for i in range(len(near)):
                for n in range(max(1, len(text) - 1), len(text) + 2):
                    win = near[i:i + n]
                    if len(win) != n: continue
                    r = SequenceMatcher(None, text, [t for w in win for t in norm(w['text'])]).ratio()
                    cand = (r, -abs(win[0]['start'] - a), win[0]['start'] - a)
                    if best is None or cand > best: best = cand
        if best and best[0] >= .7: offs.append(best[2])
        else: unmatched += 1
    return offs, unmatched
summary = {m: {'captions': 0, 'matched': 0, 'off150': 0, 'unmatched': 0, 'abs': [], 'audio_s': 0., 'asr_s': 0.} for m in models}
for job in JOBS:
    rec = S.job_data(job); brief = S.s.read_json(S.job_path(job) / 'enhanced_brief.json')
    # Fresh analyses live in '<cache_key>-fresh-<ns>' folders; take the one holding track audio.
    src = next(d for d in sorted((S.STATE / 'data' / 'context').glob(rec['cache_key'] + '*')) if list(d.glob('video_track_*.wav')))
    for m in models:
        tracks = []
        for wav in sorted(src.glob('video_track_*.wav')):
            dest = out / job / wav.name; dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists(): shutil.copy(wav, dest)
            rep = C.transcribe(dest, m, lambda _: None)
            tracks.append([w for row in rep['rows'] for w in row.get('words', [])])
            summary[m]['asr_s'] += rep['seconds'] if not rep['cached'] else 0
            summary[m]['audio_s'] += rec['duration']
        offs, un = score(brief['captions'], tracks); s = summary[m]
        s['captions'] += len(offs) + un; s['matched'] += len(offs); s['unmatched'] += un
        s['off150'] += sum(abs(o) > .15 for o in offs); s['abs'] += [abs(o) for o in offs]
        print(f"{rec['timeline']:8s} {m:16s} matched {len(offs)}/{len(offs)+un} >150ms {sum(abs(o)>.15 for o in offs)} median|off| {statistics.median([abs(o) for o in offs]) if offs else 0:.3f}s", flush=True)
for m, s in summary.items():
    print(f"TOTAL {m:16s} matched {s['matched']}/{s['captions']} unmatched {s['unmatched']} >150ms {s['off150']} "
          f"median|off| {statistics.median(s['abs']) if s['abs'] else 0:.3f}s mean|off| {statistics.mean(s['abs']) if s['abs'] else 0:.3f}s "
          f"speed {s['audio_s']/s['asr_s'] if s['asr_s'] else float('nan'):.1f}x realtime")
