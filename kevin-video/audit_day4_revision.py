"""Compare frozen Day 4 edits with saved revisions without editing CapCut."""
import json, sys, copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGIN = Path(r'C:\Users\srijon\.codex\plugins\cache\srijon-sfx\capcut-sfx-learning\0.1.15')
sys.path.insert(0, str(PLUGIN))
import service as api
import zoom, hooks

JOBS = ['4bba52416cb34246', '373100e5361a4787', '5807249f095f4529']
catalog = api.s.read_json(api.s.DATA / 'sound_catalog.json')
out = ROOT / 'outputs' / 'day4-revision'
out.mkdir(parents=True, exist_ok=True)
reports = []

for job in JOBS:
    rec = api.job_data(job)
    folder = api.job_path(job)
    original = api.s.read_json(folder / 'source.json')
    plan = api.s.read_json(folder / 'plan.json')
    project = api.s.project_path(rec['project'])
    timeline, draft, path = api.s.load_timeline(project, rec['timeline_id'])
    manual_hash = api.digest(path)
    mapping = api.ra.TimelineMap(original, draft)
    analysis = api.s.read_json(folder / 'context_report.json')
    old = []
    for cue in plan['effects']:
        at = mapping.new_time(0, cue['start'])
        if at is not None:
            old.append({**cue, 'start': at})
    native = list(api.s.flatten_sfx(draft, catalog, project))
    truth = api.ra.logical_events(native, envelope_references=old)
    diff = api.revision_diff(old, truth)
    rows = []
    for i, e in enumerate(truth):
        row = {k: e.get(k) for k in ('sound', 'start', 'duration', 'source_start', 'speed', 'volume', 'energy_gain', 'gain_envelope', 'gain_parts')}
        row['index'] = i
        row['both_stream_context'] = [
            {'role': t['role'], 'text': api.ra.word_context(analysis, n, mapping.old_time(n, e['start']))}
            for n, t in enumerate(analysis['tracks'])
        ]
        row['caption_context'] = api.s.context_at(api.s.caption_rows(original), mapping.old_time(0, e['start']))
        rows.append(row)
    zplan = api.s.read_json(api.STATE / 'zoom_jobs' / rec['zoom_job_id'] / 'plan.json')['zooms']
    observed = zoom.extract(draft)
    for e in observed:
        e.pop('native_clip', None)
        e['both_stream_context'] = [
            {'role': t['role'], 'text': api.ra.word_context(analysis, n, mapping.old_time(n, e['start']))}
            for n, t in enumerate(analysis['tracks'])
        ]
    fields = hooks.fields(draft)
    hplan = api.s.read_json(api.STATE / 'hook_jobs' / rec['hook_job_id'] / 'plan.json')
    matched_levels = []
    for pair in diff['matches']:
        p, m = old[pair['old']], truth[pair['manual']]
        installed = p['volume'] * plan.get('master_gain', 1)
        matched_levels.append({'old_index': pair['old'], 'manual_index': pair['manual'], 'sound': p['sound'], 'delta': pair['delta'], 'installed_gain': installed, 'manual_gain': m['volume'], 'change_db': round(api.ra.db(m['volume']/installed), 2), 'old_duration': p['duration'], 'manual_duration': m['duration']})
    assert api.digest(path) == manual_hash, 'Saved revision changed during comparison'
    report = {'job_id': job, 'timeline': timeline['name'], 'timeline_id': timeline['id'], 'path': str(path), 'manual_hash': manual_hash,
              'frozen_style_version': rec['style_version'], 'old_master_gain': plan.get('master_gain', 1),
              'old': old, 'manual': rows, 'diff': diff, 'level_changes': matched_levels,
              'zoom_old': zplan, 'zoom_manual': observed, 'zoom_diff': zoom.revision_diff(zplan, observed),
              'hook_old': hplan['hook'], 'hook_manual': [{'text': f['text'], 'highlights': hooks.highlights(f['material']), 'appearance': hooks.appearance(f)} for f in fields],
              'voice_levels': api.ra.level_spans(draft), 'original_voice_balance': plan['quality_notes'].get('dialogue_balance'),
              'background_audio': api.ra.background_references(api.s, draft, catalog, project)}
    reports.append(report)

versions = {n: api.s.read_json(api.s.DATA / n)['version'] for n in ['style_profile.json', 'zoom_style.json', 'hook_style.json']}
code_files = ['service.py', 'zoom.py', 'hooks.py', 'revision_audio.py', 'engine/soundpilot.py', 'edit_modes.py']
code_comparison = {n: {'installed_sha256': api.digest(PLUGIN/n), 'workspace_sha256': api.digest(ROOT/'plugins/capcut-sfx-learning'/n)} for n in code_files}
result = {'batch_id': '0db216191b2e412b', 'before_learning_versions': versions, 'code_comparison': code_comparison, 'reports': reports, 'capcut_modified': False}
api.s.write_json(out / 'BEFORE_LEARNING_CORRECTED.json', result)
print(json.dumps({'versions':versions,'code_matches_workspace':{n:v['installed_sha256']==v['workspace_sha256'] for n,v in code_comparison.items()},
 'timelines':[{'job_id':r['job_id'],'timeline':r['timeline'],'old_cues':len(r['old']),'manual_cues':len(r['manual']),
 'diff':r['diff'],'voice_levels':r['voice_levels'],'hook_unchanged':r['hook_old']['text']==r['hook_manual'][0]['text'],
 'unchanged_zooms':r['zoom_diff']['retained_without_material_change']} for r in reports]},ensure_ascii=False))
