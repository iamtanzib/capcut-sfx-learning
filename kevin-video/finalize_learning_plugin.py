"""Install instruction artifacts and package only portable source and curated style."""
import json,shutil,zipfile
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE/'plugins/capcut-sfx-learning';DIST=BASE/'outputs/plugin-release';DIST.mkdir(exist_ok=True)
version=json.loads((ROOT/'plugin.json').read_text(encoding='utf-8'))['version']
market=BASE/'.agents/plugins/marketplace.json';market.parent.mkdir(parents=True,exist_ok=True)
entry={'name':'capcut-sfx-learning','source':{'source':'local','path':'./plugins/capcut-sfx-learning'},'policy':{'installation':'AVAILABLE','authentication':'ON_INSTALL'},'category':'Productivity'}
listing=json.loads(market.read_text(encoding='utf-8')) if market.exists() else {'name':'srijon-sfx','plugins':[]}
listing['plugins']=[p for p in listing['plugins'] if p['name']!='capcut-sfx-learning']+[entry]
market.write_text(json.dumps(listing,indent=2),encoding='utf-8')
config={'mcpServers':{'capcut-sfx-learning':{'command':'powershell','args':['-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'launch.ps1')]}}}
(DIST/'claude-desktop-example.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
(ROOT/'claude-desktop-example.json').write_text(json.dumps({'mcpServers':{'capcut-sfx-learning':{'command':'powershell','args':['-NoProfile','-ExecutionPolicy','Bypass','-File','C:\\PATH\\capcut-sfx-learning\\launch.ps1']}}},indent=2),encoding='utf-8')
result=json.loads((BASE/'outputs/plugin-benchmark/RESULT.json').read_text(encoding='utf-8'))
(ROOT/'BENCHMARK.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
summary=f'''# Verified results

- 21 focused tests passed: five-target synthetic writes/rollback; stale sources/styles/manual edits protected; lossless briefs; mix headroom/fades; empty-path compound links and multiplicative gains; split-cue envelopes; source-time trims; latest manual gain tiers; above-unity FAH variant; explicit speaker balance; silent whole-mix attenuation blocked.
- Actual MCP stdio handshake, discovery of 13 tools, read-only project listing and minified memory response passed.
- Five real contexts completed read-only; project JSON SHA-256 hashes unchanged. Total elapsed: {result['wall_seconds']} seconds (mixed cache reuse/preprocessing on this PC, not an uncached speed benchmark).
- Payload estimate (`o200k_base`): ordinary formatted briefs {result['aggregate_pretty_tokens']:,}; minified ordinary briefs {result['aggregate_full_minified_tokens']:,}; compact separate briefs {result['aggregate_compact_tokens']:,}; compact shared batch {result['shared_batch_tokens']:,}.
- Shared batch saves {result['saving_vs_pretty_pct']}% vs formatted JSON and {result['saving_vs_full_minified_pct']}% vs minified JSON. Every field/stream/caption/rule/negative example round-trips exactly.
- These tests prove technical operation/information preservation, not creative accuracy or total ChatGPT/Claude token savings. No Claude/GPT creative comparison or ChatGPT web account connection was run. No real CapCut target was written by the verification.

Quality work: word/caption offset audit, exact source frame retrieval, appraisal/rare-evidence guards, explicit silence review, source/audio/style freshness checks and revision memory. Offline base.en is retained. Captions don't invalidate media-only extraction caches; changing source media or proxy configuration does. Audit unsupported composite/audio processing before writing.
'''
(ROOT/'VERIFIED.md').write_text(summary,encoding='utf-8');(DIST/'VERIFIED.md').write_text(summary,encoding='utf-8')
def archive(path,source,prefix):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(source.rglob('*')):
            if not p.is_file() or p.is_symlink() or any(part in ('.venv','__pycache__','models','node_modules','.git') for part in p.relative_to(source).parts):continue
            if p.suffix in ('.pyc','.log'):continue
            z.write(p,str(Path(prefix)/p.relative_to(source)))
archive(DIST/f'capcut-sfx-learning-{version}.zip',ROOT,'capcut-sfx-learning')
archive(DIST/'capcut-sfx-learning-skill.zip',ROOT/'skills/capcut-sfx-learning','capcut-sfx-learning')
skill=Path.home()/'.claude/skills/capcut-sfx-learning'
if skill.exists():
    # Only update our own prior installation, never an unrelated skill with same name.
    marker=skill/'.soundpilot-owned'
    if not marker.exists():raise ValueError('Existing Claude skill was not created by this installer; preserved.')
shutil.copytree(ROOT/'skills/capcut-sfx-learning',skill,dirs_exist_ok=True);(skill/'.soundpilot-owned').write_text('capcut-sfx-learning '+version,encoding='utf-8')
print(json.dumps({'plugin_zip':str(DIST/f'capcut-sfx-learning-{version}.zip'),'skill_zip':str(DIST/'capcut-sfx-learning-skill.zip'),'claude_skill':str(skill),'bytes':(DIST/f'capcut-sfx-learning-{version}.zip').stat().st_size},indent=2))
