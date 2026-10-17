# Kevin SoundPilot

Uses the existing Sound Effect Sidebar library and CapCut project files. No mouse, keyboard, screen access or OpenAI API is required. The source app and its sound library are retained.

## User style corrections

Active profile **v7** includes the corrected test 4. Gaming-cart conversational recognition lost its ooooo cue; the dry I-would-too echo gained awkward. Three attacks were moved earlier. This reinforces that naming an option is not automatically an expressive reaction, and positive wording alone does not make an approval cue. Current final-reference files are refreshed when indexing, including user-added changes to earlier references. Caption timing comparison merges continuous split clips so zoom cuts do not invalidate an otherwise aligned caption source. The revised test 4 is read only; no saved project backup is made during learning.

Active profile **v6** indexes **127 placements across seven references**, including the corrected test 3. The car revision keeps 13 cues unchanged, retimes 6, replaces 4 sound choices and adds 4 cues. See `outputs/test3_revision/REVISION_NOTES.md`. Strong iconic admiration can use anime-wow, mild oh uses ooooo, car-name emphasis can use a boom, and deadpan disbelief can use awkward. The exceptional Koenigsegg reveal supports a heavenly bed plus distinct hit/approval functions. Undertaker can support a specifically observed absurd lifelong consequence, while cooked/habit/date wording alone still does not justify a rare cue. Prior deleted caption-source tabs are now resolved through verified saved snapshots; renamed manual tabs use their stable timeline IDs.

The active profile is now **version 5**, with **100 placements across six references**. The user's revised test 2 removes five forced palette cues (two Undertaker bells, Among Us, creepy and movie), retimes three cues, and adds ooooo at 17.20s. Read `outputs/test2_revision/REVISION_NOTES.md`. Silence is a valid choice. Quick local suggestions disable rare context sounds by default; new v5 plans require specific context evidence or explicit user review before exporting them. These are convention/evidence checks, not proof of creative accuracy.

`data/style_profile.json` and `outputs/style_audit/LEARNED_STYLE.md` now document 69 placements from the four original 0928 timelines. The explicit rules are **genuine approval → MMMMMM** and **funny line/roast → FAH**. Do not substitute correct/check/ding for approval. Future compact/enhanced briefs include this style contract and require an exact reaction cue rather than labeling a whole caption. Plans annotated with `function=approval` or `function=comic_line` reject conflicting sound names. These checks enforce the convention; they do not establish 80% creative accuracy.

The user's saved **Srijon version** in **test 1** is the fifth protected reference. The latest user correction replaces the 21.23s MMMMMM with FAHH at 20.60s on **I failed everything**. It currently contains 12 placements, including one FAHH and two MMMMMM. The earlier zero-FAHH comparison is a historical snapshot, not the current user preference. The active style profile is version 4 and there are 81 reference placements. Do not change Srijon version; validate the revised workflow on a genuinely new video.

The main refinements are: neutral okay is not approval; excited oh-heck-yeah can use ooooo; a funny confession can use FAHH even when followed by acceptance; there is no FAHH quota; a recognized noun such as breakfast can get an emphasis boom rather than MMMMMM. The fifth reference uses Timeline 01 caption timing for analysis because its manually edited caption track is shifted relative to the unchanged video; neither track was edited by this learning step.

## Prepared edit

`outputs/demo_plan.json` contains 15 Codex-reviewed placements for the two video tracks from Timeline 11. A separate project copy is already saved inside the CapCut drafts folder under `0928 - Timeline 12 Auto SFX …`. It retains both video tracks, the original edits, 23 speech captions and background music. The old SFX compound was removed from the copy, then new effects were added as individually editable audio clips. Original Timeline 11 was not edited.

To place the result into the original project's empty Timeline 12:

1. Close CapCut normally so it saves its open project.
2. Double-click **Apply Timeline 12.bat**.
3. Reopen project **0928** and select **Timeline 12**.

The installer checks that CapCut is closed and Timeline 12 is still empty. It saves backups in `outputs/timeline-install-backup-…` before writing. If Timeline 12 already contains edits, use the independent output copy instead. Do not use Task Manager to force-close CapCut.

