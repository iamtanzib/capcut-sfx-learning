"""Prepare local, labelled frame sheets for Codex to review visual context."""
import argparse
import io
from pathlib import Path
import shutil
import subprocess
from PIL import Image,ImageDraw,ImageFont
import soundpilot as s


def make_storyboard(project_name,timeline_name,step=4):
    project=s.project_path(project_name)
    _,draft,_=s.load_timeline(project,timeline_name)
    videos={m['id']:m for m in draft['materials'].get('videos',[])}
    tracks=[t for t in draft['tracks'] if t.get('type')=='video' and t.get('segments')]
    captions=s.caption_rows(draft)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    entries=[]
    for at in range(0,int(draft['duration']/s.MICRO)+1,step):
        card=Image.new('RGB',(360,410),'#151923'); draw=ImageDraw.Draw(card)
        draw.text((8,5),f'{at:02d}s',font=font,fill='#78e0bc')
        for i,track in enumerate(tracks[:2]):
            seg=next((x for x in track['segments'] if x['target_timerange']['start']/s.MICRO<=at<(x['target_timerange']['start']+x['target_timerange']['duration'])/s.MICRO),None)
            if not seg: continue
            mat=videos.get(seg['material_id'],{})
            path=s.resolve_path(mat.get('path',''),project)
            source=seg.get('source_timerange') or {'start':0}
            source_time=source['start']/s.MICRO+(at-seg['target_timerange']['start']/s.MICRO)*float(seg.get('speed',1))
            proc=subprocess.run([shutil.which('ffmpeg'),'-v','error','-ss',str(source_time),'-i',str(path),'-frames:v','1','-vf','scale=172:270:force_original_aspect_ratio=decrease','-f','image2pipe','-vcodec','png','-'],capture_output=True,creationflags=s.CREATE_NO_WINDOW,timeout=30)
            if proc.returncode==0 and proc.stdout:
                image=Image.open(io.BytesIO(proc.stdout));card.paste(image,(8+i*176,34))
        text=s.context_at(captions,at,1,2)
        words=text.split();lines=[];line=''
        for word in words:
            if len(line+' '+word)>36: lines.append(line);line=word
            else: line=(line+' '+word).strip()
        lines.append(line)
        for i,line in enumerate(lines[:5]):draw.text((8,310+i*18),line,font=font,fill='white')
        entries.append(card)
    dest=s.OUTPUTS/'storyboards';dest.mkdir(parents=True,exist_ok=True)
    paths=[]
    for page in range(0,len(entries),8):
        sheet=Image.new('RGB',(1440,820),'#101216')
        for i,card in enumerate(entries[page:page+8]):sheet.paste(card,((i%4)*360,(i//4)*410))
        out=dest/f'{timeline_name.replace(" ","_")}-{page//8+1}.jpg';sheet.save(out,quality=90);paths.append(str(out))
    s.write_json(s.OUTPUTS/'codex_brief.json',{'project':project_name,'timeline':timeline_name,'duration':draft['duration']/s.MICRO,'captions':captions,'storyboards':paths,
        'sounds':[{k:a[k] for k in ('name','duration','tags','role')} for a in s.read_json(s.DATA/'sound_catalog.json')],
        'examples':[{k:e[k] for k in ('timeline','start','sound','anchor_text','context','duration','volume')} for e in s.read_json(s.DATA/'examples.json')],
        'request':'Read captions and view storyboard images. Choose tasteful local SFX with exact onset/trim/volume. Use existing examples for style; do not treat them as ground-truth timing for this new edit. Save a reviewed plan for soundpilot.export_copy. No API required.'})
    return paths


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',default='0928');p.add_argument('--timeline',default='Timeline 11');args=p.parse_args()
    print(make_storyboard(args.project,args.timeline))
