"""Local CapCut SFX planner. Reads source projects; writes new projects only."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time
import uuid

BASE = Path(__file__).resolve().parent
DATA = BASE / 'data'
OUTPUTS = BASE / 'outputs'
MICRO = 1_000_000
CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'{path}: unreadable/encrypted draft; no changes made.') from exc


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.writing')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def config():
    cfg = read_json(BASE / 'config.json')
    settings = Path(cfg['sidebar_settings'])
    if settings.exists():
        cfg['library'] = read_json(settings).get('library', cfg['library'])
    return cfg


def uid():
    return str(uuid.uuid4()).upper()


def draft_file(folder):
    for name in ('draft_content.json', 'draft_info.json'):
        p = Path(folder) / name
        if p.exists():
            return p
    raise ValueError(f'No draft JSON in {folder}')


def project_path(name):
    root = Path(config()['draft_root']).resolve()
    path = (root / name).resolve()
    if path.parent != root or not path.is_dir():
        raise ValueError('Choose an existing CapCut project from the list.')
    return path


def timelines(project):
    path = Path(project) / 'Timelines' / 'project.json'
    if path.exists():
        return [t for t in read_json(path)['timelines'] if not t.get('is_marked_delete')]
    d = read_json(draft_file(project))
    return [{'id': d['id'], 'name': Path(project).name}]


def load_timeline(project, name):
    for t in timelines(project):
        if t['name'].casefold() == name.casefold() or t['id'] == name:
            folder = Path(project) / 'Timelines' / t['id']
            path = draft_file(folder) if folder.exists() else draft_file(project)
            return t, read_json(path), path
    # Reference tabs may be renamed by the user; resolve only known stable IDs.
    known_ids=set()
    for ref in config().get('additional_reference_sources',[]):
        if ref['project']==Path(project).name:
            if ref.get('timeline')==name and ref.get('timeline_id'):known_ids.add(ref['timeline_id'])
            if ref.get('caption_timeline')==name and ref.get('caption_timeline_id'):known_ids.add(ref['caption_timeline_id'])
    if len(known_ids)==1 and name not in known_ids:
        return load_timeline(project,next(iter(known_ids)))
    raise ValueError(f'Timeline {name!r} not found. Save in CapCut, then refresh.')


def list_projects():
    result = []
    for p in Path(config()['draft_root']).iterdir():
        if not p.is_dir():
            continue
        try:
            result.append({'name': p.name, 'timelines': timelines(p)})
        except (ValueError, KeyError, OSError):
            pass
    return result


def resolve_path(value, project):
    return Path(re.sub(r'##_draftpath_placeholder_[^#]+_##', str(Path(project).as_posix()), value))


def caption_rows(draft):
    materials = {m['id']: m for m in draft.get('materials', {}).get('texts', [])}
    result = []
    for track in draft.get('tracks', []):
        if track.get('type') != 'text':
            continue
        for s in track.get('segments', []):
            m = materials.get(s['material_id'], {})
            # Ignore title overlays; use actual speech captions.
            if m.get('type') != 'subtitle' and not m.get('recognize_text'):
                continue
            text = m.get('recognize_text') or json.loads(m.get('content', '{}')).get('text', '')
            r = s['target_timerange']
            if text.strip() and r['duration'] > 0:
                result.append({'start': r['start'] / MICRO, 'end': (r['start'] + r['duration']) / MICRO, 'text': text.strip()})
    return sorted(result, key=lambda x: x['start'])


def context_at(rows, start, before=2.5, after=2.5):
    nearby = [r for r in rows if r['end'] >= start-before and r['start'] <= start+after]
    return ' '.join(r['text'] for r in nearby)


TAGS = {
    'vine-boom': 'shock surprise dramatic revelation emphasis disbelief',
    'fah': 'comic line funny remark roast absurd punchline comic dismissal',
    'awkward': 'awkward silence uncomfortable pause failed joke embarrassment',
    'error': 'wrong answer mistake confusion fail interruption error',
    'wrong': 'wrong answer mistake incorrect fail',
    'among-us': 'suspicious questionable statement accusation inappropriate double meaning',
    'undertaker': 'ominous dark death dramatic threat punishment',
    'suspense': 'suspense warning shocking unexpected danger tension',
    'creepy': 'creepy scary sinister threat unsettling',
    'eww': 'disgust gross nasty repulsive rejection',
    'ooooo': 'surprise impressed excited discovery',
    'mmmm': 'genuine agreement approval liking accepting choosing an option',
    'movie_1': 'dramatic opening reveal cinematic emphasis',
    'heavenly': 'beautiful angelic heavenly perfection admiration',
    'quack': 'silly funny nonsense cartoon interruption',
    'tindeck': 'brief cartoon joke punchline surprise',
    'patrick': 'happy yes agreement celebration',
    'yay': 'success celebration happy win',
    'correct': 'success correct answer approval',
    'check-mark': 'success correct answer approval',
    'wow': 'amazement impressed surprise',
    'rizz': 'flirting confident charm romantic',
    'huh': 'confusion questioning disbelief',
    'death': 'death failure game over',
    'fart': 'crude joke silly embarrassing bodily humor',
    'cricket': 'awkward silence uncomfortable pause',
    'shocked': 'shocking surprised sudden reveal',
    'ding': 'idea success realization',
    'milk': 'pain injury failure distress',
    'sad': 'sad disappointment loss',
    'screech': 'panic sudden shocking interruption',
    'chill': 'relaxed calm background music',
}


def tags_for(name):
    lowered = name.lower()
    return ' '.join(dict.fromkeys(v for k, v in TAGS.items() if k in lowered)) or re.sub(r'[_\-]+', ' ', Path(name).stem)


def scan_library(progress=print):
    lib = Path(config()['library'])
    if not lib.is_dir():
        raise ValueError(f'Sound library missing: {lib}')
    ffprobe = shutil.which('ffprobe')
    if not ffprobe:
        raise ValueError('FFmpeg/ffprobe is required to read sound durations.')
    cache_path = DATA / 'sound_catalog.json'
    cache = {s['path']: s for s in read_json(cache_path)} if cache_path.exists() else {}
    sounds = []
    for p in sorted(lib.rglob('*.mp3')):
        stat = p.stat()
        item = cache.get(str(p))
        if not item or item.get('mtime') != stat.st_mtime_ns or item.get('size') != stat.st_size:
            proc = subprocess.run([ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(p)], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW, timeout=20)
            if proc.returncode:
                progress(f'Skipped unreadable audio: {p.name}')
                continue
            duration = float(json.loads(proc.stdout)['format']['duration'])
            item = {'name': p.name, 'path': str(p), 'duration': duration, 'mtime': stat.st_mtime_ns, 'size': stat.st_size, 'tags': tags_for(p.name), 'role': 'music' if duration > 20 else 'sfx'}
        item['tags']=tags_for(p.name)
        sounds.append(item)
    write_json(cache_path, sounds)
    progress(f'Library: {len(sounds)} MP3s ({sum(s["role"]=="sfx" for s in sounds)} short sounds).')
    return sounds


def flatten_sfx(draft, sounds, project, offset=0.0, scale=1.0, gain=1.0, crop=None, ancestry=()):
    """Map compound source ranges and speed to the visible parent timeline."""
    sound_map = {s['name'].casefold(): s for s in sounds if s['role'] == 'sfx'}
    materials = draft.get('materials', {})
    audios = {m['id']: m for m in materials.get('audios', [])}
    combinations = {m.get('combination_id'): m for m in materials.get('drafts', [])}
    for track in draft.get('tracks', []):
        if track.get('type') != 'audio':
            continue
        for seg in track.get('segments', []):
            if not seg.get('visible', True) or seg.get('volume', 1) <= 0:
                continue
            mat = audios.get(seg.get('material_id'), {})
            target = seg['target_timerange']
            local_start = target['start'] / MICRO
            local_end = local_start + target['duration'] / MICRO
            lo, hi = max(local_start, crop[0]) if crop else local_start, min(local_end, crop[1]) if crop else local_end
            if hi <= lo:
                continue
            speed = float(seg.get('speed') or 1.0)
            source = seg.get('source_timerange') or {'start': 0, 'duration': target['duration']}
            source_start = source['start'] / MICRO
            basename = Path(mat.get('path', '').replace('\\', '/')).name
            combination_id = re.sub(r'_audio\.[^.]+$', '', basename)
            nested = combinations.get(combination_id)
            if nested and nested.get('draft'):
                child_crop = (source_start + (lo-local_start)*speed, source_start + (hi-local_start)*speed)
                yield from flatten_sfx(nested['draft'], sounds, project,
                    offset=offset + (local_start-source_start/speed)*scale,
                    scale=scale/speed, gain=gain*float(seg.get('volume', 1)), crop=child_crop,
                    ancestry=ancestry+(mat.get('name', 'Compound'),))
                continue
            sound = sound_map.get(basename.casefold()) or sound_map.get(mat.get('name', '').casefold())
            if sound:
                yield {'sound': sound['name'], 'path': sound['path'], 'start': offset+lo*scale,
                    'duration': (hi-lo)*scale, 'source_start': source_start+(lo-local_start)*speed,
                    'speed': speed/scale, 'volume': gain*float(seg.get('volume', 1)), 'compound': list(ancestry),
                    'material': copy.deepcopy(mat), 'segment': copy.deepcopy(seg),
                    'materials': copy.deepcopy(materials)}


def reference_sources(cfg=None):
    cfg=cfg or config()
    return [{'project':cfg['reference_project'],'timeline':n} for n in cfg['reference_timelines']]+cfg.get('additional_reference_sources',[])


def video_timing_signature(draft):
    """Compare audio timing even when the user splits a clip for zoom edits."""
    videos={m['id']:m.get('path','').replace('\\','/').lower() for m in draft.get('materials',{}).get('videos',[])}
    result=[]
    for track in draft.get('tracks',[]):
        if track.get('type')!='video':continue
        merged=[]
        for seg in sorted(track.get('segments',[]),key=lambda e:e['target_timerange']['start']):
            target=seg['target_timerange'];source=seg.get('source_timerange') or {'start':0}
            speed=float(seg.get('speed') or 1);reverse=bool(seg.get('reverse'))
            row=[videos.get(seg['material_id'],''),source['start'],round(source['start']+target['duration']*speed),
                target['start'],target['start']+target['duration'],speed,reverse]
            if merged and not reverse and merged[-1][0]==row[0] and merged[-1][5:]==row[5:] and abs(merged[-1][2]-row[1])<=2 and abs(merged[-1][4]-row[3])<=2:
                merged[-1][2]=row[2];merged[-1][4]=row[4]
            else:merged.append(row)
        result.append(merged)
    return result


def extract_examples(sounds, progress=print):
    cfg = config()
    result = []
    summary = []
    for reference in reference_sources(cfg):
        project=project_path(reference['project']);name=reference['timeline']
        _, draft, _ = load_timeline(project, name)
        captions = caption_rows(draft)
        if reference.get('caption_snapshot'):
            caption_draft=read_json(reference['caption_snapshot'])
            if video_timing_signature(caption_draft)!=video_timing_signature(draft):
                raise ValueError('Reference caption snapshot does not match the saved video edits.')
            captions=caption_rows(caption_draft)
        elif reference.get('caption_timeline'):
            _,caption_draft,_=load_timeline(project,reference['caption_timeline'])
            captions=caption_rows(caption_draft)
        sfx = list(flatten_sfx(draft, sounds, project))
        for effect in sfx:
            effect['timeline'] = name
            effect['project'] = reference['project']
            effect['caption_timing_source']=reference.get('caption_timeline',name)
            effect['context'] = context_at(captions, effect['start'])
            nearest = min(captions, key=lambda c: min(abs(c['start']-effect['start']), abs(c['end']-effect['start']))) if captions else None
            effect['anchor_text'] = nearest['text'] if nearest else ''
            effect['anchor_edge'] = 'start' if nearest and abs(nearest['start']-effect['start']) < abs(nearest['end']-effect['start']) else 'end'
            effect['anchor_offset'] = effect['start']-nearest[effect['anchor_edge']] if nearest else 0
            # Keep only referenced material objects, not the entire draft per example.
            referenced = set(effect['segment'].get('extra_material_refs', []))
            effect['extras'] = {kind: [copy.deepcopy(m) for m in values if isinstance(m, dict) and m.get('id') in referenced] for kind, values in effect.pop('materials').items() if isinstance(values, list)}
            effect['extras'] = {k: v for k, v in effect['extras'].items() if v}
            result.append(effect)
        summary.append({'project':reference['project'],'timeline': name, 'duration': draft['duration']/MICRO, 'captions': len(captions), 'effects': len(sfx)})
        progress(f'{name}: {len(sfx)} effects, {len(captions)} captions.')
    if not result:
        raise ValueError('No local SFX examples found.')
    write_json(DATA / 'examples.json', result)
    write_json(DATA / 'training_summary.json', summary)
    return result, summary


class Planner:
    def __init__(self, progress=print):
        self.progress = progress
        self.model = None

    def embed(self, texts):
        import numpy as np
        if self.model is None:
            from fastembed import TextEmbedding
            cfg = config()
            self.progress('Loading small local semantic model...')
            self.model = TextEmbedding(model_name=cfg['model'], cache_dir=str(BASE/'models'), threads=cfg['threads'], local_files_only=True)
        arr = np.array(list(self.model.embed(texts, batch_size=16)), dtype=np.float32)
        return arr / np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), 1e-8)

    def train(self):
        import numpy as np
        sounds = scan_library(self.progress)
        examples, summary = extract_examples(sounds, self.progress)
        texts = [e['anchor_text']+' '+e['context'] for e in examples]
        vectors = self.embed(texts)
        np.save(DATA/'examples.npy', vectors)
        sfx = [s for s in sounds if s['role']=='sfx']
        np.save(DATA/'sounds.npy', self.embed([s['tags'] for s in sfx]))
        write_json(DATA/'index.json', {'model':config()['model'], 'example_hash':hashlib.sha256(json.dumps(examples,sort_keys=True).encode()).hexdigest(), 'sound_names':[s['name'] for s in sfx], 'created':time.time()})
        return {'summary':summary, 'examples':len(examples), 'sounds':len(sounds), 'sfx':len(sfx)}

    def plan(self, project_name, timeline_name, density=1.0, excluded=None):
        import numpy as np
        if not (DATA/'examples.npy').exists():
            self.train()
        project = project_path(project_name)
        _, draft, _ = load_timeline(project, timeline_name)
        captions = caption_rows(draft)
        if not draft.get('duration'):
            raise ValueError(f'{timeline_name} is empty. Add the edited video and Auto Captions in CapCut, then save and Refresh.')
        if not captions:
            raise ValueError('No speech captions found. Run Auto Captions in CapCut, save, then refresh. Captions supply the timing and dialogue for this free local mode.')
        examples = read_json(DATA/'examples.json')
        all_vectors = np.load(DATA/'examples.npy')
        indices = [i for i,e in enumerate(examples) if e['timeline'] != excluded]
        examples = [examples[i] for i in indices]
        if not examples:
            raise ValueError('No reference examples remain.')
        vectors = all_vectors[indices]
        sounds = read_json(DATA/'sound_catalog.json')
        catalog = {s['name']:s for s in sounds}
        query_texts = [c['text']+' '+context_at(captions,c['end'],2,1.5) for c in captions]
        queries = self.embed(query_texts)
        similarities = queries @ vectors.T
        duration = draft['duration']/MICRO
        summaries = read_json(DATA/'training_summary.json')
        rate = sum(s['effects'] for s in summaries if s['timeline']!=excluded) / sum(s['duration'] for s in summaries if s['timeline']!=excluded)
        count = max(1, round(duration*rate*max(0.25,min(float(density),1.8))))
        candidates = []
        for c, scores in zip(captions, similarities):
            order = np.argsort(scores)[::-1][:6]
            best = examples[int(order[0])]
            score = float(scores[order[0]])
            alternatives = []
            for idx in order:
                e = examples[int(idx)]
                if e['sound'] not in [a['sound'] for a in alternatives]:
                    alternatives.append({'sound':e['sound'], 'similarity':round(float(scores[idx]),3), 'example':e['anchor_text'], 'timeline':e['timeline']})
            edge = best['anchor_edge']
            at = c[edge] + max(-0.65,min(best['anchor_offset'],0.65))
            at = max(0,min(at,duration-0.1))
            candidates.append({'start':round(at,3), 'duration':round(min(best['duration'],duration-at,catalog[best['sound']]['duration']/best['speed']),3),
                'source_start':round(best['source_start'],3), 'speed':best['speed'], 'volume':round(min(best['volume'],0.65),4),
                'sound':best['sound'], 'dialogue':c['text'], 'similarity':round(score,3), 'review':True,
                'reason':f'Similar dialogue in {best["timeline"]}: {best["anchor_text"]}',
                'alternatives':alternatives, 'enabled':True, 'example_index':indices[int(order[0])]})
        # Scores indicate semantic similarity, not accuracy probabilities.
        chosen = []
        gap = float(config()['minimum_gap']) / max(0.5,float(density))
        for c in sorted(candidates,key=lambda c:c['similarity'],reverse=True):
            if c['similarity'] < 0.50:
                continue
            if all(abs(c['start']-x['start']) >= gap for x in chosen):
                chosen.append(c)
            if len(chosen)>=count:
                break
        chosen.sort(key=lambda c:c['start'])
        profile_path=DATA/'style_profile.json'
        style_version=None
        if profile_path.exists():
            profile=read_json(profile_path);style_version=profile['version']
            rare=set(profile.get('selection_policy',{}).get('rare_context_sounds',[]))
            if style_version>=5:
                for effect in chosen:
                    if effect['sound'] in rare:
                        effect['enabled']=False
                        effect['reason']='Omitted by default: this context sound needs a specific scene/intent justification or explicit user review. '+effect['reason']
                    if style_version>=8 and effect['sound']=='MMMMMM.mp3':
                        effect['enabled']=False
                        effect['reason']='Needs resolved positive appraisal or explicit affirmation; raw sentence similarity is not enough. '+effect['reason']
        snapshot = hashlib.sha256(draft_file(project/'Timelines'/draft['id']).read_bytes()).hexdigest()
        plan = {'project':project_name, 'timeline':timeline_name, 'duration':duration, 'source_hash':snapshot,
            'created':time.time(), 'engine':'local semantic retrieval; captions only',
            'limitations':'Does not see facial expression, gesture, tone or visual-only jokes. Similarity is not a success percentage. Review every suggestion.',
            'effects':chosen, 'captions':captions, 'excluded_reference':excluded,
            'existing_sfx':len(list(flatten_sfx(draft,sounds,project))),'style_profile_version':style_version}
        OUTPUTS.mkdir(exist_ok=True)
        write_json(OUTPUTS/'latest_plan.json',plan)
        self.progress(f'{len(chosen)} suggestions for {timeline_name} ({duration:.1f}s).')
        return plan

    def evaluate(self):
        """Leave one whole timeline out; match both timing and filename."""
        examples = read_json(DATA/'examples.json')
        results=[]
        for reference in reference_sources():
            name=reference['timeline']
            plan=self.plan(reference['project'],name,excluded=name)
            truth=[e for e in examples if e['timeline']==name and e.get('project',config()['reference_project'])==reference['project']]
            used=set(); matched=0; timing=0
            for predicted in plan['effects']:
                near=[(abs(t['start']-predicted['start']),i,t) for i,t in enumerate(truth) if i not in used and abs(t['start']-predicted['start'])<=0.75]
                if near:
                    timing+=1
                exact=[x for x in near if x[2]['sound']==predicted['sound']]
                if exact:
                    _,i,_=min(exact,key=lambda x:x[0]); used.add(i); matched+=1
            results.append({'timeline':name,'manual':len(truth),'suggested':len(plan['effects']),'same_sound_within_750ms':matched,'any_sound_within_750ms':timing,
                'precision':round(matched/max(len(plan['effects']),1),3),'recall':round(matched/max(len(truth),1),3)})
        report={'method':'Leave one whole reference timeline out. Exact filename + onset within 0.75 seconds. This measures agreement with the old edit, not artistic quality.', 'results':results}
        write_json(DATA/'evaluation.json',report)
        return report


def replace_values(obj, mapping):
    if isinstance(obj,dict):
        return {k:replace_values(v,mapping) for k,v in obj.items()}
    if isinstance(obj,list):
        return [replace_values(v,mapping) for v in obj]
    if isinstance(obj,str):
        return mapping.get(obj,obj)
    return obj


def rebase_paths(obj, project):
    if isinstance(obj,dict):
        return {k:rebase_paths(v,project) for k,v in obj.items()}
    if isinstance(obj,list):
        return [rebase_paths(v,project) for v in obj]
    if isinstance(obj,str) and '##_draftpath_placeholder_' in obj:
        return resolve_path(obj,project).as_posix()
    return obj


def strip_direct_sfx(draft, sounds):
    sfx_names={s['name'].casefold() for s in sounds if s['role']=='sfx'}
    audios={a['id']:a for a in draft['materials'].get('audios',[])}
    combinations={m.get('combination_id'):m for m in draft['materials'].get('drafts',[])}
    removed=0
    for track in draft.get('tracks',[]):
        if track.get('type')=='audio':
            keep=[]
            for seg in track['segments']:
                mat=audios.get(seg['material_id'],{})
                basename=Path(mat.get('path','')).name
                nested=combinations.get(re.sub(r'_audio\.[^.]+$','',basename))
                if nested:
                    child=nested['draft']
                    child_audio={a['id']:a for a in child['materials'].get('audios',[])}
                    active=[child_audio.get(s['material_id'],{}) for t in child['tracks'] if t.get('type')=='audio' for s in t.get('segments',[]) if s.get('volume',1)>0]
                    is_sfx=[Path(a.get('path','')).name.casefold() in sfx_names for a in active]
                    if any(is_sfx) and not all(is_sfx):
                        raise ValueError('A compound mixes music and SFX. Separate its tracks in CapCut before replacement.')
                    if is_sfx and all(is_sfx):
                        removed+=1
                        continue
                if basename.casefold() in sfx_names:
                    removed+=1
                else:
                    keep.append(seg)
            track['segments']=keep
    return removed


def validate_plan(plan, sounds):
    catalog={s['name']:s for s in sounds}
    profile_path=DATA/'style_profile.json'
    profile=read_json(profile_path) if profile_path.exists() else {}
    rare=set(profile.get('selection_policy',{}).get('rare_context_sounds',[]))
    for e in plan['effects']:
        if not e.get('enabled',True):
            continue
        if e['sound'] not in catalog:
            raise ValueError(f'Unknown sound: {e["sound"]}')
        # Optional event annotation enforces the user's explicit style corrections.
        function=e.get('function')
        if e['sound']=='MMMMMM.mp3' and e.get('evaluation_polarity')=='negative':
            raise ValueError('Negative appraisal/rejection must not use MMMMMM merely because it agrees with another speaker.')
        if (plan.get('style_profile_version') or 0)>=8 and e['sound']=='MMMMMM.mp3' and not e.get('user_reviewed'):
            if e.get('evaluation_polarity') not in {'positive','explicit_affirmation'}:
                raise ValueError('MMMMMM needs resolved positive appraisal or explicit affirmation; verbal agreement alone is insufficient.')
        if function=='approval' and e['sound']!='MMMMMM.mp3':
            raise ValueError('User style: approval must use MMMMMM, not a generic positive chime.')
        if function=='comic_line' and e['sound'] not in {'fahhhh.mp3','fahhhhhhhhhhhhhh.mp3'}:
            raise ValueError('User style: a comic-line event must use the learned FAH family.')
        if function=='explicit_disgust' and e['sound']!='ewww.mp3':
            raise ValueError('User style: spoken eww must use ewww.mp3.')
        if (plan.get('style_profile_version') or 0)>=5 and e['sound'] in rare and not e.get('user_reviewed'):
            evidence=e.get('context_evidence',{})
            if not (evidence.get('kind') in {'visual_context','spoken_context','reference'} and evidence.get('strength')=='high'
                    and len(evidence.get('cue','').strip())>=8 and len(evidence.get('why_this_sound','').strip())>=15):
                raise ValueError(f'{e["sound"]}: omit unless there is explicit scene/intent evidence or user review; palette variety is not evidence.')
        sound=catalog[e['sound']]
        if not Path(sound['path']).is_file():
            raise ValueError(f'Missing sound: {sound["path"]}')
        for key in ('start','duration','source_start','volume','speed'):
            if not isinstance(e.get(key),(int,float)) or not math.isfinite(e[key]):
                raise ValueError(f'Invalid {key} for {e["sound"]}')
        if e['start']<0 or e['duration']<=0 or e['start']+e['duration']>plan['duration']+0.001:
            raise ValueError('Sound timing is outside the video.')
        if not 0<=e['volume']<=1 or not 0.1<=e['speed']<=4 or e['source_start']<0:
            raise ValueError('Invalid volume, speed or source trim.')
        if e['source_start']+e['duration']*e['speed']>sound['duration']+0.05:
            raise ValueError(f'{e["sound"]}: trim exceeds the source sound duration.')


def add_effects(draft, plan, examples, sounds):
    catalog={s['name']:s for s in sounds}
    lanes=[]
    for effect in sorted([e for e in plan['effects'] if e.get('enabled',True)],key=lambda e:e['start']):
        template=copy.deepcopy(examples[effect['example_index']])
        sound=catalog[effect['sound']]
        seg=template['segment']; audio=template['material']; extras=template['extras']
        objects=[audio]+[x for arr in extras.values() for x in arr]
        mapping={x['id']:uid() for x in objects if x.get('id')}
        audio=replace_values(audio,mapping)
        audio.update({'path':Path(sound['path']).as_posix(),'name':sound['name'],'duration':round(sound['duration']*MICRO),'type':'music','local_material_id':''})
        draft['materials'].setdefault('audios',[]).append(audio)
        for kind,items in extras.items():
            draft['materials'].setdefault(kind,[]).extend(replace_values(items,mapping))
        seg=replace_values(seg,mapping)
        seg.update({'id':uid(),'material_id':audio['id'],'volume':effect['volume'],'last_nonzero_volume':effect['volume'],
            'speed':effect['speed'],'source_timerange':{'start':round(effect['source_start']*MICRO),'duration':round(effect['duration']*effect['speed']*MICRO)},
            'target_timerange':{'start':round(effect['start']*MICRO),'duration':round(effect['duration']*MICRO)},
            'group_id':'','keyframe_refs':[],'common_keyframes':[],'raw_segment_id':''})
        seg['extra_material_refs']=[mapping[r] for r in template['segment'].get('extra_material_refs',[]) if r in mapping]
        fade_in=round(min(float(effect.get('fade_in',.005)),effect['duration']/3)*MICRO)
        fade_out=round(min(float(effect.get('fade_out',.08)),effect['duration']/3)*MICRO)
        fades=draft['materials'].setdefault('audio_fades',[])
        fade=next((f for f in fades if f['id'] in seg['extra_material_refs']),None)
        if fade is None:
            fade={'id':uid(),'type':'audio_fade','fade_type':0}
            fades.append(fade);seg['extra_material_refs'].append(fade['id'])
        fade.update({'fade_in_duration':fade_in,'fade_out_duration':fade_out})
        # Speed objects must agree with segment speed.
        for speed_obj in draft['materials'].get('speeds',[]):
            if speed_obj.get('id') in seg['extra_material_refs']:
                speed_obj['speed']=effect['speed']
        lane=next((l for l in lanes if l['end']<=effect['start']+0.001),None)
        if lane is None:
            lane={'end':0,'segments':[]}; lanes.append(lane)
        lane['segments'].append(seg); lane['end']=effect['start']+effect['duration']
    base_index=max((s.get('track_render_index',0) for t in draft['tracks'] for s in t.get('segments',[])),default=0)+1
    for i,lane in enumerate(lanes):
        for s in lane['segments']:
            s['track_render_index']=base_index+i
        draft['tracks'].append({'id':uid(),'type':'audio','segments':lane['segments'],'flag':0,'attribute':0,'name':f'SoundPilot SFX {i+1}','is_default_name':False})
    return len(lanes)


def validate_draft(draft):
    ids={m['id'] for arr in draft['materials'].values() if isinstance(arr,list) for m in arr if isinstance(m,dict) and 'id' in m}
    missing=[]
    for t in draft['tracks']:
        for s in t.get('segments',[]):
            for ref in [s.get('material_id')]+s.get('extra_material_refs',[]):
                if ref and ref not in ids:
                    missing.append(ref)
            if t.get('name','').startswith('SoundPilot') and s['target_timerange']['start']+s['target_timerange']['duration']>draft['duration']+1000:
                raise ValueError('Generated sound exceeds timeline duration.')
    if missing:
        raise ValueError(f'Draft contains unresolved material references: {missing[:5]}')


def export_copy(plan, replace_existing=False):
    sounds=read_json(DATA/'sound_catalog.json')
    validate_plan(plan,sounds)
    project=project_path(plan['project'])
    timeline,draft,source_file=load_timeline(project,plan['timeline'])
    if hashlib.sha256(source_file.read_bytes()).hexdigest()!=plan['source_hash']:
        raise ValueError('Timeline changed in CapCut. Generate a fresh plan before exporting.')
    existing=list(flatten_sfx(draft,sounds,project))
    if existing and not replace_existing:
        raise ValueError('This timeline already contains local SFX. Select Replace existing sounds to avoid duplicates.')
    if replace_existing:
        strip_direct_sfx(draft,sounds)
    examples=read_json(DATA/'examples.json')
    lanes=add_effects(draft,plan,examples,sounds)
    master_gain=float(plan.get('master_gain',1))
    if not math.isfinite(master_gain) or not 0<master_gain<=1:
        raise ValueError('Master gain must be greater than 0 and at most 1.')
    if master_gain!=1:
        for track in draft['tracks']:
            if track.get('type') in ('audio','video'):
                for seg in track.get('segments',[]):
                    seg['volume']=float(seg.get('volume',1))*master_gain
                    seg['last_nonzero_volume']=float(seg.get('last_nonzero_volume',1))*master_gain
    draft=rebase_paths(draft,project)
    validate_draft(draft)
    now=int(time.time()*MICRO); new_id=uid(); new_timeline_id=uid()
    output_name=plan.get('output_timeline',plan['timeline']+' Auto SFX')
    name=f'{plan["project"]} - {output_name} {time.strftime("%m%d-%H%M%S")}'
    dest=Path(config()['draft_root'])/name
    if dest.exists():
        raise ValueError('Output already exists. Try again in a second.')
    dest.mkdir()
    draft['id']=new_timeline_id
    draft['name']=output_name
    # Copy small app sidecars, retaining external resource paths in the draft.
    for f in project.iterdir():
        if f.is_file() and f.name not in {'.locked','draft_content.json','draft_content.json.bak','draft_info.json','draft_meta_info.json','timeline_layout.json','draft_cover.jpg','template-2.tmp'} and f.stat().st_size<2_000_000 and not f.name.startswith('crypto_'):
            if f.suffix=='.json':
                try:
                    write_json(dest/f.name,rebase_paths(read_json(f),project))
                except ValueError:
                    shutil.copy2(f,dest/f.name)
            elif f.name not in {'draft.extra'}:
                shutil.copy2(f,dest/f.name)
    cover=project/'draft_cover.jpg'
    if cover.exists():
        shutil.copy2(cover,dest/cover.name)
    timeline_dir=dest/'Timelines'/new_timeline_id
    timeline_dir.mkdir(parents=True)
    write_json(dest/'draft_content.json',draft)
    write_json(dest/'draft_content.json.bak',draft)
    write_json(dest/'template-2.tmp',draft)
    write_json(timeline_dir/'draft_content.json',draft)
    write_json(timeline_dir/'draft_content.json.bak',draft)
    source_timeline_folder=source_file.parent
    for fname in ('attachment_editing.json','attachment_pc_common.json','draft.extra'):
        f=source_timeline_folder/fname
        if f.exists() and f.stat().st_size<1_000_000:
            shutil.copy2(f,timeline_dir/fname)
    tp=read_json(project/'Timelines'/'project.json')
    tp.update({'id':uid(),'main_timeline_id':new_timeline_id,'timelines':[{'id':new_timeline_id,'name':draft['name'],'create_time':now,'update_time':now,'is_marked_delete':False}]})
    write_json(dest/'Timelines'/'project.json',tp)
    write_json(dest/'Timelines'/'project.json.bak',tp)
    write_json(dest/'timeline_layout.json',{'dockItems':[{'dockIndex':0,'ratio':1,'timelineIds':[new_timeline_id],'timelineNames':[draft['name']]}],'layoutOrientation':1})
    meta=rebase_paths(read_json(project/'draft_meta_info.json'),project)
    meta.update({'draft_name':name,'draft_id':new_id,'draft_fold_path':dest.as_posix(),'draft_root_path':str(dest.parent.as_posix()),'draft_cover':(dest/'draft_cover.jpg').as_posix(),'tm_draft_create':now,'tm_draft_modified':now,'tm_duration':draft['duration']})
    # Register newly referenced sounds in the media bin as well as in the timeline.
    music_group=next((g for g in meta.get('draft_materials',[]) if g.get('type')==0),None)
    if music_group is None:
        music_group={'type':0,'value':[]}; meta.setdefault('draft_materials',[]).append(music_group)
    known={Path(m.get('file_Path','')).name.casefold() for m in music_group['value']}
    for e in plan['effects']:
        if e.get('enabled',True) and e['sound'].casefold() not in known:
            sound=next(s for s in sounds if s['name']==e['sound'])
            music_group['value'].append({'id':uid(),'file_Path':Path(sound['path']).as_posix(),'extra_info':sound['name'],'metetype':'music','type':0,'duration':round(sound['duration']*MICRO),'width':0,'height':0,'md5':'','create_time':0,'import_time':0,'import_time_ms':0,'roughcut_time_range':{'start':0,'duration':round(sound['duration']*MICRO)},'sub_time_range':{'start':-1,'duration':-1},'item_source':1,'enter_from':0})
            known.add(e['sound'].casefold())
    write_json(dest/'draft_meta_info.json',meta)
    report={'path':str(dest),'name':name,'draft_id':new_id,'source':str(project),'source_timeline':plan['timeline'],'source_hash':plan['source_hash'],
        'effects':sum(e.get('enabled',True) for e in plan['effects']),'tracks':lanes,'registered':False,'master_gain':master_gain,
        'resource_policy':'Existing video/compound resources reference the original project; keep the source project and sound library.',
        'verification':'JSON/material/timing validated. CapCut open/playback still needs checking.'}
    write_json(dest/'soundpilot_export.json',report)
    write_json(OUTPUTS/'latest_export.json',report)
    return report


def install_into_empty_timeline(export_path, project_name, timeline_name, reviewed_source=False):
    """Install reviewed output into an empty tab; do not overwrite edited tabs."""
    if capcut_running():
        raise ValueError('Close CapCut first. Its open editor would overwrite an external timeline update.')
    export_path=Path(export_path).resolve()
    if export_path.parent!=Path(config()['draft_root']).resolve() or not (export_path/'soundpilot_export.json').exists():
        raise ValueError('Choose a SoundPilot output project.')
    project=project_path(project_name)
    target,current,target_file=load_timeline(project,timeline_name)
    if current.get('duration',0)>0 or any(t.get('segments') for t in current.get('tracks',[])):
        report=read_json(export_path/'soundpilot_export.json')
        if not reviewed_source or report.get('source')!=str(project) or report.get('source_timeline')!=timeline_name:
            raise ValueError(f'{timeline_name} contains edits. Use the independent output copy instead.')
        if report.get('source_hash')!=hashlib.sha256(target_file.read_bytes()).hexdigest():
            raise ValueError('Original timeline changed since the reviewed copy was made. Rebuild the copy from the current edit.')
    updated=read_json(export_path/'draft_content.json')
    updated['id']=target['id']; updated['name']=timeline_name
    meta=read_json(project/'draft_meta_info.json')
    out_meta=read_json(export_path/'draft_meta_info.json')
    known={m.get('file_Path') for g in meta.get('draft_materials',[]) for m in g.get('value',[])}
    for group in out_meta.get('draft_materials',[]):
        additions=[m for m in group.get('value',[]) if m.get('file_Path') not in known]
        target_group=next((g for g in meta['draft_materials'] if g.get('type')==group.get('type')),None)
        if target_group is None:
            target_group={'type':group['type'],'value':[]}; meta['draft_materials'].append(target_group)
        target_group['value'].extend(additions)
    tp=read_json(project/'Timelines'/'project.json'); tp['main_timeline_id']=target['id']
    now=int(time.time()*MICRO); tp['update_time']=now
    meta['tm_duration']=updated['duration']; meta['tm_draft_modified']=now
    changes={target_file:updated,target_file.with_name(target_file.name+'.bak'):updated,
        project/'draft_content.json':updated,project/'draft_content.json.bak':updated,project/'template-2.tmp':updated,
        project/'Timelines'/'project.json':tp,project/'Timelines'/'project.json.bak':tp,project/'draft_meta_info.json':meta}
    before={str(p):p.read_bytes() if p.exists() else None for p in changes}
    backup=OUTPUTS/f'timeline-install-backup-{time.time_ns()}'; backup.mkdir(parents=True)
    for path,content in before.items():
        if content is not None:
            dest=backup/Path(path).relative_to(project); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(content)
    if capcut_running() or any(Path(p).read_bytes()!=content for p,content in before.items() if content is not None):
        raise ValueError('Project changed while preparing the update. Close CapCut and retry.')
    try:
        for path,value in changes.items():
            write_json(path,value)
    except Exception:
        for p,content in before.items():
            if content is not None:
                Path(p).write_bytes(content)
            elif Path(p).exists():
                Path(p).unlink()
        raise
    result={'installed':True,'project':project_name,'timeline':timeline_name,'backup':str(backup),'effects':sum(len(t['segments']) for t in updated['tracks'] if t.get('name','').startswith('SoundPilot'))}
    write_json(OUTPUTS/'latest_install.json',result)
    return result


def capcut_running():
    if os.name!='nt':
        return False
    proc=subprocess.run(['tasklist','/FI','IMAGENAME eq CapCut.exe','/FO','CSV','/NH'],capture_output=True,text=True,creationflags=CREATE_NO_WINDOW)
    return 'capcut.exe' in proc.stdout.lower()


def register_export(path):
    """Update project list only while CapCut is closed, with an original backup."""
    if capcut_running():
        raise ValueError('Close CapCut first, then press Add to CapCut. This avoids racing its project-list autosave.')
    root=Path(config()['draft_root']).resolve(); dest=Path(path).resolve()
    if dest.parent!=root or not (dest/'soundpilot_export.json').exists():
        raise ValueError('Only a SoundPilot output project can be registered.')
    meta=read_json(dest/'draft_meta_info.json')
    root_file=root/'root_meta_info.json'; before=root_file.read_bytes(); root_meta=read_json(root_file)
    if any(d.get('draft_id')==meta['draft_id'] for d in root_meta['all_draft_store']):
        return {'registered':True,'path':str(dest),'already_present':True}
    entry=copy.deepcopy(root_meta['all_draft_store'][0])
    for key in list(entry):
        if key in meta:
            entry[key]=meta[key]
    entry.update({'draft_id':meta['draft_id'],'draft_name':meta['draft_name'],'draft_fold_path':dest.as_posix(),'draft_root_path':root.as_posix(),
        'draft_json_file':(dest/'draft_content.json').as_posix(),'draft_cover':(dest/'draft_cover.jpg').as_posix(),'tm_duration':meta['tm_duration'],
        'tm_draft_create':meta['tm_draft_create'],'tm_draft_modified':meta['tm_draft_modified'],'draft_is_invisible':False})
    root_meta['all_draft_store'].insert(0,entry)
    # Preserve the actual draft_ids schema (some versions use strings, others objects).
    if isinstance(root_meta.get('draft_ids'),list) and all(isinstance(x,str) for x in root_meta['draft_ids']):
        root_meta['draft_ids'].insert(0,meta['draft_id'])
    backup=OUTPUTS/f'root_meta_info-before-{time.time_ns()}.json'
    backup.parent.mkdir(exist_ok=True); backup.write_bytes(before)
    if capcut_running() or root_file.read_bytes()!=before:
        raise ValueError('CapCut started or project list changed. Close it and retry.')
    write_json(root_file,root_meta)
    report=read_json(dest/'soundpilot_export.json'); report['registered']=True
    write_json(dest/'soundpilot_export.json',report); write_json(OUTPUTS/'latest_export.json',report)
    return report


def compact_brief(project_name, timeline_name, excluded_timelines=None):
    """A small text-only brief for Codex; no screen capture or cloud API."""
    project=project_path(project_name)
    _,draft,source_file=load_timeline(project,timeline_name)
    excluded_timelines=excluded_timelines or []
    examples=[e for e in read_json(DATA/'examples.json') if e['timeline'] not in excluded_timelines]
    sounds=read_json(DATA/'sound_catalog.json')
    used={e['sound'] for e in examples}
    style=[]
    for name in sorted(used):
        relevant=[e for e in examples if e['sound']==name]
        style.append({'sound':name,'usual_volume':round(statistics.median(e['volume'] for e in relevant),3),
            'usual_length':round(statistics.median(e['duration'] for e in relevant),3),
            'examples':[e['anchor_text'] for e in relevant[:3]]})
    brief={'project':project_name,'timeline':timeline_name,'duration':round(draft['duration']/MICRO,3),
        'source_hash':hashlib.sha256(source_file.read_bytes()).hexdigest(),'captions':caption_rows(draft),'excluded_style_timelines':excluded_timelines,
        'sound_style':style,'other_short_sounds':[{'name':a['name'],'length':round(a['duration'],2),'tags':a['tags']} for a in sounds if a['role']=='sfx' and a['name'] not in used],
        'request':'Choose local sounds from this brief with onset, duration and volume. Use soundpilot export_copy to apply into a duplicate. Captions do not establish visual-only events; request a local storyboard only if necessary. Do not use computer control. No OpenAI API calls.'}
    profile_path=DATA/'style_profile.json'
    if profile_path.exists():
        profile=read_json(profile_path)
        brief['user_style']={'version':profile['version'],'authoritative_rules':profile['authoritative_user_rules'],
            'preferred_sounds':profile['preferred_sounds'],'timing_policy':profile['timing_policy'],
            'sound_functions':[{'sound':r['sound'],'function':r['function'],'rule':r['rule'],'evidence_strength':r['evidence_strength'],
                'reference_volume':r['median_volume']} for r in profile['rules']],
            'avoid_generic_substitutes':profile['avoid_generic_substitutes']}
        brief['user_style']['selection_refinements']=profile.get('additional_timing_and_selection_rules',[])
        brief['user_style']['selection_policy']=profile.get('selection_policy',{})
        brief['user_style']['negative_examples']=profile.get('negative_examples',[])
        if 'Srijon version' not in excluded_timelines:
            brief['user_style']['manual_case_examples']=[{k:e[k] for k in ('cue','sound','function')} for e in profile.get('case_corrections',[])]
        if 'test 3' not in excluded_timelines:
            brief['user_style']['car_revision_examples']=[{k:e[k] for k in ('cue','sound','function')} for e in profile.get('car_revision_examples',[])]
        if 'test 4' not in excluded_timelines:
            brief['user_style']['shopping_cart_revision_examples']=profile.get('shopping_cart_revision_examples',[])
        brief['user_style']['appraisal_policy']=profile.get('appraisal_policy',{})
        brief['request']+=' Follow user_style before generic sound-name associations. Annotate each effect with function and the exact spoken/visual cue. Agreement uses MMMMMM; funny lines use FAH. Do not infer artistic accuracy from schema checks.'
        if profile['version']>=5:
            brief['request']+=' Set style_profile_version to the active version. Do not fill quiet gaps or meet a palette quota. Rare-context sounds require context_evidence with kind, strength=high, cue and why_this_sound; otherwise omit them.'
        if profile['version']>=8:
            brief['request']+=' For each MMMMMM cue, annotate evaluation_polarity as positive or explicit_affirmation after resolving the referenced object/context. Agreement that an option is uncomfortable/bad is negative appraisal, not MMMMMM. Not-bad/dont-mind can still be positive.'
    write_json(OUTPUTS/'compact_brief.json',brief)
    return {'path':str(OUTPUTS/'compact_brief.json'),'captions':len(brief['captions']),'characters':len(json.dumps(brief,ensure_ascii=False))}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['scan','train','evaluate','plan','export','register','install','brief','projects'])
    p.add_argument('--project',default=config()['default_project'])
    p.add_argument('--timeline',default=config()['default_timeline'])
    p.add_argument('--plan',default=str(OUTPUTS/'latest_plan.json'))
    p.add_argument('--replace-existing',action='store_true')
    args=p.parse_args(); planner=Planner()
    if args.command=='scan': result=scan_library()
    elif args.command=='train': result=planner.train()
    elif args.command=='evaluate': result=planner.evaluate()
    elif args.command=='plan': result=planner.plan(args.project,args.timeline)
    elif args.command=='export': result=export_copy(read_json(args.plan),args.replace_existing)
    elif args.command=='register': result=register_export(read_json(OUTPUTS/'latest_export.json')['path'])
    elif args.command=='install': result=install_into_empty_timeline(read_json(OUTPUTS/'latest_export.json')['path'],args.project,args.timeline)
    elif args.command=='brief': result=compact_brief(args.project,args.timeline)
    else: result=list_projects()
    print(json.dumps(result,ensure_ascii=False,indent=2,default=str))


if __name__=='__main__':
    main()
