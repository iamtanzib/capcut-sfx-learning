---
description: Learn the user's CapCut revisions cheaply (one script call, compact output)
---
The user revised an applied CapCut batch. Learn it in as few tokens as possible. Do not load the capcut-sfx-learning skill and do not read plugin code.

0. The user typed: `$ARGUMENTS`. Pass a batch ID only if it is a hex ID. Every other word is a rule for step 1, never a positional argument.
1. Turn any rule the user stated (e.g. "ignore music", "SFX too quiet") into a `--rule` with `--evidence` quoting the user. Rules that only mean "ignore music" use `--scope revision_learning`.
2. Run exactly one Bash command:
   `"C:/Users/srijon/Documents/ChatGPT/Kevin Video/.venv/Scripts/python.exe" "G:/Kevin video plug in/tools/capcut_revise.py" [batch_id] [--rule "..." --evidence "..." --scope ...]`
   With no batch ID it uses the newest batch.
3. Reply with one short table per video (strict and loose P/R as %, added, removed, moved, big dB changes, zoom/hook changed), an average row from the script's last line, a note that the revisions are saved, and at most 2 lines of patterns. Nothing else.

If it fails, show the one decisive error line and stop. Do not debug the plugin in this chat.
