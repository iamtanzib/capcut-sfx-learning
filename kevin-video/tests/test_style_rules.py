import unittest
import soundpilot as s


class StyleContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sounds=s.read_json(s.DATA/'sound_catalog.json')

    def effect(self,sound,function):
        return {'enabled':True,'sound':sound,'function':function,'start':1,'duration':.7,'source_start':0,'speed':1,'volume':.3}

    def test_approval_rejects_generic_chime(self):
        with self.assertRaisesRegex(ValueError,'approval'):
            s.validate_plan({'effects':[self.effect('correct.mp3','approval')],'duration':5},self.sounds)

    def test_comedy_rejects_arbitrary_quack(self):
        with self.assertRaisesRegex(ValueError,'comic-line'):
            s.validate_plan({'effects':[self.effect('mac-quack.mp3','comic_line')],'duration':5},self.sounds)

    def test_explicit_user_mappings_pass(self):
        s.validate_plan({'effects':[self.effect('MMMMMM.mp3','approval'),self.effect('fahhhh.mp3','comic_line')],'duration':5},self.sounds)


if __name__=='__main__':unittest.main()
