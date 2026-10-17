# Mac setup: CapCut SFX Learning

**Status: not tested on macOS.** The engine is Python and mostly portable, but the
plugin was built on Windows. Read the limitations before you rely on it.

## Limitations

- **Apply does not auto-close CapCut on Mac.** `app_lifecycle.py` supports auto-close
  on Windows only. On Mac, quit CapCut yourself (Menu > Quit CapCut) and pass
  `auto_close:false` to `apply_edit_batch` / `apply_batch` / `apply_zoom_batch`.
  Otherwise apply raises `Auto-close supports Windows only`.
- **`launch.ps1` is Windows-only.** `mcp.json` points at it, so do not use `mcp.json`
  on Mac. Register the server with `launch.py` (step 6).
- **CapCut Mac draft format is unverified.** The writer was built against the Windows
  CapCut draft layout. Test on a copy of a timeline first, and keep CapCut's own
  backup of the project.
- Pinned wheels (`onnxruntime==1.19.2`, `ctranslate2==4.4.0`, `opencv-python==4.10.0.84`)
  may not all have Apple Silicon wheels for Python 3.12. If `pip install` fails, see step 3.

## 1. Install prerequisites

```bash
brew install python@3.12 ffmpeg
```

Confirm: `python3.12 --version` and `ffprobe -version`.

## 2. Get the repo

```bash
git clone https://github.com/iamtanzib/capcut-sfx-learning.git
cd capcut-sfx-learning
```

Use the **repo root** as the plugin root. Ignore `kevin-video/plugins/` (stale copy).

## 3. Create the environment and install dependencies

```bash
cd ~/capcut-sfx-learning
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

If a pin fails on arm64, install the closest available version of that package
and record it. Do not change the others.

## 4. Set the state folder

Without this, state goes to `~/SoundPilotLearning`. Set it explicitly and restore the learned memory into it:

```bash
export SOUNDPILOT_STATE="$HOME/SoundPilotLearning"
mkdir -p "$SOUNDPILOT_STATE"
cp -R sound-learning-state/. "$SOUNDPILOT_STATE/"
```

`sound-learning-state/` is in the repo. Add this to `~/.zshrc` so every session uses the same folder.

## 5. Run setup (CapCut draft root and SFX library)

Find the CapCut draft folder on your Mac. Open CapCut once, create a project, then search for
`com.lveditor.draft`. The usual location is:

`~/Movies/CapCut/User Data/Projects/com.lveditor.draft` (verify; yours may differ)

Put your SFX library in a folder. The repo has a copy in `sfx-library/`:

```bash
cp -R sfx-library "$HOME/Documents/Sound Effect Sidebar Library"
```

Run setup:

```bash
.venv/bin/python setup.py \
  --draft-root "$HOME/Movies/CapCut/User Data/Projects/com.lveditor.draft" \
  --library "$HOME/Documents/Sound Effect Sidebar Library" \
  --reuse-python "$PWD/.venv/bin/python"
```

Setup downloads `base.en` (speech) and the embedding model, unless you pass `--skip-model-download`
and copy them into `models/` yourself. Models are not in the repo.

## 6. Connect to Claude Code

Copy the skill:

```bash
mkdir -p ~/.claude/skills
cp -R claude-skill ~/.claude/skills/capcut-sfx-learning
```

Copy the memory (Claude Code keys project memory by the project folder path). Open Claude Code once in the project folder
and find its memory folder under `~/.claude/projects/`, then copy:

```bash
cp claude-memory/*.md "<that memory folder>/"
```

Register the MCP server:

```bash
claude mcp add --scope user --transport stdio capcut-sfx-learning -- \
  "$HOME/capcut-sfx-learning/.venv/bin/python" "$HOME/capcut-sfx-learning/launch.py"
```

Start a new Claude Code session and check that the `capcut-sfx-learning` tools appear.
Run a harmless `list_projects` call.

## 7. Check it works (before any apply)

1. `list_projects` returns your CapCut projects.
2. `prepare_edit_batch` on one short test timeline (read-only, safe).
3. Apply only after you have a copy of the timeline and CapCut is quit, with `auto_close:false`.

## Troubleshooting

- `Run setup.py with Python 3.12 before connecting`: `.venv` missing or wrong; rerun step 3 and 5.
- `Auto-close supports Windows only`: pass `auto_close:false` and quit CapCut first.
- Empty memory / no learned style: `SOUNDPILOT_STATE` was not set in the session that launched the MCP server.
- `ffprobe` not found: install `ffmpeg` with Homebrew and open a new terminal.
