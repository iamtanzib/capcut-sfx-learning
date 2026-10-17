import copy
import unittest
from unittest.mock import patch
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import soundpilot as s


class DraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sounds=s.read_json(s.DATA/'sound_catalog.json')
        cls.project=s.project_path('0928')

    def test_compound_timing_crop_speed_and_gain(self):
        sound=self.sounds[0]
        child={'tracks':[{'type':'audio','segments':[{'material_id':'a','target_timerange':{'start':2_000_000,'duration':4_000_000},'source_timerange':{'start':0,'duration':4_000_000},'speed':1,'volume':0.5}]}],
            'materials':{'audios':[{'id':'a','path':sound['path'],'name':sound['name']}],'drafts':[]}}
        parent={'tracks':[{'type':'audio','segments':[{'material_id':'c','target_timerange':{'start':10_000_000,'duration':2_000_000},'source_timerange':{'start':3_000_000,'duration':4_000_000},'speed':2,'volume':0.4}]}],
            'materials':{'audios':[{'id':'c','path':'abc_audio.aac','name':'Compound'}],'drafts':[{'combination_id':'abc','draft':child}]}}
        effect=list(s.flatten_sfx(parent,self.sounds,self.project))[0]
        self.assertEqual(effect['start'],10)
        self.assertEqual(effect['duration'],1.5)
        self.assertEqual(effect['source_start'],1)
        self.assertEqual(effect['speed'],2)
        self.assertAlmostEqual(effect['volume'],0.2)

    def test_compound_sfx_removal_keeps_music_and_video(self):
        _,draft,_=s.load_timeline(self.project,'Timeline 11')
        videos=copy.deepcopy([t for t in draft['tracks'] if t.get('type')=='video'])
        self.assertEqual(len(list(s.flatten_sfx(draft,self.sounds,self.project))),14)
        self.assertEqual(s.strip_direct_sfx(draft,self.sounds),1)
        self.assertEqual(len(list(s.flatten_sfx(draft,self.sounds,self.project))),0)
        self.assertEqual(videos,[t for t in draft['tracks'] if t.get('type')=='video'])
        remaining=[seg for t in draft['tracks'] if t.get('type')=='audio' for seg in t['segments']]
        self.assertEqual(len(remaining),1)

    def test_generated_refs_and_overlap_lanes(self):
        _,draft,_=s.load_timeline(self.project,'Timeline 08')
        examples=s.read_json(s.DATA/'examples.json')
        e=next(e for e in examples if e['sound']=='vine-boom (20).mp3')
        effects=[{'start':1,'duration':1,'source_start':0,'speed':1,'volume':0.3,'sound':e['sound'],'example_index':examples.index(e),'enabled':True},
            {'start':1.5,'duration':1,'source_start':0,'speed':1,'volume':0.3,'sound':e['sound'],'example_index':examples.index(e),'enabled':True}]
        self.assertEqual(s.add_effects(draft,{'effects':effects},examples,self.sounds),2)
        s.validate_draft(draft)
        ids=[seg['id'] for t in draft['tracks'] for seg in t.get('segments',[])]
        self.assertEqual(len(ids),len(set(ids)))

    def test_reject_out_of_bounds_sound(self):
        e={'enabled':True,'sound':'vine-boom (20).mp3','start':5,'duration':2,'source_start':0,'speed':1,'volume':0.4}
        with self.assertRaises(ValueError): s.validate_plan({'effects':[e],'duration':6},self.sounds)

    def test_empty_timeline_is_clear_error(self):
        with patch('soundpilot.load_timeline',return_value=({'id':'empty'},{'duration':0,'materials':{},'tracks':[]},Path('unused.json'))):
            with self.assertRaisesRegex(ValueError,'empty'):
                s.Planner().plan('0928','Empty test timeline')


if __name__=='__main__': unittest.main()
