import unittest
import soundpilot as s

class EwwRuleTests(unittest.TestCase):
    def test_spoken_eww_rejects_a_different_sound(self):
        sounds=s.read_json(s.DATA/'sound_catalog.json')
        e={'enabled':True,'sound':'fahhhh.mp3','function':'explicit_disgust','start':1,'duration':1,'source_start':0,'speed':1,'volume':.3}
        with self.assertRaisesRegex(ValueError,'spoken eww'):
            s.validate_plan({'duration':5,'effects':[e]},sounds)
        e['sound']='ewww.mp3'
        s.validate_plan({'duration':5,'effects':[e]},sounds)

if __name__=='__main__':unittest.main()
