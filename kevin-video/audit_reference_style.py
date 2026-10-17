"""Reference audit from saved CapCut placements and cached source speech only."""
import collections
import hashlib
import statistics
import soundpilot as s
import context_pipeline as c


def words_near(rows,at,before=1.5,after=2.5):
    words=[w for row in rows for w in row.get('words',[]) if w['end']>=at-before and w['start']<=at+after]
    return ' '.join(w['text'] for w in words)


def main():
    project=s.project_path('0928');sounds=s.read_json(s.DATA/'sound_catalog.json')
    audit=[];snapshots={};summary=[]
    for name in s.config()['reference_timelines']:
        _,draft,path=s.load_timeline(project,name)
        _,key=c.context_inputs(project,draft)
        folder=s.DATA/'context'/key
        report=s.read_json(folder/'report-base.en.json')
        examples=[e for e in s.read_json(s.DATA/'examples.json') if e['timeline']==name]
        captions=s.caption_rows(draft)
        tracks=report['tracks']
        snapshots[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        for e in sorted(examples,key=lambda e:e['start']):
            at=e['start']
            close=[]
            for row in tracks[0]['speech']:
                for word in row.get('words',[]):
                    if abs(word['start']-at)<=1.5:close.append({'word':word['text'],'start':word['start'],'offset':round(at-word['start'],3)})
            close.sort(key=lambda word:abs(word['offset']))
            audit.append({'timeline':name,'start':round(at,3),'sound':e['sound'],
                'captions':s.context_at(captions,at,1.2,1.7),
                'reaction_words':words_near(tracks[0]['speech'],at),
                'second_video_words':words_near(tracks[1]['speech'],at) if len(tracks)>1 else '',
                'nearest_words':close[:3],'volume':round(e['volume'],3),'duration':round(e['duration'],3),
                'compound':e['compound']})
        summary.append({'timeline':name,'effects':len(examples),'duration':draft['duration']/s.MICRO})
    grouped=[]
    for sound,events in sorted(collections.defaultdict(list,((sound,[e for e in audit if e['sound']==sound]) for sound in {e['sound'] for e in audit})).items()):
        grouped.append({'sound':sound,'count':len(events),'median_volume':round(statistics.median(e['volume'] for e in events),3),
            'median_duration':round(statistics.median(e['duration'] for e in events),3),'events':events})
    result={'source_project':'0928','summary':summary,'groups':grouped,'source_snapshots':snapshots,
        'evidence_policy':'Saved manual placements are ground truth for these four videos. Automatic speech may contain errors; captions and exact visual frames resolve ambiguity. Sound function must be inferred from context, not assumed from the file name. No percentage represents performance on a new video.'}
    out=s.OUTPUTS/'style_audit';out.mkdir(exist_ok=True)
    s.write_json(out/'reference_events.json',result)
    lines=['# 0928 reference SFX audit','',f'{len(audit)} placements across four timelines. Automatic speech is supporting evidence; saved manual selections/timing are the references.','',
        '| Timeline | Time | Sound | Reaction/caption | Second-video speech |','|---|---:|---|---|---|']
    for e in audit:
        cells=[e['timeline'],f'{e["start"]:.2f}',e['sound'],e['captions'],e['second_video_words']]
        lines.append('| '+' | '.join(str(x).replace('|','/').replace('\n',' ') for x in cells)+' |')
    (out/'REFERENCE_EVENTS.md').write_text('\n'.join(lines),encoding='utf-8')
    print('AUDIT_READY',len(audit),'placements',len(grouped),'sounds')


if __name__=='__main__':main()
