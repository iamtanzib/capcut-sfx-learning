"""File-only audio + scene context. Never reads existing SFX placements."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
import wave
import soundpilot as s

# Compatible backend for this Pentium CPU; no system environment is modified.
os.environ.setdefault('CT2_FORCE_CPU_ISA','GENERIC')
os.environ.setdefault('CT2_USE_MKL','0')

RATE=16000


def run_ffmpeg(args,timeout=480):
    proc=subprocess.run([shutil.which('ffmpeg'),'-v','error','-threads','2']+args,
        capture_output=True,creationflags=s.CREATE_NO_WINDOW,timeout=timeout)
    if proc.returncode:
        raise ValueError(proc.stderr.decode(errors='replace')[-1200:])
    return proc.stdout


def context_inputs(project,draft):
    """Digest only visible video edits/files and captions; ignore SFX material data."""
    materials={m['id']:m for m in draft['materials'].get('videos',[])}
    tracks=[]
    for track in draft.get('tracks',[]):
        if track.get('type')!='video':continue
        clips=[]
        for seg in sorted(track.get('segments',[]),key=lambda x:x['target_timerange']['start']):
            if not seg.get('visible',True):continue
            mat=materials.get(seg['material_id'],{})
            if not mat.get('path'):continue
            path=s.resolve_path(mat['path'],project)
            if not path.is_file():raise ValueError(f'Missing source video: {path}')
            stat=path.stat()
            target=seg['target_timerange'];source=seg.get('source_timerange') or target
            if target['duration']<=0:continue
            clips.append({'path':str(path),'size':stat.st_size,'mtime':stat.st_mtime_ns,
                'start':target['start']/s.MICRO,'duration':target['duration']/s.MICRO,
                'source_start':source['start']/s.MICRO,'speed':float(seg.get('speed') or 1),
                'reverse':bool(seg.get('reverse',False))})
        if clips:tracks.append({'role':f'video_track_{len(tracks)+1}','clips':clips})
    if not tracks:raise ValueError('No video tracks with local source files found.')
    inputs={'duration':draft['duration']/s.MICRO,'tracks':tracks,'captions':s.caption_rows(draft),'schema':2}
    key=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:20]
    return inputs,key


def resample_clip(source,source_origin,clip):
    import numpy as np
    count=round(clip['duration']*RATE)
    positions=(clip['source_start']-source_origin)*RATE+np.arange(count)*clip['speed']
    if clip.get('reverse'):
        positions=positions[::-1]
    # Linear interpolation adjusts speech tempo only for context extraction.
    return np.interp(positions,np.arange(len(source)),source,left=0,right=0).astype(np.float32)


def track_audio(track,duration,folder,progress):
    import numpy as np
    output=folder/(track['role']+'.wav')
    if output.exists():return output
    samples=np.zeros(round(duration*RATE),dtype=np.float32)
    paths=sorted({c['path'] for c in track['clips']})
    for path in paths:
        clips=[c for c in track['clips'] if c['path']==path]
        lo=max(0,min(c['source_start'] for c in clips)); hi=max(c['source_start']+c['duration']*c['speed'] for c in clips)
        progress(f'Decoding {track["role"]}: {Path(path).name}')
        try:
            raw=run_ffmpeg(['-ss',str(lo),'-i',path,'-t',str(hi-lo+0.1),'-vn','-ac','1','-ar',str(RATE),'-f','f32le','-'])
            source=np.frombuffer(raw,dtype='<f4')
        except ValueError as exc:
            progress(f'No usable audio in {Path(path).name}: {exc}')
            continue
        if len(source)==0:continue
        for clip in clips:
            segment=resample_clip(source,lo,clip)
            start=round(clip['start']*RATE); end=min(len(samples),start+len(segment))
            samples[start:end]+=segment[:end-start]
    peak=float(np.max(np.abs(samples))) if len(samples) else 0
    if peak>0.001:samples*=min(0.85/peak,4)
    with wave.open(str(output),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(RATE)
        wav.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())
    return output


def transcribe(audio,model_name,progress,beam=3):
    output=audio.with_name(audio.stem+'.'+model_name+'.json')
    if output.exists():
        report=s.read_json(output);report['cached']=True;return report
    from faster_whisper import WhisperModel
    progress(f'Transcribing {audio.stem}, {model_name}, CPU int8...')
    begin=time.perf_counter()
    cfg=s.config()
    model=WhisperModel(model_name,device='cpu',compute_type='int8',cpu_threads=cfg['speech_threads'],
        num_workers=1,download_root=str(s.BASE/'models'/'speech'),local_files_only=True)
    import numpy as np
    with wave.open(str(audio),'rb') as wav:
        if wav.getframerate()!=RATE or wav.getnchannels()!=1 or wav.getsampwidth()!=2:
            raise ValueError('Speech input must be 16 kHz mono PCM.')
        pcm=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(np.float32)/32768
    segments,_=model.transcribe(pcm,language='en',beam_size=beam,word_timestamps=True,
        vad_filter=True,vad_parameters={'min_silence_duration_ms':450},condition_on_previous_text=False)
    rows=[]
    for seg in segments:
        rows.append({'start':round(seg.start,3),'end':round(seg.end,3),'text':seg.text.strip(),
            'words':[{'start':round(w.start,3),'end':round(w.end,3),'text':w.word.strip()} for w in (seg.words or [])]})
        progress(f'{audio.stem}: speech read through {seg.end:.1f}s')
    report={'model':model_name,'seconds':round(time.perf_counter()-begin,2),'cached':False,'rows':rows}
    s.write_json(output,report)
    return report


def proxy_video(track,folder,width):
    """Build a small, silent proxy in visible timeline order for shot detection."""
    decode_mode=s.config().get('scene_decode','keyframes')
    output=folder/(track['role']+'.proxy-'+decode_mode+'.mp4')
    if output.exists():return output
    import numpy as np
    import cv2
    height=180
    temporary=output.with_name(output.stem+'.writing.mp4')
    writer=cv2.VideoWriter(str(temporary),cv2.VideoWriter_fourcc(*'mp4v'),8,(width,height))
    if not writer.isOpened():raise ValueError('OpenCV proxy writer could not open.')
    cursor=0
    decoded={}
    try:
        # Decode each unique source once, rather than reopening it for every cut.
        for path in sorted({c['path'] for c in track['clips']}):
            clips=[c for c in track['clips'] if c['path']==path]
            origin=min(c['source_start'] for c in clips)
            end=max(c['source_start']+c['duration']*c['speed'] for c in clips)
            source_fps=8*max(c['speed'] for c in clips)
            skip=['-skip_frame','nokey'] if decode_mode=='keyframes' else []
            data=run_ffmpeg(skip+['-ss',str(origin),'-i',path,'-t',str(end-origin+.2),'-an',
                '-vf',f'fps={source_fps},scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
                '-f','rawvideo','-pix_fmt','bgr24','-'])
            size=width*height*3
            frames=np.frombuffer(data,dtype=np.uint8)[:len(data)//size*size].reshape(-1,height,width,3)
            decoded[path]=(origin,source_fps,frames)
        for clip in track['clips']:
            desired=round(clip['start']*8)
            while cursor<desired:
                writer.write(np.zeros((height,width,3),dtype=np.uint8));cursor+=1
            count=max(1,round((clip['start']+clip['duration'])*8)-desired)
            origin,source_fps,frames=decoded[clip['path']]
            for i in range(count):
                offset=i/8*clip['speed']
                if clip.get('reverse'):offset=clip['duration']*clip['speed']-offset
                index=round((clip['source_start']-origin+offset)*source_fps)
                writer.write(frames[min(max(index,0),len(frames)-1)] if len(frames) else np.zeros((height,width,3),dtype=np.uint8));cursor+=1
    finally:writer.release()
    os.replace(temporary,output)
    return output


def scene_rows(proxy,folder,progress):
    output=proxy.with_suffix('.scenes.json')
    if output.exists():return s.read_json(output)
    from scenedetect import detect,ContentDetector
    progress(f'Detecting scene changes in {proxy.stem}...')
    scenes=detect(str(proxy),ContentDetector(threshold=24,min_scene_len=6),start_in_scene=True)
    rows=[{'start':round(a.get_seconds(),3),'end':round(b.get_seconds(),3)} for a,b in scenes]
    s.write_json(output,rows)
    return rows


def energy_peaks(wav_path):
    import numpy as np
    with wave.open(str(wav_path),'rb') as f:samples=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(float)/32768
    step=round(RATE*0.1);values=[]
    for i in range(0,len(samples),step):
        chunk=samples[i:i+step];values.append(float(np.sqrt(np.mean(chunk*chunk))) if len(chunk) else 0)
    if not values:return []
    threshold=float(np.percentile(values,85));peaks=[]
    for i in range(1,len(values)-1):
        if values[i]>=threshold and values[i]>values[i-1] and values[i]>=values[i+1]:
            at=i*.1
            if not peaks or at-peaks[-1]>0.8:peaks.append(round(at,2))
    return peaks


def frame_sheet(inputs,scenes,folder,max_frames):
    """Sparse local frames at scene reveals. This is analysis, not desktop capture."""
    from PIL import Image,ImageDraw,ImageFont
    points={0.5}
    duration=inputs['duration']
    for group in scenes:
        points.update(min(duration-.1,r['start']+.35) for r in group['scenes'])
    # Keep chronological coverage when there are more cuts than the frame budget.
    points=sorted(p for p in points if 0<=p<duration)
    if len(points)>max_frames:
        points=[points[round(i*(len(points)-1)/(max_frames-1))] for i in range(max_frames)]
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
    import cv2
    captures=[cv2.VideoCapture(str(folder/(track['role']+'.proxy-'+s.config().get('scene_decode','keyframes')+'.mp4'))) for track in inputs['tracks'][:2]]
    cards=[]
    for at in points:
        card=Image.new('RGB',(340,330),'#171c25');draw=ImageDraw.Draw(card)
        draw.text((8,5),f'{at:.2f}s',font=font,fill='#78e0bc')
        for index,track in enumerate(inputs['tracks'][:2]):
            clip=next((c for c in track['clips'] if c['start']<=at<c['start']+c['duration']),None)
            if not clip:continue
            capture=captures[index];capture.set(cv2.CAP_PROP_POS_MSEC,at*1000)
            ok,frame=capture.read()
            if ok:
                image=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
                # Remove proxy letterboxing for a readable portrait preview.
                bbox=image.getbbox()
                if bbox:image=image.crop(bbox)
                image.thumbnail((158,240));card.paste(image,(8+index*168,28))
        caption=s.context_at(inputs['captions'],at,1,1.5)
        lines=[];line=''
        for word in caption.split():
            if len(line+' '+word)>42:lines.append(line);line=word
            else:line=(line+' '+word).strip()
        lines.append(line)
        for i,line in enumerate(lines[:3]):draw.text((8,272+i*17),line,font=font,fill='white')
        cards.append(card)
    for capture in captures:capture.release()
    paths=[]
    for page in range(0,len(cards),6):
        sheet=Image.new('RGB',(1020,660),'#101216')
        for i,card in enumerate(cards[page:page+6]):sheet.paste(card,((i%3)*340,(i//3)*330))
        dest=folder/f'keyframes-{s.config().get("scene_decode","keyframes")}-{page//6+1}.jpg';sheet.save(dest,quality=85);paths.append(str(dest))
    return paths


def prepare(project_name,timeline_name,model_name=None,progress=print,include_images=True):
    started=time.perf_counter();cfg=s.config();model_name=model_name or cfg['speech_model']
    project=s.project_path(project_name);_,draft,path=s.load_timeline(project,timeline_name)
    inputs,key=context_inputs(project,draft)
    folder=s.DATA/'context'/key;folder.mkdir(parents=True,exist_ok=True)
    tracks=[];scenes=[]
    for track in inputs['tracks']:
        progress(f'Preparing {track["role"]} (cached results are reused)...')
        audio=track_audio(track,inputs['duration'],folder,progress)
        transcript=transcribe(audio,model_name,progress)
        progress(f'Preparing small frame proxy for {track["role"]}...')
        proxy=proxy_video(track,folder,cfg['scene_proxy_width'])
        shot_rows=scene_rows(proxy,folder,progress)
        tracks.append({'role':track['role'],'speech':transcript['rows'],'transcription_seconds':transcript['seconds'],'cached':transcript['cached'],'loud_moments':energy_peaks(audio)})
        scenes.append({'role':track['role'],'scenes':shot_rows})
    images=[]
    if include_images:
        cached_images=sorted(folder.glob('keyframes-'+cfg.get('scene_decode','keyframes')+'-*.jpg'))
        images=[str(p) for p in cached_images] if cached_images else frame_sheet(inputs,scenes,folder,cfg['maximum_keyframes'])
    # Sound names/style remain useful; do not include old placement times for this target.
    excluded=[]
    for reference in s.reference_sources(cfg):
        ref_project=s.project_path(reference['project']);name=reference['timeline']
        _,ref_draft,_=s.load_timeline(ref_project,name)
        ref_inputs,_=context_inputs(ref_project,ref_draft)
        # Captions can move independently of video; compare the actual video edits.
        same_video=s.video_timing_signature(ref_draft)==s.video_timing_signature(draft) and ref_inputs['duration']==inputs['duration']
        if same_video or (project_name==reference['project'] and name==timeline_name):excluded.append(name)
    s.compact_brief(project_name,timeline_name,excluded);brief=s.read_json(s.OUTPUTS/'compact_brief.json')
    brief.update({'pipeline':'two-track local speech + scene changes + sparse keyframes',
        'visual_sampling':{'mode':cfg.get('scene_decode','keyframes'),'timing_note':'Keyframe-only scene boundaries and expressions are approximate. Use speech word timing and captions for precise sound onsets; request an exact video frame when a visual reaction is ambiguous.'},
        'source_dialogue':[{ 'role':t['role'],'speech':[{k:r[k] for k in ('start','end','text')} for r in t['speech']]} for t in tracks],
        'scene_changes':[{ 'role':g['role'],'at':[r['start'] for r in g['scenes']]} for g in scenes],
        'audio_emphasis':[{'role':t['role'],'at':t['loud_moments']} for t in tracks],
        'keyframes':images,'old_sfx_used_as_input':False,
        'request':'Read both source-dialogue streams and scene-reveal timing. View sparse keyframes when visual context is needed. Choose SFX from the local library by meaning and comedic timing. Do not copy target old placement times; none are provided. Save/export through soundpilot; no desktop control or paid API.'})
    s.write_json(s.OUTPUTS/'enhanced_brief.json',brief)
    elapsed=round(time.perf_counter()-started,2)
    report={'project':project_name,'timeline':timeline_name,'model':model_name,'cache_key':key,'cache_folder':str(folder),
        'seconds':elapsed,'tracks':tracks,'scenes':scenes,'keyframes':images,'brief':str(s.OUTPUTS/'enhanced_brief.json'),
        'scene_decode':cfg.get('scene_decode','keyframes'),
        'brief_characters':len(json.dumps(brief,ensure_ascii=False)),'old_sfx_used_as_input':False,'excluded_style_timelines':excluded,
        'quality_note':'Preprocessing validated. This does not establish sound-selection accuracy or a 90% score.'}
    s.write_json(folder/f'report-{model_name}.json',report);s.write_json(s.OUTPUTS/'context_report.json',report)
    progress(f'Context ready: {elapsed}s; {len(tracks)} video tracks; {sum(len(t["speech"]) for t in tracks)} speech segments.')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',default='0928');p.add_argument('--timeline',default='Timeline 11');p.add_argument('--model',default=None);p.add_argument('--no-images',action='store_true');args=p.parse_args()
    report=prepare(args.project,args.timeline,args.model,include_images=not args.no_images)
    print(json.dumps({k:report[k] for k in ('brief','seconds','model','cache_key','old_sfx_used_as_input')},indent=2))
