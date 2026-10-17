"""Meaningful safety/information tests; all writes are synthetic temporary drafts."""
import os,tempfile,sys,json,copy,unittest
from pathlib import Path
from unittest.mock import patch
TMP=tempfile.TemporaryDirectory();os.environ['SOUNDPILOT_STATE']=str(Path(TMP.name)/'state')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import service as a
import revision_audio as ra

class WorkflowTests(unittest.TestCase):
    def test_own_footage_excludes_legacy_rule_timestamps(self):
        profile={'learned_feedback':[{'video_signature':'own','reference':'receipt-a'},{'video_signature':'other','reference':'receipt-b'}],
            'revision_rules':[{'rule':'own at12.3','reference':'receipt-a'},{'rule':'other at4.2','reference':'receipt-b'},{'rule':'generic process rule'}]}
        feedback,rules=a.scene_memory_for_video(profile,'own')
        self.assertEqual(len(feedback),1)
        self.assertEqual([r['rule'] for r in rules],['other at4.2','generic process rule'])

    def test_strict_timing_does_not_hide_half_second_retime(self):
        result=a.revision_diff([{'sound':'x','start':5}],[{'sound':'x','start':5.5}])
        self.assertEqual(result['precision'],1)
        self.assertEqual(result['timing']['strict_precision'],0)
        self.assertEqual(len(result['timing']['retimed_matches']),1)
        substitution=a.revision_diff([{'sound':'x','start':5}],[{'sound':'y','start':5.1}])
        self.assertEqual(substitution['precision'],0)
        self.assertEqual(substitution['review_candidates'][0]['kind'],'possible_substitution')
        self.assertTrue(substitution['review_candidates'][0]['requires_context_review'])

    def test_new_split_tail_preserves_gap_and_source_position(self):
        first={'sound':'MMMMMM.mp3','path':'same.mp3','source_start':0,'start':59.866666,'duration':.966667,'volume':.3,'speed':1,'segment':{'id':'first'}}
        tail={**first,'source_start':.966666,'start':60.933333,'duration':.033333,'segment':{'id':'new-tail'}}
        events=ra.logical_events([first,tail]);self.assertEqual(len(events),1)
        rendered=ra.render_plan({'effects':[{**events[0],'fade_in':0,'fade_out':0}]})['effects']
        self.assertAlmostEqual(rendered[1]['start'],60.933333)
        self.assertAlmostEqual(rendered[1]['source_start'],.966666)
        # A repeated attack must remain a separate cue, even using the same file.
        self.assertEqual(len(ra.logical_events([first,{**tail,'source_start':0}])),2)
        self.assertEqual(len(ra.logical_events([first,{**tail,'path':'different.mp3'}])),2)

    def test_frozen_envelope_proves_new_id_attack_and_long_body(self):
        first={'sound':'bell','path':'same.mp3','source_start':0,'start':59.3,'duration':.333333,'volume':.36,'speed':1,'segment':{'id':'attack'}}
        body={**first,'source_start':.333333,'start':59.633333,'duration':1.766667,'volume':.23,'segment':{'id':'new-body'}}
        ref={'sound':'bell','start':59.28,'source_start':0,'speed':1,'gain_envelope':[
            {'offset':0,'duration':.333334,'gain':1},{'offset':.333334,'source_offset':.333334,'duration':1.766666,'gain':.635}]}
        self.assertEqual(len(ra.logical_events([first,body])),2)
        events=ra.logical_events([first,body],[ref]);self.assertEqual(len(events),1)
        self.assertAlmostEqual(events[0]['duration'],2.1)
        self.assertAlmostEqual(events[0]['gain_envelope'][1]['gain'],.23/.36)
        self.assertEqual(len(events[0]['gain_parts']),2)
        for changed in ({**body,'source_start':0},{**body,'path':'different.mp3'},
                        {**body,'duration':1.3},{**body,'start':59.9}):
            self.assertEqual(len(ra.logical_events([first,changed],[ref])),2)
        self.assertEqual(len(ra.logical_events([first,body,{**body,'segment':{'id':'duplicate'}}],[ref])),3)
        moved=[{**first,'start':65.3},{**body,'start':65.633333}]
        self.assertEqual(len(ra.logical_events(moved,[ref])),2)

    def test_revision_learns_native_envelope_body_as_part_of_one_cue(self):
        job=self.jobs[0];folder=a.job_path(job);plan=a.s.read_json(folder/'plan.json')
        effect=plan['effects'][0];effect['duration']=2
        effect['gain_envelope']=[{'offset':0,'duration':.333334,'gain':1},{'offset':.333334,'duration':1.666666,'gain':.3}]
        a.stage_plan(job,[effect],{'whole_video_reviewed':True,'silence_reviewed':True,'unresolved':[]})
        a.s.write_json(folder/'mix.json',{'plan_hash':a.digest(folder/'plan.json')})
        with patch.object(a.s,'capcut_running',return_value=False):a.apply_batch(self.batch)
        result=a.learn_revision(job,'project0','test0')
        self.assertEqual(result['old_cues'],1);self.assertEqual(result['manual_cues'],1)
        self.assertEqual(result['native_sfx_pieces'],2)
        self.assertEqual(result['sound_level_changes'][0]['manual_duration'],2)
        feedback=a.s.read_json(a.s.DATA/'style_profile.json')['learned_feedback']
        choices=[f for f in feedback if f['reference']==result['reference'] and f['decision']=='manual_choice']
        self.assertEqual(len(choices),1);self.assertEqual(len(choices[0]['gain_envelope']),2)

    def test_word_audit_ignores_long_sentence_start(self):
        brief={'captions':[{'start':54.1,'end':55.5,'text':'yeah you might be cooked'}]}
        report={'tracks':[{'role':'video_track_1','speech':[{'start':51.5,'text':'Bro what yeah you might be cooked','words':[
            {'start':51.5,'end':51.9,'text':'Bro'},{'start':51.94,'end':52.2,'text':'what'},
            {'start':54.16,'end':54.44,'text':'yeah'},{'start':54.44,'end':54.52,'text':'you'},
            {'start':54.52,'end':54.66,'text':'might'},{'start':54.66,'end':54.78,'text':'be'},{'start':54.78,'end':55,'text':'cooked'}]}]}]}
        self.assertEqual(a.timing_audit(brief,report)['warnings'],[])
        brief['captions'][0]['start']=53.5
        warning=a.timing_audit(brief,report)['warnings'][0]
        self.assertEqual(warning['speech_at'],54.16)

    def test_new_job_requires_real_anchor_and_offset_reason(self):
        job=self.jobs[0];folder=a.job_path(job);record=a.job_data(job);record['plan_schema_version']=2;a.s.write_json(folder/'job.json',record)
        a.s.write_json(folder/'context_report.json',{'tracks':[{'role':'video_track_1','speech':[{'start':1,'end':2,'text':'fire','words':[{'start':1,'end':1.4,'text':'fire'}]}]}]})
        effect=a.s.read_json(folder/'plan.json')['effects'][0];notes={'whole_video_reviewed':True,'silence_reviewed':True,'unresolved':[]}
        with self.assertRaisesRegex(ValueError,'timing_anchor'):a.stage_plan(job,[effect],notes)
        effect['timing_anchor']={'kind':'speech_word','role':'video_track_1','at':1,'word_index':0,'text':'fire'}
        a.stage_plan(job,[effect],notes)
        effect['timing_anchor']['at']=1.2
        with self.assertRaisesRegex(ValueError,'frozen speech'):a.stage_plan(job,[effect],notes)
        effect['timing_anchor']['at']=1;effect['start']=1.5
        with self.assertRaisesRegex(ValueError,'150ms'):a.stage_plan(job,[effect],notes)
        effect['timing_anchor']['offset_reason']='Deliberately place the release after the emphasized fire syllable.'
        a.stage_plan(job,[effect],notes)

    def test_manual_retime_does_not_inherit_model_cue_label(self):
        job=self.jobs[0];folder=a.job_path(job)
        with patch.object(a.s,'capcut_running',return_value=False):a.apply_batch(self.batch)
        draft=a.s.read_json(self.paths[0]);draft['tracks'][-1]['segments'][0]['target_timerange']['start']=1_500_000;a.s.write_json(self.paths[0],draft)
        a.s.write_json(folder/'context_report.json',{'tracks':[{'role':'video_track_1','speech':[{'start':1.4,'end':1.8,'text':'actual reaction','words':[{'start':1.4,'end':1.6,'text':'actual'},{'start':1.6,'end':1.8,'text':'reaction'}]}]}]})
        result=a.learn_revision(job,'project0','test0')
        feedback=a.s.read_json(a.s.DATA/'style_profile.json')['learned_feedback']
        choice=next(f for f in feedback if f['reference']==result['reference'] and f['decision']=='manual_choice')
        self.assertEqual(choice['cue'],'actual reaction')
        self.assertEqual(choice['cue_source'],'mapped_manual_source_context')

    def setUp(self):
        self.root=Path(TMP.name)/a.ident();self.root.mkdir();self.drafts=self.root/'drafts';self.drafts.mkdir()
        sound=self.root/'MMMMMM.mp3';sound.write_bytes(b'fixture-only')
        self.catalog=[{'name':'MMMMMM.mp3','path':str(sound),'duration':2,'role':'sfx','tags':'approval'}]
        cfg=a.s.read_json(a.ROOT/'seed/config.json');cfg['draft_root']=str(self.drafts);cfg['library']=str(self.root);a.s.write_json(a.STATE/'config.json',cfg)
        profile=a.s.read_json(a.ROOT/'seed/style_profile.json');a.s.write_json(a.s.DATA/'style_profile.json',profile)
        # Controlled legacy fixture; exported personal memory can advance independently.
        profile['version']=8;profile.pop('mix_preferences',None);a.s.write_json(a.s.DATA/'style_profile.json',profile)
        example=a.s.read_json(a.ROOT/'seed/examples.json')[0];example['sound']='MMMMMM.mp3';example['volume']=.22;example['duration']=1
        a.s.write_json(a.s.DATA/'examples.json',[example]);a.s.write_json(a.s.DATA/'sound_catalog.json',self.catalog)
        self.jobs=[];self.paths=[]
        for n in range(5):
            name=f'project{n//2}';project=self.drafts/name;tid=f'T{n}';folder=project/'Timelines'/tid;folder.mkdir(parents=True)
            draft={'id':tid,'duration':10_000_000,'materials':{'videos':[],'audios':[],'texts':[]},'tracks':[]}
            index_path=project/'Timelines'/'project.json'
            index=a.s.read_json(index_path) if index_path.exists() else {'main_timeline_id':tid,'timelines':[]}
            index['timelines'].append({'id':tid,'name':'test'+str(n)})
            for path,value in [(folder/'draft_content.json',draft),(project/'draft_content.json',draft),(index_path,index),(project/'draft_meta_info.json',{'draft_materials':[]})]:a.s.write_json(path,value)
            job=a.ident();out=a.job_path(job);out.mkdir();record={'job_id':job,'project':name,'timeline':'test'+str(n),'timeline_id':tid,'source_hash':a.digest(folder/'draft_content.json'),'duration':10,'style_version':8,'status':'ready','has_existing_sfx':False}
            for filename,value in [('job.json',record),('source.json',draft),('profile.json',profile),('examples.json',[example]),('catalog.json',self.catalog),('enhanced_brief.json',{'captions':[],'source_dialogue':[]})]:a.s.write_json(out/filename,value)
            a.stage_plan(job,[{'sound':'MMMMMM.mp3','start':1,'duration':1,'dialogue':'that is fire','function':'approval','evaluation_polarity':'positive','reason':'Genuine positive appraisal of the object.','confidence':'high'}],{'whole_video_reviewed':True,'silence_reviewed':True,'unresolved':[]})
            plan=a.s.read_json(out/'plan.json');plan['master_gain']=.8;a.s.write_json(out/'plan.json',plan);a.s.write_json(out/'mix.json',{'plan_hash':a.digest(out/'plan.json')})
            self.jobs.append(job);self.paths.append(folder/'draft_content.json')
        self.batch=a.ident();a.s.write_json(a.STATE/'batches'/(self.batch+'.json'),{'jobs':self.jobs,'batch_id':self.batch,'workers':2})

    def test_five_targets_same_and_different_projects(self):
        with patch.object(a.s,'capcut_running',return_value=False):
            self.assertTrue(a.preflight_batch(self.batch)['valid']);result=a.apply_batch(self.batch)
        self.assertEqual(result['targets'],5)
        for path in self.paths:
            draft=a.s.read_json(path);effects=list(a.s.flatten_sfx(draft,self.catalog,path.parents[2]));self.assertEqual(len(effects),1);self.assertAlmostEqual(effects[0]['volume'],.22*.8)
        for project in self.drafts.iterdir():
            group=a.s.read_json(project/'draft_meta_info.json')['draft_materials'][0]
            self.assertEqual(len(group['value']),1)

    def test_one_stale_target_blocks_all_five_writes(self):
        source=a.s.read_json(self.paths[-1]);source['changed']=True;a.s.write_json(self.paths[-1],source)
        previous=[p.read_bytes() for p in self.paths]
        with patch.object(a.s,'capcut_running',return_value=False),self.assertRaisesRegex(ValueError,'Source changed'):a.apply_batch(self.batch)
        self.assertEqual(previous,[p.read_bytes() for p in self.paths])

    def test_open_capcut_blocks_every_write(self):
        previous=[p.read_bytes() for p in self.paths]
        with patch.object(a.s,'capcut_running',return_value=True),self.assertRaisesRegex(ValueError,'Quit CapCut'):a.apply_batch(self.batch,auto_close=False)
        self.assertEqual(previous,[p.read_bytes() for p in self.paths])

    def test_failure_restores_every_file(self):
        paths=list(a.batch_changes(a.batch_data(self.batch)));previous={p:p.read_bytes() for p in paths};write=a.s.write_json;calls=[]
        def broken(path,value):
            calls.append(path)
            if len(calls)==4:raise OSError('simulated write failure')
            return write(path,value)
        with patch.object(a.s,'capcut_running',return_value=False),patch.object(a.s,'write_json',side_effect=broken),self.assertRaises(OSError):a.apply_batch(self.batch)
        self.assertEqual(previous,{p:p.read_bytes() for p in paths})

    def test_revised_style_invalidates_old_plan(self):
        profile=a.s.read_json(a.s.DATA/'style_profile.json');profile['version']=9;a.s.write_json(a.s.DATA/'style_profile.json',profile)
        with patch.object(a.s,'capcut_running',return_value=False),self.assertRaisesRegex(ValueError,'Style changed'):a.apply_batch(self.batch)

    def test_user_sfx_not_overwritten(self):
        draft=a.s.read_json(self.paths[0]);plan=a.s.read_json(a.job_path(self.jobs[0])/'plan.json')
        a.s.add_effects(draft,plan,a.s.read_json(a.s.DATA/'examples.json'),self.catalog);a.s.write_json(self.paths[0],draft)
        record=a.job_data(self.jobs[0]);record['source_hash']=a.digest(self.paths[0]);a.s.write_json(a.job_path(self.jobs[0])/'job.json',record)
        plan['source_hash']=record['source_hash'];a.s.write_json(a.job_path(self.jobs[0])/'plan.json',plan);a.s.write_json(a.job_path(self.jobs[0])/'mix.json',{'plan_hash':a.digest(a.job_path(self.jobs[0])/'plan.json')})
        with patch.object(a.s,'capcut_running',return_value=False),self.assertRaisesRegex(ValueError,'already contains'):a.apply_batch(self.batch)

    def test_negative_agreement_cannot_pass_mmm(self):
        plan=a.s.read_json(a.job_path(self.jobs[0])/'plan.json');plan['effects'][0]['evaluation_polarity']='negative'
        with self.assertRaisesRegex(ValueError,'Negative appraisal'):a.s.validate_plan(plan,self.catalog)

    def test_unresolved_context_and_fake_review_cannot_bypass(self):
        job=self.jobs[0];effect=a.s.read_json(a.job_path(job)/'plan.json')['effects'][0]
        with self.assertRaisesRegex(ValueError,'uncertain'):a.stage_plan(job,[effect],{'whole_video_reviewed':True,'silence_reviewed':True,'unresolved':['why creepy?']})
        effect['user_reviewed']=True
        with self.assertRaisesRegex(ValueError,'Only actual'):a.stage_plan(job,[effect],{'whole_video_reviewed':True,'silence_reviewed':True,'unresolved':[]})

    def test_maximum_matching_avoids_greedy_mismatch(self):
        result=a.revision_diff([{'sound':'x','start':0},{'sound':'x','start':.6}],[{'sound':'x','start':.3},{'sound':'x','start':1.2}],.75)
        self.assertEqual(len(result['matches']),2)

    def test_compact_preserves_all_semantic_fields(self):
        value={'tracks':[{'role':'one','rows':[{'start':1.234567,'end':2,'text':'not bad'}, {'start':3,'end':4,'text':'ewww'}]}],'negative':[{'cue':'not comfortable','decision':'error'}],'rules':['silence is valid']}
        self.assertEqual(a.unpack(a.pack(value)),value)

    def test_shared_batch_preserves_per_video_exceptions(self):
        rows=[{'rules':{'mmm':'approval','case':str(i)},'dialogue':[{'text':'unique '+str(i),'start':i}], 'optional':False} for i in range(5)]
        rows[-1].pop('optional');common=a.shared_fields(rows)
        for row in rows:self.assertEqual(a.merge(common,a.difference(row,common)),row)
        self.assertNotIn('optional',common);self.assertEqual(common['rules'],{'mmm':'approval'})

    def test_revision_commits_once_and_never_edits_manual(self):
        job=self.jobs[0];draft=a.s.read_json(self.paths[0]);plan=a.s.read_json(a.job_path(job)/'plan.json')
        plan['effects'][0]['start']=1.3;a.s.add_effects(draft,plan,a.s.read_json(a.s.DATA/'examples.json'),self.catalog);a.s.write_json(self.paths[0],draft)
        before=self.paths[0].read_bytes()
        first=a.learn_revision(job,'project0','test0',[{'rule':'This onset follows the visible reaction.','evidence':'User moved onset +0.3 seconds.','scope':'scene_only','authority':'scene_inference'}])
        second=a.learn_revision(job,'project0','test0')
        self.assertTrue(second['already_learned']);self.assertEqual(first['new_style_version'],9);self.assertEqual(before,self.paths[0].read_bytes())
        self.assertIn('extras',a.s.read_json(a.s.DATA/'examples.json')[-1]);self.assertNotIn('materials',a.s.read_json(a.s.DATA/'examples.json')[-1])
        old_count=len(a.s.read_json(a.s.DATA/'examples.json'))
        # Another saved manual retime should replace the old truth, not duplicate it.
        generated=draft['tracks'][-1]['segments'][0];generated['target_timerange']['start']+=100_000;a.s.write_json(self.paths[0],draft)
        third=a.learn_revision(job,'project0','test0')
        self.assertEqual(third['new_style_version'],10);self.assertEqual(old_count,len(a.s.read_json(a.s.DATA/'examples.json')))

    def test_caption_edit_reuses_media_cache_but_media_edit_invalidates(self):
        import context_pipeline as c
        src=self.root/'video.mov';src.write_bytes(b'fixture media')
        draft={'duration':10_000_000,'materials':{'videos':[{'id':'v','path':str(src)}],'texts':[{'id':'t','type':'subtitle','recognize_text':'eww'}]},
            'tracks':[{'type':'video','segments':[{'material_id':'v','target_timerange':{'start':0,'duration':10_000_000},'source_timerange':{'start':0,'duration':10_000_000}}]},
            {'type':'text','segments':[{'material_id':'t','target_timerange':{'start':1_000_000,'duration':1_000_000}}]}]}
        inputs,key=c.context_inputs(self.drafts/'project0',draft)
        draft['tracks'][1]['segments'][0]['target_timerange']['start']+=200_000
        new_inputs,new_key=c.context_inputs(self.drafts/'project0',draft)
        self.assertEqual(key,new_key);self.assertNotEqual(inputs['captions'],new_inputs['captions'])
        src.write_bytes(b'changed actual media')
        self.assertNotEqual(key,c.context_inputs(self.drafts/'project0',draft)[1])

    def test_real_mix_headroom_fades_and_final_gain(self):
        import wave,math,struct
        def tone(path,gain):
            with wave.open(str(path),'wb') as wav:
                wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(48000)
                wav.writeframes(b''.join(struct.pack('<hh',int(32767*gain*math.sin(i*2*math.pi*440/48000)),int(32767*gain*math.sin(i*2*math.pi*440/48000))) for i in range(96000)))
        tone(Path(self.catalog[0]['path']),.9);voice=self.root/'voice.wav';tone(voice,.95)
        draft=a.s.read_json(self.paths[0]);draft['materials']['audios']=[{'id':'voice','path':str(voice),'name':'voice.wav'}]
        draft['tracks']=[{'type':'audio','segments':[{'id':'seg','material_id':'voice','volume':1,'target_timerange':{'start':0,'duration':2_000_000},'source_timerange':{'start':0,'duration':2_000_000}}]}]
        a.s.write_json(self.paths[0],draft);job=self.jobs[0];folder=a.job_path(job);record=a.job_data(job);record['source_hash']=a.digest(self.paths[0]);a.s.write_json(folder/'job.json',record)
        plan=a.s.read_json(folder/'plan.json');plan['source_hash']=record['source_hash'];plan['effects'][0]['volume']=.8;a.s.write_json(folder/'plan.json',plan)
        report=a.audit_mix(job);self.assertLess(report['master_gain'],1);self.assertAlmostEqual(report['peak_after'],.891,places=5)
        with wave.open(report['preview'],'rb') as wav:self.assertEqual(wav.getnframes(),480000)
        with patch.object(a.s,'capcut_running',return_value=False):changes=a.build_changes(job)
        installed=changes[self.paths[0]];self.assertAlmostEqual(installed['tracks'][0]['segments'][0]['volume'],report['master_gain'])
        profile=a.s.read_json(folder/'profile.json');profile['mix_preferences']={'automatic_whole_mix_attenuation':False};a.s.write_json(folder/'profile.json',profile)
        report=a.audit_mix(job);self.assertTrue(report['headroom_review_required']);self.assertEqual(a.s.read_json(folder/'plan.json')['master_gain'],1)
        with self.assertRaisesRegex(ValueError,'silently reduce'):a.build_changes(job)
        plan=a.s.read_json(folder/'plan.json');plan['quality_notes']['headroom_mode']='uniform_attenuation';plan['quality_notes']['headroom_reason']='Deliberate shared attenuation preserves this chosen relative mix balance.';a.s.write_json(folder/'plan.json',plan)
        report=a.audit_mix(job);self.assertFalse(report['headroom_review_required']);self.assertLess(report['master_gain'],1)

    def test_blank_compound_path_and_parent_gain_are_not_lost(self):
        child={'materials':{'audios':[{'id':'s','name':'MMMMMM.mp3','path':self.catalog[0]['path']}], 'drafts':[]},
            'tracks':[{'type':'audio','segments':[{'id':'leaf','material_id':'s','volume':.2,'speed':1,'target_timerange':{'start':0,'duration':1_000_000},'source_timerange':{'start':0,'duration':1_000_000}}]}]}
        draft={'materials':{'audios':[{'id':'parent','name':'Compound','path':''}],'drafts':[{'id':'D','combination_id':'C','draft':child}]},
            'tracks':[{'type':'audio','segments':[{'id':'outer','material_id':'parent','volume':1.5,'extra_material_refs':['D'],'target_timerange':{'start':2_000_000,'duration':1_000_000},'source_timerange':{'start':0,'duration':1_000_000}}]}]}
        result=list(a.s.flatten_sfx(draft,self.catalog,self.drafts/'project0'))
        self.assertEqual(len(result),1);self.assertAlmostEqual(result[0]['volume'],.3);self.assertEqual(result[0]['start'],2);self.assertEqual(result[0]['compound_gain'],1.5)

    def test_compound_pieces_form_one_event_with_attack_body_levels(self):
        base={'sound':'bell','source_start':0,'start':0,'duration':.3,'volume':.7,'speed':1,'segment':{'id':'same'},'compound_gain':1.4,'leaf_volume':.5}
        rows=[base,{**base,'start':.3,'source_start':.3,'duration':1.7,'volume':.2,'compound_gain':.4}]
        events=ra.logical_events(rows);self.assertEqual(len(events),1);self.assertEqual(events[0]['duration'],2)
        self.assertAlmostEqual(events[0]['gain_envelope'][1]['gain'],.2/.7)
        rendered=ra.render_plan({'effects':[{'sound':'bell','start':5,'duration':2,'source_start':0,'speed':1,'volume':.7,'gain_envelope':events[0]['gain_envelope'],'fade_in':.01,'fade_out':.2}]})['effects']
        self.assertEqual(len(rendered),2);self.assertAlmostEqual(rendered[1]['volume'],.2);self.assertEqual(rendered[1]['fade_in'],0);self.assertEqual(rendered[0]['fade_out'],0)

    def test_trim_and_split_mapping_rejects_unrelated_source(self):
        def draft(clips):
            return {'materials':{'videos':[{'id':'v','path':'same.mov'}]},'tracks':[{'type':'video','segments':[{'material_id':'v','target_timerange':{'start':round(t*1e6),'duration':round(n*1e6)},'source_timerange':{'start':round(src*1e6),'duration':round(n*1e6)}} for t,src,n in clips]}]}
        old=draft([(0,0,20)]);new=draft([(0,0,8),(8,8.3,11.7)])
        mapping=ra.TimelineMap(old,new);self.assertAlmostEqual(mapping.old_time(0,10),10.3);self.assertAlmostEqual(mapping.new_time(0,10),9.7)
        self.assertAlmostEqual(mapping.old_time(0,8),8.3)
        new['materials']['videos'][0]['path']='unrelated.mov'
        with self.assertRaisesRegex(ValueError,'new, extended'):ra.TimelineMap(old,new)

    def test_recent_final_levels_override_old_low_defaults(self):
        job=self.jobs[0];folder=a.job_path(job);profile=a.s.read_json(folder/'profile.json')
        profile['mix_preferences']={'sound_levels':{'MMMMMM.mp3':{'normal_gain':.4,'soft_gain':.2,'emphasis_gain':.7,'median_duration':1,'references':[{'gain':.4,'duration':1,'gain_envelope':[]}]}}}
        a.s.write_json(folder/'profile.json',profile);effect=a.s.read_json(folder/'plan.json')['effects'][0];effect['volume']=.22;effect['gain_tier']='emphasis'
        a.stage_plan(job,[effect],{'whole_video_reviewed':True,'silence_reviewed':True,'unresolved':[]})
        self.assertEqual(a.s.read_json(folder/'plan.json')['effects'][0]['volume'],.7)

    def test_manual_gain_above_unity_and_new_fah_variant(self):
        profile=a.s.read_json(a.s.DATA/'style_profile.json');profile['authoritative_user_rules']['comic_line'].append('fahhh_KcgAXfs.mp3');a.s.write_json(a.s.DATA/'style_profile.json',profile)
        plan=a.s.read_json(a.job_path(self.jobs[0])/'plan.json');effect=plan['effects'][0];effect.update(sound='fahhh_KcgAXfs.mp3',function='comic_line',volume=1.122018)
        cat=[{**self.catalog[0],'name':'fahhh_KcgAXfs.mp3'}];a.s.validate_plan(plan,cat)
        effect['volume']=5
        with self.assertRaisesRegex(ValueError,'Invalid volume'):a.s.validate_plan(plan,cat)

    def test_default_envelope_fits_real_source_length(self):
        job=self.jobs[0];folder=a.job_path(job);profile=a.s.read_json(folder/'profile.json')
        profile['mix_preferences']={'sound_levels':{'MMMMMM.mp3':{'normal_gain':.4,'soft_gain':.2,'emphasis_gain':.7,'median_duration':4.2,'references':[{'gain':.4,'duration':4.2,'gain_envelope':[{'offset':0,'duration':2.1,'gain':1},{'offset':2.1,'duration':2.1,'gain':.3}]}]}}}
        a.s.write_json(folder/'profile.json',profile);e=a.s.read_json(folder/'plan.json')['effects'][0];e.pop('duration')
        a.stage_plan(job,[e],{'whole_video_reviewed':True,'silence_reviewed':True,'unresolved':[]})
        result=a.s.read_json(folder/'plan.json')['effects'][0];self.assertEqual(result['duration'],2);self.assertEqual(result['gain_envelope'][-1]['offset']+result['gain_envelope'][-1]['duration'],2)

    def test_deliberate_speaker_balance_is_distinct_from_sfx_gain(self):
        job=self.jobs[0];folder=a.job_path(job);draft=a.s.read_json(self.paths[0])
        draft['materials']['videos']=[{'id':'v1','path':'foreground.mov'},{'id':'v2','path':'narrator.mov'}]
        draft['tracks']=[{'type':'video','segments':[{'id':f's{i}','material_id':f'v{i}','volume':1,'target_timerange':{'start':0,'duration':10_000_000},'source_timerange':{'start':0,'duration':10_000_000}}]} for i in (1,2)]
        a.s.write_json(self.paths[0],draft);record=a.job_data(job);record['source_hash']=a.digest(self.paths[0]);a.s.write_json(folder/'job.json',record);a.s.write_json(folder/'source.json',draft)
        old=a.s.read_json(folder/'plan.json');notes={'whole_video_reviewed':True,'silence_reviewed':True,'unresolved':[],'dialogue_balance':{'video_track_1':1.3,'video_track_2':.6},'dialogue_balance_reason':'Foreground reaction should lead the softer narration in this measured mix.'}
        a.stage_plan(job,old['effects'],notes);plan=a.s.read_json(folder/'plan.json');plan['master_gain']=1;a.s.write_json(folder/'plan.json',plan);a.s.write_json(folder/'mix.json',{'plan_hash':a.digest(folder/'plan.json')})
        draft=a.build_changes(job)[self.paths[0]];self.assertEqual(draft['tracks'][0]['segments'][0]['volume'],1.3);self.assertEqual(draft['tracks'][1]['segments'][0]['volume'],.6)
        self.assertEqual(draft['tracks'][-1]['segments'][0]['volume'],.22)

if __name__=='__main__':unittest.main()
