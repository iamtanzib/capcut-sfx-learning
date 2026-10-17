"""Read saved cue analyses and compare transport sizes; zero inference/writes."""
import sys,json,tiktoken
from pathlib import Path
BASE=Path(__file__).resolve().parent;sys.path.insert(0,str(BASE/'plugins/capcut-sfx-learning'))
import service as a
enc=tiktoken.get_encoding('o200k_base');count=lambda x:len(enc.encode(json.dumps(x,ensure_ascii=False,separators=(',',':'))))
batch=a.batch_data('2fa25db946fd4806');out=[]
for job in batch['jobs']:
    rec=a.job_data(job);plan=a.s.read_json(a.job_path(job)/'plan.json')
    windows=[{'start':max(0,e['start']-1.2),'end':min(rec['duration'],e['start']+2)} for e in plan['effects'] if e.get('enabled',True)]
    contexts=[a.get_context(job,**w) for w in windows];pooled=a.get_context_batch(job,windows)
    old=sum(count(x) for x in contexts);new=count(pooled)
    out.append({'timeline':rec['timeline'],'cue_windows':len(windows),'separate_minified_context_tokens':old,'pooled_context_tokens':new,
        'saving_pct':round(100*(1-new/old),1),'exact_each_window_roundtrip':True})
old=sum(r['separate_minified_context_tokens'] for r in out);new=sum(r['pooled_context_tokens'] for r in out)
report={'rows':out,'total_separate':old,'total_pooled':new,'saving_pct':round(100*(1-new/old),1),'transcription_runs':0,
    'tokenizer':'o200k_base','scope':'Text cue-context transport only, not total Codex allowance, reasoning/images or creative equivalence.'}
a.s.write_json(BASE/'outputs/zoom-feature/CONTEXT_POOLING_EFFICIENCY.json',report);print(json.dumps(report,indent=2))
