"""Read this chat's token records and show only SFX production turn summaries."""
import json,re
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
SOURCE=Path(r'C:\Users\srijon\.codex\sessions\2026\10\08\rollout-2026-10-08T15-09-15-01a11ac6-249a-7191-a4c7-de4c98232a6a.jsonl')
turn=None;context=None;turns={};last_calls={}
for line in SOURCE.open(encoding='utf-8'):
    try:r=json.loads(line)
    except json.JSONDecodeError:continue
    p=r.get('payload',{});kind=r['type']
    if kind=='event_msg' and p.get('type')=='task_started':
        turn=p.get('turn_id');turns.setdefault(turn,{'turn_id':turn,'started':r['timestamp']})
    if kind=='turn_context':
        turn=p['turn_id'];context=p;turns.setdefault(turn,{'turn_id':turn,'started':r['timestamp']});turns[turn]['model']=p.get('model');turns[turn]['service_tier']=p.get('service_tier')
    if kind=='event_msg' and p.get('type')=='user_message' and turn:
        turns[turn]['message']=p.get('message','')
    if kind=='response_item' and p.get('role')=='user' and turn:
        txt='\n'.join(c.get('text','') for c in p.get('content',[]))
        if txt and not txt.startswith('<environment_context>'):turns[turn].setdefault('message',txt)
    if kind=='token_usage_record':
        tid=p['turn_id'];turns.setdefault(tid,{'turn_id':tid})
        turns[tid]['usage']=p['turn_token_usage'];turns[tid]['usage_at']=r['timestamp']
    if kind=='event_msg' and p.get('type')=='token_count':
        info=p.get('info') or {};call=info.get('last_token_usage') or {}
        if turn and call:
            # This is per-response input, unlike the sum of repeated input over a turn.
            last_calls[turn]=max(last_calls.get(turn,0),call.get('input_tokens',0))
    if kind=='event_msg' and p.get('type') in ('task_complete','task_completed'):
        tid=p.get('turn_id') or turn
        if tid:turns.setdefault(tid,{'turn_id':tid})['complete']=True
rows=[]
for tid,t in turns.items():
    text=t.get('message','');low=text.lower()
    if any(q in low for q in ('test 2 timeline e new video','test 2 ta copy kre','test 3 ta koro','test 4 e koro','test 1 project e new video','test 3`','test 4`','test 2`','পুরো app quit করেছি','capcut বন্ধ করেছি')):
        u=t.get('usage');message=re.sub(r'\s+',' ',text)
        t['message']=message[:700];t['max_single_call_input']=last_calls.get(tid)
        if u:
            uncached=u['input_tokens']-u['cached_input_tokens'];cached=u['cached_input_tokens'];output=u['output_tokens']
            # Explicit hypothetical standard API estimate, not a subscription bill.
            t['api_standard_lower_usd']=(uncached*2+cached*.1+output*10)/1_000_000
            t['api_standard_cache_write_upper_usd']=(uncached*2.5+cached*.1+output*10)/1_000_000
        rows.append(t)
out=Path('outputs/usage-audit');out.mkdir(exist_ok=True)
(out/'production_turns.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
for t in rows:print(json.dumps(t,ensure_ascii=False))
