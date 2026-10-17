"""Compound-aware revision events, time mapping and native gain envelopes."""
import copy,math,statistics

def db(value):return 20*math.log10(max(value,1e-12))

def _known_envelope_groups(rows, references):
    """Prove longer new-ID bodies using a frozen envelope, never proximity alone."""
    chains=set()
    for ref in references or []:
        envelope=ref.get('gain_envelope') or []
        if len(envelope)<2 or abs(envelope[0].get('offset',0))>.002:continue
        speed=float(ref.get('speed',1));source=float(ref.get('source_start',0))
        for first in rows:
            if first['sound']!=ref['sound'] or first['speed']!=speed:continue
            shift=first['start']-ref['start']
            if abs(shift)>3 or abs(first['source_start']-source)>.002:continue
            indices=[]
            for part in envelope:
                offset=float(part['offset']);source_offset=float(part.get('source_offset',offset*speed))
                matches=[i for i,row in enumerate(rows) if row['sound']==ref['sound'] and row['speed']==speed
                    and first.get('path') and row.get('path')==first['path']
                    and abs(row['start']-(first['start']+offset))<=.002
                    and abs(row['source_start']-(source+source_offset))<=.002
                    and abs(row['duration']-float(part['duration']))<=.002]
                if len(matches)!=1:break
                indices.append(matches[0])
            if len(indices)==len(envelope) and len(set(indices))==len(indices):chains.add(tuple(indices))
    # Ambiguous overlapping chains do not establish a common logical cue.
    counts={i:sum(i in chain for chain in chains) for chain in chains for i in chain}
    return {i:chain for chain in chains if all(counts[i]==1 for i in chain) for i in chain}

def logical_events(rows, envelope_references=None):
    """Join one leaf across split compounds, retaining piecewise effective gain."""
    events=[];rows=sorted(rows,key=lambda e:(e['start'],e['sound']))
    known_groups=_known_envelope_groups(rows,envelope_references)
    for index,row in enumerate(rows):
        candidates=[]
        for event in reversed(events):
            last=event['gain_parts'][-1]
            gap=row['start']-(event['start']+event['duration'])
            source_end=event['source_start']+last['source_offset']+last['duration']*event['speed']
            same_leaf=event['segment'].get('id')==row['segment'].get('id')
            same_media=bool(event.get('path')) and event.get('path')==row.get('path')
            # CapCut gives independently split tails new IDs. Join only a tiny,
            # source-continuous tail with a bounded gap; never merge new attacks.
            split_tail=same_media and row['duration']<=.1 and -.002<=gap<=.15
            verified_body=(known_groups.get(index) is not None and event.get('_envelope_group')==known_groups[index]
                and same_media and -.002<=gap<=.15)
            if event['sound']==row['sound'] and event['speed']==row['speed'] and abs(source_end-row['source_start'])<=.002 and ((same_leaf and abs(gap)<=.002) or split_tail or verified_body):
                candidates.append(event)
        previous=candidates[0] if len(candidates)==1 else None
        part={'offset':0,'source_offset':0,'duration':row['duration'],'volume':row['volume'],'compound_gain':row.get('compound_gain',1),'leaf_volume':row.get('leaf_volume',row['volume'])}
        if previous:
            part['offset']=row['start']-previous['start'];part['source_offset']=row['source_start']-previous['source_start'];previous['gain_parts'].append(part)
            previous['duration']=row['start']+row['duration']-previous['start'];previous['volume']=max(previous['volume'],row['volume'])
        else:
            event=copy.deepcopy(row);event['gain_parts']=[part]
            if index in known_groups:event['_envelope_group']=known_groups[index]
            events.append(event)
    for e in events:
        e.pop('_envelope_group',None)
        e['energy_gain']=math.sqrt(sum(p['volume']**2*p['duration'] for p in e['gain_parts'])/sum(p['duration'] for p in e['gain_parts']))
        e['gain_envelope']=[{'offset':p['offset'],'source_offset':p['source_offset'],'duration':p['duration'],'gain':p['volume']/e['volume']} for p in e['gain_parts']]
    return sorted(events,key=lambda e:e['start'])

