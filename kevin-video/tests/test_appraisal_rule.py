import unittest
import soundpilot as s

class AppraisalTests(unittest.TestCase):
    def effect(self,polarity):
        return {'enabled':True,'sound':'MMMMMM.mp3','start':1,'duration':.7,'source_start':0,'speed':1,'volume':.3,'evaluation_polarity':polarity}
    def test_negative_agreement_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Negative appraisal'):
            s.validate_plan({'style_profile_version':8,'duration':5,'effects':[self.effect('negative')]},s.read_json(s.DATA/'sound_catalog.json'))
    def test_qualified_positive_or_affirmation_is_allowed(self):
        for polarity in ('positive','explicit_affirmation'):
            s.validate_plan({'style_profile_version':8,'duration':5,'effects':[self.effect(polarity)]},s.read_json(s.DATA/'sound_catalog.json'))
    def test_unresolved_mmm_is_not_auto_approved(self):
        with self.assertRaisesRegex(ValueError,'resolved'):
            s.validate_plan({'style_profile_version':8,'duration':5,'effects':[self.effect(None)]},s.read_json(s.DATA/'sound_catalog.json'))

if __name__=='__main__':unittest.main()
