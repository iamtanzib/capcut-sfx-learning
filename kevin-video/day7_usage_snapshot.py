"""Actual running-turn usage snapshot; no exact per-video attribution in a shared batch."""
import json,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
SOURCE=Path(r'C:\Users\srijon\.codex\sessions\2026\10\08\rollout-2026-10-08T15-09-15-01a11ac6-249a-7191-a4c7-de4c98232a6a.jsonl')
turn=None;target=None;last_total=None;calls={};models={};batch_started_at=None
for line in SOURCE.open(encoding='utf-8'):
    r=json.loads(line);p=r.get('payload',{})
    if r['type']=='turn_context':turn=p['turn_id'];models[turn]=p.get('model')
    if r['type']=='event_msg' and p.get('type')=='task_started':turn=p.get('turn_id')
    if r['type']=='response_item' and p.get('role')=='user':
        text=' '.join(c.get('text','') for c in p.get('content',[]))
        if target is None and '7.3-1.6' in text and '4ta' in text:target=turn;batch_started_at=r['timestamp']
    if r['type']=='event_msg' and p.get('type')=='token_count':
        info=p.get('info') or {};total=info.get('total_token_usage');last=info.get('last_token_usage')
        if last and total and total!=last_total:calls.setdefault(turn,[]).append({'timestamp':r['timestamp'],**last})
        if total:last_total=total
if not target:raise ValueError('This batch turn not found in local usage records.')
rows=sorted([row for tid,group in calls.items() for row in group if row['timestamp']>=batch_started_at],key=lambda row:row['timestamp'])
usage={k:sum(r.get(k,0) for r in rows) for k in ('input_tokens','cached_input_tokens','cache_write_input_tokens','output_tokens','reasoning_output_tokens','total_tokens')}
cost=None
if models.get(target)=='gpt-6.1-sol':
    cost=0
    for r in rows:
        cached=r.get('cached_input_tokens',0);written=r.get('cache_write_input_tokens',0);uncached=r['input_tokens']-cached-written
        long=r['input_tokens']>272000;cost+=((uncached*2+cached*.1+written*2.5)*(2 if long else 1)+r['output_tokens']*10*(1.5 if long else 1))/1e6
report={'scope':'Day 7.3–7.6 four-video batch, log-recorded running snapshot across continuation turns since the request; only through the displayed as-of timestamp. Includes troubleshooting/alignment/plugin reliability fix; no exact per-video attribution.',
    'turn_id':target,'model':models.get(target),'as_of_utc':rows[-1]['timestamp'] if rows else None,'usage':usage,'model_calls':len(rows),
    'standard_api_equivalent_usd':round(cost,4) if cost is not None else None,'actual_separate_inference_api_bill_usd':0,
    'billing_note':'ChatGPT Plus included usage, not an API invoice. Standard API equivalent excludes tool/regional/processing-tier fees and final response. A quarter of batch cost is only an allocation, not an exact per-video meter.',
    'pricing_source':'https://developers.openai.com/api/docs/models/gpt-6.1-sol'}
out=Path('outputs/day7-batch');(out/'USAGE_SNAPSHOT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