def video_tracks(draft):
    mats={m['id']:m for m in draft['materials'].get('videos',[])};result=[]
    for track in draft['tracks']:
        if track.get('type')!='video':continue
        clips=[]
        for seg in track.get('segments',[]):
            mat=mats.get(seg['material_id'],{})
            if not mat.get('path') or not seg.get('visible',True):continue
            target=seg['target_timerange'];src=seg.get('source_timerange') or target
            clips.append({'path':mat['path'].replace('\\','/').lower(),'start':target['start']/1e6,'duration':target['duration']/1e6,
                'source_start':src['start']/1e6,'speed':float(seg.get('speed') or 1),'reverse':bool(seg.get('reverse')),'volume':float(seg.get('volume',1))})
        if clips:result.append(sorted(clips,key=lambda c:c['start']))
    return result

class TimelineMap:
    """Map revised source samples back to frozen dialogue; reject unrelated assets."""
    def __init__(self,before,after):
        self.before=video_tracks(before);self.after=video_tracks(after)
        if len(self.before)!=len(self.after):raise ValueError('Revision changed video roles; inspect correspondence first.')
        for original,manual in zip(self.before,self.after):
            for clip in manual:
                if clip['reverse']:raise ValueError('Reversed revision needs an explicit timing map.')
                compatible=[old for old in original if old['path']==clip['path'] and not old['reverse'] and abs(old['speed']-clip['speed'])<1e-8
                    and old['source_start']-2e-6<=clip['source_start']
                    and clip['source_start']+clip['duration']*clip['speed']<=old['source_start']+old['duration']*old['speed']+2e-6]
                if len(compatible)!=1:raise ValueError('Revision source is new, extended, or ambiguous; inspect correspondence first.')
    def old_time(self,role,at):
        if not self.after:return at
        clip=next((c for c in reversed(self.after[role]) if c['start']<=at<c['start']+c['duration']+2e-6),None)
        if clip is None:raise ValueError('No revised video at cue time.')
        source=clip['source_start']+(at-clip['start'])*clip['speed']
        matches=[c for c in self.before[role] if c['path']==clip['path'] and c['source_start']-2e-6<=source<=c['source_start']+c['duration']*c['speed']+2e-6]
        if not matches:raise ValueError('No original source timing.')
        targets=[c['start']+(source-c['source_start'])/c['speed'] for c in matches]
        if max(targets)-min(targets)>2e-6:raise ValueError('Ambiguous original source timing.')
        return max(targets)
    def new_time(self,role,at):
        if not self.before:return at
        old=next((c for c in self.before[role] if c['start']<=at<c['start']+c['duration']),None)
        if old is None:return None
        source=old['source_start']+(at-old['start'])*old['speed']
        matches=[c for c in self.after[role] if c['path']==old['path'] and c['source_start']-2e-6<=source<c['source_start']+c['duration']*c['speed']+2e-6]
        if not matches:return None # A user-trimmed source section has no prediction in revised coordinates.
        if len(matches)>1:
            # Shared endpoints of adjacent splits differ by at most rounding microseconds.
            targets=[c['start']+(source-c['source_start'])/c['speed'] for c in matches]
            if max(targets)-min(targets)>2e-6:raise ValueError('Revision repeats a source range; inspect it before scoring.')
        clip=matches[-1];return clip['start']+(source-clip['source_start'])/clip['speed']

def word_context(report,role,at,before=2.5,after=2.5):
    if not report:return ''
    track=next((t for t in report.get('tracks',[]) if t['role']==f'video_track_{role+1}'),{})
    words=[w['text'] for row in track.get('speech',[]) for w in row.get('words',[]) if w['end']>=at-before and w['start']<=at+after]
    return ' '.join(words)

