"""Document observed behavior; confidence here is evidence strength, not accuracy."""
import soundpilot as s

definitions={
 'MMMMMM.mp3':('approval','high','Genuine agreement, liking, accepting or choosing an option. Anchor to the approving word/choice, not to a generic oh or the reveal alone.',
   "'that might be fire', 'that is fire', 'I am taking the castle', 'I could do the nails'"),
 'fahhhh.mp3':('comic_line','high','A funny line, roast, absurd consequence or comic dismissal. Not a default for every no, mistake, or surprised face.',
   "'just eat the floor', 'how are you eating glass', 'you are cooked', 'how are you gonna eat it'"),
 'fahhhhhhhhhhhhhh.mp3':('comic_line','medium','Longer FAH variant for a stronger/longer comic disgust line; only one observed use.',
   "'it is not edible, dog, that is disgusting'"),
 'error_CDOxCYm.mp3':('confusion_or_rejection','high','A short what/no/never-mind realization, inconsistency or rejection beat. Separate the initial confusion from later approval in the same caption.',
   "'oh heck nah', 'I mean nah', 'oh no never mind', 'what the'"),
 'vine-boom (20).mp3':('impact_or_emphasis','high','Punchy emphasis on a surprising reveal, amount, key word, or emphatic decision; can be positive or negative. Do not put it on every cut.',
   "'$20 million', '$1', 'five', 'really', 'yo I am doing that'"),
 'ewww.mp3':('disgust','high','Actual disgust, eww, dirty/gross substance, or revulsion. Distinguish it from ordinary disagreement.',
   "'eww', 'is that poop', gross clam / cat-hairball / leaking-bed reactions"),
 'sudden-suspense-sound-effect.mp3':('unexpected_or_tense','medium','A tense or unsettling surprise/transition into a shocking option. Often leads the spoken reaction; not every oh-wait rethink.',
   'A 1825 potato-chip reveal, rotten-fish bed, fire-alarm shock.'),
 'awkward-moment.mp3':('dry_or_awkward','medium','Deadpan, awkward pause, flat observation or skeptical setup. Do not replace a clear positive acceptance with this.',
   "'I mean it is normal', 'what if it is a rock', flat 'that is what I am saying'"),
 'among-us-role-reveal-sound.mp3':('dubious_or_ironic','medium','Dubious, unsettling, suspicious or ironic context. Not automatic cheating = Among Us. Positive-looking words can be sarcastic in context.',
   "chalk as food, cat litter, crocodile Pickles, ironic 'it is the thought that counts' after a $1 inheritance"),
 'undertakers-bell_2UwFCIe.mp3':('doom_or_danger','medium','A bad/dangerous/fatal-feeling option or dramatic doom reaction; inferred from three examples.',
   'Eating glass, chalk/unsafe snacks, coughing up cat hairballs.'),
 'anime-wow-sound-effect.mp3':('visual_admiration','medium','Impressive visual reveal: mansion or rare Pokemon card. This is a reveal cue, distinct from MMMMMM on spoken approval.',
   'Mansion at 8.77s and rare-card reaction at 58.33s in Timeline 11.'),
 'heavenly-music-gaming-sound-effect-hd-mp3cut.mp3':('exceptional_good_reveal','low','A very desirable reveal after bad options; one example. Do not generalize all agreement to heavenly music.',
   'Chocolate caramel egg after chalk in Timeline 06.'),
 'Creepy Sound Effect.mp3':('unsettling','low','Continued unsettling reaction following suspense. Only one example, exact interpretation remains tentative.',
   'Timeline 06 at 44.97s after the suspense beat.'),
 'movie_1.mp3':('dramatic_setup','medium','Short dramatic setup/opening or a scene reset. One use is mid-video, so this is not a mandatory intro sound.',
   'Timeline 06 opening, Timeline 09 opening, bird-feather-bed reset at 41.40s in Timeline 08.'),
 'mac-quack.mp3':('cartoon_beat','low','One short cartoon beat before a clam-shell realization. No evidence to use it for every bro.',
   'Timeline 06 at 75.40s.'),
 'patrick-star-yeah.mp3':('specific_positive_reaction','low','One specific positive/comic reaction. Not the main approval sound.',
   'Timeline 09 at 18.43s.'),
 'ooooo.mp3':('anticipation','low','One anticipatory oh/lets-see beat. Avoid treating this single example as a universal reveal rule.',
   'Timeline 08 at 5.73s.'),
}

