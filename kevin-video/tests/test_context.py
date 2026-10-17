import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import context_pipeline as c
import soundpilot as s


class ContextTests(unittest.TestCase):
    def test_context_ignores_existing_sound_effects(self):
        project=s.project_path('0928');_,draft,_=s.load_timeline(project,'Timeline 11')
        original_inputs,original_key=c.context_inputs(project,draft)
        changed=copy.deepcopy(draft)
        changed['materials']['audios']=[]
        changed['materials']['drafts']=[]
        changed['tracks']=[t for t in changed['tracks'] if t.get('type')!='audio']
        changed_inputs,changed_key=c.context_inputs(project,changed)
        self.assertEqual(original_inputs,changed_inputs)
        self.assertEqual(original_key,changed_key)

    def test_copy_has_same_video_fingerprint(self):
        project=s.project_path('0928')
        one=s.load_timeline(project,'Timeline 11')[1]
        two=s.load_timeline(project,'Timeline 12')[1]
        self.assertEqual(c.context_inputs(project,one)[1],c.context_inputs(project,two)[1])

    def test_trim_and_speed_mapping(self):
        source=np.arange(10*c.RATE,dtype=np.float32)
        clip={'duration':1,'source_start':2,'speed':2}
        out=c.resample_clip(source,0,clip)
        self.assertEqual(len(out),c.RATE)
        self.assertEqual(out[0],2*c.RATE)
        self.assertEqual(out[-1],4*c.RATE-2)

    def test_style_excludes_same_video(self):
        s.compact_brief('0928','Timeline 11',['Timeline 11'])
        brief=s.read_json(s.OUTPUTS/'compact_brief.json')
        self.assertEqual(brief['excluded_style_timelines'],['Timeline 11'])
        self.assertNotIn('start',brief['sound_style'][0])


if __name__=='__main__':unittest.main()
