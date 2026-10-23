---
name: capcut-ranking-type
description: "2026-10-22 new \"ranking video\" type in the CapCut tool (ranking.py) - learned from 4 references; Day6.3-6.6 cut, user cut revisions learned (v5), SFX applied; SFX revision learning pending"
metadata:
  node_type: memory
  type: project
  originSessionId: d1de4bd0-4ada-4d43-aecd-3797ed0de9d3
  modified: 2026-10-22T13:04:30.500Z
---

On 2026-10-22 Srijon asked for a new video type, "ranking video": a PEPERANKER-style ranking compilation interleaved with Kevin's reactions from one raw take. The tool cuts. Srijon adds CapCut default transitions, music and captions. He said the cut is the main thing.

- Code: `capcut-sfx-learning/ranking.py`, with wrappers in service/server/cli and `tests/test_ranking.py` (7 tests). Backups are `*.pre-ranking.bak` (service, server, cli, app_lifecycle, SKILL.md). Docs: skill `references/ranking.md`.
- Style: `~/SoundPilotLearning/data/ranking_style.json` (v1, also `seed/`), learned from `/Volumes/128 gb/Kevin/Example/Ranking*.mp4`. Each reference had 6 items, 4 B&W tail replays (zoom 1.1, face first >=1s), a `core-sound-effect.mp3` whoosh 0.33s before every reaction->item cut (20/20), and Kevin about +4.65 dB over the items. Added template-only examples for core-sound-effect and rizz so the SFX stage can install them.
- Applied the same day, batch `157db8b20b7d40f0`, project folder `1022`: Day6.3 Backrooms (IMG_7667, job f85f6868b80a4f52, 57.0s), Day6.4 Spiderman (IMG_7668, c0dd14bb14224fea, 39.0s), Day6.5 Golf (IMG_7669, b5f37bf3adfa44ad, 50.6s), Day6.6 Sea Lion (IMG_7670, f379de491bd44dbd, 33.8s). Pre-apply copy: `~/SoundPilotLearning/ranking_backups/1022-20261022-154145`.
- Srijon then fixed the cuts. `learn_ranking_revision` (style v5) found the same change on all 4 videos: item starts about 3 frames later (the source has a whip-blur at each item start), reaction starts 0.1-0.27s later, ends kept, all 14 B&W kept. `stage` now applies these offsets once 2 or more revised videos agree.
- SFX were applied the same day on the revised cuts, batch `3cf1b3139b374060` (jobs 0e46fda9e8884e67 / 4f4aca11b5ca4976 / 390e1d76e3aa4af1 / 1d61388d89dc45a1): 34 reaction cues plus 15 `core-sound-effect` whooshes at each cut minus 0.33s, all audits clean. Next: `learn_edit_revision(3cf1b3139b374060)` after he revises the SFX.

**Why:** he plans to improve the output through revisions, the same way as the SFX work.
**How to apply:** the ranking MCP tools are live (since the 2026-10-22 server restart); `cli.py` also works. Pitfalls already fixed in code:
- an item ending on a scene-cut timestamp flashed the next shot's first frame;
- scene detection at 0.25 misses item changes at the same location;
- ASR stretches words over asides;
- CapCut answers osascript quit with -128 but exits anyway.
See [[capcut-batch-pitfalls]], [[capcut-mac-install]].

**2026-10-23 Day 7 batch (project `1022`):**
- 7.3–7.6 were EMPTY timelines, so `prepare_ranking_batch` needed explicit `kevin`/`ranking` paths. Media is in `/Volumes/128 gb/Kevin/mnth 4/week 1/Day 7/New Videos 3/`. Takes were matched to sources by a quick base.en ASR plus one frame per source: 7.3 Fainting (IMG_7720 + copy_7AD0), 7.4 Disguise (7721 + copy_9218), 7.5 Beach (7722 + copy_567C), 7.6 Sawblade (7723 + copy_4C2E). IMG_7724/7725 are riddle takes, not used.
- Cut batch `2afc47f79fff480f` (jobs 4559b386 / 9ffd7301 / fe506ae3 / 39b7c208); SFX batch `ea7c80cb06a04e43` (48 cues, whoosh at each cut). Day 7.2 full combo batch `32db47889ff840ff` (14 SFX, 7 zooms, stale "HOOD/GANG" hook replaced with the Olympics hook).
- Bug fixed: a B&W tail defaulting to the raw scene-cut time rendered the NEXT shot's first frame (or a whip-blur) as its last frame. `ranking.py` now defaults to `tail_end = end - 0.05` (backup `ranking.py.pre-bwtail.bak`, test updated). The running MCP server needs a restart to load it; until then pass `tail_end` explicitly.
- Next: `learn_ranking_revision` + `learn_edit_revision(ea7c80cb06a04e43)` / `learn_edit_revision(32db47889ff840ff)` after Srijon revises.
