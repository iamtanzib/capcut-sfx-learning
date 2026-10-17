"""Read this chat's actual token records; do not treat API prices as Plus charges."""
import argparse
import json
from pathlib import Path
from datetime import datetime,timezone,timedelta
import soundpilot as s

SESSION=Path(r'C:\Users\srijon\.codex\sessions\2026\10\08\rollout-2026-10-08T15-09-15-01a11ac6-249a-7191-a4c7-de4c98232a6a.jsonl')
def report(folder='test2v2'):
    rows=[]
    for line in SESSION.read_text(encoding='utf-8').splitlines():
        try:rows.append(json.loads(line))
        except json.JSONDecodeError:pass
    requests=[];context=None
    for row in rows:
        if row['type']=='turn_context':context=row['payload']
        if row['type']=='response_item' and row['payload'].get('role')=='user':
            txt=''.join(c.get('text','') for c in row['payload'].get('content',[]))
            if 'test 2 timeline e new video' in txt:
                requests.append(('test2_initial',context['turn_id'],False))
            if 'test 2 ta copy kre new vbe' in txt:
                requests.append(('test2_palette_redesign',context['turn_id'],True))
            if 'test 3 ta koro' in txt.lower():
                requests.append(('test3_initial',context['turn_id'],True))
    records={}
    completed={row['payload'].get('turn_id') for row in rows if row['type']=='event_msg' and row['payload'].get('type') in ('task_complete','task_completed')}
    for row in rows:
        if row['type']=='token_usage_record':records[row['payload']['turn_id']]=(row['timestamp'],row['payload']['turn_token_usage'])
    results=[]
    for name,turn_id,partial in requests:
        stamp,usage=records[turn_id]
        item={'task':name,'model':'gpt-6.1-sol','turn_id':turn_id,'as_of_utc':stamp,
            'as_of_dhaka':datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(timezone(timedelta(hours=6))).isoformat(),
            'complete':not partial or turn_id in completed,'input_tokens':usage['input_tokens'],'cached_input_tokens':usage['cached_input_tokens'],
            'uncached_input_tokens':usage['input_tokens']-usage['cached_input_tokens'],'output_tokens':usage['output_tokens'],
            'reasoning_output_tokens':usage['reasoning_output_tokens'],'total_tokens':usage['total_tokens'],
            'billing_plan':'Plus','actual_per_video_usd':None,
            'money_policy':'No direct per-video USD charge is available from these records. Plus included usage must not be priced using API token rates.',
            'count_policy':'Input includes all repeated context across model calls. Cached input is a subset of input, and reasoning output is a subset of output; do not add either twice.'}
        results.append(item)
    out=s.OUTPUTS/folder
    if out.resolve().parent!=s.OUTPUTS.resolve():raise ValueError('Choose one output folder name.')
    out.mkdir(exist_ok=True)
    data={'source':'Local Codex token_usage_record entries for this chat only','tasks':results,
        'official_pricing_source':'https://learn.chatgpt.com/docs/pricing',
        'account_snapshot':{'plan':'plus','shared_weekly_used_percent':21,'per_video_limit_percent':None},
        'scope':'Initial test 2 turn includes analysis, code changes, file writes and verification. Palette-redesign count is a live partial snapshot until the turn finishes. Earlier setup/research and reference-learning turns are not included.'}
    s.write_json(out/'CHAT_TOKEN_USAGE.json',data)
    lines=['# ChatGPT/Codex token usage for test 2','',
        'Actual local usage records; account is Plus. These are not external API-call charges.','',
        '| Task | Uncached input | Cached input | Output incl. reasoning | Complete? |',
        '|---|---:|---:|---:|---|']
    for item in results:lines.append(f'| {item["task"]} | {item["uncached_input_tokens"]:,} | {item["cached_input_tokens"]:,} | {item["output_tokens"]:,} | {item["complete"]} |')
    lines.extend(['','Input totals repeatedly include chat history, instructions and tool context; this is not the size of the video transcript. Cached input is already included in total input. Reasoning tokens are already included in output.',
        '', 'The Plus plan includes usage. API token rates cannot determine the actual USD cost of an included task. The current account-wide weekly snapshot is 21% used; it is shared across chats and cannot be attributed to this one video.',
        '', 'For subscription allocation only: monthly subscription price divided by completed videos that month gives an average budget per video. That is an allocation, not a metered token bill.',
        '',data['scope'],'','[Official pricing](https://learn.chatgpt.com/docs/pricing)'])
    (out/'CHAT_TOKEN_USAGE.md').write_text('\n'.join(lines),encoding='utf-8')
    print([(x['task'],x['uncached_input_tokens'],x['cached_input_tokens'],x['output_tokens'],x['complete']) for x in results])
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--folder',default='test2v2');args=parser.parse_args();report(args.folder)
