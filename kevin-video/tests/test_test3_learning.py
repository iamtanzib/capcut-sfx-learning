import hashlib
import unittest
import soundpilot as s


class Test3LearningTests(unittest.TestCase):
    def test_revision_untouched(self):
        ref=s.read_json(s.DATA/'style_profile.json')['latest_revised_reference']
        _,_,path=s.load_timeline(s.project_path(ref['project']),ref['timeline'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),ref['sha256'])

    def test_expected_new_reference_events(self):
        examples=s.read_json(s.DATA/'examples.json')
        revised=[e for e in examples if e['project']=='test 1' and e['timeline']=='test 3']
        self.assertEqual(len(revised),27)
        self.assertTrue(any(e['sound']=='ewww.mp3' and abs(e['start']-7.966666)<.01 for e in revised))
        self.assertTrue(any(e['sound']=='heavenly-music-gaming-sound-effect-hd-mp3cut.mp3' for e in revised))
        self.assertFalse(any(e['sound']=='among-us-role-reveal-sound.mp3' for e in revised))

    def test_frozen_comparison_distinguishes_sound_changes(self):
        diff=s.read_json(s.OUTPUTS/'test3_revision'/'DIFF.json')
        self.assertEqual(len(diff['replaced']),4)
        self.assertEqual(len(diff['added']),4)
        self.assertEqual(len(diff['retimed']),6)

    def test_renamed_reference_and_deleted_caption_source_are_supported(self):
        config=s.config();source=next(r for r in s.reference_sources(config) if r['timeline']=='Srijon version')
        self.assertEqual(s.load_timeline(s.project_path(source['project']),source['timeline'])[0]['id'],source['timeline_id'])
        self.assertTrue(s.Path(source['caption_snapshot']).exists())


if __name__=='__main__':unittest.main()
