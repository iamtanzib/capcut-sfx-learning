# Lossless transport and batched timing — 0.1.12

## Additional compacting in 0.1.12

Repeated identical table columns are stored once in `$defaults`. Every row
inherits those complete fields, then takes its variable fields from
`$columns`/`$rows`. Empty variable rows still represent separate observations;
row order, duplicates, full prose, negative evidence, native settings and JSON
types/precision are preserved. Small tables use plain rows when shorter. Old
tables and literal reserved keys remain supported. Frozen jobs use the new
transport on read, without changing their saved media evidence/plans/cache.

Measured on the SAME frozen four Day 1 evidence snapshots, minified
`o200k_base` text (full combo includes the linked native hook briefs):

| Dataset | 0.1.11 tokens | 0.1.12 tokens | Reduction |
|---|---:|---:|---:|
| Four-video SFX briefing | 153,369 | 101,621 | 33.74% |
| Four-video full-combo briefing | 161,044 | 109,133 | 32.23% |
| Four-video hook-only briefing | 7,680 | 7,517 | 2.12% |
| Full saved memory bundle | 439,456 | 409,903 | 6.72% |

Each reconstructed input matches the full source JSON, including types. These
are separate datasets, not percentages to add. The full memory bundle includes
historical data and is NOT a recommended routine tool payload. One batch brief
plus one pooled timing call per video remains the preferred workflow; preserve
necessary adaptive audio/frame inspection. The benchmark performs no inference
or CapCut writes. The 57-test workflow/zoom/hook/cache/transport suite passed.

These are text-payload savings, not measured total Codex quota savings. No new
creative quality comparison, visual interpretation equivalence or complete
CapCut playback evaluation has been run. Host model/reasoning, preprocessing,
scene decisions, mix/timing/framing/native-layout audits and revision adoption
are unchanged. Use independent manual revisions on the next unseen batch to
evaluate actual creative results. Plain full briefs remain available when the
inherited table format needs clarification.

## Earlier pooling result (0.1.10)

No model/reasoning changes, cue-density limits, transcript cuts, weaker ASR,
precision rounding or skipped visual/audio audits. No CapCut file edits.

Mixed lists now use ordered contiguous column-table chunks when shorter. All
original fields, negative/positive evidence, words, numeric precision and list
order round-trip exactly. Literal reserved-format keys are escaped safely.

`get_context_batch` reads every selected SFX/zoom timing window in one call per
video. Identical full dialogue/caption rows are sent once with zero-based row
references. Both speaker streams, global word indices, timing warnings and
whole ASR rows are preserved. Each returned window is reconstructed and asserted
equal to the original `get_context` result inside the service. No new inference.

Saved four-video Day 1 SFX plans, text payload estimate (`o200k_base`, minified):

| Timeline | Cue windows | Separate context tokens | Pooled context tokens |
|---|---:|---:|---:|
| Day 1.3 | 11 | 7,829 | 4,881 |
| Day 1.4 | 12 | 10,140 | 4,173 |
| Day 1.5 | 12 | 10,516 | 4,764 |
| Day 1.6 | 19 | 16,474 | 7,497 |
| Total | 54 | 44,959 | 21,315 |

This is 52.6% less cue-context text, not 52.6% less total Codex allowance. Images,
reasoning, normal briefing, tool overhead, caching and adaptive follow-ups still
contribute. Mechanical evidence preservation is verified; end-to-end creative
equivalence and actual quota reduction have not been measured on a new video.

The additional mixed-table format candidate saves about 5% on the saved SFX
batch and 7.4% on latest full SFX memory vs the previous compact format. These
datasets are distinct; do not add savings percentages. Use fresh batch chats,
read shared style once, fetch full context for all beats together, and keep
necessary ambiguity/frame checks. Normal local revision learning remains cached.
