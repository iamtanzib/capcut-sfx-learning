import copy
import unittest
from unittest.mock import patch
import soundpilot as s


class ReviewedOutputTests(unittest.TestCase):
    def test_video_caption_layout_and_new_sfx(self):
        current=s.load_timeline(s.project_path('test 1'),'Timeline 01')[1]
        backup=s.read_json(s.OUTPUTS/'latest_install.json')['backup']
        target_id=current['id']
        before=s.read_json(s.Path(backup)/'Timelines'/target_id/'draft_content.json')
        def visual_tracks(draft):
            tracks=copy.deepcopy([t for t in draft['tracks'] if not t.get('name','').startswith('SoundPilot')])
            for t in tracks:
                for seg in t.get('segments',[]):
                    seg.pop('volume',None);seg.pop('last_nonzero_volume',None)
            return tracks
        self.assertEqual(visual_tracks(before),visual_tracks(current))
        self.assertEqual(s.caption_rows(before),s.caption_rows(current))
        effects=[x for t in current['tracks'] if t.get('name','').startswith('SoundPilot') for x in t['segments']]
        self.assertEqual(len(effects),15)
        fades={x['id']:x for x in current['materials']['audio_fades']}
        for effect in effects:
            applied=[fades[r] for r in effect['extra_material_refs'] if r in fades]
            self.assertEqual(len(applied),1)
            self.assertGreater(applied[0]['fade_out_duration'],0)
        s.validate_draft(current)

    def test_reinstall_rejects_changed_source(self):
        export=s.read_json(s.OUTPUTS/'test1'/'export.json')
        with patch('soundpilot.capcut_running',return_value=False):
            with self.assertRaisesRegex(ValueError,'changed'):
                s.install_into_empty_timeline(export['path'],'test 1','Timeline 01',reviewed_source=True)


if __name__=='__main__':unittest.main()
