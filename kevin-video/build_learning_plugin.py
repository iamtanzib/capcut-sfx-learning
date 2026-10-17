"""Package the reusable engine; never writes a CapCut project."""
import json, shutil
import argparse
from pathlib import Path

BASE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--engine-only',action='store_true');args=parser.parse_args()
ROOT=BASE/'plugins'/'capcut-sfx-learning'
for name in ('engine','seed','skills/capcut-sfx-learning/references','.codex-plugin','tests'):
    (ROOT/name).mkdir(parents=True,exist_ok=True)
for name in ('soundpilot.py','context_pipeline.py'):
    source=(BASE/name).read_text(encoding='utf-8')
    if name=='soundpilot.py':
        source=source.replace("BASE = Path(__file__).resolve().parent", "BASE = Path(os.environ['SOUNDPILOT_STATE']).resolve()")
        source=source.replace("settings = Path(cfg['sidebar_settings'])", "settings = Path(cfg.get('sidebar_settings') or BASE/'no-sidebar-settings')")
        source=source.replace("combinations = {m.get('combination_id'): m for m in materials.get('drafts', [])}", "combinations = {m.get('combination_id'): m for m in materials.get('drafts', [])}\n    combinations_by_id = {m.get('id'): m for m in materials.get('drafts', [])}")
        source=source.replace("nested = combinations.get(combination_id)", "linked = [combinations_by_id[r] for r in seg.get('extra_material_refs', []) if r in combinations_by_id]\n            if len(linked)>1: raise ValueError('Ambiguous compound draft references; do not treat them as deleted SFX.')\n            nested = linked[0] if linked else combinations.get(combination_id)")
        source=source.replace("'compound': list(ancestry),", "'compound': list(ancestry), 'compound_gain':gain, 'leaf_volume':float(seg.get('volume',1)),")
        source=source.replace("not 0<=e['volume']<=1", "not 0<=e['volume']<=4")
        source=source.replace("e['sound'] not in {'fahhhh.mp3','fahhhhhhhhhhhhhh.mp3'}", "e['sound'] not in set(profile.get('authoritative_user_rules',{}).get('comic_line',['fahhhh.mp3','fahhhhhhhhhhhhhh.mp3']))")
    else:
        source=source.replace("str(s.BASE/'models'/'speech')", "str(Path(s.config().get('model_root',s.BASE/'models'))/'speech')")
        source=source.replace("key=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:20]", "cache_inputs={k:v for k,v in inputs.items() if k!='captions'}\n    cache_inputs.update(schema=3,proxy_width=s.config()['scene_proxy_width'],scene_decode=s.config().get('scene_decode','keyframes'))\n    key=hashlib.sha256(json.dumps(cache_inputs,sort_keys=True).encode()).hexdigest()[:20]")
        source=source.replace("'-v','error','-threads','2'", "'-nostdin','-v','error','-threads','2'")
        source=source.replace('capture_output=True,creationflags=s.CREATE_NO_WINDOW', 'stdin=subprocess.DEVNULL,capture_output=True,creationflags=s.CREATE_NO_WINDOW')
    (ROOT/'engine'/name).write_text(source,encoding='utf-8')
if args.engine_only:
    print('Engine updated; seed/user memory preserved.');raise SystemExit(0)
profile=json.loads((BASE/'data/style_profile.json').read_text(encoding='utf-8-sig'))
# Remove local filesystem and incidental latest-reference state, retain style decisions.
profile.pop('latest_revised_reference',None)
(ROOT/'seed/style_profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8')
examples=json.loads((BASE/'data/examples.json').read_text(encoding='utf-8-sig'))
import soundpilot as original
signatures={}
for ref in original.reference_sources():
    try:_,draft,_=original.load_timeline(original.project_path(ref['project']),ref['timeline'])
    except ValueError:continue # Preserve existing curated examples even if user deleted an old reference tab.
    import hashlib
    signatures[(ref['project'],ref['timeline'])]=hashlib.sha256(json.dumps(original.video_timing_signature(draft),sort_keys=True,ensure_ascii=False).encode()).hexdigest()
for e in examples:
    e['path']='';e['material']['path']=''
    e.pop('source_file',None)
    e['video_signature']=signatures.get((e['project'],e['timeline']))
(ROOT/'seed/examples.json').write_text(json.dumps(examples,ensure_ascii=False,indent=2),encoding='utf-8')
cfg=json.loads((BASE/'config.json').read_text(encoding='utf-8-sig'))
portable={k:cfg[k] for k in ('model','threads','minimum_gap','speech_model','speech_threads','scene_proxy_width','scene_decode','maximum_keyframes')}
portable.update(draft_root='',library='',sidebar_settings='',reference_project='',reference_timelines=[],additional_reference_sources=[])
(ROOT/'seed/config.json').write_text(json.dumps(portable,indent=2),encoding='utf-8')
req=(BASE/'requirements.txt').read_text(encoding='utf-8')+'\nmcp==1.29.0\ntiktoken==0.12.0\n'
(ROOT/'requirements.txt').write_text(req,encoding='utf-8')
print(ROOT)