audit=s.read_json(s.OUTPUTS/'style_audit'/'reference_events.json')
rules=[]
for group in audit['groups']:
    function,strength,rule,evidence=definitions[group['sound']]
    rules.append({'sound':group['sound'],'function':function,'evidence_strength':strength,'count':group['count'],
        'rule':rule,'examples':evidence,'median_volume':group['median_volume'],'median_duration':group['median_duration'],
        'references':[{'timeline':e['timeline'],'start':e['start'],'caption':e['captions']} for e in group['events']]})
profile={'version':2,'source':'Four manual 0928 timelines plus explicit user corrections',
    'authoritative_user_rules':{'approval':['MMMMMM.mp3'],'comic_line':['fahhhh.mp3','fahhhhhhhhhhhhhh.mp3']},
    'preferred_sounds':[r['sound'] for r in rules],
    'rules':rules,
    'timing_policy':['Identify the particular word/reaction beat, not the whole caption label.',
        'Observed approval alignment: nice at 11.61s -> MMMMMM at 11.67s; castle at 36.60s -> 36.63s; fire at 35.30s -> 35.43s. These illustrate word alignment, not a universal delay.',
        'A caption can contain confusion followed by approval; select different cues at their own times.',
        'Use reaction dialogue to choose approval/comedy cues. Use the second video to establish reveal/danger/irony context.',
        'Do not automatically sound every caption, oh, bro or scene cut.',
        'If event function is ambiguous, flag it for review rather than inventing a generic sound.'],
    'avoid_generic_substitutes':['correct.mp3','ding-sound-effect_2.mp3','check-mark_oPG7Xo5.mp3'],
    'generic_substitute_policy':'Do not substitute these for the users approval MMMMMM rule; they have no placement examples in the four references.',
    'validation_policy':'80% is the requested target, not an achieved result. Evaluate future predictions against the users manual corrected edit; report sound choice, onset timing and omissions separately.',
    'test1_policy':'User is manually editing test 1. Read and compare when the user says it is saved; do not modify it.'}
s.write_json(s.DATA/'style_profile.json',profile)
out=s.OUTPUTS/'style_audit'
s.write_json(out/'STYLE_PROFILE.json',profile)
lines=['# Your 0928 sound style','', '**69 placements, 17 sound files, four timelines.** Evidence strength describes how many consistent examples support a rule; it is not an accuracy score.','',
    'The explicit user rules are: genuine approval → MMMMMM; funny line/roast → FAH.','',
    '| Sound | Function | Examples | Evidence |','|---|---|---:|---|']
for rule in rules:lines.append(f'| {rule["sound"]} | {rule["function"]} | {rule["count"]} | {rule["evidence_strength"]} |')
for rule in rules:
    lines.extend(['',f'## {rule["sound"]}',rule['rule'],'',rule['examples'],'',f'Observed median volume: {rule["median_volume"]}. Observed median duration: {rule["median_duration"]} seconds. These are references, not forced values.'])
lines.extend(['','## Timing distinctions',*['- '+x for x in profile['timing_policy']],'',
    '## What went wrong in the earlier test 1',
    '- Approval was replaced with correct/check/ding instead of the users MMMMMM convention.',
    '- A generic cartoon quack was placed on bro despite only one unrelated reference example.',
    '- Choosing test answers was treated as an automatic Among Us cue instead of checking whether the speaker was approving, joking or being ironic.',
    '- Entire caption/scene labels were used instead of the exact reaction word and its timing.',
    '',profile['validation_policy'],'',profile['test1_policy']])
(out/'LEARNED_STYLE.md').write_text('\n'.join(lines),encoding='utf-8')
print('STYLE_PROFILE_READY',len(rules),'rules; test 1 untouched')
