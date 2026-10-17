# Shared-analysis reaction zooms — 0.1.8

Update 0.1.9: new edits default to SFX + zoom, with engine guards against
silently skipped zoom review and an explicit SFX-only opt-out. The four saved
Day 1 revisions were ingested without changing CapCut files or rerunning ASR:
28 original zooms retained, six added, 34 total. Zoom memory v5 retains these
scene examples; interval/scale/framing diffs and recalculated statistics are
stored. All 40 focused tests passed, including default-mode enforcement,
opt-out, empty reviewed zoom plans and revision-diff classification.

The SFX and zoom workflow reuses one frozen dialogue/scene analysis. Native
constant-speed clip splits create short reaction punch-ins and baseline resets;
sound design happens before zooms in the same apply transaction. Zoom-only edits
preserve existing manual SFX. Manual zoom revisions are stored separately from
SFX memory, with scoped source dialogue evidence and removed predictions.

Verified: 38 focused tests (27 SFX + 11 zoom) passed. The zoom tests exercise
source-sample continuity, unaffected speaker tracks/audio/captions, real word
anchors, protected keyframes/curves/gaps, media hashes, stale style/preview,
closed-app writes, RAM rollback, combined SFX-then-zoom construction, lossless
shared briefs, zero transcription reruns, and manual all-zoom removal learning.
Actual MCP stdio initialization/discovery and read-only calls passed with 21 tools.

For Day 1.3–1.6, cached analysis was reused and 28 contextual zooms were staged.
Every baseline/onset/end framing sheet was inspected. Day 1.4 framing was
adjusted lower for stronger closeups. Complete cached evidence was retained;
no new ASR or scene inference ran. The four-video shared zoom briefing is 26,183
`o200k_base` text tokens vs 35,706 for separate compact briefs (26.7% less).
This is a payload comparison, not a measured reduction in total Codex allowance.

Preview compositing omits CapCut captions/effects/color processing. Native
CapCut playback and creative quality still require review; file validation is
not a promise of perfect edits. Existing learned SFX rules/levels remain intact.
