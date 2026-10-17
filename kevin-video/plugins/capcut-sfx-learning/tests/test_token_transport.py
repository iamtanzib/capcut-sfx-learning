"""Exact context preservation across compact tables and pooled cue windows."""
import copy,json,unittest
import test_workflow as workflow
a=workflow.a

class TokenTransportTests(unittest.TestCase):
    def test_mixed_tables_keep_every_row_field_precision_and_order(self):
        value=[{'decision':'removed','scope':'Scene only','at':12.345678,'text':'কি? ewww — no!'} for _ in range(8)]
        value += [{'decision':'manual','scale':1.1940677966101696,'gain':.079123,'negative':False,'words':['full','context']} for _ in range(8)]
        packed=a.pack(value)
        self.assertIn('$segments',packed);self.assertEqual(a.unpack(packed),value)
        reordered=[{'start':1.123456,'word':'fire'},{'word':'no','start':2.987654}]
        self.assertEqual(a.unpack(a.pack(reordered)),reordered)

    def test_literal_format_keys_cannot_be_mistaken_for_transport(self):
        values=[{'$segments':[[{'actual':'data'}]]},{'$columns':['real'],'$rows':[['literal']]},{'$literal':{'$segments':[1,2]}},
            {'$defaults':{'cue':'literal'},'$columns':['x'],'$rows':[[1]]}]
        for value in values:self.assertEqual(a.unpack(a.pack(value)),value)

    def test_inherited_columns_preserve_negative_evidence_and_every_row(self):
        shared={'rule':'Negative agreement is rejection; MMM needs actual approval.','gain':[.079123456789,1.1940677966101696],'reviewed':False}
        values=[{'style':copy.deepcopy(shared),'cue':i,'scope':'Scene-specific, never a global keyword ban.'} for i in range(12)]
        packed=a.pack(values)
        self.assertIn('$defaults',packed);self.assertEqual(len(packed['$rows']),12)
        result=a.unpack(packed);self.assertEqual(result,values)
        result[0]['style']['gain'][0]=0
        self.assertEqual(result[1]['style']['gain'],shared['gain'])
        self.assertEqual(packed['$defaults']['style']['gain'],shared['gain'])

    def test_defaults_keep_duplicates_empty_variable_rows_and_nested_tables(self):
        values=[{'a':'Repeated contextual rule '*8,'b':[{'word':'ewww','start':.123456789}]} for _ in range(9)]
        packed=a.pack(values);self.assertEqual(packed['$columns'],[])
        self.assertEqual(packed['$rows'],[[] for _ in range(9)])
        self.assertEqual(a.unpack(packed),values)

    def test_json_types_cannot_collapse_into_a_constant(self):
        values=[{'common':'Keep the full quote '*10,'typed':v} for v in [True,1,1.0,{'v':False},{'v':0},{'v':0.0},None,'']]
        restored=a.unpack(a.pack(values))
        dump=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False)
        self.assertEqual(dump(restored),dump(values))

    def test_tiny_plain_rows_and_legacy_tables_are_supported(self):
        value=[{'start':1.25}]
        self.assertEqual(a.pack(value),value)
        self.assertEqual(a.unpack({'$columns':['text','start'],'$rows':[['whole evidence',1.23456789]]}),[{'text':'whole evidence','start':1.23456789}])

    def test_old_frozen_jobs_use_new_pack_without_changing_saved_evidence(self):
        fixture=workflow.WorkflowTests();fixture.setUp();job=fixture.jobs[0];dest=a.job_path(job)
        evidence={'captions':[{'text':'full native sentence '*5,'role':'reaction','start':i} for i in range(12)]}
        a.s.write_json(dest/'enhanced_brief.json',evidence);a.s.write_json(dest/'compact.json',{'legacy':'do not replace'})
        before={p:p.read_bytes() for p in [dest/'enhanced_brief.json',dest/'compact.json',dest/'job.json']}
        current=a.get_brief(job)
        self.assertIn('$defaults',current['captions']);self.assertEqual(a.unpack(current),evidence)
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_every_window_reconstructs_full_original_context(self):
        fixture=workflow.WorkflowTests();fixture.setUp();job=fixture.jobs[0];dest=a.job_path(job)
        rows=[{'start':1,'end':7,'text':'Keep the entire sentence, not just the cue.','words':[{'start':i+.1,'end':i+.3,'text':str(i)} for i in range(1,7)]}]
        report={'tracks':[{'role':f'video_track_{i}','speech':copy.deepcopy(rows)} for i in (1,2)],'caption_speech_audit':{'warnings':[{'offset':.8,'note':'verify actual audio'}]}}
        a.s.write_json(dest/'context_report.json',report)
        a.s.write_json(dest/'enhanced_brief.json',{'captions':[{'start':2,'end':3,'text':'Full caption'}]})
        windows=[{'start':i,'end':i+1.5} for i in range(1,6)]
        pooled=a.unpack(a.get_context_batch(job,windows));self.assertEqual(len(pooled['speech_rows']),2)
        self.assertEqual(len(pooled['captions']),1)
        for window,refs in zip(windows,pooled['windows']):
            restored={'captions':[pooled['captions'][i] for i in refs['caption_ids']],
                'speech':[{'role':s['role'],'rows':[pooled['speech_rows'][i]['row'] for i in s['row_ids']]} for s in refs['speech']],
                'timing_audit':pooled['timing_audit'],'note':pooled['note']}
            self.assertEqual(restored,a.get_context(job,**window))
        with self.assertRaises(ValueError):a.get_context_batch(job,[{'start':-1,'end':1}])
        with self.assertRaises(ValueError):a.get_context_batch(job,[])

if __name__=='__main__':unittest.main()
