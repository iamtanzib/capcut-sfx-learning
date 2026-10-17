# Bundle file map

| Path | Role and authority |
|---|---|
| `README_BN.md` | Bangla user guide and clear local-input boundaries |
| `CLAUDE.md` | Claude session requirements and preserved workflow |
| `INSTALL_CLAUDE_CODE.bat`, `.ps1` | Native Windows setup, current-state reuse or portable restoration, personal skill/MCP registration |
| `START_CLAUDE_CODE.bat` | Starts Claude in this folder so `CLAUDE.md` is discovered |
| `VERIFY.bat`, `.ps1` | Read-only health, optional file-integrity and MCP checks |
| `CALL_TOOL.ps1` | Same-engine CLI fallback, selected state/runtime |
| `plugins/capcut-sfx-learning/` | Current plugin code, skills, bundled seeds/font, tests and release documents |
| `plugins/capcut-sfx-learning/server.py` | 31 local MCP tool declarations and stdio/loopback transport |
| `plugins/capcut-sfx-learning/cli.py` | Local tool dispatcher; includes setup `configure` |
| `plugins/capcut-sfx-learning/service.py` | Durable state, frozen planning/learning workflow and engine entry points |
| `plugins/capcut-sfx-learning/.claude-plugin/plugin.json` | Optional Claude native plugin manifest |
| `plugins/capcut-sfx-learning/.mcp.json` | Optional plugin-relative MCP configuration; installer default uses separate user registration |
| `state/memory.json` | Atomic SFX snapshot: profile/examples/receipts |
| `state/data/zoom_style.json` | Current manual zoom learning snapshot |
| `state/data/hook_style.json` | Current manual hook learning snapshot |
| `state/jobs/` and other state caches/history | Frozen revision context/plans/analysis/cache; retain freshness/expiry checks |
| `runtime/python/` | Tested native Python base installation |
| `runtime/env/` | Current dependency environment; installer updates `pyvenv.cfg` |
| `runtime/tools/` | FFmpeg/ffprobe and bundled supporting tools |
| `models/` | Copied offline model cache |
| `library/`, `assets/fonts/` | Current/reference sound and font files, including external imports |
| `reference-projects/` | Saved JSON/font metadata archive; not automatically imported into live CapCut |
| `reports/prior-history/` | Previous master recovery reports/history |
| `reports/workspace/` | Workspace revisions, update documents/archives and verification evidence |
| `development-source/` | Workspace development scripts/documents/data/tests/vendor |
| `development-source/installed-plugin-source/` | Exact original installed v0.1.15 source, before Claude launcher/manifest/current-seed adaptations |
| `migration/restore_state.py` | Component-version-aware state restoration/path rebasing; never writes native CapCut drafts |
| `migration/health_check.py` | Health/file/protocol verification implementation |
| `local-install/claude-session.json` | Created on installation; records selected active state/shared runtime mode |
| `BUNDLE_INFO.json` | Authoritative capture version/counts/config/asset mapping |
| `EXTERNAL_INPUTS.json` | Original video paths, missing historical paths and saved-project inventory |
| `SOURCE_PARITY.json` | Source snapshot hashes; migration launch/manifests/seeds are intentional adaptations |
| `RUNTIME_PACKAGES.txt` | Exact captured installed dependency inventory |
| `docs/`, `examples/` | Setup, troubleshooting, tool/workflow map and placeholder argument templates |

File manifest/checksum names are recorded with the final delivery. The manifest inventories the bundled payload; the adjacent ZIP SHA-256 verifies the archive itself. Do not mistake either for artistic validation or full original-video recovery.

Live `%LOCALAPPDATA%\SoundPilotLearning` or the selected `StateRoot` is the post-install writable authority. Bundled `state/` and reports remain dated snapshots. Do not run historical apply scripts or overwrite native projects solely because a script is retained in the archive.
