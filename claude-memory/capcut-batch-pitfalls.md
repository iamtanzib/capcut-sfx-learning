---
name: capcut-batch-pitfalls
description: 2026-10-15 batch pitfalls - CapCut close-save invalidates prepared jobs; zoom float-equality bug (fixed 2026-10-15)
metadata:
  node_type: memory
  type: project
  originSessionId: 2a0144b8-fae3-42a6-92ea-bd2d87c4d1d7
  modified: 2026-10-15T13:45:27.947Z
---

Two failures cost a full restage in the 2026-10-15 day 6.3-6.6 batch:

1. CapCut was open during prepare. On apply's auto-close, CapCut's final save normalized trivial fields (`sound_channel_mappings.type` "" -> "none", speed float repr), so apply said "Source changed after planning. Prepare again."
   **Why:** the source hash covers the whole draft.
   **How to apply:** ask the user to close CapCut before `prepare_edit_batch`. If it still happens, re-prepare (cache is reused, no ASR rerun) and resend the same plans.
   **Enforced 2026-10-15:** `prepare_batch` now refuses with "Close CapCut before prepare" while CapCut runs (backup `service.py.pre-capcutopen.bak`). `tests/mcp_worker_startup.py` fails while CapCut is open on this machine; close it first.

2. `zoom.py` `apply_native` rejects with "Zoom unexpectedly changed timing/audio/captions" when float sums in `revision_audio.level_spans` drift (seen on a timeline with a 0.991x narrator clip). Zoom times are snapped to fps before the check.
   **Fixed 2026-10-15:** `level_spans` now rounds merged durations to 6 decimals (backup `revision_audio.py.pre-levelfix.bak`; self-check `tests/check_zoom_float_drift.py`). The cause was float drift in `video_levels` on every role, not only the 0.991x clip. No nudging needed after the MCP server restarts. See [[capcut-speed-patch]].
