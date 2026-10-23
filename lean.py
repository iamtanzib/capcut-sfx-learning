"""Opt-in smaller briefs. Default briefs are unchanged; lean=1 only changes what is SENT.

lean=1 drops fields the planner never decides: stage_plan re-reads gain envelopes from the
job's frozen profile.json, and ids/hashes/file paths are bookkeeping. A relevance-selected
memory (old lean=2) was removed on 2026-10-23 after it lost 11-32% of the closest
precedents for real manual revisions; see CHANGELOG.md.
"""
import copy

BOOKKEEPING = {'source_hash', 'analysis_job_id', 'timeline_id', 'revision_hash', 'path'}

def _drop(value, keys):
    if isinstance(value, dict): return {k: _drop(v, keys) for k, v in value.items() if k not in keys}
    if isinstance(value, list): return [_drop(v, keys) for v in value]
    return value

def level1(row):
    row = copy.deepcopy(row)
    us = row.get('user_style', {})
    for level in us.get('mix_preferences', {}).get('sound_levels', {}).values():
        for r in level.get('references', []): r.pop('gain_envelope', None)
    for key in ('dialogue_level_references', 'background_level_references'):
        if key in us: us[key] = _drop(us[key], BOOKKEEPING)
    if 'zoom_style' in row:
        z = row['zoom_style']
        for key in ('references', 'framing_only_examples'):
            if key in z: z[key] = _drop(z[key], BOOKKEEPING)
    return row

def apply(rows, lean):
    if lean not in (0, 1): raise ValueError('lean must be 0 (full) or 1.')
    if not lean: return rows
    rows = [level1(r) for r in rows]
    for r in rows: r['lean_memory'] = {'level': 1, 'policy': 'Machine-applied fields (gain envelopes, ids, hashes, paths) omitted; stage_plan re-reads them.'}
    return rows
