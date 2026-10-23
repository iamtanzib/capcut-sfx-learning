"""Learn manual revisions for an applied edit batch and print a compact summary.

Usage: python capcut_revise.py [batch_id] [--rule "text" --evidence "user said ..." --scope future_edits]
Without batch_id the newest edit batch is used. A --rule is stored as explicit_user on every job.
"""
import argparse, glob, json, os, sys
BUNDLE=os.environ.get('SOUNDPILOT_BUNDLE') or (os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if os.name!='nt' else r'C:\Users\srijon\Documents\ChatGPT\Kevin Video\outputs\CapCut-SFX-Learning-Claude-Code-FULL-2026-10-13-v0.1.15\plugins\capcut-sfx-learning')
STATE=os.environ.get('SOUNDPILOT_STATE') or os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'SoundPilotLearning')
sys.path.insert(0,BUNDLE)
import service as a

p=argparse.ArgumentParser();p.add_argument('batch',nargs='?');p.add_argument('--rule',action='append',default=[])
p.add_argument('--evidence',default='');p.add_argument('--scope',default='future_edits')
args=p.parse_args()
path=os.path.join(STATE,'edit_batches',args.batch+'.json') if args.batch else max(glob.glob(os.path.join(STATE,'edit_batches','*.json')),key=os.path.getmtime)
batch=json.load(open(path,encoding='utf-8'))
if args.rule and len(args.evidence)<10:sys.exit('--evidence must quote what the user said.')
rules=[{'rule':r,'evidence':args.evidence,'scope':args.scope,'authority':'explicit_user'} for r in args.rule]
print('batch',batch['batch_id']);scores=[]
for job,target in zip(batch['analysis_jobs'],batch['targets']):
    r=a.learn_revision(job,target['project'],target['timeline'],rules or None)
    name=a.job_data(job).get('timeline')
    if 'diff' not in r:print(name,'already learned');continue
    d=r['diff'];t=d['timing'];plan=a.s.read_json(a.job_path(job)/'plan.json')
    old=[e for e in plan['effects'] if e.get('enabled',True)]
    hist=json.load(open(os.path.join(STATE,'history',r['reference']+'.json'),encoding='utf-8'))
    ex=sorted([e for e in hist['examples'] if e.get('feedback_source')==r['reference']],key=lambda e:e['start'])
    scores.append((t['strict_precision'],t['strict_recall'],d['precision'],d['recall']))
    print(f"{name}: v{r['new_style_version']} strict P/R {t['strict_precision']:.2f}/{t['strict_recall']:.2f} loose {d['precision']:.2f}/{d['recall']:.2f}")
    for i in d['removed']:print(f"  - {old[i]['sound'][:16]} {old[i]['start']:.2f} {old[i]['dialogue'][:40]}")
    for i in d['added']:print(f"  + {ex[i]['sound'][:16]} {ex[i]['start']:.2f} {(ex[i].get('anchor_text') or '')[:40]}")
    for m in t['retimed_matches']:print(f"  ~ {old[m['old']]['sound'][:16]} {old[m['old']]['start']:.2f} moved {m['delta']:+.2f}s")
    for x in r['sound_level_changes']:
        if abs(x['peak_gain_change_db'])>=1:print(f"  dB {x['sound'][:16]} {x['start']:.2f} {x['peak_gain_change_db']:+.1f}")
    z=r.get('zoom_revision',{}).get('diff',{});h=r.get('hook_revision',{})
    changed=sum(bool(m.get('retimed') or m.get('reframed')) for m in z.get('matches',[]))
    print(f"  zoom added {len(z.get('added',[]))} removed {len(z.get('removed_or_distant_move',[]))} changed {changed}; hook wording changed {h.get('wording_changed')}")
if scores:
    avg=[sum(x)/len(scores)*100 for x in zip(*scores)]
    print(f"saved to style memory: {len(scores)} videos; avg strict P/R {avg[0]:.0f}%/{avg[1]:.0f}% loose {avg[2]:.0f}%/{avg[3]:.0f}%")
