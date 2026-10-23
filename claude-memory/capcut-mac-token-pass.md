---
name: capcut-mac-token-pass
description: "2026-10-23 Mac cost pass - where tokens really go (cache reads), read_parts.py, lean=1 adopted, lean=2 rejected by revision test, fresh chat for learning, ASR model test"
metadata:
  node_type: memory
  type: project
  originSessionId: c0aca079-ab38-4425-b937-eca88aa5ae56
  modified: 2026-10-23T12:52:49.462Z
---

On 2026-10-23 Srijon asked for lower cost with the same or better output, and said to test everything before adopting it. Local LLMs were ruled out: this Mac is an M6 with 16 GB, and a 150k-token brief plus judgment of comedic timing is beyond what it can run.

- Measured with `tools/session_cost.py` (US$ at list prices; Opus 5.5 and Sonnet 5.5 both charge $0.20 for a cache read): 3bc3ebd9 cost $10.38, with 49% cache reads, 25% writes and 26% output. The context is 300–560k tokens per turn. The 4-video session 3bc3ebd9 read its 417KB brief in about 37 small windows (about 27 turns), then did revision learning in the same 550k context.
- Added `tools/read_parts.py`: lossless parts of 18k tokens or less, read in one parallel message. Added `lean` to get_edit_briefs/get_batch_briefs: default 0. `lean=1` drops gain envelopes, ids, hashes and paths, which stage_plan re-reads from profile.json. That took the Day 7.2 brief from 165k to 146k. SKILL.md now says: use lean=1, read parts in one message, learn revisions in a NEW chat, workers=2. Backups are `*.pre-lean.bak`.
- `lean=2` (bge-small relevance selection, model now downloaded to `~/SoundPilotLearning/models`) was REJECTED. `tests/eval_lean_memory.py` on Day 4.3–4.6 kept only 68% of the closest same-sound precedents for the real final cues, and 89% for zooms. The 97% setting keeps 89% of memory, so it saves nothing.
- The estimated saving on 3bc3ebd9 is 30% ($10.38 to $7.22). An earlier 39% figure used wrong cache weights. Sonnet is used only in the new learning chat ($0.56 to $0.32). Switching to Sonnet for apply inside the batch chat costs more ($2.33 against $1.51), because caches are per model and the whole context gets rewritten. The failed ASR models, bge-small and the lean=2 code were deleted on 2026-10-23 at the user's request. This was not yet measured on a real new batch. The MCP server needs a restart (new session) to load `lean`.
- ASR: `tests/eval_asr_models.py` compares models against timeline captions. large-v3-turbo, small.en and medium.en were downloaded to `models/speech`. base.en stayed best against 98 timeline captions: mean |offset| 0.27 s, 28 off by more than 150 ms, 23.8x realtime. Turbo had 0.54 s / 36 / 3.4x, medium.en 0.49 s / 44, small.en 0.24 s / 35. The config stays `base.en`. Captions are CapCut's own ASR, so they are a reference, not ground truth. The bigger models were deleted.

**Why:** the user said "test it yourself before applying; adopt only if the output matches ours or is better."
**How to apply:** compare the next batch with session_cost.py against 3bc3ebd9 (3.86M) and 7e694776 (2.42M). Do not revive lean=2 without a new revision test. See [[capcut-token-slimming]], [[capcut-sfx-density]], [[capcut-mac-install]].
