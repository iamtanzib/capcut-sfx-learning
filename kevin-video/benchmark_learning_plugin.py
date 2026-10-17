"""Five real read-only contexts and exact information-preservation benchmark."""
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
import soundpilot as original
import context_pipeline as context
BASE=Path(__file__).resolve().parent;ROOT=BASE/'plugins/capcut-sfx-learning';STATE=Path(os.environ['LOCALAPPDATA'])/'SoundPilotLearning'
targets=[{'project':'0928','timeline':f'Timeline {n}'} for n in ('06','09','11','08')]+[{'project':'test 1','timeline':'test 3'}]
paths=[p for t in targets for p in original.project_path(t['project']).rglob('*.json')]
before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in set(paths)}
if not (STATE/'memory.json').exists():shutil.copyfile(ROOT/'seed/examples.json',STATE/'data/examples.json')
for t in targets:
    project=original.project_path(t['project']);_,draft,_=original.load_timeline(project,t['timeline']);_,key=context.context_inputs(project,draft)
    src=original.DATA/'context'/key
    if src.exists():shutil.copytree(src,STATE/'data/context'/key,dirs_exist_ok=True)
def invoke(tool,params):
    result=subprocess.run([sys.executable,str(ROOT/'cli.py'),tool,'--json',json.dumps(params)],capture_output=True,text=True,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stderr)
    return json.loads(result.stdout)
begin=time.perf_counter();batch=invoke('prepare_batch',{'targets':targets,'workers':2})
(BASE/'outputs/plugin-benchmark').mkdir(exist_ok=True)
(BASE/'outputs/plugin-benchmark/batch.json').write_text(json.dumps(batch,indent=2),encoding='utf-8')
print('BATCH '+json.dumps(batch),flush=True)
while True:
    report=invoke('batch_status',{'batch_id':batch['batch_id']})
    states=[r['status'] for r in report['jobs']]
    if all(x in ('ready','failed') for x in states):break
    print('STATUS '+','.join(states),flush=True);time.sleep(8)
if 'failed' in states:raise RuntimeError(str(report))
sys.path.insert(0,str(ROOT));import service as api
import tiktoken
enc=tiktoken.get_encoding('o200k_base')
rows=[]
for job in batch['jobs']:
    full=api.get_brief(job,True);compact=api.get_brief(job)
    assert api.unpack(compact)==full
    def tokens(value,indent=None):return len(enc.encode(json.dumps(value,ensure_ascii=False,indent=indent,separators=None if indent else (',',':'))))
    row={'job_id':job,'project':full['project'],'timeline':full['timeline'],'full_pretty_tokens':tokens(full,2),'full_minified_tokens':tokens(full),'compact_minified_tokens':tokens(compact),'exact_roundtrip':True}
    row['saving_vs_pretty_pct']=round(100*(1-row['compact_minified_tokens']/row['full_pretty_tokens']),1)
    row['saving_vs_minified_pct']=round(100*(1-row['compact_minified_tokens']/row['full_minified_tokens']),1)
    rows.append(row)
after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in set(paths)}
assert before==after,'CapCut files changed during read-only benchmark.'
result={'rows':rows,'wall_seconds':round(time.perf_counter()-begin,2),'targets':5,'project_files_unchanged':before==after,
    'aggregate_pretty_tokens':sum(r['full_pretty_tokens'] for r in rows),'aggregate_full_minified_tokens':sum(r['full_minified_tokens'] for r in rows),'aggregate_compact_tokens':sum(r['compact_minified_tokens'] for r in rows),
    'token_note':'o200k_base payload estimate, not actual ChatGPT billing/total conversational usage. Compact text must be emitted minified; tool schemas, reasoning and context images add tokens.',
    'quality_note':'All captions, both speech streams, style rules and negative evidence exactly round-trip. This does not prove creative accuracy across models.'}
original.write_json(BASE/'outputs/plugin-benchmark/RESULT.json',result)
print(json.dumps(result,indent=2),flush=True)
