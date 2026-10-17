"""Normal-close control and transactions use mock processes and temporary drafts."""
import copy,json,subprocess,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
import test_workflow as w
import app_lifecycle as life
import edit_modes
a=w.a

class ClosureTests(unittest.TestCase):
    def test_already_closed_and_explicit_optout_never_request(self):
        with patch.object(life,'request_close') as close:
            self.assertTrue(life.ensure_closed(lambda:False)['already_closed'])
            with self.assertRaisesRegex(ValueError,'Quit CapCut'):life.ensure_closed(lambda:True,False)
            close.assert_not_called()

    def test_waits_for_process_exit_and_checks_absence_twice(self):
        running=Mock(side_effect=[True,True,False,False])
        with patch.object(life,'request_close',return_value=[{'close_requested':True}]) as request,patch.object(life.time,'sleep'):
            result=life.ensure_closed(running)
        self.assertTrue(result['closed']);self.assertFalse(result['forced']);request.assert_called_once()
        self.assertEqual(running.call_count,4)

    def test_dialog_tray_refusal_times_out_without_escalation(self):
        with patch.object(life,'request_close',return_value=[{'close_requested':False}]) as request,patch.object(life.time,'monotonic',side_effect=[0,0,2]):
            with self.assertRaisesRegex(ValueError,'save/export dialog'):life.ensure_closed(lambda:True,timeout=1)
        request.assert_called_once()

    def test_closure_backend_failure_is_not_success(self):
        with patch.object(life,'request_close',side_effect=subprocess.TimeoutExpired('powershell',12)):
            with self.assertRaisesRegex(ValueError,'no files were written'):life.ensure_closed(lambda:True)
        with patch.object(life.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='[]')):
            with self.assertRaises(ValueError):life.request_close()

    def test_editor_to_home_transition_closes_new_window_once(self):
        running=Mock(side_effect=[True,True,False,False])
        with patch.object(life,'request_close',side_effect=[[{'window_handle':10,'close_requested':True}],[{'window_handle':20,'close_requested':True}]]) as close,patch.object(life.time,'sleep'),patch.object(life.time,'monotonic',side_effect=[0,0,0,2,2.1]):
            result=life.ensure_closed(running)
        self.assertEqual(result['close_requests'],2);self.assertEqual(close.call_args.args,([10],))

    def test_fixed_capcut_only_backend_never_forces_or_answers_dialogs(self):
        with patch.object(life.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='[{"close_requested":true,"process_id":123}]')) as run:
            self.assertEqual(life.request_close()[0]['process_id'],123)
        argv=run.call_args.args[0];script=argv[-1]
        self.assertIn("GetProcessesByName('CapCut')",script);self.assertIn('.CloseMainWindow()',script)
        for forbidden in ['.Kill(', 'Stop-Process','taskkill','SendKeys']:self.assertNotIn(forbidden,script)
        self.assertEqual(run.call_args.kwargs['creationflags'],0x08000000)

    def test_process_detection_failure_blocks_writes(self):
        with patch.object(a.s.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='')):
            with self.assertRaisesRegex(RuntimeError,'Cannot verify'):a.s.capcut_running()

    def test_all_modes_propagate_auto_close_and_optout(self):
        api=SimpleNamespace(apply_batch=Mock(),apply_zoom_batch=Mock())
        for mode,method in [('full_combo',api.apply_batch),('just_sfx',api.apply_batch),('just_zoom',api.apply_zoom_batch)]:
            rec={'mode':mode,'analysis_batch_id':'analysis','zoom_batch_id':'zoom'}
            with patch.object(edit_modes,'load',return_value=rec):edit_modes.apply(api,'batch',False)
            self.assertEqual(method.call_args.args[-1],False)
        with patch.object(edit_modes,'load',return_value={'mode':'just_text_hook','hook_jobs':['hook']}),patch.object(edit_modes,'apply_hooks') as hook:
            edit_modes.apply(api,'batch');hook.assert_called_once_with(api,['hook'],True)

class AutoApplyTests(unittest.TestCase):
    def setUp(self):
        self.fixture=w.WorkflowTests();self.fixture.setUp();self.batch=self.fixture.batch
        self.files=list(a.batch_changes(a.batch_data(self.batch)));self.before={p:p.read_bytes() for p in self.files}

    def test_invalid_plan_does_not_close_the_editor(self):
        job=self.fixture.jobs[0];mix=a.s.read_json(a.job_path(job)/'mix.json');mix['plan_hash']='bad';a.s.write_json(a.job_path(job)/'mix.json',mix)
        with patch.object(a,'close_for_apply') as close,self.assertRaisesRegex(ValueError,'audio audit'):a.apply_batch(self.batch)
        close.assert_not_called();self.assertEqual(self.before,{p:p.read_bytes() for p in self.files})

    def test_success_normal_close_before_any_draft_write(self):
        state={'running':True};write=a.s.write_json
        def close():state['running']=False;return [{'close_requested':True}]
        def guarded_write(path,value):
            if path in self.files:self.assertFalse(state['running'])
            return write(path,value)
        with patch.object(a.s,'capcut_running',side_effect=lambda:state['running']),patch.object(life,'request_close',side_effect=close),patch.object(life.time,'sleep'),patch.object(a.s,'write_json',side_effect=guarded_write):
            result=a.apply_batch(self.batch)
        self.assertTrue(result['installed']);self.assertTrue(result['capcut_close']['auto_close_requested'])

    def test_final_autosave_edit_is_preserved_and_blocks_stale_plan(self):
        changed=self.fixture.paths[-1];saved={}
        def close(auto_close):
            draft=a.s.read_json(changed);draft['manual_final_save']=True;a.s.write_json(changed,draft);saved['bytes']=changed.read_bytes()
            return {'closed':True}
        with patch.object(a,'close_for_apply',side_effect=close),self.assertRaisesRegex(ValueError,'Source changed'):a.apply_batch(self.batch)
        self.assertEqual(changed.read_bytes(),saved['bytes'])
        for p in self.files:
            if p!=changed:self.assertEqual(p.read_bytes(),self.before[p])

    def test_blocked_close_writes_no_project_files(self):
        with patch.object(a,'close_for_apply',side_effect=ValueError('save dialog blocked')),self.assertRaisesRegex(ValueError,'save dialog'):a.apply_batch(self.batch)
        self.assertEqual(self.before,{p:p.read_bytes() for p in self.files})

    def test_readonly_preflight_does_not_close_open_app(self):
        with patch.object(a.s,'capcut_running',return_value=True),patch.object(a,'close_for_apply') as close:
            result=a.preflight_batch(self.batch)
        self.assertTrue(result['valid']);self.assertTrue(result['capcut_running']);close.assert_not_called()
        self.assertEqual(self.before,{p:p.read_bytes() for p in self.files})

if __name__=='__main__':unittest.main()
