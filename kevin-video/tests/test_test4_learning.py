import hashlib
import unittest
import soundpilot as s


class CartRevisionTests(unittest.TestCase):
    def test_manual_reference_not_modified(self):
        ref=s.read_json(s.DATA/'style_profile.json')['latest_revised_reference']
        _,_,path=s.load_timeline(s.project_path(ref['project']),ref['timeline'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),ref['sha256'])

    def test_removed_and_added_cues_are_indexed(self):
        events=[e for e in s.read_json(s.DATA/'examples.json') if e['project']=='test 1' and e['timeline']=='test 4']
        self.assertEqual(len(events),12)
        self.assertFalse(any(e['sound']=='ooooo.mp3' and 8<e['start']<11 for e in events))
        self.assertTrue(any(e['sound']=='awkward-moment.mp3' and abs(e['start']-15.466666)<.01 for e in events))

    def test_continuous_split_does_not_change_audio_timing(self):
        def draft(parts):
            return {'materials':{'videos':[{'id':'v','path':'video.mov'}]},'tracks':[{'type':'video','segments':[
                {'material_id':'v','source_timerange':{'start':source,'duration':duration},
                 'target_timerange':{'start':target,'duration':duration},'speed':1} for source,target,duration in parts]}]}
        whole=draft([(2_000_000,0,4_000_000)])
        split=draft([(2_000_000,0,1_000_000),(3_000_000,1_000_000,3_000_000)])
        gap=draft([(2_000_000,0,1_000_000),(3_100_000,1_000_000,3_000_000)])
        self.assertEqual(s.video_timing_signature(whole),s.video_timing_signature(split))
        self.assertNotEqual(s.video_timing_signature(whole),s.video_timing_signature(gap))


if __name__=='__main__':unittest.main()
