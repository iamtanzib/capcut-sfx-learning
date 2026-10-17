"""Learn the explicit uncomfortable-cart rejection correction. Read only."""
import hashlib
import statistics
import soundpilot as s

p=s.project_path('test 1');_,draft,path=s.load_timeline(p,'test 4')
digest=hashlib.sha256(path.read_bytes()).hexdigest()
events=list(s.flatten_sfx(draft,s.read_json(s.DATA/'sound_catalog.json'),p))
event=next(e for e in events if 27<e['start']<30)
assert event['sound']=='error_CDOxCYm.mp3'
profile=s.read_json(s.DATA/'style_profile.json');profile['version']=8
profile['latest_revised_reference'].update(sha256=digest,placements=len(events))
profile['appraisal_policy']={
    'first_step':'Resolve what the speaker is evaluating and whether the completed meaning accepts or rejects it.',
    'negative_agreement':'Agreeing that the glass cart is not comfortable is a negative appraisal. Use the learned rejection cue, not MMMMMM.',
    'positive_qualified':'Not bad / I do not mind that can express positive acceptance; do not use a raw not-word filter.',
    'explicit_affirmation':'Exactly can be explicit affirmation, but do not infer it from any negative statement that happens to echo the narrator.'}
profile['shopping_cart_revision_examples'].append({'cue':'it does not look comfortable at all','sound':'error_CDOxCYm.mp3',
    'time':round(event['start'],3),'function':'negative_appraisal','replaces':'MMMMMM.mp3','source':'Explicit user correction'})
profile['negative_examples'].append({'sound':'MMMMMM.mp3','cue':'It does not [look comfortable] at all, glass cart',
    'decision':'use error','lesson':'Logical agreement with a negative appraisal is still rejection of the option; do not treat it as positive approval.'})
profile['additional_timing_and_selection_rules'].append('Resolve appraisal polarity before MMMMMM. The uncomfortable-glass-cart line was explicitly corrected from MMMMMM to error at 27.83s.')
for rule in profile['rules']:
    if rule['sound']=='MMMMMM.mp3':rule['rule']+=' Do not confuse negative appraisal with approval: agreeing that a glass cart does not look comfortable uses error. Resolve context/polarity first.'
    if rule['sound']=='error_CDOxCYm.mp3':rule['rule']+=' Includes agreement with a negative assessment of an option, such as it does not look comfortable at all.'
s.write_json(s.DATA/'style_profile.json',profile)
trained=s.Planner().train();examples=s.read_json(s.DATA/'examples.json')
for rule in profile['rules']:
    matching=[e for e in examples if e['sound']==rule['sound']]
    rule['count']=len(matching);rule['median_volume']=round(statistics.median(e['volume'] for e in matching),3)
s.write_json(s.DATA/'style_profile.json',profile)
out=s.OUTPUTS/'test4_revision';s.write_json(out/'NEGATIVE_AGREEMENT_CORRECTION.json',{
    'old_sound':'MMMMMM.mp3','current_user_sound':event['sound'],'current_onset':event['start'],'cue':'it does not look comfortable at all',
    'mistake':'Classified grammatical agreement rather than the negative evaluation of the cart.',
    'correct_rule':'Negative appraisal remains rejection even when it agrees with the narrator.',
    'source_sha256':digest,'profile_version':8})
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
print('CORRECTED_RULE',event['sound'],round(event['start'],3),'manual timeline unchanged')
