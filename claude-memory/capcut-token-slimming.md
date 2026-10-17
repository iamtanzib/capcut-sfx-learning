---
name: capcut-token-slimming
description: 2026-10-14 token cuts to CapCut SFX MCP transport and reader helper; backup locations for rollback
metadata:
  type: project
---
On 2026-10-14 the user approved three token cuts for the capcut-sfx-learning tooling (v0.1.15 bundle):
1. `claude-code-installed/read_complete_context.py` writes compact JSON parts (format v2_compact) instead of indent=2. A real brief went from 76 to 32 parts (888,528 to 353,070 chars).
2. + 3. `plugins/capcut-sfx-learning/server.py` `slim()` rounds floats to 6 dp and cuts 64-hex digests to 12 chars, in transport only. A real brief went from 352,794 to 318,715 chars.
SKILL.md gained a per-batch Claude Code workflow paragraph.

**Why:** 97% of brief tokens are learned memory, not video evidence; the user wants the best output with fewer tokens.
**How to apply:** Backups are `server.py.pre-slim.bak`, `read_complete_context.py.pre-slim.bak` and `claude-code-installed/skill.pre-slim.bak/`. Do not apply relevance filtering to memory without the user's approval.

Also on 2026-10-14: added `frame_sheet(job_id,times,roles)` tool (service.py + server.py): both streams x 1-4 times in one image, 320px tiles, also saves exact_frame artifacts. Measured ~1353 vs ~5113 image tokens for 8 frames. Backups: `service.py.pre-sheet.bak`, `server.py.pre-sheet.bak`.

Also on 2026-10-14: SKILL.md now tells Claude to verify EVERY selected cue with `frame_sheet` (4 times per call) before staging, spending part of the token savings on quality. Judge it by the next 2-3 batches' revision scores.
