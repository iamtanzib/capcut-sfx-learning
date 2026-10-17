# File-only workflow research and installation

Research used the connected Firecrawl plugin on 8 October 2026: web/developer searches, repository READMEs, CTranslate2 CPU documentation and PySceneDetect API documentation. Results were targeted, not an exhaustive ranking of all public repositories.

## Selected components

| Component | Purpose | Installed configuration |
|---|---|---|
| [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) | Transcribe source-video speech with word timestamps and VAD | 1.2.1, local CPU int8, two threads |
| [CTranslate2](https://opennmt.net/CTranslate2/hardware_support.html) | Speech inference | 4.4.0; GENERIC CPU backend, MKL disabled for this process |
| [PySceneDetect](https://www.scenedetect.com/docs/0.7/api.html) | Approximate scene-change timing | 0.7.1 ContentDetector on 320×180, 8 FPS proxies derived from codec keyframes |
| OpenCV | Decode scene proxies | 4.10.0.84 with NumPy 1.26.4 |
| Existing FFmpeg | Decode selected audio/video ranges | Already installed; no duplicate download |
| Existing FastEmbed/BGE-small | Optional quick caption retrieval | Retained; measured accuracy limitation remains |

Both `tiny.en` and `base.en` speech models were downloaded into `models/speech`. `base.en` is the default for English source videos; `tiny.en` is available when latency matters more. These transcription models do not choose sound effects.

Faster-Whisper's README documents CPU int8, word timestamps and VAD. Its published CPU benchmark uses a different, much stronger CPU and is not treated as this PC's speed. CTranslate2 documents an SSE4.1 CPU minimum and [GENERIC execution](https://opennmt.net/CTranslate2/environment_variables.html). Actual testing on this Pentium G5420 found that version 4.8.2 crashed while loading a model; 4.4.0 with the chosen process flags loaded successfully. Setuptools 75.8.0 is pinned because 4.4.0 imports `pkg_resources`. Dependencies are isolated in this workspace's `.venv`; system Python settings were not changed.

Public source copies are in `vendor/faster-whisper` and `vendor/PySceneDetect`, with upstream licenses retained. Runtime installation uses pinned PyPI releases rather than executing arbitrary development-branch setup scripts. Research source revisions:

- Faster-Whisper: `9fa78645d7913ff9d94d0907a2156526b19b4556`.
- PySceneDetect: `81c414cb4b706e58648f98efd381024790b1565f`.

## Why this improves the inputs

The original compact brief contained the reaction captions but omitted most dialogue from the second video. A meme sound might fit the reveal in that video, a later reaction, or the relation between them. The new pipeline separately transcribes both visible video tracks after mapping the existing source trims and speeds to timeline time. It also extracts scene boundaries, loud moments and up to 12 local keyframes.

Processing is cached by video files, edit ranges/speeds and captions. Changing the SFX does not change this fingerprint. Target old SFX tracks are not decoded, and reference examples from the same video are excluded, including duplicate timeline tabs. These properties are covered by tests.

The supplied files are 4K HEVC, at roughly 60 and 120 FPS. Full frame decoding on this CPU was too slow for the default workflow. A short decoder probe measured 17.93 seconds with normal decoding versus 1.73 seconds with codec-keyframe-only decoding for a 3-second range (the probe ran alongside another local task, so these are indicative, not controlled throughput figures). The default scene proxy uses `skip_frame=nokey`; scene boundaries and facial expressions can therefore be coarse. Exact SFX timing should use speech words/captions, and an exact local frame can be extracted when a visual moment is ambiguous. Set `scene_decode` to `full` for full decoding at substantially higher processing time. Proxies also omit CapCut overlays and crop/zoom effects; they supply source context rather than a finished-render preview.

`outputs/enhanced_brief.json` is the small input for Codex sound selection. Audio recognition and shot detection run locally; Codex still decides comedic meaning and effect choice. There is no paid inference API or desktop-control requirement. Codex chat tokens and any Firecrawl credits are separate from the free local runtime.

## Repositories not installed as the editing engine

[FoleyCrafter](https://github.com/open-mmlab/FoleyCrafter) generates new synchronized audio from video using additional model checkpoints. Its README does not describe selecting a user's existing local meme files and writing them into CapCut. That is different from the requested task, so its generation stack was not installed.

[pyCapCut](https://github.com/GuanYixuan/pyCapCut/blob/main/english_readme.md) documents draft loading and new audio tracks, but also limitations on imported template tracks. The existing exporter retains this user's installed CapCut schema and complex video/caption tracks directly. Installing an additional exporter would not itself improve creative sound decisions.

## What is and is not established

Installed/runtime/processing tests establish that local files can supply richer context and that the output is separated from old SFX placements. They do not establish 90% sound-selection accuracy. The old caption-only baseline matched 12 of 66 exact filename+timing predictions. That old score is not presented as the accuracy of the new workflow. A genuinely unseen video, followed by user review of the choices, is still required to measure creative performance.

Local benchmarks and transcript samples are saved in `outputs/context_report.json` and `outputs/context_benchmark.json` when benchmark execution completes.

Measured on the supplied 64.03-second edit: tiny.en speech processing took 12.63 + 26.88 seconds across the two tracks; base.en took 22.88 + 34.03 seconds. A base.en context run with scene proxies already cached completed in 59.12 seconds. A fully cached rerun completed in 0.46 seconds. No fully cold combined run was measured. Nine automated checks passed, and the local HTTP context route was tested without browser or desktop control.
