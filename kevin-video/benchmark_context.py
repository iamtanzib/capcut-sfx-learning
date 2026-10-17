"""Record tested local timings, then measure a fully cached run."""
import context_pipeline as c
import soundpilot as s
folder=s.DATA/'context'/s.read_json(s.OUTPUTS/'context_report.json')['cache_key']
base=s.read_json(folder/'report-base.en.json')
tiny=s.read_json(folder/'report-tiny.en.json')
cached=c.prepare('0928','Timeline 11',progress=print)
report={'hardware':'Intel Pentium Gold G5420, Intel UHD 610, 15.9 GB RAM',
    'video_seconds':64.033,'source_format':'4K HEVC, approximately 60 and 120 FPS',
    'chosen_default':'base.en, CPU int8, two threads; codec-keyframe scene proxies',
    'tiny_transcription_seconds':[t['transcription_seconds'] for t in tiny['tracks']],
    'base_transcription_seconds':[t['transcription_seconds'] for t in base['tracks']],
    'tiny_context_with_speech_cached_seconds':tiny['seconds'],
    'base_context_with_scene_proxies_cached_seconds':base['seconds'],
    'fully_cached_context_seconds':cached['seconds'],
    'cold_end_to_end_seconds':None,
    'speech_segments':sum(len(t['speech']) for t in base['tracks']),
    'scene_counts':[len(g['scenes']) for g in base['scenes']],
    'brief_characters':cached['brief_characters'],
    'excludes_target_style':cached['excluded_style_timelines'],
    'old_sfx_used_as_input':False,'selection_accuracy_measured':False,
    'note':'Timings are individual runs on this PC, not a controlled multi-run benchmark. Keyframe scenes are approximate; final sound choice remains Codex-assisted.'}
s.write_json(s.OUTPUTS/'context_benchmark.json',report)
print(report)
