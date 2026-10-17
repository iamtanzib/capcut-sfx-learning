"""Auditable local mix preview; source videos and SFX remain unmodified."""
import json
import argparse
import wave
import numpy as np
import context_pipeline as c
import soundpilot as s

parser=argparse.ArgumentParser();parser.add_argument('--folder',default='test1');args=parser.parse_args()
out=s.OUTPUTS/args.folder
plan=s.read_json(out/'reviewed_plan.json')
RATE=48000
project=s.project_path(plan['project']);_,draft,_=s.load_timeline(project,plan['timeline'])
inputs,_=c.context_inputs(project,draft)
count=round(plan['duration']*RATE)
voice=np.zeros((count,2),dtype=np.float32)
video_tracks=[t for t in draft['tracks'] if t.get('type')=='video' and t.get('segments')]
for track_index,track in enumerate(inputs['tracks']):
    for clip in track['clips']:
        span=clip['duration']*clip['speed']
        raw=c.run_ffmpeg(['-ss',str(clip['source_start']),'-i',clip['path'],'-t',str(span+.05),'-vn','-ac','2','-ar',str(RATE),'-f','f32le','-'])
        source=np.frombuffer(raw,dtype='<f4').reshape(-1,2)
        positions=np.arange(round(clip['duration']*RATE))*clip['speed']
        audio=np.column_stack([np.interp(positions,np.arange(len(source)),source[:,ch],left=0,right=0) for ch in range(2)]).astype(np.float32)
        original_segment=next(seg for seg in video_tracks[track_index]['segments']
            if abs(seg['target_timerange']['start']/s.MICRO-clip['start'])<.001)
        audio*=float(original_segment.get('volume',1))
        start=round(clip['start']*RATE);end=min(count,start+len(audio))
        voice[start:end]+=audio[:end-start]
effects=np.zeros((count,2),dtype=np.float32)
catalog={a['name']:a for a in s.read_json(s.DATA/'sound_catalog.json')}
for effect in plan['effects']:
    raw=c.run_ffmpeg(['-ss',str(effect['source_start']),'-i',catalog[effect['sound']]['path'],'-t',str(effect['duration']),'-ac','2','-ar',str(RATE),'-f','f32le','-'])
    audio=np.frombuffer(raw,dtype='<f4').copy().reshape(-1,2)*effect['volume']
    fade_in=min(len(audio),round(effect.get('fade_in',0)*RATE));fade_out=min(len(audio),round(effect.get('fade_out',0)*RATE))
    if fade_in:audio[:fade_in]*=np.linspace(0,1,fade_in)[:,None]
    if fade_out:audio[-fade_out:]*=np.linspace(1,0,fade_out)[:,None]
    start=round(effect['start']*RATE);end=min(count,start+len(audio))
    effects[start:end]+=audio[:end-start]
mix=voice+effects
peak=float(np.max(np.abs(mix)));gain=min(1,.891/max(peak,1e-8))
with wave.open(str(out/'audio_preview.wav'),'wb') as wav:
    wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(RATE)
    wav.writeframes((np.clip(mix*gain,-1,1)*32767).astype('<i2').tobytes())
report={'voice_peak':float(np.max(np.abs(voice))),'mix_peak_before_preview_gain':peak,
    'master_gain':gain,
    'preview_gain_db':round(20*np.log10(gain),2),'samples_above_full_scale':int(np.sum(np.abs(mix)>1)),
    'preview_policy':'48 kHz stereo source-audio mix with SFX and fades; whole-preview attenuation avoids clipping. Apply this same gain to all source/SFX clip volumes in the final draft.',
    'preview_length_seconds':len(mix)/RATE}
s.write_json(out/'audio_verification.json',report)
print(json.dumps(report,indent=2))
