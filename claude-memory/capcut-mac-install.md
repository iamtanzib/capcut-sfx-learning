---
name: capcut-mac-install
description: 2026-10-20 CapCut SFX Learning ported to this Mac - where code, venv, state, ffmpeg live; Mac-specific behaviour
metadata:
  type: project
---

Installed 2026-10-20 on macOS (arm64). Supersedes the Windows path in [[capcut-speed-patch]] on this Mac.

- Code (MCP bundle root): `/Volumes/128 gb/Capcutauto/capcut-sfx-learning` (ExFAT external drive; must be mounted)
- Python 3.12 venv: `~/.local/share/capcut-sfx-learning/.venv` (kept off ExFAT because of `._` AppleDouble files)
- State: `~/SoundPilotLearning` (`SOUNDPILOT_STATE`), SFX library: `~/Documents/Sound Effect Sidebar Library`
- ffmpeg/ffprobe/gh/uv: `~/.local/bin` (no Homebrew)
- MCP registered in `~/.claude.json` as `capcut-sfx-learning` (launch.py); skill at `~/.claude/skills/capcut-sfx-learning`
- CapCut Mac drafts: `~/Movies/CapCut/User Data/Projects/com.lveditor.draft`, single timeline per project in `draft_info.json`, no `Timelines/` folder. Code patched to handle that.
- Mac auto-close sends a normal Quit via osascript (bundle id com.lemon.lvoverseas); CapCut detection uses `pgrep -x CapCut`.

**Why:** the bundle was written for Windows CapCut; Mac draft writing is new and was untested at install time.
**How to apply:** test apply on a copy of a project first; if apply misbehaves, suspect the Mac single-timeline write path in engine/soundpilot.py and service.build_changes.
