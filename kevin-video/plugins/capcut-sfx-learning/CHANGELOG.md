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