def render_plan(plan):
    """Expand a logical gain envelope to editable native clip pieces, not an audio render."""
    result=copy.deepcopy(plan);result['effects']=[]
    for effect in plan['effects']:
        envelope=effect.get('gain_envelope') or [{'offset':0,'duration':effect['duration'],'gain':1}]
        for index,part in enumerate(envelope):
            offset=float(part['offset']);duration=min(float(part['duration']),effect['duration']-offset)
            if duration<=0:continue
            e=copy.deepcopy(effect);e.pop('gain_envelope',None)
            e.update(start=effect['start']+offset,source_start=effect['source_start']+part.get('source_offset',offset*effect['speed']),duration=duration,
                volume=effect['volume']*part['gain'],fade_in=effect.get('fade_in',0) if index==0 else 0,
                fade_out=effect.get('fade_out',0) if index==len(envelope)-1 else 0)
            result['effects'].append(e)
    return result

def update_levels(profile,examples):
    """Latest manually approved final gains, not old automatic headroom gains."""
    rows=[e for e in examples if e.get('manual_level_reference')]
    levels={}
    for sound in sorted({e['sound'] for e in rows}):
        values=sorted(e['volume'] for e in rows if e['sound']==sound)
        selected=[e for e in rows if e['sound']==sound]
        levels[sound]={'count':len(values),'normal_gain':statistics.median(values),'soft_gain':values[max(0,round((len(values)-1)*.2))],
            'emphasis_gain':values[round((len(values)-1)*.8)],'median_duration':statistics.median(e['duration'] for e in selected),
            'fade_in':statistics.median(e.get('fade_in',0) for e in selected),'fade_out':statistics.median(e.get('fade_out',0) for e in selected),
            'references':[{'cue':e['anchor_text'],'gain':e['volume'],'duration':e['duration'],'gain_envelope':e.get('gain_envelope',[]),'timeline':e['timeline']} for e in selected]}
    profile['mix_preferences']={'sound_levels':levels,'gain_basis':'Final effective amplitude including ALL compound parents; do not divide by the old automatic master gain.',
        'automatic_whole_mix_attenuation':False,'policy':'Use per-asset normal/soft/emphasis references. Preserve foreground/narrator balance; peak protection is a separate explicit mix decision. RMS/sample peaks do not establish perceived loudness.'}

def background_references(s,draft,catalog,project):
    known={r['name'].lower():r for r in catalog};all_catalog=[{**r,'role':'sfx'} for r in catalog]
    def collect(d):
        for mat in d['materials'].get('audios',[]):
            name=mat.get('name');path=mat.get('path')
            if name and path and name.lower() not in known:
                row={'name':name,'path':str(s.resolve_path(path,project)),'duration':mat.get('duration',0)/1e6,'role':'sfx'}
                all_catalog.append(row);known[name.lower()]=row
        for child in d['materials'].get('drafts',[]):
            if child.get('draft'):collect(child['draft'])
    collect(draft)
    short={r['name'].lower() for r in catalog if r['role']=='sfx'}
    return [{'name':r['sound'],'start':r['start'],'duration':r['duration'],'source_start':r['source_start'],'effective_gain':r['volume'],
        'effective_db':round(db(r['volume']),2),'compound_gain':r.get('compound_gain',1),'leaf_gain':r.get('leaf_volume',r['volume']),
        'role':'library_music' if any(x['name']==r['sound'] and x['role']=='music' for x in catalog) else 'other_imported_audio',
        'note':'Read-only observed background/reference level; no global music-volume rule inferred.'}
        for r in s.flatten_sfx(draft,all_catalog,project) if r['sound'].lower() not in short]

def level_spans(draft):
    result=[]
    for clips in video_tracks(draft):
        spans=[]
        for clip in clips:
            row={k:clip[k] for k in ('path','start','duration','volume')}
            if spans and spans[-1]['path']==row['path'] and spans[-1]['volume']==row['volume'] and abs(spans[-1]['start']+spans[-1]['duration']-row['start'])<2e-6:
                spans[-1]['duration']=row['start']+row['duration']-spans[-1]['start']
            else:spans.append(row)
        result.append(spans)
    return result
