import hashlib
import unittest
import soundpilot as s
import context_pipeline as c


class ManualLearningTests(unittest.TestCase):
    def test_reference_is_unchanged(self):
        report=s.read_json(s.DATA/'style_profile.json')['new_manual_reference']
        _,_,path=s.load_timeline(s.project_path('test 1'),'Srijon version')
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),report['sha256'])

    def test_training_includes_correct_manual_events(self):
        examples=s.read_json(s.DATA/'examples.json')
        manual=[e for e in examples if e['project']=='test 1' and e['timeline']=='Srijon version']
        self.assertEqual(len(manual),12)
        self.assertEqual(sum(e['sound'].startswith('fah') for e in manual),1)
        self.assertEqual(sum(e['sound']=='MMMMMM.mp3' for e in manual),2)
        self.assertTrue(all(e['caption_timing_source']=='Timeline 01' for e in manual))

    def test_whole_video_match_ignores_caption_offset(self):
        project=s.project_path('test 1')
        original=c.context_inputs(project,s.load_timeline(project,'Timeline 01')[1])[0]
        manual=c.context_inputs(project,s.load_timeline(project,'Srijon version')[1])[0]
        self.assertEqual(original['tracks'],manual['tracks'])
        self.assertNotEqual(original['captions'],manual['captions'])


if __name__=='__main__':unittest.main()
