---
name: capcut-sfx-density
description: 2026-10-15 root cause of flat SFX accuracy - planner too sparse; density calibration + slim style memory added to briefs
metadata:
  node_type: memory
  type: project
  originSessionId: c0ff00fd-1774-4f41-b3d8-5d4333f3eadd
  modified: 2026-10-20T18:07:14.883Z
---

Flat strict SFX accuracy (0.40-0.91 since 2026-10-10, no trend) came mainly from low recall. Across 23 revision reports the user's final videos had more SFX than the plan in 22 of 23 (added 106, removed 45). The density was 13.7 SFX/min manual against 11.4/min planned. Retime deltas flip sign between batches, so no global timing offset exists.

Fix (live bundle `service.py`, backup `service.py.pre-density.bak`, test in `tests/test_workflow.py`):
- `sfx_density()` reads `history/*.json` and caches the result in `data/sfx_density.json`.
- Each brief gets `plan_requirements.sfx_density`, with a per-video target and guidance that says "calibration, not a quota".
- `BRIEF_DROP` strips hash/boilerplate fields from the `learned_feedback` and `revision_rules` in the brief, which made the 10-15 batch brief 16% smaller (470KB to 396KB).

**Mac check 2026-10-21 (Day 4.3-4.6, style v37-40):** on the Mac bundle the brief had no `plan_requirements.sfx_density`, so the density fix above may not be in the Mac `service.py`. Results: strict P/R 0.73/0.67, 0.80/0.67, 0.80/0.75, 0.74/0.65. The user still added 11 cues and replaced only 3. Most additions landed on beats I left silent: anime-wow on 3 option reveals (personal chef, money tree, midnight snack), movie_1 on 2 deadpan "bro" lines, plus tindeck, a vine on the flying reveal and Among Us on a loyalty denial. Zooms and hooks were unchanged in all 4.
**How to apply:** treat a visual option reveal as a candidate for anime-wow or a vine, not automatic silence. Then check whether recall rose after the next revised batch (the capcut_revise.py avg line). If precision drops a lot, the guidance is too strong. Still unchecked: `zoom_style` (143KB) and `mix_preferences` (61KB) in the shared SFX brief may duplicate the zoom/mix briefs. See [[capcut-batch-pitfalls]], [[capcut-token-slimming]].
