# CapCut SFX Learning — local setup

This Windows update package contains engine code, a portable Agent Skill, an MCP service, Srijon SFX style version 16 (263 native examples), zoom style version 5 (60 reference zoom events), hook style version 1 and the bundled native Rubik Bold font. It contains no source videos, sound library, model weights, credentials or CapCut project backup. Keep your local sound library and runtime. The older full MASTER archive is separate.

## First install on another Windows PC

Install Python 3.12 and FFmpeg/ffprobe, then run:

```powershell
python setup.py --draft-root 'C:\Users\YOU\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft' --library 'C:\Users\YOU\Documents\Sound Effect Sidebar Library'
```

Setup creates a local virtual environment, installs pinned dependencies, scans your MP3 library and downloads `base.en` for offline speech analysis. It does not modify CapCut. Match filenames to the reference library. On a different CPU/GPU, benchmark transcription/settings before changing them. Rename collisions in the library must be resolved before use.

On Srijon's PC, setup already reuses the tested workspace `.venv` and existing model cache. State is `%LOCALAPPDATA%\SoundPilotLearning`. One state directory is shared by all connected hosts. To deliberately use a different user's isolated style, set `SOUNDPILOT_STATE` before setup and connection.

## Codex desktop

Register the included workspace marketplace, then install:

```powershell
codex plugin marketplace add 'C:\Users\srijon\Documents\ChatGPT\Kevin Video'
codex plugin add capcut-sfx-learning@srijon-sfx
```

Restart/reload the host if its MCP server is still old, and open a new chat. Run a harmless project-list call to check connection. Portable `mcp.json` and older `.codex-plugin`/`.mcp.json` overlays are included. `launch.ps1` reads the configured Python path; it does not rely on the Windows Store Python alias. Both manifests are version 0.1.14. Lossless tables inherit `$defaults` plus variable `$columns`/`$rows`; read all inherited evidence. Use `prepare_edit_batch` (default full combo) for new work, then `get_edit_briefs` once per batch and `get_context_batch` for selected timing windows. Media analysis is reusable for seven days with source/config/timing validation; reads do not extend expiry and revision memory is durable.

## Normal automatic closure before apply

`apply_edit_batch`, `apply_batch` and `apply_zoom_batch` default to
`auto_close:true`. All selected plans/audio/visual audits validate first. The
Windows helper uses .NET `Process.CloseMainWindow` for CapCut main windows,
waits for CapCut.exe process absence, then revalidates source/style/audits after
the final autosave. Newly exposed Home main windows can receive another normal
close request; an already-requested main window is not repeatedly closed.
There is no force termination, save/export dialog response, screenshot or new
media inference. Read-only operations and keep-existing hook no-ops leave the
app open. The app stays closed after successful writes; reopening is manual.

If CapCut refuses, shows a modal prompt, stays in the tray or saves a changed
timeline during closure, the engine blocks writes and gives a specific reason.
Resolve the prompt and Quit manually when needed; a stale timeline needs a new
cached preparation/review, not a bypassed hash. Pass `auto_close:false` to retain
manual closure. This user-authorized behavior is described in the owned skill.
The native request can be refused: [Microsoft API documentation](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.process.closemainwindow).

## Claude Code

Copy `skills/capcut-sfx-learning` into `%USERPROFILE%\.claude\skills\capcut-sfx-learning`, then:

```powershell
claude mcp add --scope user --transport stdio capcut-sfx-learning -- powershell -NoProfile -ExecutionPolicy Bypass -File 'C:\PATH\capcut-sfx-learning\launch.ps1'
```

Start a fresh session and invoke the skill. This changes only Claude's MCP registration, not CapCut. For Claude Desktop, merge the generated `claude-desktop-example.json` entry into the existing `%APPDATA%\Claude\claude_desktop_config.json`, preserving other settings. Restart and check the named tools. Do not put a whole plugin archive into the Desktop config.

## ChatGPT web or another cloud chat

A ZIP/skill upload loads instructions; it does not grant access to this PC. Use the account's supported Secure MCP Tunnel or an authenticated remote MCP connector. Local optional HTTP:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\launch.ps1 -Http
```

The service binds only `127.0.0.1:8776/mcp`. A supported tunnel must establish secure account access. No public endpoint/tunnel or ChatGPT web account connection was created here. Avoid an unauthenticated public port-forward. Cloud skill uploads alone can use uploaded brief files to return a plan, which you apply through the local CLI.

## Example requests

“Use my learned SFX style on project X timelines A, B, C, D, E. Review the full context, inspect ambiguous beats, then apply when CapCut is closed.”

“I revised project X timeline A. Compare it to job ID …, learn my corrections, and tell me what changed.”

No paid inference API is called by this plugin. Host ChatGPT/Claude usage still consumes its normal tokens/limits. Token estimates use `o200k_base`; they are payload measurements, not invoices or a Claude tokenizer measurement.

## Quality and limitations

Read both speaker streams and inspect visual context; don't choose sounds from keywords alone. Saved context/speech caches are reusable. Word timings and caption offset audit improve onset review. Exact-frame tools decode the source at the requested edited time, but don't render CapCut overlays. Every plan passes semantic annotation checks, native material checks, source/style freshness checks and a local sample-peak mix audit. None of those proves humor/creative correctness.

Batch supports five clean targets across projects, including multiple timelines in one project. Context uses up to two isolated workers with the same base.en/beam/settings. Apply preflights all targets then writes serially. Existing SFX are protected; stage into a new clean target if needed. No saved backup by default; RAM rollback handles ordinary write failures but cannot guarantee recovery from power loss.

Learning commits manual choices/removals and scoped rules to durable local memory. Compounds resolve by material IDs even with blank render paths; final levels multiply parent and leaf gains. Split pieces count as one cue with a preserved gain envelope. Source-time maps handle visual splits and bounded trims. Asset-specific normal/emphasis levels and speaker/background gain spans capture the latest balance; peak headroom no longer silently reduces all learned clips. Use a documented deliberate attenuation decision or re-balance a flagged mix. It does not fine-tune ChatGPT/Claude. Keep broad corrections tied to explicit user instructions, and scene-specific choices tied to their evidence. Actual quality must be measured on unseen user-reviewed videos; cross-model creative equivalence is untested.

Primary documentation: [OpenAI local plugins](https://developers.openai.com/plugins/build/plugins), [OpenAI MCP connections](https://developers.openai.com/api/docs/guides/custom-mcp-server), [Claude local MCP](https://code.claude.com/docs/en/mcp), [Anthropic skills](https://github.com/anthropics/skills), [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
