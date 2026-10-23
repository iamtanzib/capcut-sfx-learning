# Mac token pass — 2026-10-23

- Measured cost first (`tools/session_cost.py`, local transcripts, US$ at list prices: Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, both $0.20 for a cache read). The 4-video full-combo session 3bc3ebd9 cost $10.38: 49% cache reads, 25% cache writes, 26% output. Every turn re-reads a 300–560k-token context. The brief was read in about 37 small windows over about 27 turns, and revision learning ran later in the same 550k context.
- `tools/read_parts.py` (macOS): splits a saved MCP result into parts of 18k tokens or less, with lines of 1,500 characters or less. Newlines go only between JSON tokens, and the script asserts exact reconstruction. Read every part in one parallel message. The content is identical; only the number of turns changes.
- `get_edit_briefs` / `get_batch_briefs` accept `lean`. The default is 0 (unchanged). `lean=1` omits gain envelopes, ids, hashes and file paths. `stage_plan` re-reads these from the job's frozen profile.json, so staged plans cannot change. Savings are 165k to 146k tokens on the Day 7.2 brief. `tests/test_lean.py` checks that only those keys disappear.
- `lean=2` (relevance-selected memory, local bge-small embeddings) was REJECTED by `tests/eval_lean_memory.py`. On Day 4.3–4.6 it kept 68% of the closest same-sound precedents for the user's real final cues (82% / 90% / 97% at larger sizes, which keep 63–89% of memory) and 89% of the closest zoom precedents. Its code and the bge-small model were then removed.
- SKILL.md: use lean=1, read parts in one message, learn revisions in a new chat on Sonnet 5.5, never switch models inside a batch chat, and use workers=2 (the service refuses 4). Estimate on 3bc3ebd9: $10.38 becomes about $7.22 (30% lower). That splits into $1.11 for reading in one message, $1.88 for learning in a new chat and $0.17 for lean=1, plus about $0.24 more for Sonnet in that learning chat. Moving apply to Sonnet inside the batch chat would cost MORE ($2.33 against $1.51), because caches are per model. Backups: `*.pre-lean.bak` beside service.py, edit_modes.py, server.py, CHANGELOG.md, SKILL.md and references/claude-code-local.md.
- No model, reasoning, ASR, rules, checks or CapCut writes changed. `tests/eval_asr_models.py` compares speech models against timeline captions without touching state. On Day 4.3–4.6 + 7.2 (98 captions, 2 threads) base.en stayed best: matched 78, >150 ms 28, mean |offset| 0.27 s, 23.8x realtime. small.en: 78 / 35 / 0.24 s / 9.8x. medium.en: 73 / 44 / 0.49 s / 3.6x. large-v3-turbo: 78 / 36 / 0.54 s / 3.4x. The config stays `base.en`.

# 0.1.15 — 2026-10-13

- Revision learning recognizes native clips with distinct IDs as one attack/body event only when the frozen gain envelope proves their file, source ranges, durations and relative timing. The Day 4.3 bell keeps its full 2.1-second envelope instead of learning a new quiet bell attack.
- New attacks, different files, mismatched trims, ambiguous overlaps and unverified longer split bodies stay separate. Tests exercise native application followed by learning, not only the merge helper.
- Creative sound selection, ASR quality, audio gain policies, manual timelines and saved revisions are unchanged by this scoring fix.

# 0.1.14 — 2026-10-10

- SFX, zoom, hook and full-combo apply default to normal automatic CapCut closure after every selected plan/audit validates. Newly exposed Home main windows receive their own close request; previously requested windows are not spammed. Save/export dialogs and tray/background processes can require manual Quit. No process termination or dialog answers are used.
- Verify complete process exit, revalidate every frozen source/style/audit after final autosave, retain existing reopen detection and RAM rollback. Stale autosave blocks application without overwriting manual edits. No extra analysis/provider inference or UI screenshots.
- Read-only preflight/preparation/learning never closes CapCut. A keep-existing hook no-op also stays open. `auto_close:false` preserves explicit manual closure. Failed process detection fails closed.
- Mock-process and synthetic-draft tests cover exit/refusal/Home transitions, source changes during closure, all modes, no-op protection and failure recovery. Actual closure of Srijon's live CapCut editor has not been attempted during this update.

# 0.1.12 — 2026-10-10

- Lossless table defaults send repeated identical column values once, preserving all rows, numeric/JSON types, complete wording and negative examples. Tiny rows stay plain when that is smaller. Literal transport keys are escaped; old tables remain readable.
- Existing frozen jobs use the current compact transport without rewriting their analysis, plans or cache. Full-combo and hook-only briefings now assert exact reconstruction, as SFX/zoom briefs already did.
- Shared batch/context calls are preferred over per-component repeats. No model, reasoning, ASR, cache expiry, artistic rules, level/timing guards, visual/audio checks or CapCut edits changed.
- Payload benchmark and regression results are in TOKEN_EFFICIENCY.md. Text savings do not establish total Codex quota savings or creative equivalence on an unseen batch.

# 0.1.6 — 2026-10-10

- Incorporated saved Day 1.3–1.6 revisions into durable style version 16: 62 logical manual cues across 63 native pieces, including user-selected new assets, scoped substitutions, retimes, gain references and silence decisions.
- New prepared jobs require real indexed speech/caption or inspected-frame timing anchors. An intentional offset larger than 150ms requires its own reason. This validates evidence correspondence, not delivery or artistic accuracy.
- Word/caption audit aligns local word sequences instead of the start of a long ASR sentence; unresolved reactions remain explicit.
- Revision scoring separates strict ±150ms sound/onset matching from loose ±750ms association and moves larger than one 30fps frame. Possible substitutions/distant retimes require context review.
- Manual cue learning no longer borrows a nearby different-family/distant prediction's label.
- New evaluation briefs exclude the same footage's scene-rule timestamps, including older rules identified through their learning receipt.
- Source-continuous independently split short tails retain their small timeline gap and real source offset; repeated attacks stay separate.
- All 27 synthetic workflow regression tests passed. Original saved manual timelines stayed byte-for-byte unchanged during learning. The observed strict score on this revised batch is 34/54 predictions and 34/62 manual cues; this is not a future quality guarantee or an auditory review.

Existing frozen jobs keep their original schema and style. Installation preserves the same plugin identity, marketplace and local memory location.
