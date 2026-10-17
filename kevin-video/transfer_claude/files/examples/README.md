# Argument templates

These are schemas/examples for the same named MCP/CLI tools, not executable plans. Replace every `REPLACE_...` value with the exact saved project/stable timeline ID or engine-returned job/batch ID. Start with `list_projects`.

The `get_context_batch.json` times are illustrative. Replace them with actual selected cue windows, each at most 12 seconds and inside the target video's duration. New placements require real indexed timing anchors from returned evidence; these example numbers cannot establish an onset.

Run a chosen template through:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\CALL_TOOL.ps1 -Tool prepare_edit_batch -InputFile .\examples\prepare_full_combo.json
```

Change `-Tool` to match the template's tool. `get_edit_briefs.json`/`batch_status.json` use the returned batch ID; learning templates require the matching frozen/applied IDs after the user saves revisions. Do not add unsupported keys.

SFX/zoom/hook stage schemas contain creative content, complete quality notes and timing/frame evidence. Read the skill's `references/plan.md`, `references/zooms.md` and `references/text-hooks.md` and construct those plans from the actual video. Do not copy sample cue times, labels or source words into a real edit.
