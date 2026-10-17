# Transfer troubleshooting

Start from the extracted bundle root. Keep the exact error and selected `StateRoot`; do not retry an unchanged failing apply in a loop.

| Symptom | What to check |
|---|---|
| `claude` command unavailable | Install native Windows Claude Code, open a new terminal and sign in. Runtime/memory setup may already be complete; rerun the installer afterward. |
| Existing MCP name prevents registration | Inspect `claude mcp get capcut-sfx-learning`, then use the installer’s `-ReplaceClaudeRegistration` to intentionally replace this user-scoped entry. |
| MCP configured but failed to connect | Run `VERIFY.ps1 -Mcp`; check the launcher path, `local-install/claude-session.json`, selected state's `runtime.json` and Python path. Restart a fresh Claude session. |
| Skill missing | Check `%USERPROFILE%\.claude\skills\capcut-sfx-learning\SKILL.md`; invoke `/capcut-sfx-learning` in a fresh local session. Account cloud sessions do not automatically run the local Windows MCP process. |
| Python/runtime moved | Rerun the installer from the permanent extracted folder. It rewrites portable venv home. If using a shared runtime that was removed, use portable mode with a deliberate state choice. |
| Project list empty | Verify `config.json` points to the intended real CapCut drafts folder. An empty default directory is not a restored project collection. |
| Audio/font/model missing | Read health output and `EXTERNAL_INPUTS.json`; verify fully extracted payload and the selected config paths. Original video media must remain available. |
| New PC has different footage paths | Copy/relink original media in the native CapCut project and refresh compatible analysis. Do not forge hashes to reuse unavailable source evidence. |
| Old cache/job cannot apply | Seven-day expiry and current source/style validation still apply after migration. Prepare/review a new job rather than bypassing checks. |
| Large brief appears incomplete | Read the full saved tool-results file. Reconstruct every inherited table row and both speaker streams; use `get_brief(full=true)` if necessary. |
| Existing SFX blocks full combo | Use a clean new timeline for SFX/full-combo work. Zoom/hook-only modes preserve existing SFX. |
| Filled manual hook blocks replacement | Preserve it with `keep_existing`; replacement needs direct user authorization. |
| Apply blocked after closure | Resolve the actual CapCut prompt/tray/refusal or changed final autosave. Quit normally when needed, prepare/review changed sources, and revalidate. Never force-kill. |
| Audio audit passes but delivery sounds wrong | Listen to the preview, inspect gain tiers/balance/tails and adjust from actual scene evidence, then audit again. A sample-peak check does not establish creative quality. |
| Claude/Codex appear to remember different corrections | Confirm they use the same `SOUNDPILOT_STATE`/session-selected state. Separate state directories retain separate learning. |

For connection/configuration behavior consult [Claude MCP documentation](https://code.claude.com/docs/en/mcp); for skill locations consult [Claude skills documentation](https://code.claude.com/docs/en/skills). Current engine requirements and schemas are in `plugins/capcut-sfx-learning/skills/capcut-sfx-learning/references/`.

The ZIP is a snapshot. After new revisions are learned, preserve/export the active state in a new dated bundle if you need that later learning on another PC. Do not replace a newer live state wholesale with this archive. Preserve unknown existing history and inspect component versions before choosing another state.
