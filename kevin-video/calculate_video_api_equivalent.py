"""Counterfactual Standard API pricing, validated against real per-turn totals."""
import json,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
source=Path(r'C:\Users\srijon\.codex\sessions\2026\10\08\rollout-2026-10-08T15-09-15-01a11ac6-249a-7191-a4c7-de4c98232a6a.jsonl')
selected={'01a11aff-fa8e-7b01-a01a-131a3ca8234a':'test 1','01a11b2a-553b-71f3-bcb5-2c8e7211e002':'test 2','01a11cf6-1693-7a42-a98d-e8b62f8c76e3':'test 4'}
data={tid:{'video':name,'calls':[],'record':None} for tid,name in selected.items()};turn=None;last_total=None
for line in source.open(encoding='utf-8'):
    r=json.loads(line);p=r.get('payload',{})
    if r['type']=='turn_context':turn=p['turn_id']
    if r['type']=='event_msg' and p.get('type')=='task_started':turn=p.get('turn_id')
    if r['type']=='token_usage_record' and p['turn_id'] in data:data[p['turn_id']]['record']=p['turn_token_usage']
    if r['type']=='event_msg' and p.get('type')=='token_count':
        info=p.get('info') or {};total=info.get('total_token_usage');call=info.get('last_token_usage')
        if call and total and total!=last_total and turn in data:
            row=dict(call);row['long_context']=call['input_tokens']>272_000
            scale=2 if row['long_context'] else 1;out_scale=1.5 if row['long_context'] else 1
            cached=call['cached_input_tokens'];written=call.get('cache_write_input_tokens',0)
            uncached=call['input_tokens']-cached-written
            assert uncached>=0
            row['standard_api_equivalent_usd']=((uncached*2+cached*.1+written*2.5)*scale+call['output_tokens']*10*out_scale)/1_000_000
            data[turn]['calls'].append(row)
        if total:last_total=total
results=[]
for tid,item in data.items():
    record=item['record'];calls=item['calls']
    for key in ('input_tokens','cached_input_tokens','output_tokens','cache_write_input_tokens'):
        assert sum(c.get(key,0) for c in calls)==record.get(key,0),(item['video'],key)
    cached=record['cached_input_tokens']
    results.append({'video':item['video'],'model':'gpt-6.1-sol','turn_id':tid,'input_tokens':record['input_tokens'],
        'cached_input_tokens':cached,'uncached_input_tokens':record['input_tokens']-cached,'output_including_reasoning':record['output_tokens'],
        'calls':len(calls),'long_context_calls':sum(c['long_context'] for c in calls),'total_tokens':record['total_tokens'],
        'standard_api_equivalent_usd':round(sum(c['standard_api_equivalent_usd'] for c in calls),6),'call_totals_verified':True})
report={'actual_access':'ChatGPT Plus included usage; no separate API calls made by the local SFX workflow','actual_separate_api_bill_usd':0,
    'rates_usd_per_million':{'input':2,'cached_input':.1,'cache_write':2.5,'output':10},'long_context':'Each request >272K input: 2x input/cache rates, 1.5x output.',
    'pricing_source':'https://developers.openai.com/api/docs/models/gpt-6.1-sol','rows':results,
    'scope':'One original SFX production turn per video, including its analysis/code/verification/apply within that turn. Excludes earlier setup, later revision-learning and plugin development. Historical workflow, not a measured post-plugin per-video run.',
    'limits':'Counterfactual Standard text-token estimate, not the Plus invoice. Fast/Ultrafast/tools/regional fees would differ. Subscription allocation and actual OpenAI backend cost are not observable here.'}
out=Path('outputs/usage-audit');out.mkdir(exist_ok=True);(out/'API_EQUIVALENT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
lines=['# Actual usage and hypothetical API price','',report['scope'],'','| Video | Uncached input | Cached input | Output incl. reasoning | Standard API equivalent |','|---|---:|---:|---:|---:|']
for row in results:lines.append(f'| {row["video"]} | {row["uncached_input_tokens"]:,} | {row["cached_input_tokens"]:,} | {row["output_including_reasoning"]:,} | ${row["standard_api_equivalent_usd"]:.2f} |')
lines+=['','Actual separate API bill: $0; current account is Plus. No external inference API was invoked by the local SFX scripts.','',report['long_context'],report['limits'],'','[Official model pricing]('+report['pricing_source']+')']
(out/'API_EQUIVALENT.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(report,indent=2))
