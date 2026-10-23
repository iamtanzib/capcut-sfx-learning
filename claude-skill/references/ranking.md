# Ranking videos (video type `ranking_video`)

A ranking video interleaves a downloaded ranking compilation (PEPERANKER-style: baked title, rank list, its own SFX) with Kevin's reactions from one raw take. The tool cuts and places; the user adds CapCut transitions, music and captions.

Learned from 4 rendered references (`/Volumes/128 gb/Kevin/Example/Ranking*.mp4`, style in `~/SoundPilotLearning/data/ranking_style.json`, rules in `ranking.RULES`):
- Open on ranked item #1; strictly item -> Kevin's reaction to it -> next item; end on Kevin's reaction to the last item. No slate.
- Items: whole item from its first frame through the payoff/label reveal; median 3.8s (1.9-8.5).
- Reactions: tight jump cuts on Kevin's words; median 3.35s (1.9-6.1). Drop slates, false starts, off-take asides, ASR junk.
- B&W replay: the LAST part of the same item, 1x speed, zoom 1.1, muted, over the later part of a long reaction where Kevin points back at the clip. Face first >=1.0s (median 1.8s), B&W 0.9-2.1s (median 1.4s), usually to the cut (13/16), sometimes mid-reaction then face again (3/16). Every reference: 4 of 6 reactions; the final reaction usually stays on the face.
- SFX on Kevin only, 1-3 per reaction (error most common, FAH often at the B&W start). Items already contain the source's own SFX. `core-sound-effect.mp3` whoosh starts 0.33s before every reaction -> next-item cut (20/20). Kevin about 4.65 dB above the items.

## Workflow (CLI fallback: `cli.py <tool> --json/--input`)

1. `prepare_ranking_batch(targets)`; each target `{project, timeline, kevin?, ranking?}`. Raw timeline (exactly the two files) or an empty timeline with explicit `kevin`/`ranking` paths (templates are cloned from another timeline in the same project). CapCut may stay open: the target is protected by a content signature, not a whole-file hash.
2. `get_ranking_briefs(batch_id)`: Kevin words with global indices, phrases, scene cuts, label onsets, the source's built-in SFX, contact sheets (2 fps) and an unverified proposal. Read every sheet. Use `ranking_frames(job, 'ranking'|'kevin'|'bw', times)` for exact boundaries. Scene detection at 0.25 misses same-location item changes; find them with a lower threshold or frames.
3. Map each reaction to its item by content. ASR can stretch a word over silence or an aside; re-transcribe a suspicious window without VAD before choosing pieces.
4. `stage_ranking_plan(job, items, reactions, quality_notes, volumes?)`:
   - item `{start, end, rank, label, reason>=10}`; `end` = the next shot's first-frame time (scene cut). The tool stops 10 ms before it and rounds item length down to whole frames, so the next shot never flashes.
   - reaction `{item, about>=10, pieces:[{from_word, to_word, start_adjust?, end_adjust?, adjust_reason?}], tighten?: true, bw?:{at_word, duration|until_end, tail_end?, zoom?, reason>=12}}`. Pieces move forward through the take; edges snap to sustained syllable energy; internal pauses >0.45s become jump cuts.
   - `quality_notes`: `item_boundaries_checked_on_frames`, `reaction_mapping_reviewed`, `dropped_speech_reviewed` all true after real review.
   - All errors return at once. Read `dropped_speech` (must be only slates/asides/junk), `timeline`, `warnings`.
5. `preview_ranking_plan(job)`: frame-exact 360x640 MP4, a boundary sheet (last frame before / first after every cut, B&W mid) and planned-vs-heard text. Whisper word times run early at cuts, so a first word can show up in the previous clip's "heard" text; confirm edges from energy, not that column.
6. `apply_ranking_batch(batch)`: renders full-res B&W tails into `~/SoundPilotLearning/ranking_media/<job>/`, normal auto-close (AppleScript -128 with a real exit is accepted), revalidates, writes the timeline + media registry, RAM rollback. Main timeline/root draft are written only if the target is the main timeline.
7. SFX: `prepare_edit_batch(mode='just_sfx')` on the same timelines. The brief gains `ranking` (cut map read from the saved timeline, B&W spans, whoosh cues, item built-in SFX, reference reactions) and `plan_requirements.ranking`; the generic SFX density target does not apply. Whoosh cues use a `visual_reveal` anchor on an inspected cut frame.
8. After the user revises: `learn_ranking_revision(job)` compares what was written (whole frames) with the saved timeline: item/piece edge deltas, B&W kept/removed/added, duration and zoom changes. Stored in `ranking_style.revisions` and `learned_adjustments`; the next brief carries them.
