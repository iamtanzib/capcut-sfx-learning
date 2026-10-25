# Setup for Google Antigravity (or any MCP-capable agent) on macOS

An agent can run this by itself. Steps, in order:

```bash
brew install python@3.12 ffmpeg
git clone https://github.com/iamtanzib/capcut-sfx-learning.git ~/capcut-sfx-learning
cd ~/capcut-sfx-learning
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
export SOUNDPILOT_STATE="$HOME/SoundPilotLearning"
mkdir -p "$SOUNDPILOT_STATE" && cp -R sound-learning-state/. "$SOUNDPILOT_STATE/"
.venv/bin/python setup.py --reuse-python "$PWD/.venv/bin/python" \
  --draft-root "$HOME/Movies/CapCut/User Data/Projects/com.lveditor.draft" \
  --library "$HOME/Documents/Sound Effect Sidebar Library"
```

If a pinned wheel fails on Apple Silicon, install the nearest version of that package and leave the others. More detail and limits: `MAC_SETUP.md`.

## Connect the MCP server

Add to the Antigravity MCP config (replace `YOU` or use absolute paths):

```json
{
  "mcpServers": {
    "capcut-sfx-learning": {
      "command": "/Users/YOU/capcut-sfx-learning/.venv/bin/python",
      "args": ["/Users/YOU/capcut-sfx-learning/launch.py"],
      "env": { "SOUNDPILOT_STATE": "/Users/YOU/SoundPilotLearning" }
    }
  }
}
```

Restart, then call `list_projects` to verify. Do not use `mcp.json` or `launch.ps1` (Windows only).

## Skill and rules
Open this repo as the workspace. `AGENTS.md` (rules) and `.agent/skills/capcut-sfx-learning/` (the skill) are picked up from there. If your build looks elsewhere, copy that skill folder to the global skills location and paste the contents of `AGENTS.md` into the global rules.

## Smoke test
Close CapCut. Run `just_sfx` on ONE timeline of a copied project, compare with the learned style (SFX per minute, levels), and only then run real batches. Keep a copy of the CapCut project.
