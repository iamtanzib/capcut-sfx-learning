"""Freeze comparison of the old prediction against the user's new reference."""
import collections
import hashlib
import math
import soundpilot as s

project=s.project_path('test 1');timeline,manual,path=s.load_timeline(project,'Srijon version')
sounds=s.read_json(s.DATA/'sound_catalog.json')
truth=sorted(s.flatten_sfx(manual,sounds,project),key=lambda e:e['start'])
plan=s.read_json(s.OUTPUTS/'test1'/'reviewed_plan.json')
pred=[e for e in plan['effects'] if e.get('enabled',True)]
tolerance=.75
def match(same_sound):
    edges=sorted((abs(t['start']-p['start']),i,j) for i,p in enumerate(pred) for j,t in enumerate(truth)
        if abs(t['start']-p['start'])<=tolerance and (not same_sound or p['sound']==t['sound']))
    used_pred=set();used_truth=set();selected=[]
    for delta,i,j in edges:
        if i not in used_pred and j not in used_truth:
            used_pred.add(i);used_truth.add(j);selected.append({'prediction':i,'manual':j,'delta':round(delta,3)})
    return selected
exact=match(True);timing=match(False)
paired={m['manual']:m for m in timing}
base=s.load_timeline(project,'Timeline 01')[1]
captions=s.caption_rows(base)
rows=[]
for i,e in enumerate(truth):
    pair=paired.get(i);old=pred[pair['prediction']] if pair else None
    rows.append({'start':round(e['start'],3),'manual_sound':e['sound'],'manual_volume':round(e['volume'],3),
        'cue':s.context_at(captions,e['start'],.8,1.3),'old_prediction':old['sound'] if old else None,
        'old_start':old['start'] if old else None,'timing_delta':pair['delta'] if pair else None,
        'exact_match':bool(old and old['sound']==e['sound'])})
counts=collections.Counter(e['sound'] for e in truth)
report={'project':'test 1','ground_truth_timeline':'Srijon version','onset_tolerance_seconds':tolerance,
    'original_predictions':len(pred),'manual_placements':len(truth),'exact_sound_and_onset_matches':len(exact),
    'precision':len(exact)/len(pred),'recall':len(exact)/len(truth),
    'onset_only_matches':len(timing),'onset_only_policy':'A matching time with the wrong sound is not an exact success.',
    'counts':dict(counts),'rows':rows,'exact_pairs':exact,
    'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
    'frozen_prediction_sha256':hashlib.sha256((s.OUTPUTS/'test1'/'reviewed_plan.json').read_bytes()).hexdigest(),
    'evaluation_policy':'Measured before adding this manual video to the reference index. It is agreement with the user edit, not an artistic-quality guarantee. Do not retrain and score on the same video as an unseen test.'}
out=s.OUTPUTS/'srijon_comparison';out.mkdir(exist_ok=True)
s.write_json(out/'comparison.json',report)
s.write_json(out/'manual_snapshot.json',manual)
lines=['# Srijon version vs previous SoundPilot prediction','',
    f'Previous predictions: **{len(pred)}**. Manual placements: **{len(truth)}**.',
    f'Exact sound + onset within ±{tolerance}s: **{len(exact)}**. Precision **{report["precision"]*100:.1f}%**, recall **{report["recall"]*100:.1f}%**.',
    f'Onset-only pairs: {len(timing)}; wrong sound names still count as failures.','',
    '| Manual time | Your sound | Relevant dialogue | My nearby sound | Result |','|---:|---|---|---|---|']
for row in rows:
    cells=[f'{row["start"]:.2f}s',row['manual_sound'],row['cue'],row['old_prediction'] or 'No prediction within tolerance',
        'Same sound' if row['exact_match'] else 'Different sound / missed']
    lines.append('| '+' | '.join(str(v).replace('|','/').replace('\n',' ') for v in cells)+' |')
lines.extend(['','## Concrete corrections',
    '- Fast-food excitement: ooooo, rather than treating every positive reaction as MMMMMM.',
    '- Give me wings / I will do that / that is perfect: MMMMMM on the approval beat.',
    '- The failed-everything line resolves to a positive choice. The word failed alone does not justify FAHH.',
    '- There are zero FAHH placements in this user edit. Do not force a comedy quota.',
    '- Neutral okay and losing-pencils setup: awkward; that does not mean every negative or dry line should get FAHH.',
    '- Breakfast/free sequence: Among Us at 35.17s. The user did not put Among Us automatically on choosing test answers at 39.93s.',
    '- Ice-cream rejection: error. Ordinary rejection is not automatically a funny punchline.',
    '- Volume levels are intentional per sound, not one fixed volume for all clips.',
    '',report['evaluation_policy']])
(out/'COMPARISON.md').write_text('\n'.join(lines),encoding='utf-8')
print({k:report[k] for k in ['original_predictions','manual_placements','exact_sound_and_onset_matches','precision','recall','onset_only_matches','counts']})
