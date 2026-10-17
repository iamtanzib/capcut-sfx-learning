"""Read-only second alignment pass for flagged caption/speech timing differences."""
import os,sys,json,wave
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8');os.environ.setdefault('CT2_FORCE_CPU_ISA','GENERIC');os.environ.setdefault('CT2_USE_MKL','0')
import numpy as np
from faster_whisper import WhisperModel
sys.path.insert(0,str(Path(__file__).resolve().parent/'plugins/capcut-sfx-learning'))
import service as a
job='9b2ee23ff259474c';folder=a.job_path(job);report=a.s.read_json(folder/'context_report.json')
audio=Path(report['cache_folder'])/'video_track_1.wav'
with wave.open(str(audio),'rb') as wav:pcm=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(np.float32)/32768
cfg=a.s.config();model=WhisperModel('base.en',device='cpu',compute_type='int8',cpu_threads=2,num_workers=1,download_root=str(Path(cfg['model_root'])/'speech'),local_files_only=True)
rows=[]
for lo,hi in [(10,18),(22,33),(35,40),(45,54),(61,74),(78,88),(88,96),(98,104)]:
    segments,_=model.transcribe(pcm[round(lo*16000):round(hi*16000)],language='en',beam_size=5,word_timestamps=True,vad_filter=False,condition_on_previous_text=False)
    for seg in segments:
        row={'start':round(lo+seg.start,3),'end':round(lo+seg.end,3),'text':seg.text.strip(),'words':[[round(lo+w.start,3),w.word.strip()] for w in seg.words or []]};rows.append(row);print(json.dumps(row),flush=True)
a.s.write_json(folder/'alignment_check.json',{'policy':'base.en beam5 on short raw-audio windows without VAD. Read-only corroboration; not a rendered CapCut preview or guarantee.','rows':rows})
