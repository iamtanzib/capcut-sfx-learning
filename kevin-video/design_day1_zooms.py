"""Contextual zoom choices from complete cached dialogue and manual SFX."""
import sys,json
from pathlib import Path
BASE=Path(__file__).resolve().parent;sys.path.insert(0,str(BASE/'plugins/capcut-sfx-learning'))
import service as a
import zoom
batch=a.s.read_json(BASE/'outputs/zoom-feature/BATCH.json')
# start, end, scale, verified foreground word, phrase, contextual selection reason.
choices={
'Day 1.3':[
 (5.33,6.63,1.25,3,'I need the job','Dry pleading after the fired-from-job threat; a restrained reaction punch-in, not a zoom on the intro.'),
 (23.1,24.9,1.32,20,'Yeah I am not sleeping on those','Hold the explicit nail-bed refusal through those, then reset before the next toilet option.'),
 (28.03,29.1,1.25,26,'Yeah I am cooked','Short self-directed cooked punchline after the public-toilet punishment; return before the quieter yeah no.'),
 (34.3,35.47,1.38,35,'This is torture','Emphatic personal reaction to the 24-hour mosquito room; the actor expression carries the beat.'),
 (47.23,48.7,1.40,49,'Not gonna work if I am not alive','Comic conclusion of the freezing-snow punishment; zoom on the active punchline, not the preceding ASR silence.'),
 (50.9,52.03,1.30,56,'Bro no','Brief disgust/refusal at rotten garbage; reset before help so the closeups remain distinct.')],
'Day 1.4':[
 (12.83,13.9,1.38,8,'I eat my blanket','Funny personal admission about the tortilla blanket; emphasize eat through blanket and release.'),
 (16.6,17.67,1.25,14,'Grass','Brief confused recognition of the grass blanket, then reset before evaluating comfort.'),
 (22.93,24.2,1.32,27,'What the oh heck nah','Grass-and-insect objection builds into an expressive refusal before the spiderweb reveal.'),
 (28.87,29.83,1.28,35,'I freak out','Short stated fear of spiders crawling on the actor; do not hold across the pizza option.'),
 (36.93,38.0,1.49,48,'I eat the whole blanket','Strong comic payoff repeats the edible-blanket idea with whole blanket, matching the references stronger punch-ins.'),
 (51.93,52.93,1.25,64,'Bro what','Dry incredulous bubble-wrap reaction, followed by a reset before the final you might be cooked line.')],
'Day 1.5':[
 (10.77,11.73,1.25,9,'What if I need battery','Practical battery objection gets a restrained reaction closeup; the narrator example remains visible.'),
 (26.03,27.67,1.32,26,'How do you get them','Suspicious teeth-acquisition question: actor reaction, not the whole long Among Us bed.'),
 (31.73,33.03,1.30,36,'No no','Complete horrified refusal after where/who the teeth came from; reset before duck-currency commentary.'),
 (43.03,43.97,1.38,45,'Save up my nails','Comical self-directed nail-saving payoff; hold on the distinctive final phrase.'),
 (46.8,48.3,1.32,50,'Eww','Actual revised disgust beat just before chicken currency; ASR renders this vocalization as eel, so retain the manual ewww cue as supporting context.'),
 (56.93,58.13,1.28,64,'Oh heck nah','Immediate underwear-currency refusal; release before later narrator jokes rather than zooming the entire option.')],
'Day 1.6':[
 (17.7,19.0,1.35,14,'What','Disbelief at the farting-pill reveal, before the quieter public-laughing consequence.'),
 (23.47,24.67,1.28,18,'I laugh all the time','Personal comic confession about laughing constantly; one reaction closeup for the complete punchline.'),
 (44.53,45.7,1.28,39,'Low key tough','Dry appraisal of instant hairstyle; preserve awkward delivery instead of treating every positive word as enthusiasm.'),
 (55.53,56.8,1.30,54,'I would not take that pill','Decisive pickle-pill refusal; no full-length zoom matching the longer doom-bell tail.'),
 (59.93,61.53,1.38,59,'That is fire yo','Teleportation enthusiasm gets one expressive closeup; the repeated later fire remains at baseline.'),
 (66.53,67.73,1.32,64,'What the','Short giant-hands disbelief; reset before the basketball explanation.'),
 (76.27,77.93,1.40,70,'September','Impressed time-freeze response and lucky-month address; leave the full anime-wow tail unzoomed.'),
 (85.8,87.27,1.32,75,'Trade with me please','Personal Luffy/stretching trade plea rather than an automatic zoom on every month label.'),
 (90.4,91.3,1.49,81,'What','Strong instant food-duplication surprise; a short high-emphasis punch-in with immediate baseline reset.'),
 (95.47,96.73,1.38,83,'Opening a restaurant','Food-duplication business punchline is distinct from the previous surprise and gets its own short reaction.')]
}
for jid in batch['jobs']:
    r=zoom.data(a,jid);b=a.s.read_json(zoom.folder(a,jid)/'brief.json');words={w['word_index']:w for row in b['dialogue']['tracks'][0]['speech'] for w in row['words']};events=[]
    for start,end,scale,index,phrase,reason in choices[r['timeline']]:
        w=words[index]
        # Source framing differs by recording; keep hair/eyes inside the top panel.
        baseline=b['layout'][0]['segments'][-1]['clip']['transform']['y']
        dy=-max(0,(baseline-.65)*.6+(scale-1.3)*.13)
        events.append({'role':'video_track_1','start':start,'end':end,'scale':scale,'dx':0,'dy':round(dy,6),
            'dialogue':phrase,'reason':reason,'timing_anchor':{'kind':'speech_word','role':'video_track_1','at':w['start'],'word_index':index,'text':w['text']}})
    notes={'whole_video_reviewed':True,'silence_reviewed':True,'unresolved':[],'framing_reviewed':False,
        'policy':'Host reviewed both complete cached dialogue streams plus all native reference zooms. Meaningful actor reactions only; no SFX or month quota.'}
    print(json.dumps(a.stage_zoom_plan(jid,events,notes)))
    print(json.dumps(a.preview_zoom_plan(jid)),flush=True)
summary={'batch_id':batch['batch_id'],'jobs':batch['jobs'],'zooms':{name:len(rows) for name,rows in choices.items()},'transcription_runs':0,'cached_analysis_reused':True,'native_capcut_preview_verified':False}
a.s.write_json(BASE/'outputs/zoom-feature/DESIGN.json',summary)
