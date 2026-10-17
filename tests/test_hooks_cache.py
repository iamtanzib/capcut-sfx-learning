"""Native hook preservation, combined modes, and seven-day cache correctness."""
import unittest,copy,json,time
from pathlib import Path
from unittest.mock import patch
import test_zoom as zoom_tests
import hooks,analysis_cache as ac,edit_modes,context_pipeline as c
a=zoom_tests.a

class HookCacheTests(unittest.TestCase):
    def test_hook_auto_close_then_apply_preserves_other_tracks(self):
        import app_lifecycle as life
        self.staged();state={'running':True}
        def close():state['running']=False;return [{'close_requested':True}]
        with patch.object(a.s,'capcut_running',side_effect=lambda:state['running']),patch.object(life,'request_close',side_effect=close),patch.object(life.time,'sleep'):
            result=edit_modes.apply_hooks(a,[self.hid])
        self.assertTrue(result['capcut_close']['auto_close_requested'])
        updated=a.s.read_json(self.file)
        self.assertEqual(updated['tracks'],self.draft['tracks'])
        self.assertEqual(hooks.text(updated['materials']['texts'][0]),self.hook['text'])

    def test_keep_existing_noop_leaves_capcut_open(self):
        import app_lifecycle as life
        draft=copy.deepcopy(self.draft);mat=draft['materials']['texts'][0]
        content=hooks.parsed(mat);content['text']='THAT IS WILD';mat['content']=json.dumps(content)
        a.s.write_json(self.file,draft);a.s.write_json(self.pr/'draft_content.json',draft)
        fresh=hooks.prepare(a,[{'project':'project0','timeline':'test0','analysis_job_id':self.job}])
        hid=fresh['jobs'][0];hooks.stage(a,hid,{'action':'keep_existing'},self.notes);hooks.preview(a,hid)
        before=self.file.read_bytes()
        with patch.object(a.s,'capcut_running',return_value=True),patch.object(life,'request_close') as close:
            result=edit_modes.apply_hooks(a,[hid])
        close.assert_not_called();self.assertEqual(result['files_written'],0);self.assertEqual(self.file.read_bytes(),before)

    def setUp(self):
        self.fixture=zoom_tests.ZoomTests();self.fixture.setUp();self.job=self.fixture.job;self.pr=self.fixture.project;self.file=self.fixture.path
        self.draft=copy.deepcopy(self.fixture.draft);self.font=a.ROOT/'assets/fonts/Rubik-Bold.ttf'
        mat={'id':'hook-mat','type':'text','recognize_type':0,'font_path':str(self.font),'font_size':15,'background_alpha':1,'background_color':'#000000',
            'line_spacing':-.2,'letter_spacing':-.05,'alignment':1,'fixed_width':755,'content':json.dumps({'text':'','styles':[{'range':[0,0],'font':{'path':str(self.font)},'size':15,'fill':{'content':{'solid':{'color':[1,1,1]}}}}]})}
        seg={'id':'hook-segment','material_id':mat['id'],'target_timerange':{'start':0,'duration':10_000_000},'source_timerange':None,'extra_material_refs':[],
            'clip':{'scale':{'x':1.25,'y':1.25},'transform':{'x':0,'y':.14},'rotation':0,'alpha':1}}
        self.draft['materials']['texts']=[mat];self.draft['tracks'].append({'id':'hook-track','type':'text','segments':[seg]})
        a.s.write_json(self.file,self.draft);a.s.write_json(self.pr/'draft_content.json',self.draft)
        r=a.job_data(self.job);r['source_hash']=a.digest(self.file);a.s.write_json(a.job_path(self.job)/'job.json',r);a.s.write_json(a.job_path(self.job)/'source.json',self.draft)
        a.s.write_json(a.s.DATA/'hook_style.json',a.s.read_json(a.ROOT/'seed/hook_style.json'))
        self.batch=hooks.prepare(a,[{'project':'project0','timeline':'test0','analysis_job_id':self.job}]);self.hid=self.batch['jobs'][0]
        self.hook={'text':'THAT IS WILD\nWHAT DID YOU GET?','highlight_phrases':['WILD'],'evidence':{'role':'video_track_2','quote':'that is wild'},'reason':'The complete original intro says that is wild; retain the user question style.'}
        self.notes={'intro_reviewed':True,'unresolved':[],'layout_reviewed':True}
    def staged(self):
        hooks.stage(a,self.hid,self.hook,self.notes);hooks.preview(a,self.hid)

    def test_only_content_changes_with_exact_native_settings_and_other_tracks(self):
        self.staged();result=hooks.validated(a,self.hid,self.draft)
        before=copy.deepcopy(self.draft);after=copy.deepcopy(result);before['materials']['texts'][0].pop('content');after['materials']['texts'][0].pop('content')
        self.assertEqual(before,after);self.assertEqual(hooks.highlights(result['materials']['texts'][0]),['WILD'])
        self.assertEqual(hooks.text(result['materials']['texts'][0]),self.hook['text'])

    def test_filled_manual_hook_fabricated_quote_and_bad_topic_block(self):
        r=hooks.record(a,self.hid);r['existing_text']='MANUAL';a.s.write_json(hooks.path(a,self.hid)/'job.json',r)
        with self.assertRaisesRegex(ValueError,'protected'):hooks.stage(a,self.hid,self.hook,self.notes)
        r['existing_text']='';a.s.write_json(hooks.path(a,self.hid)/'job.json',r)
        fake=copy.deepcopy(self.hook);fake['evidence']['quote']='fabricated topic'
        with self.assertRaisesRegex(ValueError,'real cached'):hooks.stage(a,self.hid,fake,self.notes)
        fake=copy.deepcopy(self.hook);fake['text']='ALIENS ARE HERE';fake['highlight_phrases']=['ALIENS']
        with self.assertRaisesRegex(ValueError,'grounded'):hooks.stage(a,self.hid,fake,self.notes)

    def test_hook_apply_closed_guard_rollback_and_revision_adoption(self):
        self.staged();before=self.file.read_bytes()
        with patch.object(a.s,'capcut_running',return_value=True),self.assertRaisesRegex(ValueError,'Quit CapCut'):edit_modes.apply_hooks(a,[self.hid],auto_close=False)
        self.assertEqual(before,self.file.read_bytes())
        with patch.object(a.s,'capcut_running',return_value=False):edit_modes.apply_hooks(a,[self.hid])
        d=a.s.read_json(self.file);material=d['materials']['texts'][0];content=hooks.parsed(material);content['text']='THIS IS WILD\nWHAT DID YOU GET?';material['content']=json.dumps(content);a.s.write_json(self.file,d)
        revised=self.file.read_bytes();v=hooks.learn_revision(a,self.hid)
        self.assertTrue(v['wording_changed']);self.assertEqual(revised,self.file.read_bytes());self.assertTrue(hooks.learn_revision(a,self.hid)['already_learned'])

    def test_seven_day_expiry_without_extension_and_source_invalidation(self):
        ac.register(a,self.job);original=ac.index(a)['entries'][self.job]['expires_at']
        found=ac.find(a,self.pr,self.draft,self.job);self.assertEqual(found['entry']['expires_at'],original)
        report=a.s.read_json(a.job_path(self.job)/'context_report.json');report['analysis_created_at']=time.time()-ac.TTL-1;a.s.write_json(a.job_path(self.job)/'context_report.json',report)
        with self.assertRaises(LookupError):ac.find(a,self.pr,self.draft,self.job)
        self.assertTrue(ac.find(a,self.pr,self.draft,self.job,allow_expired=True))
        Path(self.draft['materials']['videos'][0]['path']).write_bytes(b'new bytes')
        with self.assertRaisesRegex(ValueError,'source media'):ac.find(a,self.pr,self.draft,self.job)

    def test_hook_text_and_zoom_split_do_not_invalidate_speech(self):
        self.staged();changed=hooks.validated(a,self.hid,self.draft)
        import zoom
        plan=a.s.read_json(zoom.folder(a,self.fixture.zid)/'plan.json');changed=zoom.apply_native(a,changed,plan)
        cached=ac.find(a,self.pr,changed,self.job);mapped=ac.mapped_report(a,cached,changed)
        self.assertTrue(mapped['analysis_reused']);self.assertEqual(mapped['tracks'][0]['speech'][0]['text'],'that is wild')
        clone=self.pr/'Timelines/clone';clone.mkdir();a.s.write_json(clone/'draft_content.json',changed)
        self.assertTrue(ac.find(a,self.pr,changed))

    def test_trim_mapping_refreshes_visuals_and_keeps_scene_intersection(self):
        cached=ac.find(a,self.pr,self.draft,self.job);cached['report']['scenes']=[{'role':f'video_track_{i}','scenes':[{'start':0,'end':10}]} for i in (1,2)]
        d=copy.deepcopy(self.draft);d['duration']=4_000_000
        for t in d['tracks'][:2]:t['segments'][0]['source_timerange']={'start':4_000_000,'duration':4_000_000};t['segments'][0]['target_timerange']={'start':0,'duration':4_000_000}
        before=copy.deepcopy(self.draft);mapping=a.ra.TimelineMap(before,d);cached['mapping']=mapping
        report=ac.mapped_report(a,cached,d);self.assertTrue(report['visual_refresh_required']);self.assertEqual(report['scenes'][0]['scenes'],[{'start':0.0,'end':4.0}])

    def test_modes_do_not_require_unselected_components(self):
        self.assertEqual(edit_modes.mode('just sfz'),'just_sfx');self.assertEqual(edit_modes.mode('just zoom line'),'just_zoom')
        with patch.object(a,'prepare_batch',return_value={'batch_id':a.ident(),'jobs':[self.job]}) as call:
            edit_modes.prepare(a,[self.fixture.target],'just text hook');self.assertFalse(call.call_args.kwargs['include_zoom']);self.assertFalse(call.call_args.kwargs['include_hook'])
            edit_modes.prepare(a,[self.fixture.target],'full combo edit');self.assertTrue(call.call_args.kwargs['include_zoom']);self.assertTrue(call.call_args.kwargs['include_hook'])
        with self.assertRaises(ValueError):edit_modes.mode('delete everything')

    def test_full_combo_build_has_sfx_zoom_and_hook_without_second_analysis(self):
        r=a.job_data(self.job);r['hook_required']=True;a.s.write_json(a.job_path(self.job)/'job.json',r)
        effect=a.s.read_json(a.job_path(self.job)/'plan.json')['effects'][0]
        with self.assertRaisesRegex(ValueError,'text-hook'):a.stage_plan(self.job,[effect],self.fixture.notes,[self.fixture.event],self.fixture.notes)
        result=a.stage_plan(self.job,[effect],self.fixture.notes,[self.fixture.event],self.fixture.notes,self.hook,self.notes)
        r=a.job_data(self.job);hooks.preview(a,r['hook_job_id']);self.fixture.audit(r['zoom_job_id'])
        plan=a.s.read_json(a.job_path(self.job)/'plan.json');plan['master_gain']=1;a.s.write_json(a.job_path(self.job)/'plan.json',plan);a.s.write_json(a.job_path(self.job)/'mix.json',{'plan_hash':a.digest(a.job_path(self.job)/'plan.json')})
        with patch.object(c,'prepare',side_effect=AssertionError('Do not analyze again')):draft=a.build_changes(self.job)[self.file]
        self.assertEqual(len(draft['tracks'][0]['segments']),3);self.assertEqual(hooks.text(draft['materials']['texts'][0]),self.hook['text']);self.assertEqual(len(list(a.s.flatten_sfx(draft,self.fixture.fixture.catalog,self.pr))),1)

    def test_utf16_highlight_ranges_preserve_unicode(self):
        template=a.s.read_json(hooks.path(a,self.hid)/'template.json');v=hooks.style_runs(template['material'],template,'🤔 WILD',['WILD'])
        self.assertEqual(v['styles'][1]['range'],[3,7])

if __name__=='__main__':unittest.main()
