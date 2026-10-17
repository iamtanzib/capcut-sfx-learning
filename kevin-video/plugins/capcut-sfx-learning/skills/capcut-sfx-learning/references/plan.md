# Plan input

`stage_plan(job_id, effects, quality_notes)` fills template IDs and defaults from native manual references. Supply duration explicitly. Sound names must exactly match the local catalog. All times are timeline seconds; gain is a linear amplitude factor, not dB.

```json
{
  "job_id": "returned-job-id",
  "effects": [{
    "sound": "MMMMMM.mp3", "start": 12.4, "duration": 1.0,
    "source_start": 0, "speed": 1, "volume": 0.22,
    "fade_in": 0.005, "fade_out": 0.08,
    "dialogue": "that is fire", "function": "approval",
    "evaluation_polarity": "positive", "confidence": "high",
    "reason": "Speaker genuinely likes the revealed cart and accepts it.",
    "gain_tier": "normal"
  }],
  "quality_notes": {
    "whole_video_reviewed": true,
    "silence_reviewed": true,
    "unresolved": [],
    "auditory_review": "pending local preview"
  }
}
```

New jobs (`plan_schema_version=2`) require `timing_anchor` on every effect. Prefer `get_context_batch(job_id, windows)` for every selected cue window in one call, or `get_context` for a later additional window. Batched windows point to complete `speech_rows` and captions via zero-based row IDs; all word indices are global to the source stream. Do not guess an index from a cropped window:

```json
"timing_anchor": {
  "kind": "speech_word", "role": "video_track_1",
  "at": 12.36, "text": "fire.", "word_index": 37
}
```

The word/text/time must match frozen evidence. A deliberate lead/lag exceeding 150ms needs `offset_reason` explaining the specific attack/reveal relationship. This is documentation of an artistic offset, not a timing guarantee. For a missed exclamation, `caption_reaction` uses the real `caption_index`, exact caption text/start, and role `video_track_1`; caption-only timing still needs actual reaction/audio review. `visual_reveal` uses role, exact inspected frame time and observable action in `text`; call `exact_frame` first. Older frozen jobs retain their original schema. A file/anchor check cannot verify comedic meaning or perceived delivery.

`evaluation_polarity` for MMM: `positive` or `explicit_affirmation` after resolving completed meaning. Never use a raw negation-keyword filter: "not bad" can express acceptance.

For rare-context sounds include:
```json
"context_evidence": {
  "kind": "visual_context",
  "strength": "high",
  "cue": "specific observable unsettling action at 20.4s",
  "why_this_sound": "Explain why this context warrants creepy rather than awkward, error, or silence."
}
```
Allowed kind: `visual_context`, `spoken_context`, `reference`. Refer to an actual inspected frame/line/example. Do not fabricate evidence. Never set `user_reviewed` yourself.

Recent manual reference levels replace stale generic volume defaults. `gain_tier` is `soft`, `normal`, or `emphasis`; choose a tier from delivery/role, not a fixed quota. MMM normal/emphasis and FAH normal/emphasis are distinct in Srijon's revisions. A purposeful override uses `level_source: "explicit_override"` and a specific `level_reason`; do not mark this as user-reviewed.

Optional `gain_envelope` contains `{offset,duration,gain}` pieces relative to the cue. Optional `source_offset` is a source-seconds offset from the cue's `source_start`; it preserves a source-continuous split tail even when the user inserted a small timeline gap. Without it, source position follows `offset * speed`. The approved death-book bell has a strong short attack and a quiet body; the miniature-house creepy bed dips under the actor. The engine expands these to editable native segments. Preserve the cue's full meaningful tail; physical source duration still bounds each rendered trim.

`quality_notes.dialogue_balance` can specify per-role **multipliers**, e.g. `{ "video_track_1": 1.3, "video_track_2": 0.6 }`, with `dialogue_balance_reason`. Verify which role is foreground, compare the actual recording, and preserve pre-existing per-clip gain differences. Stored role slider references are guidance, not a universal gain for every recording.

Music beds use low gain and adapt beneath speech; stored background/reference levels are scene evidence, not an automatic playlist. A peak-safe WAV can be attenuated for preview only. If `headroom_review_required` is true, apply is blocked: adjust the mix or deliberately set `quality_notes.headroom_mode: "uniform_attenuation"` with a meaningful `headroom_reason`, then audit again. Explain the decision; never silently undo the learned levels. Audits reject compound audio and processing they cannot reproduce.

`apply_batch` only installs into clean targets. To revise an already generated version, the user can make a new clean timeline in CapCut and the host prepares that stable ID. This avoids deleting the user's manual edits.

Optional `zooms` and `zoom_quality_notes` stage reaction punch-ins from this same analysis. See [zoom workflow](zooms.md). The returned `zoom_job_id` needs a framing preview before apply. Existing revised SFX targets use the zoom-only workflow; never bypass this clean-SFX guard.
