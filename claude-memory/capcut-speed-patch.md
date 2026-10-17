---
name: capcut-speed-patch
description: "2026-10-14 speed/cost patch to the live CapCut MCP bundle (v0.1.15 in outputs/, not plugins/); backups and what changed"
metadata:
  node_type: memory
  type: project
  originSessionId: 990e58b8-4b7e-4228-b7cd-120b12fbf605
  modified: 2026-10-14T15:26:54.287Z
---

The live CapCut MCP server runs from `C:\Users\srijon\Documents\ChatGPT\Kevin Video\outputs\CapCut-SFX-Learning-Claude-Code-FULL-2026-10-13-v0.1.15\plugins\capcut-sfx-learning\`. The older `Kevin Video\plugins\capcut-sfx-learning\` copy is stale (it has no frame_sheet), so do not edit it.

On 2026-10-14, after the Day 5.3–5.6 batch took about 1 hour (Codex takes about 30 min), the user asked for the same quality with less time and cost. The changes in the live bundle:
- `stage_plan` reports every effect, zoom and hook error in one pass.
- Hook line width is checked at staging, with a per-line percentage.
- Anchor errors name the real cached word.
- New `set_mix` tool changes dialogue_balance/headroom without restaging.
- `audit_mix` caches decoded PCM in `jobs/<id>/audio_cache` and returns `suggested_source_lowering` (a dialogue-only factor).
- `learn_revision`/`learn_edit_revision` return a compact summary unless `full=true`.
- 3 new tests were added; 78/78 pass.

SKILL.md gained a "Speed with the same quality" checklist and a headroom rule.

**Why:** most of the wall time went to repeated full `stage_plan` resends (6 calls of about 12k output tokens each), to audit-driven restages and to roughly 10k-token revision outputs.
**How to apply:** backups are the `*.pre-speed.bak` files beside service.py, server.py, hooks.py, zoom.py and the tests in the live bundle, plus `~/.claude/skills/capcut-sfx-learning/SKILL.md.pre-speed.bak`. New tools load only in a new session. Related: [[capcut-token-slimming]].
