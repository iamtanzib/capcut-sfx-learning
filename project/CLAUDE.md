# CapCut SFX work: token rules

Goal: the same edit quality while burning the fewest tokens. Every tool call re-sends the whole chat, so a long chat is the biggest cost. The 2026-10-14 revision step cost about 33% of the 5-hour limit because it ran at the end of a 600k-token chat.

## One job per chat
- **New batch** (up to 5 videos, `/capcut-sfx-learning`): use a fresh chat and end that chat after apply.
- **Revision learning**: use a fresh chat and run `/capcut-revise`. Target cost is under 5% of the 5-hour limit.
- **Tool or skill code changes**: use a separate fresh chat. Never edit code in a batch or revision chat.
- If a chat passes about 300k tokens, finish the current step and tell the user to start a new chat.

## Batch chat discipline
- Read the brief parts once, in order. Never re-read a part, a reference file or SKILL.md.
- Send independent calls in one message: all videos' `get_context_batch`, each video's `frame_sheet` calls, all previews and all audits.
- Stage right the first time using the SKILL.md "Speed with the same quality" checklist. One failed `stage_plan` costs a full plan resend.
- Run zoom and hook previews and audits right after staging. Fix all problems in one restage per part: `stage_zoom_plan`/`stage_hook_plan` with linked job IDs, and `set_mix` for loudness. Never resend `stage_plan` for these.
- Loudness: take the audit's `suggested_source_lowering` and call `set_mix`. Uniform attenuation made the SFX too quiet (user, 2026-10-14).
- Zoom preview: Read the image once. Crop only the rows that look wrong.
- Waiting on ASR: start one background Bash loop on `SoundPilotLearning/jobs/<id>/job.json` and do nothing else until it finishes. No repeated `batch_status` calls.
- Keep thinking and replies short. No narration between routine calls. The final report is one table plus at most 3 lines.

## Never do these
- Dump raw MCP JSON, plugin source or long logs into the chat. Summarize with a local Python one-liner that prints only the needed fields.
- Call `learn_revision`/`learn_edit_revision` with `full=true` unless the user asks.
- Use Read on large files to "check". Use grep or a Python slice for the exact lines needed.
- Spawn agents for this work. They start cold and re-read everything.

## Paths
- The live MCP bundle is `C:\Users\srijon\Documents\ChatGPT\Kevin Video\outputs\CapCut-SFX-Learning-Claude-Code-FULL-2026-10-13-v0.1.15\plugins\capcut-sfx-learning\`. `Kevin Video\plugins\` is a stale copy; do not edit it.
- Python: `C:\Users\srijon\Documents\ChatGPT\Kevin Video\.venv\Scripts\python.exe`.
- State: `C:\Users\srijon\AppData\Local\SoundPilotLearning\`.
