"""lean=1 removes only machine-applied/bookkeeping fields; the Mac part reader is lossless."""
import copy,json,os,subprocess,sys,tempfile,unittest
BUNDLE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,BUNDLE)
import lean

def removed_paths(full,small,path=''):
    """Every key present in full but missing in small; fails if any kept value changed."""
    if isinstance(full,dict):
        assert isinstance(small,dict),path
        out=[path+'/'+k for k in full if k not in small]
        for k in small:
            if k=='lean_memory' and not path:continue
            assert k in full,path+'/'+k
            out+=removed_paths(full[k],small[k],path+'/'+k)
        return out
    if isinstance(full,list):
        assert isinstance(small,list) and len(full)==len(small),path
        return [p for a,b in zip(full,small) for p in removed_paths(a,b,path+'[]')]
    assert full==small,(path,full,small);return []

BRIEF={'captions':[{'start':1.0,'end':2.0,'text':'what'}],'source_dialogue':[{'role':'video_track_1','speech':[{'start':1,'end':2,'text':'What? No way.'}]}],
    'user_style':{'learned_feedback':[{'decision':'manual_choice','sound':'a.mp3','cue':'what','volume':.18609,'learned_version':3}],
        'mix_preferences':{'policy':'p','sound_levels':{'a.mp3':{'count':1,'normal_gain':.2,'soft_gain':.1,'emphasis_gain':.3,'median_duration':1.0,
            'references':[{'cue':'what','gain':.2,'duration':1.0,'gain_envelope':[{'offset':0,'duration':1.0,'gain':1.0}],'timeline':'Day 1'}]}}},
        'dialogue_level_references':[{'timeline':'Day 1','timeline_id':'X','roles':[{'role':'video_track_1','gain_spans':[{'path':'g:/a.mov','start':0,'duration':5,'volume':1.58}]}]}],
        'background_level_references':[{'timeline':'Day 1','timeline_id':'X','audio':[{'name':'bg','effective_gain':.06}]}]},
    'zoom_style':{'statistics':{'events':1},'references':[{'project':'p','timeline':'Day 1','timeline_id':'X','source_hash':'f'*64,'analysis_job_id':'j',
        'events':[{'role':'video_track_1','start':1.0,'end':2.0,'scale':1.3,'dx':0,'dy':-.07,'contexts':[{'role':'video_track_1','text':'What?'}]}]}],
        'framing_only_examples':[{'timeline':'Day 2','revision_hash':'e'*64,'analysis_job_id':'k','timeline_id':'Y','manual_scale':1.55}]}}

class LeanTests(unittest.TestCase):
    def test_default_is_unchanged(self):
        rows=[copy.deepcopy(BRIEF)];self.assertIs(lean.apply(rows,0),rows)

    def test_level1_drops_only_machine_applied_fields(self):
        small=lean.apply([copy.deepcopy(BRIEF)],1)[0]
        names={p.rsplit('/',1)[1] for p in removed_paths(BRIEF,small)}
        self.assertEqual(names,{'gain_envelope','timeline_id','path','source_hash','analysis_job_id','revision_hash'})
        self.assertEqual(small['user_style']['learned_feedback'],BRIEF['user_style']['learned_feedback'])
        self.assertEqual(small['captions'],BRIEF['captions']);self.assertEqual(small['lean_memory']['level'],1)

    def test_level1_on_a_real_brief_if_present(self):
        path=os.path.expanduser('~/SoundPilotLearning/jobs/14bae7ad87744687/enhanced_brief.json')
        if not os.path.exists(path):self.skipTest('no frozen brief on this machine')
        full=json.load(open(path,encoding='utf-8'));small=lean.apply([copy.deepcopy(full)],1)[0]
        names={p.rsplit('/',1)[1] for p in removed_paths(full,small)}
        self.assertTrue(names<= {'gain_envelope','timeline_id','path','source_hash','analysis_job_id','revision_hash'},names)

    def test_stage_reads_levels_from_frozen_profile_not_transport(self):
        # stage_plan fills volume/duration/envelope from the job's profile.json, so dropping
        # them from what the planner reads cannot change a staged plan.
        src=open(os.path.join(BUNDLE,'service.py'),encoding='utf-8').read()
        self.assertIn("profile=s.read_json(folder/'profile.json');learned_levels=profile.get('mix_preferences',{}).get('sound_levels',{})",src)
        self.assertIn("refs=learned['references'];closest=min(refs",src)

    def test_part_reader_round_trips(self):
        value={'rows':[{'text':'x'*4000,'n':i,'w':'কি? ewww'} for i in range(60)],'tail':[1.5,None,True]}
        with tempfile.TemporaryDirectory() as d:
            src=os.path.join(d,'mcp-capcut-sfx-learning-get_edit_briefs-1.txt')
            json.dump([{'type':'text','text':json.dumps(value)}],open(src,'w',encoding='utf-8'))
            env={**os.environ,'SOUNDPILOT_STATE':d}
            out=json.loads(subprocess.check_output([sys.executable,os.path.join(BUNDLE,'tools','read_parts.py'),src,'--chars','20000'],env=env))
            text=''.join(open(p,encoding='utf-8').read() for p in out['parts'])
            self.assertGreater(out['part_count'],1)
            self.assertTrue(all(len(l)<=1500 for p in out['parts'] for l in open(p,encoding='utf-8').read().split('\n')))
            self.assertEqual(json.loads(text.replace('\n','')),value)

if __name__=='__main__':unittest.main()
