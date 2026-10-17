"""Add the user's new manual reference, keeping the frozen failed prediction."""
import hashlib
import soundpilot as s

out=s.OUTPUTS/'srijon_comparison'
comparison=s.read_json(out/'comparison.json')
project=s.project_path('test 1');_,manual,path=s.load_timeline(project,'Srijon version')
if hashlib.sha256(path.read_bytes()).hexdigest()!=comparison['source_sha256']:
    raise ValueError('Manual reference changed since comparison. Re-run comparison first.')
profile=s.read_json(s.DATA/'style_profile.json')
profile['version']=3
profile['new_manual_reference']={'project':'test 1','timeline':'Srijon version','placements':12,'fah_placements':0,
    'sha256':comparison['source_sha256'],'frozen_previous_precision':comparison['precision']}
profile['case_corrections']=[
    {'cue':'okay','time':2.0,'sound':'awkward-moment.mp3','function':'neutral_acknowledgment'},
    {'cue':'bro / lets see, before the option list','time':5.5,'sound':'movie_1.mp3','function':'dramatic_setup'},
    {'cue':'oh heck yeah, fast-food excitement','time':9.133,'sound':'ooooo.mp3','function':'excited_positive_reaction'},
    {'cue':'give me some wings','time':15.767,'sound':'MMMMMM.mp3','function':'approval'},
    {'cue':'oh wait, test-answer reveal','time':17.167,'sound':'vine-boom (20).mp3','function':'impact_or_emphasis'},
    {'cue':'I failed everything, I will do that','time':21.233,'sound':'MMMMMM.mp3','function':'approval'},
    {'cue':'ooh what the, that is not even real','time':27.0,'sound':'sudden-suspense-sound-effect.mp3','function':'unexpected_or_tense'},
    {'cue':'breakfast','time':32.867,'sound':'vine-boom (20).mp3','function':'keyword_emphasis'},
    {'cue':'breakfast / sleep-in / free sequence','time':35.167,'sound':'among-us-role-reveal-sound.mp3','function':'dubious_or_ironic','interpretation':'Tentative contextual interpretation; not a keyword-only rule.'},
    {'cue':'I always lose my pencils','time':46.9,'sound':'awkward-moment.mp3','function':'dry_self_disclosure'},
    {'cue':'that is perfect','time':48.233,'sound':'MMMMMM.mp3','function':'approval'},
    {'cue':'nobody gets ice cream','time':53.267,'sound':'error_CDOxCYm.mp3','function':'rejection'},
]
profile['additional_timing_and_selection_rules']=[
    'Neutral okay is not genuine approval by itself.',
    'Positive excitement and accepting an option are distinct: ooooo vs MMMMMM in the new manual example.',
    'Read the complete intent: failed everything + I will do that is acceptance, not a failed-keyword joke detector.',
    'No FAH quota. This entire 55.7s manual video has zero FAH placements.',
    'Recognizing an option (breakfast) is not the same as approving it; a boom may emphasize the noun.',
    'Do not add a sound for every positive/negative utterance. The user selected 12 moments, leaving other lines without a cue.',
    'Caption positions can drift independently of the video/audio. Prefer validated speech-word alignment for learning.'
]
for rule in profile['rules']:
    old_count=rule['count'];additional=comparison['counts'].get(rule['sound'],0)
    rule['count_original_four']=old_count;rule['count']=old_count+additional
    if rule['sound']=='MMMMMM.mp3':
        rule['rule']='Genuine acceptance, agreement or choosing an option. Neutral okay and excited wow/oh-heck-yeah are not automatically approval cues. Read the completed intent and use the approving phrase timing.'
    elif rule['sound']=='fahhhh.mp3':
        rule['rule']='A genuinely comic delivery, roast or absurd punchline, not any word like failed/broke/not-real or ordinary rejection. The new manual video contains no FAH despite such words.'
    elif rule['sound']=='ooooo.mp3':
        rule['rule']='Anticipation or an excited positive reaction. Fast-food oh-heck-yeah uses this sound; choosing wings later uses MMMMMM.'
        rule['evidence_strength']='medium'
profile['test1_policy']='Srijon version is the protected manual ground truth. Do not change it. Use a genuinely new video for the next accuracy test.'
s.write_json(s.DATA/'style_profile.json',profile)
s.write_json(out/'STYLE_PROFILE_V3.json',profile)
trained=s.Planner().train()
s.write_json(out/'learning_summary.json',{'examples':trained['examples'],'references':trained['summary'],
    'manual_unchanged':hashlib.sha256(path.read_bytes()).hexdigest()==comparison['source_sha256'],
    'accuracy_target':.8,'target_achieved':False,'notes':'This reference was added after measuring the old prediction; no retrained same-video result is claimed as new-video accuracy.'})
print('LEARNED',trained['examples'],'placements; manual timeline unchanged')
