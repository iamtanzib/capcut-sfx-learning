# Editing and revision workflow

The authoritative workflow is the complete skill plus its referenced schemas. This guide maps the migrated files/tools; it does not replace artistic review. All `REPLACE_...` values in `examples/` are placeholders. Resolve real saved project/timeline IDs and returned batch/job IDs before calling a tool. Example times are illustrative, never inferred anchors.

## One complete edit

1. Invoke `/capcut-sfx-learning`, read the full skill and relevant `references/` files, then use `list_projects`. Resolve the user's intended saved project and stable timeline ID. SFX/full combo targets must satisfy clean-SFX protection.
2. Call `prepare_edit_batch` with 1–5 targets. Default `mode=full_combo`; explicit single-component modes are `just_sfx`, `just_zoom`, `just_text_hook`. Compatible seven-day analysis is reused without discarding either source stream. `workers=2` is the existing limit/configuration, not a creative-quality choice.
3. Use `batch_status` after independent work. Diagnose failed jobs. Once ready, read all `get_edit_briefs` evidence once for the batch. Expand exact transport inheritance; if Claude saves the result to a file, read that full file. Hook-only mode intentionally exposes intro/hook evidence rather than unrelated SFX history.
4. Resolve dialogue meaning, referenced object, completed appraisal, delivery, silence and visible reveal. Choose provisional SFX/zoom windows; fetch all in one `get_context_batch` per video. Read every referenced pooled row/caption for every window. Use `exact_frame` on each ambiguous source stream as needed. Anchors must come from inspected evidence, not example timestamps.
5. Stage only reviewed decisions. Read `references/plan.md`, `references/zooms.md` and `references/text-hooks.md`. Full combo uses `stage_plan` with effects, `quality_notes`, zooms/`zoom_quality_notes` and hook/`hook_quality_notes`. An empty reviewed zoom plan remains valid. Hook-only uses `stage_hook_plan`; zoom-only uses the returned linked zoom workflow.
6. Run `audit_mix` for SFX. Inspect every `preview_zoom_plan` image and `preview_hook_plan` image as applicable. Restage after marking only the reviews actually performed, regenerate current previews and rerun changed audits. A flagged headroom decision needs deliberate documented handling. Mark unavailable audio listening as unverified.
7. Apply the reviewed selected components with `apply_edit_batch`. Default normal automatic closure is authorized: validated plans, ordinary main-window close request, process exit and post-autosave source validation precede writes. CapCut remains closed after successful apply; reopen manually. Blocked dialogs/source changes need actual resolution.
8. Review playback in native CapCut. File validation and approximate source previews cannot establish the final composited/auditory result. Keep the returned batch/job IDs for manual revision learning.

CLI example after installation:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\CALL_TOOL.ps1 -Tool prepare_edit_batch -InputFile .\examples\prepare_full_combo.json
```

Replace placeholders first. The wrapper reads selected installed state/runtime; the CLI returns image paths for frame/preview results. Inspect those files with the host's image tool. Unlike MCP image blocks, a JSON path alone does not show an image to the model.

## Revision learning

After the user has saved a manual revision, identify the matching frozen source/job. For the full edit batch, use `learn_edit_revision(batch_id)`; it routes by selected mode. `learn_revision(job_id, revision_project, revision_timeline)` learns SFX and linked components where applicable. Standalone manual zoom/hook revisions use `learn_zoom_revision` or `learn_hook_revision` on their own job IDs. These reads update durable local memory but never edit native CapCut projects.

Compare the frozen prediction first. Read the full learning report; inspect possible substitutions/distant moves instead of relabeling them as deletion. Separate strict ±150ms exact-sound/onset metrics, loose ±750ms association, retimes, substitutions and volume. Preserve compound effective gains, attack/body envelopes and source-continuous split tails. Unchanged generated zooms/hooks are observations, not new manual approval of every old explanation.

Optional `rule_updates` require a concrete evidence string, scope and authority. One-scene inference stays `scope=scene_only`, `authority=scene_inference`; broad `explicit_user` rules need an actual direct user instruction. The revision template deliberately uses no fabricated global rule.

## Tool map: 31 MCP tools

| Tool | Purpose |
|---|---|
| `list_projects` | Read saved projects and stable timeline IDs |
| `prepare_edit_batch` | Preferred 1–5-target selected-mode preparation |
| `batch_status` | Read preparation progress/failures |
| `get_edit_briefs` | Complete selected-component batch evidence |
| `get_context_batch` | Pool complete both-stream cue-window evidence once per video |
| `get_context` | Additional/adaptive source timing window |
| `exact_frame` | Decode a requested source-stream frame |
| `stage_plan` | Stage reviewed effects plus linked zoom/hook plans |
| `audit_mix` | Render local audio and check sample peaks/headroom |
| `apply_edit_batch` | Validate and apply selected components |
| `learn_edit_revision` | Learn manual revisions by applied edit mode |
| `get_style_memory` | Current durable SFX style/rules/feedback |
| `analysis_cache_status` | Report active/expired analysis counts |
| `prepare_batch` | Legacy SFX/zoom preparation; does not supply default text hook |
| `get_brief` | Complete one-job evidence; `full=true` unfolds factoring |
| `get_batch_briefs` | Legacy whole SFX/zoom batch briefs |
| `preflight_batch` | Read-only SFX/linked-component validation |
| `apply_batch` | Legacy SFX/linked-component application |
| `learn_revision` | SFX and available linked revision learning |
| `learn_zoom_style` | Learn actual manual zoom references with cached analysis IDs |
| `prepare_zoom_batch` | Reuse existing SFX analysis for zoom-only work |
| `get_zoom_briefs` | Complete mapped zoom-only evidence |
| `get_zoom_context` | Cached indexed timing for a zoom job |
| `stage_zoom_plan` | Stage reviewed standalone zooms |
| `preview_zoom_plan` | Render every baseline/onset/end framing sheet |
| `apply_zoom_batch` | Apply audited zooms while preserving other components |
| `learn_zoom_revision` | Learn saved standalone zoom changes |
| `learn_hook_style` | Learn native text examples/settings/fonts |
| `stage_hook_plan` | Stage faithful intro text/highlights or preserve existing text |
| `preview_hook_plan` | Render native-font lines/colors/width review |
| `learn_hook_revision` | Learn manual hook content/style/layout/timing |

`configure` is a CLI/setup operation, not an additional MCP creative tool. Legacy tools are included for frozen history/compatibility; use `prepare_edit_batch` for new full-combo requests.

## Reference reading map

| Reference | Read when |
|---|---|
| `SKILL.md` | Every relevant task; overall priority/workflow |
| `references/text-hooks.md` | Component selection, native text hooks and analysis cache |
| `references/plan.md` | SFX/full-combo staging, timing anchors, gain/headroom |
| `references/zooms.md` | Native zoom staging, previews, supported processing |
| `references/revisions.md` | Manual revision scoring/learning and rule scope |
| `references/platforms.md` | Host connectivity and local/cloud boundaries |

Latest current skill and selected edit-mode instructions take precedence over historical reports describing older defaults. The transferred live memory snapshot takes precedence over older seed counts/revision notes; current service state may be newer still.
