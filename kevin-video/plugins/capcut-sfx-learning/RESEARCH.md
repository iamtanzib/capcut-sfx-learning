# Quality and token research

Implemented now:
- Whole-video context from both speaker streams; no reduction in model/beam to save host tokens.
- Lossless row tables and minified MCP text, cached local speech/scene extraction, targeted word/frame tools. Full briefing remains available.
- Appraisal-polarity guard, rare-context evidence requirement, silence/unresolved review, current rules and negative revision examples.
- Caption-to-speech mismatch warnings; retain both sources and inspect nonverbal eww.
- Exact source frames for ambiguous revelations; source audio mix with fades/headroom check.
- Frozen style and stable source hashes for each job, isolated preprocessing, aggregate batch checks, serialized writes and failure rollback.
- Revision comparison before learning, scene-scoped negative evidence and an atomic durable memory bundle.

Next quality experiments, not claims of measured improvements:
1. Collect 5–10 unseen manual revisions; score exact-family precision/recall, onset error and dialogue masking. Do not evaluate on the same reference you just ingested.
2. Compare base.en and small.en on difficult excerpts while keeping beam/settings equal. A larger ASR may improve wording, but must be tested on this CPU and actual nonverbal reactions. Current base.en remains the validated setting.
3. Optional forced word alignment for hard onsets. [WhisperX](https://github.com/m-bain/whisperX) documents limitations for numbers/symbols and overlapping speech; it is not a semantic SFX selector. It wasn't installed because the current separated streams already have word timestamps and a heavy dependency change would be unvalidated.
4. User-exported rendered video when crops, overlays or animations determine a cue; raw source frames cannot verify these faithfully.
5. Cue-window listening for dialogue masking and true-peak/loudness metering. Current mix test is sample peak, not a broadcast loudness certificate. Automatic volume flattening could ruin deliberate joke timing/relative emphasis.
6. Independent GPT-vs-Claude trials with the same frozen briefs and blind user scoring. Local engine equivalence does not establish identical creative decisions.

[Faster-Whisper's primary benchmarks](https://github.com/SYSTRAN/faster-whisper) show CPU/GPU batch settings can affect memory/throughput. They are not benchmarks of this PC. This package batches independent jobs without changing each job's transcription settings; concurrency is capped at two.

Compression round-trip tests establish information preservation, not artistic accuracy. A fresh chat plus durable memory avoids repeated conversational history; total savings depend on the host's context, tool schemas, reasoning, images and retries. ChatGPT subscription tokens are not billed using OpenAI API rates.
