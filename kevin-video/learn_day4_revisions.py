"""Learn reviewed saved Day 4 truth with the installed envelope fix."""
import sys, json, copy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PLUGIN=Path(r'C:\Users\srijon\.codex\plugins\cache\srijon-sfx\capcut-sfx-learning\0.1.15')
sys.path.insert(0,str(PLUGIN))
import service as api, zoom, hooks

comparison=api.s.read_json(ROOT/'outputs/day4-revision/BEFORE_LEARNING_CORRECTED.json')
def rule(text,evidence):return {'rule':text,'evidence':evidence,'scope':'scene_only','authority':'scene_inference'}
common=rule('These saved Day4 zooms and hook wording are unchanged generated observations, not new manual timing corrections or proof of approval of every original artistic choice.',
            'All 28 zoom intervals/scales and all three hook texts/highlights match the frozen installed plans. Earlier explicit longer-reaction-hold preference remains active.')
rules={
'Day 4.1':[
 rule('The president intro has a selected surprised I-did impact; list-sting restraint should not erase this particular opening reaction.',
      'User added vine boom 1.666666s; actor I did and narrator accidentally became president are the mapped both-stream context.'),
 rule('The tuition finally response takes awkward in this scene, replacing the inferred yeahoo celebration.',
      'Yeahoo 26.93s was replaced by awkward 27.1s, gain 0.376939. Positive topic/word meaning did not establish the chosen reaction treatment.'),
 rule('The free-mansion anime-wow is retained and moved later to the connected admiration/temptation reaction, not deleted.',
      'Same anime-wow 36.89s -> 37.8s (+0.91s), same gain 0.235983, duration 2.333333s; actor free mansion / plus / tempting and lower mansion footage reviewed.'),
 rule('Cash acceptance and its confirmation use later attacks here; do not assume every frozen ASR word start is an approved SFX onset.',
      'Easy MMM 11.23s -> 11.666666s; thats-a-bet yeahoo 15.96s -> 16.4s. These specific lags are not a global delay rule.'),
 rule('The thoughtful social-benefit line has a selected quiet suspense and the final first-option choice has a low dramatic bell in this scene.',
      'Added suspense 30.533333s gain 0.166088 and Undertaker 52.4s for 3.6s gain 0.159731. Exact 52.4 frame is a smiling choice, so this is observed dramatic-choice punctuation, not invented literal danger.'),
 rule('Foreground emphasis is local to the social-benefit phrase and final choice, while the ordinary actor and narrator balance stays unchanged.',
      'Actor gains 2.182645 during 30.866666–33.133333s and 2.099104 during 52.5–54.1s; ordinary actor 0.794328 and narrator 0.595662 remain.'), common],
'Day 4.2':[
 rule('The isolated earlier waterfall oh lift is omitted, while the later repeated better appraisal has a dry awkward layer plus retained MMM.',
      'Ooooo 17.34s is absent. New awkward 22.566666s gain 0.407539; MMM 22.86s -> 23.6s, gain 0.186090. Do not generalize this deletion into muting all excited repeats.'),
 rule('The jet has separate impact and admiration layers, and the final secret-vehicle collection has anime admiration before the retained fire MMM.',
      'New boom 13.266666s gain 0.255141 plus retained anime 13.8s; new anime 54.6s gain 0.172698, duration 1.4s, before MMM 55.39s. Exact final frame shows the exceptional vehicle collection.'),
 rule('The frozen high-tech garage reveal has a heavenly bed here, independent of the later actor choosing the waterfall.',
      'New heavenly 36.866666s for 3.633334s gain 0.298247. Exact lower frame shows the icy secret door/garage reveal; both-stream narration describes high-tech snow vehicles and the secret frozen garage.'),
 rule('The too-scary ocean/submarine refusal uses a long dramatic Undertaker in this particular scene instead of the predicted short error.',
      'Error 45.98s replaced by Undertaker 45.433333s for 4.233333s gain 0.335292; actor too scary / not doing that and narrated submarine context reviewed.'),
 rule('This recording needs quieter selected assets and one stronger actor burst, not one multiplier on every sound or every voice clip.',
      'MMM -1.98dB, jet anime -2.47dB, huh -5.30dB, suspense -5.89dB, desert boom -4.62dB relative to installed gains. Actor desert what burst 50.033333–51.2s rises to 4.763938; its ordinary 0.782871 baseline and narrator 0.587071 remain.'),common],
'Day 4.3':[
 rule('The caught-again Monopoly intro has a selected reaction boom, rather than mandatory silence on all openings.',
      'New vine boom 1.6s gain 0.245375; mapped actor Again and narrator caught cheating in Monopoly. Not a cue simply on the cheating keyword.'),
 rule('The million-dollar debt Among cue is retained and moved later, not deleted or replaced.',
      'Among 20.7s -> 22.3s (+1.6s), duration 3.266666s, same gain 0.186718. Full scene contrasts real $1 million debt with $200 of Monopoly money and generational-debt refusal.'),
 rule('Comic toilet-costume bravado and actual acceptance can receive separate scene cues; the retained FAH does not erase the later MMM.',
      'FAH 27.9s retained; new MMM 29.266666s gain 0.186718 on repeated I-could-do-that; later dry no-you-wouldnt awkward moved 31.56s -> 31.8s.'),
 rule('The giant-fight suspense comes earlier and quieter, followed by a separate doom bell at the completed destruction/refusal beat.',
      'Suspense 41.75s -> 41.033333s, gain 0.121547 (-3.98dB). New Undertaker 46.533333s for 4.233333s gain 0.245375; exact lower frame shows raised giant fists and destroy subtitle.'),
 rule('The thats-not-a-punishment complaint has a selected mac-quack cartoon beat in this scene, rather than automatic silence.',
      'New mac-quack 55.6s for 1.2s gain 0.535567; actor unfair-punishment complaint, permanent game board and no-way-out narration reviewed.'),
 rule('The final crusher bell remains one attack/body event; the body is not a new low-gain bell attack.',
      'Logical bell 59.3s, 2.1s total, attack gain 0.362512 for 0.333333s and body 0.230113 for 1.766667s, source offset 0.333333. Frozen native envelope and saved new IDs verified.'),
 rule('The closing refusal foreground is boosted while its short error cue is quieter; preserve that local contrast instead of changing the whole recording.',
      'Actor 63.533333–64.333333s gain 2.099104 versus ordinary 0.794328; final error 63.566666s gain 0.194149 (-3.68dB), narrator 0.595662 unchanged.'),common]
}

