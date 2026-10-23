# CapCut SFX Learning (Claude plugin)

Personal CapCut SFX, reaction-zoom and intro text-hook planner with revision learning.

Contents:
- Plugin engine, MCP server and tests (repo root, version 0.1.15)
- `seed/` learned SFX style (263 examples), zoom style (60 events), hook style
- `claude-skill/` the Claude Code skill (`capcut-sfx-learning`)
- `claude-memory/` Claude Code memory notes for this project
- `tools/capcut_revise.py` revision-learning helper

Not included: source videos, sound-effect MP3 library, model weights, CapCut project files, credentials. Set those up locally.

## Backup and restore (Mac, updated 2026-10-23)

This private repo is the full backup. `sound-learning-state/` is a copy of `~/SoundPilotLearning`, holding the learned style, revision history, batches and frozen jobs. Model weights, locks and re-creatable media (wav/mp4/npy) are left out. On the Mac, batches, apply and revision learning have run since 2026-10-20 (see `MAC_SETUP.md` and `claude-memory/`).

Restore after a clone:

```bash
cp -R sound-learning-state/. ~/SoundPilotLearning/
cp -R claude-skill/. ~/.claude/skills/capcut-sfx-learning/
mkdir -p ~/.claude/projects/-Volumes-128-gb-Capcutauto/memory && cp claude-memory/*.md ~/.claude/projects/-Volumes-128-gb-Capcutauto/memory/
```

Then download `base.en` again (setup does this) and restart the MCP server. To refresh the backup, rsync `~/SoundPilotLearning` into `sound-learning-state/` with the same excludes, then commit and push.

## Install on macOS (Claude Code)

1. Install Python 3.12 and FFmpeg (`brew install python@3.12 ffmpeg`).
2. Clone this repo.
3. Copy the skill: `cp -R claude-skill ~/.claude/skills/capcut-sfx-learning`
4. Copy memory: `mkdir -p ~/.claude/projects/<your-project>/memory && cp claude-memory/*.md ~/.claude/projects/<your-project>/memory/`
5. Register the MCP server from the repo root (adjust `launch` script to a POSIX launcher; `launch.ps1` is Windows-only).

## Mac limitations (read before relying on it)

- `setup.py` and `launch.ps1` are Windows-oriented. Mac support has not been tested.
- Apply/write steps use Windows CapCut draft paths and a Windows .NET window-close helper. CapCut on macOS is not supported by these writers yet. Analysis and planning may work; applying edits to CapCut on Mac does not.
- Paths inside memory/skill notes reference Windows paths (`C:\Users\srijon\...`); edit them for your machine.

## SFX library

`sfx-library/` holds the local Sound Effect Sidebar Library (72 files, ~51 MB). Copy it to your Mac, e.g. `~/Documents/Sound Effect Sidebar Library`, then point setup at it (`--library`). Some files are music or video clips rather than pure SFX; check names before reuse.
