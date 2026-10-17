---
name: capcut-sfx-density
description: 2026-10-15 root cause of flat SFX accuracy - planner too sparse; density calibration + slim style memory added to briefs
metadata:
  node_type: memory
  type: project
  originSessionId: c0ff00fd-1774-4f41-b3d8-5d4333f3eadd
  modified: 2026-10-15T15:02:51.790Z
---

Flat strict SFX accuracy (0.40-0.91 since 2026-10-10, no trend) came mainly from low recall. Across 23 revision reports the user's final videos had more SFX than the plan in 22 of 23 (added 106, removed 45). The density was 13.7 SFX/min manual against 11.4/min planned. Retime deltas flip sign between batches, so no global timing offset exists.

Fix (live bundle `service.py`, backup `service.py.pre-density.bak`, test in `tests/test_workflow.py`):
- `sfx_density()` reads `history/*.json` and caches the result in `data/sfx_density.json`.
- Each brief gets `plan_requirements.sfx_density`, with a per-video target and guidance that says "calibration, not a quota".
- `BRIEF_DROP` strips hash/boilerplate fields from the `learned_feedback` and `revision_rules` in the brief, which made the 10-15 batch brief 16% smaller (470KB to 396KB).

**How to apply:** after the next revised batch, check if recall rose (the capcut_revise.py avg line). If precision drops a lot, the guidance is too strong. Still unchecked: `zoom_style` (143KB) and `mix_preferences` (61KB) in the shared SFX brief may duplicate the zoom/mix briefs. See [[capcut-batch-pitfalls]], [[capcut-token-slimming]].
