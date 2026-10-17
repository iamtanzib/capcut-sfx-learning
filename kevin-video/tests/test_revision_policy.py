import hashlib
import unittest
import soundpilot as s


class RevisionPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.sounds=s.read_json(s.DATA/'sound_catalog.json')

    def effect(self):
        return {'enabled':True,'sound':'Creepy Sound Effect.mp3','start':1,'duration':1,'source_start':0,'speed':1,'volume':.2}

    def test_palette_only_context_sound_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'omit'):
            s.validate_plan({'style_profile_version':5,'duration':5,'effects':[self.effect()]},self.sounds)

    def test_explicit_supported_context_can_pass(self):
        effect=self.effect();effect['context_evidence']={'kind':'reference','strength':'high','cue':'an unsettling visual following suspense',
            'why_this_sound':'Matches the specific unsettling sequence observed in Timeline 06, rather than a generic bad keyword.'}
        s.validate_plan({'style_profile_version':5,'duration':5,'effects':[effect]},self.sounds)

    def test_user_revision_is_untouched(self):
        reference=s.read_json(s.DATA/'style_profile.json')['latest_revised_reference']
        _,_,path=s.load_timeline(s.project_path(reference['project']),reference['timeline'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),reference['sha256'])

    def test_learned_set_has_the_19_user_events(self):
        examples=s.read_json(s.DATA/'examples.json')
        revised=[e for e in examples if e['project']=='test 1' and e['timeline']=='test 2 - SFX v2']
        self.assertEqual(len(revised),19)
        names={e['sound'] for e in revised}
        self.assertNotIn('Creepy Sound Effect.mp3',names)
        self.assertNotIn('undertakers-bell_2UwFCIe.mp3',names)
        self.assertIn('ooooo.mp3',names)


if __name__=='__main__':unittest.main()
