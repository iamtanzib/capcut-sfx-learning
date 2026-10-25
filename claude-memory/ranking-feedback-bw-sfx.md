---
name: ranking-feedback-bw-sfx
description: "Srijon 2026-10-24 ranking-video feedback - B&W on almost every reaction and longer, 2-3 SFX per reaction, cuts 1-2 frames tighter; applies from the next batch"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 153ed0d9-a70d-49d3-9d05-35137725fcb3
  modified: 2026-10-24T12:14:17.509Z
---

After the Day 1.3-1.6 ranking batch (2026-10-24), Srijon said, for the NEXT batches (not this one):
- B&W replay was too short while Kevin kept talking, and too rare. Put it on almost every reaction (skip only very short ones) and make it long, about 1.5-3.5s, covering most of the reaction after the face-first beat.
- Put more SFX on Kevin's reactions: about 2-3 per reaction instead of the reference median of 1.
- Several cuts need 1-2 more frames trimmed. He did not say which edges, so learn the exact frames from his saved revision (`learn_ranking_revision`) rather than guessing pads.

**Why:** the reference-learned calibration (B&W on 4 of 6, 0.9-2.1s, 1 SFX per reaction) undershoots what he wants.
**How to apply:** `ranking.py` RULES and `~/SoundPilotLearning/data/ranking_style.json` (v6, `user_preferences`) carry this. Staging warns on a missing B&W on reactions of 2s or longer, and on a B&W under 1.5s in a reaction of 2.5s or longer; the B&W limit is now 0.5-4.5s. Backups: `*.pre-bwmore.bak`. The running MCP server needs a restart (new chat) to load it. See [[capcut-ranking-type]].
