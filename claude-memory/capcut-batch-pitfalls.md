---
name: capcut-batch-pitfalls
description: Batch pitfalls - close CapCut before prepare (osascript quit ok); workers<=2; zoom float bug (fixed 2026-10-15); Mac SFX trim limits, hook width, project rename, 0.63/0.50 mix; stale hooks in duplicated timelines (2026-10-22)
metadata:
  node_type: memory
  type: project
  originSessionId: 2a0144b8-fae3-42a6-92ea-bd2d87c4d1d7
  modified: 2026-10-21T18:23:08.062Z
---

Two failures cost a full restage in the 2026-10-15 day 6.3-6.6 batch:

1. CapCut was open during prepare. On apply's auto-close, CapCut's final save normalized trivial fields (`sound_channel_mappings.type` "" -> "none", speed float repr), so apply said "Source changed after planning. Prepare again."
   **Why:** the source hash covers the whole draft.
   **How to apply:** ask the user to close CapCut before `prepare_edit_batch`. If it still happens, re-prepare (cache is reused, no ASR rerun) and resend the same plans.
   **Enforced 2026-10-15:** `prepare_batch` now refuses with "Close CapCut before prepare" while CapCut runs (backup `service.py.pre-capcutopen.bak`). `tests/mcp_worker_startup.py` fails while CapCut is open on this machine; close it first.

2. `zoom.py` `apply_native` rejects with "Zoom unexpectedly changed timing/audio/captions" when float sums in `revision_audio.level_spans` drift (seen on a timeline with a 0.991x narrator clip). Zoom times are snapped to fps before the check.
   **Fixed 2026-10-15:** `level_spans` now rounds merged durations to 6 decimals (backup `revision_audio.py.pre-levelfix.bak`; self-check `tests/check_zoom_float_drift.py`). The cause was float drift in `video_levels` on every role, not only the 0.991x clip. No nudging needed after the MCP server restarts. See [[capcut-speed-patch]].

3. (2026-10-20, Mac, Day 4.3-4.6) Two `stage_plan` retries cost a full Day 4.6 resend:
   - Some learned reference durations are longer than the Mac library files. `vine-boom (20).mp3` 1.333 and `fahhh_KcgAXfs.mp3` 2.333 failed with "trim exceeds the source sound duration". Use at most 1.233 and 2.25.
   - The hook line "WORLD RULE PERMANENT" measured 101% of the Rubik-Bold width, so about 19 characters with wide letters (W, M) is the real limit.
   **How to apply:** before the first stage, ffprobe the library files in `~/Documents/Sound Effect Sidebar Library` and keep every duration under the real length.
   - The user can rename a project between sessions (folder `1020` became `New`). Always use the name from a fresh `list_projects`. Mac drafts then live in `.../com.lveditor.draft/<name>/Timelines/<timeline_id>/draft_info.json`.
   - Raw clips at 1.0 failed headroom. Setting dialogue_balance actor 0.63 / narrator 0.50 (the learned manual levels) passed every audit with no attenuation.

4. (2026-10-22, Mac, Day 5.3-5.6) `prepare_edit_batch` refuses `workers=4` ("One or two workers preserve the tested CPU settings"), even though SKILL.md says use 4. Use `workers=2`. CapCut was open; a normal osascript Quit (`tell application id "com.lemon.lvoverseas" to quit`) closed it in 4s (osascript printed "User canceled -128" but the process exited). All 4 plans staged on the first try. The timelines were duplicates of Day 4.3, so each held the stale "SOMEBODY'S MOVING INSIDE YOUR WALLS" hook. `replace_existing:true` overwrote the native field in place (the stage result still says action fill_blank).
