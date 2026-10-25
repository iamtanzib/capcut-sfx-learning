# Reuse the SFX analysis for reaction zooms

First list saved projects and resolve stable timeline IDs. Learn actual native examples with `learn_zoom_style(references)` where each row has `{project,timeline,analysis_job_id}`. Existing cached analysis is required; source file statistics and source-time correspondence are validated. This learns observed hard-cut punch-ins, phrase timing, relative scales/positions and baseline resets, not model weights. Later revisions replace this video's observations. Do not infer global word rules or target timestamps from reference beats.

For a new clean batch, SFX + zoom is the default (`prepare_batch(...,include_zoom=true)`); no extra zoom request is needed. Prepare once and read complete shared briefs. They include learned zoom style. Design SFX and zooms during the same creative review, preserving both speaker streams, scene meaning and silence. Pass `zooms` and `zoom_quality_notes` to `stage_plan`; default jobs reject silently omitted zoom review. Use an explicit reviewed `zooms: []` if no reaction warrants a closeup. Only an explicit user request for SFX-only/no-zoom selects `include_zoom=false`. Stage returns a linked `zoom_job_id`. Fetch `get_zoom_context` on that ID if anchor indices are needed. Preview every linked plan using `preview_zoom_plan`; inspect its returned local image, then restage with `framing_reviewed=true` and regenerate the preview audit. Run `audit_mix`. `apply_batch` validates all SFX and zooms, installs SFX first, then native zoom cuts, in the same RAM-rollback transaction. No second ASR or scene analysis is required.

For existing revised SFX, call `prepare_zoom_batch(targets)` with rows `{project,timeline,analysis_job_id}`. It makes read-only zoom jobs from current saved drafts and cached speech; trims/splits map to current times. It preserves native SFX and ignores old model sound predictions. Read `get_zoom_briefs(batch_id)` once: `$shared` + each complete `$delta`, lossless column/row tables. Use `get_zoom_context` for indexed words, then `stage_zoom_plan`, preview and `apply_zoom_batch`. Existing manual punch-ins are protected; no silent replacement or cache truncation. Changed media, incompatible source edits or unsupported processing must be resolved, not bypassed.

Example zoom row:

```json
{
  "role": "video_track_1", "start": 12.4, "end": 13.8,
  "scale": 1.30, "dx": 0.0, "dy": -0.025,
  "dialogue": "I eat my blanket",
  "reason": "Personal comic reaction to the edible blanket; return before the next reveal.",
  "timing_anchor": {
    "kind": "speech_word", "role": "video_track_1",
    "word_index": 17, "at": 12.4, "text": "eat"
  }
}
```

Times are current timeline seconds and snap to native fps. Scale is relative to each current baseline clip. `dx/dy` are offsets in native normalized half-canvas coordinates, not pixels; positive y moves up. Position for THIS recording and preserve hair/eyes and meaningful expressions. Do not blindly reuse a reference offset, manually changed layout or another video's absolute scale. The observed references mostly use 1.2–1.4x, sometimes stronger; technical bounds are 1.05–1.7x and 0.2–4.5s. Bounds do not establish artistic appropriateness. No quota or compulsory SFX matching.

Quality notes require `whole_video_reviewed`, `silence_reviewed`, `unresolved: []`; `framing_reviewed` must be true before apply. Cached word text/index/time must match. Deliberate offsets >150ms require `timing_anchor.offset_reason` grounded in the specific vocal/visual relationship. Do not use ASR paragraph start for a late punchline.

Preview sheets show baseline, zoom onset and zoom end using exact decoded source times and approximate native scale/position compositing. They omit captions/effects/color processing; full CapCut rendering is unverified until reviewed in CapCut. The writer only handles constant-speed, unrotated, unflipped clips without keyframes, time-dependent masks/effects/fades, responsive layouts or grouped/template processing. Unsupported clips stop the whole batch. Native source timing, per-role audio gains, non-video tracks and audio materials must remain identical.

Applying requires CapCut fully closed at write time. `apply_zoom_batch` defaults to `auto_close:true`: validate all plans/previews, request normal main-window closure, wait for process exit, then revalidate the final saved source. Do not routinely ask for manual Quit; ask only after an actual dialog/tray/refusal blocks auto-close. No forced termination or dialog answers. `auto_close:false` opts out. A stale final autosave blocks writing and needs cached re-preparation/review. No saved backups/copies by default. Audio/captions/manual SFX are preserved; all targets validate before any write and failures restore original bytes from RAM. This does not protect against power loss.

Use `learn_zoom_revision(job_id)` after a standalone manual zoom revision; `learn_revision` also ingests linked zoom revisions for the same applied timeline. Revised scale, framing, timing, removed and added zooms remain scene-scoped evidence. Keep absence of zoom valid, use latest user edits, and never call file validation a creative-quality score.

Latest Day 1.3–1.6 revisions kept all 28 original closeups and added six (now 34): Day 1.3 17.10s/41.77s, Day 1.4 43.63s/54.37s, Day 1.5 62.97s, Day 1.6 39.10s. These timestamps only locate source learning examples, never targets for new footage. Notice immediate reveal reactions and closing objections as well as explicit jokes; additions range roughly 1.19–1.42x. Contextual timing/scale/framing examples live in persistent `zoom_style.json`. Do not discard a meaningful reaction simply to meet an old density average, and do not raise density across all videos.
