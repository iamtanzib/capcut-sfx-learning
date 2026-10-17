"""Apply the user's latest manual correction to the active reference profile."""
import hashlib
import soundpilot as s

project=s.project_path('test 1');_,draft,path=s.load_timeline(project,'Srijon version')
sounds=s.read_json(s.DATA/'sound_catalog.json');events=list(s.flatten_sfx(draft,sounds,project))
confirmed=next(e for e in events if e['sound']=='fahhhh.mp3' and 19<e['start']<22)
profile=s.read_json(s.DATA/'style_profile.json');profile['version']=4
profile['new_manual_reference'].update({'placements':len(events),'fah_placements':sum(e['sound'].startswith('fah') for e in events),
    'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
profile['latest_user_correction']='User replaced the failed-everything approval cue with FAHH around 20.60s. This latest manual choice supersedes the previous no-FAH observation.'
for case in profile['case_corrections']:
    if case['cue']=='I failed everything, I will do that':
        case.update({'time':round(confirmed['start'],3),'sound':'fahhhh.mp3','function':'comic_line','source':'Explicit latest user correction'})
profile['additional_timing_and_selection_rules']=[rule for rule in profile['additional_timing_and_selection_rules'] if 'failed everything' not in rule.lower() and 'zero FAH' not in rule]
profile['additional_timing_and_selection_rules'] += ['A funny confession can use FAHH even when followed by acceptance. The failed-everything example is now confirmed FAHH by the user.',
    'There is no fixed FAHH quota: use a funny/roast beat when supported by delivery or a learned manual example.']
for rule in profile['rules']:
    if rule['sound']=='fahhhh.mp3':
        rule['rule']='Funny confession, comic delivery, roast or absurd punchline. Latest confirmed example: I failed everything -> FAHH at 20.60s. Do not use it on every negative word or force a quota.'
    if rule['sound']=='MMMMMM.mp3':
        rule['rule']='Genuine agreement, liking, or accepting an option. Neutral okay/excited wow differ. A funny confession can take FAHH instead, even if it ends with acceptance; the user corrected failed-everything to FAHH.'
s.write_json(s.DATA/'style_profile.json',profile)
out=s.OUTPUTS/'srijon_comparison';s.write_json(out/'STYLE_PROFILE_V4.json',profile);s.write_json(out/'manual_snapshot_v4.json',draft)
trained=s.Planner().train()
for rule in profile['rules']:
    rule['count']=sum(e['sound']==rule['sound'] for e in s.read_json(s.DATA/'examples.json'))
s.write_json(s.DATA/'style_profile.json',profile);s.write_json(out/'STYLE_PROFILE_V4.json',profile)
print('LATEST_CORRECTION',round(confirmed['start'],3),confirmed['sound'],'reference placements',trained['examples'])