The copy references existing media in the original project and sound library. Keep those folders and the G: video files in place. A JSON/material/timing check passed; verify actual playback in CapCut before exporting a finished video.

## Low-token workflow for the next edit

The recommended path now includes local speech from **both video tracks**, scene-change timing and a maximum of 12 keyframes. Faster-Whisper and PySceneDetect are installed. Read [RESEARCH.md](RESEARCH.md) for source selection and CPU compatibility details.

Double-click **Prepare Next Edit.bat** and enter the timeline name, or let Codex run `context_pipeline.py` directly. It writes `outputs/enhanced_brief.json`. Normal runs use cached local models and perform no desktop control or paid API calls. Repeated runs reuse transcripts/scene data when the source edits are unchanged.

Save an edited timeline with Auto Captions in CapCut. Tell Codex: **“0928-এর Timeline 13-এ SFX বসাও। শুধু project file আর local sound ব্যবহার করো; computer control নয়।”**

Codex can run:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 soundpilot.py brief --project 0928 --timeline 'Timeline 13'
```

`outputs/compact_brief.json` is the faster caption-only option. For richer context, run:

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 context_pipeline.py --project 0928 --timeline 'Timeline 13'
```

Codex reads `outputs/enhanced_brief.json`, reviews its sparse local keyframes when needed, chooses sounds, saves a plan, and runs the local exporter. It does not need screen captures, drag-and-drop or an API key. Scene detection identifies changes, not their meaning; speech recognition can make mistakes, so the final choices still need review.

## Optional local review app

Double-click **Start SoundPilot.bat**, or run `app.py`. It opens [the local review app](http://127.0.0.1:8765). You can listen to sounds, change filenames, move onsets, trim durations, adjust volume, disable effects and create a new CapCut copy. “Add copy to CapCut project list” requires CapCut closed. “Fill empty Timeline 12” installs the latest generated copy into the empty tab.

The local semantic mode runs BGE-small through FastEmbed/ONNX using two CPU threads. Its model is downloaded and cached; normal planning uses local model files. Packages and model need no paid service. FFmpeg/ffprobe were already installed. Reinstall with `Setup SoundPilot.ps1` only if the environment is missing.

## Quality and limitations

The four source timelines produced 69 local SFX examples; the library contains 70 MP3 files, including 57 short sounds and 13 longer music files. Duration-based SFX/music classification can be adjusted in `data/sound_catalog.json` if needed.

A leave-one-timeline-out test of the caption-only semantic baseline matched the same sound within 0.75 seconds for **12 of 66 suggestions (18.2%)**. Exact agreement is a strict measure, not artistic quality; this result does not support a 90% accuracy claim. Local suggestions need substantial review. The prepared demo uses Codex scene review rather than those raw suggestions. The workflow automates insertion reliably; human taste and visual interpretation determine sound selection.

Cloud API cost: **$0**. Codex-assisted selection still uses the user's chat allowance/tokens; the compact file workflow reduces screen-navigation overhead but does not eliminate chat usage.

## Files and verification

- `soundpilot.py`: library scan, compound extraction, semantic suggestions, comparison, draft export, safe installation.
- `app.py` / `ui.html`: local review app bound to 127.0.0.1.
- `config.json`: sound sidebar settings, source references and default target.
- `outputs/demo_plan.json`: reviewed placements.
- `data/evaluation.json`: measured baseline comparison results.
- `tests/test_soundpilot.py`: compound timing/cropping/speed/volume, SFX-only compound removal, overlapping track placement, references and invalid-range rejection.

Source folders are read without executing their text. Generated CapCut copies have independent identifiers. CapCut must be closed before changing its project list or installing into an existing tab, to avoid autosave races.

Open-source dependencies: [FastEmbed](https://github.com/qdrant/fastembed), [ONNX Runtime](https://github.com/microsoft/onnxruntime), [BGE-small quantized model](https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q), [FFmpeg](https://ffmpeg.org/). The exporter preserves the installed CapCut schema directly rather than rebuilding complex tracks through a third-party draft library.