before={r['path']:api.digest(r['path']) for r in comparison['reports']}
for r in comparison['reports']:
    assert before[r['path']]==r['manual_hash'],'Saved revision changed since review; compare the new saved state first.'
reports=[]
for r in comparison['reports']:
    result=api.learn_revision(r['job_id'],'test 1',r['timeline_id'],rules[r['timeline']])
    if result.get('already_learned'):result=api.s.read_json(result['report'])['report']
    reports.append(result)

# Resolve candidate associations only after the complete both-stream scene review.
reviews=[('Day 4.1',4,5,'reviewed_substitution'),('Day 4.1',6,8,'reviewed_same_sound_retime'),
         ('Day 4.2',7,9,'reviewed_substitution'),('Day 4.3',3,4,'reviewed_same_sound_retime')]
with api.lock('state'):
    bundle=api.s.read_json(api.STATE/'memory.json');profile=bundle['profile']
    for name,oi,mi,decision in reviews:
        original=next(r for r in comparison['reports'] if r['timeline']==name)
        learned=next(r for r in reports if r['job_id']==original['job_id'])
        old,manual=original['old'][oi],original['manual'][mi]
        f=next(f for f in profile['learned_feedback'] if f.get('reference')==learned['reference'] and f['sound']==old['sound'] and f['decision'] in ('omit_or_changed',decision))
        f.update(decision=decision,old_index=oi,manual_index=mi,old_start=old['start'],
                 review_note='Complete both-stream dialogue, captions, exact native asset, source continuity and relevant source frames reviewed. Scene-scoped observation; no global asset ban.')
        if decision=='reviewed_same_sound_retime':
            f.update(revised_start=manual['start'],delta=manual['start']-old['start'])
        else:
            f['replacements']=[{k:manual[k] for k in ('sound','start','duration','volume')}]
        history=api.STATE/'history'/(learned['reference']+'.json')
        h=api.s.read_json(history);h['report'].setdefault('reviewed_candidates',[])
        entry={'old_index':oi,'manual_index':mi,'decision':decision,'old_sound':old['sound'],'manual_sound':manual['sound'],
               'delta':manual['start']-old['start'],'both_stream_context':manual['both_stream_context']}
        if entry not in h['report']['reviewed_candidates']:h['report']['reviewed_candidates'].append(entry)
        api.s.write_json(history,h);learned.setdefault('reviewed_candidates',[]).append(entry)
    api.s.write_json(api.STATE/'memory.json',bundle)
    api.s.write_json(api.s.DATA/'style_profile.json',profile)

# Retain unchanged generated observations without labeling them new manual approval.
for r in comparison['reports']:
    for filename in ('zoom_style.json','hook_style.json'):
        lockname='zoom-style' if filename.startswith('zoom') else 'hook-style'
        with api.lock(lockname):
            value=api.s.read_json(api.s.DATA/filename)
            ref=next(x for x in value['references'] if x['project']=='test 1' and x['timeline_id']==r['timeline_id'])
            ref['scope']='Saved unchanged generated '+('zoom intervals/framing' if filename.startswith('zoom') else 'hook wording/layout/highlights')+'; not a new manual timing correction or an independent creative-quality approval.'
            api.s.write_json(api.s.DATA/filename,value)

assert before=={p:api.digest(p) for p in before},'Saved timelines changed during learning'
strict=sum(len(r['diff']['timing']['strict_matches']) for r in reports)
associated=sum(len(r['diff']['matches']) for r in reports)
old=sum(r['old_cues'] for r in reports);manual=sum(r['manual_cues'] for r in reports)
result={'plugin_version':'0.1.15','batch_id':comparison['batch_id'],'reports':reports,
        'versions':{n:api.s.read_json(api.s.DATA/n)['version'] for n in ('style_profile.json','zoom_style.json','hook_style.json')},
        'strict_150ms':{'matches':strict,'predictions':old,'manual':manual,'precision':strict/old,'recall':strict/manual},
        'loose_750ms':{'associations':associated,'precision':associated/old,'recall':associated/manual},
        'retimed_over_one_frame':sum(len(r['diff']['timing']['retimed_matches']) for r in reports),
        'reviewed_distant_retimes':2,'reviewed_substitutions':2,'project_files_unchanged':True,
        'native_pieces':sum(r['native_sfx_pieces'] for r in reports),'unchanged_zooms':28,'unchanged_hooks':3,
        'perceived_audio_review':'Unverified; saved manual choices/gains are authoritative, no auditory loudness score claimed.'}
out=ROOT/'outputs/day4-revision';api.s.write_json(out/'LEARNED.json',result)
print(json.dumps({k:v for k,v in result.items() if k!='reports'},ensure_ascii=False))
