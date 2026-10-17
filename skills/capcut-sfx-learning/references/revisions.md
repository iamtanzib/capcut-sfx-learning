# Learning from saved manual revisions

Frozen native gain envelopes also prove longer attack/body pieces that CapCut gives different IDs. The learner checks the actual asset, source offsets, lengths and relative timing before joining them. Preserve the complete ducking envelope; do not count its quiet body as an added cue or a new low-volume attack. Unverified longer pieces, repeated attacks and ambiguous overlaps stay separate. Unchanged generated zooms/hooks are saved observations, not new manual timing corrections or evidence that the user approved every old creative explanation.

Find the job whose frozen source footage matches the revision. `learn_revision(job_id, revision_project, revision_timeline, rule_updates)` reads saved files, never modifies CapCut. A source-time map handles visual clip splits, microsecond rounding and bounded trims; unrelated, extended, reversed or ambiguous source correspondence is rejected. A matching revision is ingested once per SHA-256 and job.

The engine retains exact-sound ±0.75s maximum-cardinality association, and separately reports strict ±0.15s precision/recall and moves larger than one 30fps frame. The loose association is not precise timing accuracy. Review candidates flag possible substitutions and same-sound moves out to 3s; they are not automatically classified or scored as correct. Inspect the complete scene before calling a cue deleted/replaced. A kept cue does not prove every old explanation was correct.

Compounds resolve from `extra_material_refs` even when their rendered audio path is empty or stale. Multiply all ancestor gains and the leaf volume to obtain the final effective gain. Join continuous pieces of the same leaf for scoring, retaining distinct gain parts. Independently split tails may have new IDs: only join a source-continuous tail of at most 100ms with the same actual media path and at most 150ms timeline gap, retaining that gap and source position. Never merge repeated new attacks or ambiguous candidates. Compare old installed volume (`planned volume × old master gain`) to the revised effective level. Do not divide revised levels by the old automatic attenuation or learn that attenuation as a user preference.

Persist asset-specific soft/normal/emphasis references, approved attack/body envelopes, trims and fades, plus foreground/narrator and background gain spans. Use actual mapped word contexts; late captions can associate a gain correction with the wrong line. Volume correctness is separate from family/timing precision, and sample peaks are separate from perceived loudness.

Automatic memory stores user's manual choices and omitted/changed scene examples with mapped words and captions from both sources. A nearby different sound's predicted label must not become the manual cue's anchor. The frozen model label can be retained only for the same-sound strict match; it still does not prove its interpretation. It does not automatically invent a global emotional rule from one deletion. `rule_updates` is optional; each update must have:

```json
{"rule":"A dry echo in this scene takes awkward, not automatic MMM.",
 "evidence":"User replaced MMM at 15.4s with awkward on I would too.",
 "scope":"scene_only", "authority":"scene_inference"}
```

`explicit_user` can have broader scope only when the user explicitly stated the rule. `scene_inference` must stay `scene_only`. More recent explicit corrections take priority; surface contradictory evidence and refine its scope rather than silently averaging it. Hard-coded mappings for approval, comic-line and explicit disgust remain guardrails; a user request to change these mappings requires an engine/schema update, not merely prose memory.

Memory has versioned reports and an atomic authoritative bundle; model weights are unchanged. A newer manual version replaces the previous examples for that video instead of accumulating contradictory duplicates; history retains prior versions. Jobs keep their frozen style. Learning a new revision invalidates old staged plans at apply so they can be reconsidered. Reference timings for the same video are excluded from a new evaluation brief. Do not score a reused training video as independent quality evidence.

Evaluate on unseen manual videos: report precision, recall, wrong-family substitutions, timing error, and dialogue masking. A target 80% score is not established until the user reviews unseen outputs. Keep quality and token measurements separate.
