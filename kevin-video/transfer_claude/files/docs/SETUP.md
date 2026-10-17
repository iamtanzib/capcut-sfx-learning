# Claude Code setup for this transfer bundle

Verified against official Claude Code documentation on 2026-10-13 (Asia/Dhaka). The package targets native Windows x64 and existing Windows CapCut drafts. Keep it in a stable extracted folder; moving/deleting that folder can break registered launcher paths or portable assets.

## Install and sign in to Claude Code

Use an already installed native Windows Claude Code if available. Otherwise, run the official native installer in PowerShell:

```powershell
irm https://claude.ai/install.ps1 | iex
```

Open a new terminal, run `claude --version`, then `claude` and complete your own sign-in. Git for Windows is optional in current Claude Code; it supplies Git Bash when installed. See the official [Windows setup instructions](https://code.claude.com/docs/en/setup). This bundle includes plugin Python/FFmpeg/dependencies/models, but does not include Claude Code or its account credentials.

## Same PC: share live memory and runtime

From the extracted bundle root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\INSTALL_CLAUDE_CODE.ps1
```

Equivalent: double-click `INSTALL_CLAUDE_CODE.bat`. It rebases the bundled venv's Python home, then checks the selected existing state for valid runtime/library/model/draft paths and SFX/zoom/hook memory. Valid existing state is reused. The selected state defaults to `%LOCALAPPDATA%\SoundPilotLearning`.

The installer copies the skill to `%USERPROFILE%\.claude\skills\capcut-sfx-learning`, preserving an existing skill copy in `.claude\migration-backups`. It registers the package's PowerShell launcher as a user-scoped stdio server. Official references: [personal skills](https://code.claude.com/docs/en/skills), [stdio MCP and user scope](https://code.claude.com/docs/en/mcp).

It does not copy credentials or replace other Claude servers/settings. Native CapCut drafts are not written during installation. Restoring memory writes only the selected SoundPilot state. Sharing this state means future learning from either host is visible to the other.

## Another PC or isolated portable setup

Create/use the correct existing CapCut drafts folder and place source footage where the native drafts can resolve it. Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\INSTALL_CLAUDE_CODE.ps1 -UsePortable -StateRoot 'C:\CapCut-Claude-State' -DraftRoot 'C:\Users\YOU\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft'
```

The state path can be a new directory. A deliberately specified draft path must exist; the default CapCut path can be created by the installer. Creating an empty drafts directory does not restore source projects. `reference-projects/` contains recovery metadata; there is no automatic native draft import.

Restoration rebinds bundled library/model/cache paths, uses the copied runtime, rescan/configure logic, preserves equal/newer existing SFX/zoom/hook components, and imports missing history/cache files. Do not treat archival jobs as current live jobs: expired analysis or changed footage requires refresh. Another PC's absolute media paths/file timestamps can invalidate cache reuse. Frozen source hashes remain archival evidence; never rewrite them to manufacture freshness. Read `migration-restore-report.json` in the state directory to see what was restored.

`-UsePortable` writes the selected state's runtime/config. A new `-StateRoot` is the clearest way to test the snapshot without switching the active shared state. Remember that isolated states do not automatically merge future learning.

## Verify before editing

Before installation, compare the delivered ZIP SHA-256 with `Get-FileHash -Algorithm SHA256 -LiteralPath 'YOUR_BUNDLE.zip'`, replacing the placeholder filename. After installation, run `VERIFY.bat`, or:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\VERIFY.ps1 -Files -Mcp
claude mcp get capcut-sfx-learning
claude mcp list
```

Read failures in full; file integrity, runtime/asset checks and protocol connection are separate evidence. Within a fresh session run `/mcp`, invoke `/capcut-sfx-learning`, then request `list_projects`. A registration entry alone does not prove that the engine can connect or read the intended drafts. The package expects 31 tools.

For a harmless direct fallback:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\CALL_TOOL.ps1 -Tool list_projects
```

`CALL_TOOL.ps1` selects the installed state/runtime and supports `-InputFile` for tools requiring JSON arguments. Let the engine handle native project mechanics.

## Existing registration, reinstall and relocation

If `capcut-sfx-learning` already exists, first inspect `claude mcp get capcut-sfx-learning`. To deliberately replace that user-scoped registration with this bundle's launcher:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\INSTALL_CLAUDE_CODE.ps1 -ReplaceClaudeRegistration
```

Use the same `-StateRoot`, `-DraftRoot` and `-UsePortable` options if you selected them earlier. Replacement targets only this server name. If a same-name local/project registration masks the user registration, inspect its scope; do not remove unrelated servers.

To prepare runtime/memory without registering Claude, pass `-NoRegister`. When Claude is installed later, rerun the installer normally. After moving the bundle, reinstall from its new location and intentionally replace the old registration; verify asset/config paths again.

## Optional native plugin loading

This package also includes `.claude-plugin/plugin.json` and a plugin `.mcp.json` using `${CLAUDE_PLUGIN_ROOT}`. The standard installed route is the personal skill plus user MCP registration above. Do not simultaneously load that same package through `--plugin-dir`; it creates a second route to the same service/skill. Plugin skills use a namespaced command instead of the personal command. See [plugin layout and variables](https://code.claude.com/docs/en/plugins-reference).

## Large results: retain complete evidence

Claude Code can save a large MCP result into a local tool-results file. The agent must read that complete file when this happens; a displayed prefix/suffix is insufficient for editing. Raising `MAX_MCP_OUTPUT_TOKENS` does not remove every character limit. See [MCP output handling](https://code.claude.com/docs/en/mcp#mcp-output-limits-and-warnings). `CLAUDE.md` records this requirement together with the plugin's lossless table reconstruction rules.

## Source inputs and models

Original source videos remain external inputs; `EXTERNAL_INPUTS.json` records paths/bytes and missing historical references. Keep existing files on this PC. On another PC, copy/relink the footage in native projects and verify exact-frame/transcription before editing. Models/asset filenames/config influence cache validity. Do not replace the tested model/ASR settings solely to save tokens.

Current stats are in `BUNDLE_INFO.json`; active service memory is authoritative after new learning. Historical documents intentionally retain their original version numbers and measured limitations.
