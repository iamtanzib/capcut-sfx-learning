"""Export curated learned memory, never media/project files or credentials."""
import sys,copy,json
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE/'plugins/capcut-sfx-learning';sys.path.insert(0,str(ROOT))
import service as a
with a.lock('state'):
    profile=copy.deepcopy(a.s.read_json(a.s.DATA/'style_profile.json'));examples=copy.deepcopy(a.s.read_json(a.s.DATA/'examples.json'))
profile['source']='Four manual 0928 references and human-reviewed test/day timelines, including Day 7.3–7.6 and Day 1.3–1.6 timing, sound-selection and final-level corrections.'
for reference in profile.get('dialogue_level_references',[]):
    for role in reference.get('roles',[]):
        for span in role.get('gain_spans',[]):span['path']=Path(span['path']).name
for example in examples:
    example['path']='';example['material']['path']=''
    example.pop('source_file',None)
a.s.write_json(ROOT/'seed/style_profile.json',profile);a.s.write_json(ROOT/'seed/examples.json',examples)
print(json.dumps({'seed_style_version':profile['version'],'examples':len(examples),'media_included':False}))
