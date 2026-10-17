"""Auditable artistic plan for four user-selected new timelines; no CapCut writes."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'plugins/capcut-sfx-learning'))
import service as a
BATCH='a1e16077faa34a5c'
S={'m':'MMMMMM.mp3','f':'fahhhh.mp3','a':'awkward-moment.mp3','e':'error_CDOxCYm.mp3','o':'ooooo.mp3','s':'sudden-suspense-sound-effect.mp3','u':'undertakers-bell_2UwFCIe.mp3','x':'ewww.mp3','c':'Creepy Sound Effect.mp3','q':'among-us-role-reveal-sound.mp3','v':'vine-boom (20).mp3'}
F={'m':'approval','f':'comic_line','a':'dry_or_awkward','e':'confusion_or_rejection','o':'mild_reaction_lift','s':'unexpected_or_tense','u':'doom_or_danger','x':'explicit_disgust','c':'unsettling','q':'dubious_or_ironic','v':'impact_or_emphasis'}
# Timing comes from actual speech words; captions only corroborate missing eww.
designs={
'074b0e05e31b4d87':[
 (9.94,'m',1.0,.22,'I wanna get school','He explicitly wants the school-ownership option; this is positive choice, not neutral okay.'),
 (15.97,'f',1.60,.32,'Yall would love me if I was a principal','The narrator cancels school; the reactor jokingly imagines becoming the students favorite principal.'),
 (18.06,'a',1.40,.48,'bro what the, reflection','Dry skeptical response to an independent reflection, distinct from his later explicit rejection.'),
 (20.97,'e',.95,.42,'heck nah, independent reflection','Clear rejection of the reflection acting independently; approval is not inferred from agreement.'),
 (23.80,'m',1.0,.22,'hey that would be nice, go to work for me','The work-for-me benefit changes his assessment to positive acceptance after earlier unease.'),
 (29.37,'m',1.0,.22,'Im doing that, teleporting bed','He chooses the bed that teleports to a vacation without getting up.'),
 (34.17,'e',.95,.42,'oh heck nah, talking dog','Expressed refusal of a talking dog; not an admiration or a neutral conversational oh.'),
 (39.74,'f',1.50,.30,'yo thats bad, your cooking is terrible','The dog directly roasts its owners cooking; the reactor covers his mouth and laughs at the insult.'),
 (47.43,'f',1.60,.32,'yeah youre cooked, gold phone','Comic consequence of turning the phone into gold and losing its use; cooked alone does not trigger a doom bell.'),
 (52.37,'o',1.10,.22,'whoa, pocket car appears','A genuine isolated reaction lift on the impossible pocket-car result, rather than reading an option name.'),
 (53.47,'m',1.0,.22,'Im taking that, anything out of a pocket','His next line explicitly accepts the pocket option; separate from the preceding reaction lift.')],
'c60986450a8c43ed':[
 (3.55,'a',1.35,.44,'what, a rumor must become true','Dry disbelief at the absurd condition, with no automatic opening sting.'),
 (15.77,'f',1.60,.32,'I already got that, feet smell so bad','Funny self-confession about already having smelly feet; the positive grammar is not approval.'),
 (16.15,'s',1.25,.23,'giant nest and eggs reveal','The scene cuts to a man inside an enormous birds nest; a tense surprise leads the reactors alarm.'),
 (20.02,'e',.95,.42,'oh heck nah, fight the mama bird','Specific rejection of the nest/bird consequence, following the reveal rather than treating it as approval.'),
 (26.60,'x',1.70,.155,'Ew, pickle-juice tears','Spoken Ew and the visible pickle tears establish disgust; finish before his qualified acceptance.'),
 (29.46,'m',1.0,.22,'that might not be bad, I dont cry','Completed meaning accepts the pickle-tears option because he does not cry. Not-bad is positive here.'),
 (34.56,'a',1.40,.46,'dog what, sneezing lays eggs','A deadpan reaction to the unnatural bodily condition, rather than inventing sexual innuendo.'),
 (40.48,'q',1.85,.24,'its free eggs though','Dry rationalization treats eggs laid by a person as free food. This grotesque positive spin resembles the learned chalk/floor-food irony, not genuine praise.'),
 (42.73,'e',.95,.40,'huh, spaghetti hair','A fresh confusion beat at edible spaghetti hair; no generic positive sound.'),
 (47.62,'f',1.60,.32,'yeah youre cooked, spaghetti haircut','Explicit comic roast about the absurd haircut/eaten-hair consequence.'),
 (50.28,'o',1.10,.22,'oh oh, garden-gnome army','Isolated expressive excitement at the gnome group, distinct from the later explicit good/army choice.'),
 (53.48,'m',1.0,.22,'thats good, I want an army','Clear acceptance of the garden-gnome army option. Earlier ambiguous words are not used as an approval anchor.')],
'd0060c04c6194b47':[
 (11.66,'a',1.40,.44,'I might mess it up if I read that','Dry hesitation about knowing his future; no sound is imposed on the ordinary list setup.'),
 (14.66,'u',2.10,.30,'book tells you when youre gonna die','Literal predicted death is revealed on die, then the reactor backs away with nah Im good. This has specific doom evidence.'),
 (24.99,'a',1.40,.44,'I dont know, portal might trap you','Uncertain deadpan response to the possibility of entering another world and never returning.'),
 (27.24,'o',1.10,.22,'oh, unlimited backpack','A distinct isolated oh lifts his discovery of the useful backpack, before an explicit choice.'),
 (29.27,'m',1.0,.22,'Im doing a backpack','He directly chooses the unlimited-resource backpack.'),
 (34.91,'s',1.25,.23,'future phone says dont go home tomorrow','A concrete whispered future warning supports tension; ordinary future-phone recognition is left quiet.'),
 (42.14,'x',1.90,.155,'eww bro what eww, human teeth','The captions retain spoken eww that base ASR misreads as it; human-teeth revulsion supports the first disgust cluster.'),
 (45.66,'x',1.70,.155,'eww bro, moving teeth','A second separate spoken disgust burst follows the revelation that the human teeth move.'),
 (50.29,'a',1.40,.46,'what the, miniature house','Initial deadpan confusion at the uncanny replica house, rather than an unsupported shock boom.'),
 (53.74,'c',2.40,.20,'who is that in your house, thats a scary movie','Exact frame shows an unknown figure in the lit miniature-house window; narrator alarm and explicit scary-movie reaction support a brief creepy bed.'),
 (63.38,'m',.60,.22,'Ill take the egg','He explicitly chooses the mysterious egg. The cue is shortened to the existing 64-second video boundary.')],
'9b2ee23ff259474c':[
 (12.94,'m',1.0,.22,'why did you get the best one, peppermint','Positive appraisal of normal peppermint toothpaste. Both timing passes place best around 12.94 despite late captions.'),
 (15.50,'f',1.50,.30,'she brushed her lips','A specific comic observation about brushing lips instead of teeth.'),
 (24.16,'f',1.60,.32,'I drink my toothpaste','Funny self-confession extends the orange-juice reaction; use the learned confession/FAH rule instead of automatic MMM.'),
 (28.08,'m',.95,.22,'thats not bad, charcoal','The short completed appraisal initially accepts charcoal. Its later reversal is handled separately.'),
 (31.86,'e',.95,.42,'she didnt brush her teeth, oh heck no','The appraisal switches to rejection of the brushing result; negative agreement must not use MMM.'),
 (38.00,'m',1.0,.22,'April might have got the best one','Genuine praise/acceptance of the pumpkin-pie option; no cue on merely reading pumpkin pie.'),
 (47.30,'m',1.0,.22,'May thats not bad at all','Qualified but clear acceptance of strawberry toothpaste, independently corroborated by short-window transcription.'),
 (51.88,'f',1.50,.32,'that has to be racist, giraffe/leaves joke','The reactor comically calls out the giraffe comparison. No suspicion/Among cue is inferred from the keyword.'),
 (62.54,'f',1.35,.30,'youre getting cavities, ice cream','Specific roast of brushing with sugary ice cream; no automatic doom bell on a negative word.'),
 (67.0,'u',3.30,.28,'hot sauce, mouth on fire, not surviving this','The exact frame shows hot sauce poured on a toothbrush; the narrator explicitly describes burning and not surviving a daily-use condition. Bell supports this consequence, not the word cooked.'),
 (72.52,'a',1.25,.44,'God bless you August','Dry sympathetic sign-off to the hot-sauce victim; this is not approval of their toothpaste.'),
 (80.14,'m',1.0,.22,'September got the best one','Positive approval of bubble-gum toothpaste; anchor the actual best word rather than the late caption.'),
 (84.55,'x',1.90,.155,'Ew yeah nah, mashed potatoes','Full speech pass hears Ew and the caption corroborates it. The second pass misses this short exclamation; keep the explicit disgust rule.'),
 (91.28,'e',.95,.42,'oh heck no, garlic is gonna stink','A clear refusal of the garlic-breath outcome, confirmed at 91.28 in the short-window pass.'),
 (99.02,'v',1.10,.25,'10000 dollars a tube, diamond toothpaste','Punch the actual extravagant price reveal rather than placing a boom on every what or month change.'),
 (100.64,'f',1.50,.30,'Im selling it bro Im selling it','A specific money/resale punchline after the expensive diamond-toothpaste reveal.')]
}

def effects(rows):
    result=[]
    for start,key,duration,volume,cue,reason in rows:
        e={'sound':S[key],'start':start,'duration':duration,'volume':volume,'source_start':0,'speed':1,'dialogue':cue,'function':F[key],
            'reason':reason,'confidence':'high','fade_in':.005,'fade_out':.10}
        if key=='m':e['evaluation_polarity']='positive'
        if key in ('u','c','q'):
            e['context_evidence']={'kind':'spoken_context' if key=='q' else 'visual_context','strength':'high','cue':cue,'why_this_sound':reason}
            e['fade_out']=.4
        if key=='x':e['fade_out']=.18
        if key=='x' and start==84.55:e['confidence']='medium'
        result.append(e)
    return result

out=ROOT/'outputs/day7-batch';out.mkdir(exist_ok=True)
summary=[]
for job,rows in designs.items():
    notes={'whole_video_reviewed':True,'silence_reviewed':True,'unresolved':[],
        'auditory_review':'Waveform/ASR/context and exact-frame checks completed; human/model playback listening is unverified in this text-only host.',
        'silence_decisions':['Neutral intros and reading ordinary option names left quiet.','No family quota, automatic cooked bell, or automatic praise sound.'],
        'timing_note':'Day 7.6 selected words rechecked using base.en beam5 on short raw-audio windows without VAD; captions preserved.' if job=='9b2ee23ff259474c' else 'Actual reaction words plus narration and inspected frames; captions corroborate missed eww.'}
    result=a.stage_plan(job,effects(rows),notes);a.s.write_json(out/(job+'-stage.json'),result);summary.append(result);print(json.dumps(result),flush=True)
a.s.write_json(out/'BATCH_DESIGN.json',{'batch_id':BATCH,'jobs':summary,'cues':sum(len(r) for r in designs.values()),'sounds':sorted({S[r[1]] for rows in designs.values() for r in rows})})
