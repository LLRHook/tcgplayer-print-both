import base64,io,json,struct,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native'))
import native_host as host
from fixtures import ensure_fixtures
ensure_fixtures()
SOURCE=Path(__file__).resolve().parent/'generated/native-default.pdf'
OID='TEST0001-ABCDEF-12345';TOKEN='d712e9fa-35c3-4f84-8812-a4b69f8918b7'
class HostTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=host.STATE;host.STATE=Path(self.tmp.name)
  self.health_patch=patch.object(host.core,'printer_health',return_value={'ok':True,'state':'ready','printer':'RW403B'});self.health_patch.start()
  (host.STATE/'config.json').write_text(json.dumps({'return_address':['Store','1 Return St','CITY, VA 00000'],'printer':'RW403B'}))
  self.payload={'command':'prepare','orderId':OID,'requestId':TOKEN,'pdfBase64':base64.b64encode(SOURCE.read_bytes()).decode()}
 def tearDown(self):self.health_patch.stop();host.STATE=self.old;self.tmp.cleanup()
 def test_actual_native_pdf_bytes_prepare_and_preserve_all_text(self):
  result=host.handle(self.payload);self.assertEqual(result['pages'],2)
  src=host.core.PdfReader(SOURCE);out=host.core.PdfReader(result['output'])
  self.assertEqual(''.join(src.pages[0].extract_text().split()),''.join(out.pages[0].extract_text().split()))
  self.assertIn(OID,out.pages[1].extract_text())
 def test_wrong_full_order_never_submits(self):
  self.payload.update(command='print',orderId='TEST0002-ABCDEF-12345')
  with patch.object(host.core.subprocess,'run') as run:
   with self.assertRaisesRegex(host.Rejected,'PDF_ORDER_MISMATCH'):host.handle(self.payload)
   run.assert_not_called()
 def test_paths_are_not_accepted(self):
  del self.payload['pdfBase64'];self.payload.update(command='print',pdfPath=str(SOURCE))
  with self.assertRaisesRegex(host.Rejected,'PDF_BYTES_REQUIRED'):host.handle(self.payload)
 def test_invalid_origin_cannot_reach_helper(self):
  with patch.object(host,'handle') as handle:
   self.assertEqual(host.serve('chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/',io.BytesIO(),io.BytesIO()),2);handle.assert_not_called()
 def test_stdio_framing_exactly_one_json_response(self):
  raw=json.dumps(self.payload).encode();out=io.BytesIO()
  self.assertEqual(host.serve(host.EXPECTED_ORIGIN,io.BytesIO(struct.pack('=I',len(raw))+raw),out),0)
  data=out.getvalue();size=struct.unpack('=I',data[:4])[0]
  self.assertEqual(size,len(data)-4);self.assertTrue(json.loads(data[4:])['ok'])
 def test_incomplete_pdf_is_rejected(self):
  self.payload['pdfBase64']=base64.b64encode(SOURCE.read_bytes()[:100]).decode()
  with self.assertRaisesRegex(host.Rejected,'INVALID_OR_INCOMPLETE_PDF'):host.handle(self.payload)
 def test_deliberate_new_click_prints_again(self):
  self.payload['command']='print'
  first_result=type('Result',(),dict(returncode=0,stdout='request id is RW403B-991 (1 file(s))',stderr=''))()
  second_result=type('Result',(),dict(returncode=0,stdout='request id is RW403B-992 (1 file(s))',stderr=''))()
  with patch.object(host.core.subprocess,'run',side_effect=[first_result,second_result]) as run,patch.object(host.core,'job_status',return_value={'job-state':9,'job-media-sheets-completed':2}):
   first=host.handle(self.payload)
   self.assertEqual(first['state'],'completed')
   self.payload['requestId']='e712e9fa-35c3-4f84-8812-a4b69f8918b7'
   second=host.handle(self.payload)
   print('SECOND_CLICK_FEEDBACK',{'first':first['state'],'second':second['state'],'lp_calls':run.call_count,'expected':'completed, 2 submissions'})
   self.assertEqual(second['state'],'completed','A deliberate new request must not be suppressed by the completed order ledger')
   self.assertEqual(run.call_count,2)
 def test_combined_submission_and_changed_export_duplicate(self):
  self.payload['command']='print'
  result=type('Result',(),dict(returncode=0,stdout='request id is RW403B-990 (1 file(s))',stderr=''))()
  with patch.object(host.core.subprocess,'run',return_value=result) as run,patch.object(host.core,'job_status',return_value={'job-state':9,'job-media-sheets-completed':2}):
   first=host.handle(self.payload);self.assertEqual(first['state'],'completed');self.assertEqual(first['sheets'],2)
   args=run.call_args.args[0];self.assertEqual(args[0],'/usr/bin/lp');self.assertIn('media=w288h432',args)
   paired=host.core.PdfReader(args[-1]);self.assertEqual(len(paired.pages),2)
   self.payload['pdfBase64']=base64.b64encode(SOURCE.read_bytes()+b'\n% Re-export test\n').decode()
   self.assertEqual(host.handle(self.payload)['state'],'duplicate');self.assertEqual(run.call_count,1)
 def test_pending_submission_blocks_new_request(self):
  self.payload['command']='print'
  result=type('Result',(),dict(returncode=0,stdout='request id is RW403B-993 (1 file(s))',stderr=''))()
  with patch.object(host.core.subprocess,'run',return_value=result) as run,patch.object(host.core,'job_status',return_value={'job-state':5}),patch.object(host.time,'monotonic',side_effect=[0,19]):
   self.assertEqual(host.handle(self.payload)['state'],'submitted')
   self.payload['requestId']='e712e9fa-35c3-4f84-8812-a4b69f8918b7'
   with self.assertRaisesRegex(host.Rejected,'PREVIOUS_SUBMISSION_NEEDS_QUEUE_CHECK'):host.handle(self.payload)
   self.assertEqual(run.call_count,1)
 def test_uncertain_same_and_new_request_never_retry(self):
  self.payload['command']='print'
  with patch.object(host.core.subprocess,'run',side_effect=TimeoutError) as run:
   with self.assertRaises(TimeoutError):host.handle(self.payload)
   for token in [TOKEN,'e712e9fa-35c3-4f84-8812-a4b69f8918b7']:
    self.payload['requestId']=token
    with self.assertRaisesRegex(host.Rejected,'PREVIOUS_SUBMISSION_NEEDS_QUEUE_CHECK'):host.handle(self.payload)
   self.assertEqual(run.call_count,1)
  with host.core.connection(host.STATE) as db:
   self.assertEqual(db.execute('select state from print_requests where request_id=?',(TOKEN,)).fetchone(),('uncertain',))
 def test_completed_job_is_archived_and_nonexplicit_cli_skips(self):
  with host.core.connection(host.STATE) as db:
   db.execute('insert into orders values (?,?,?,?,?)',(OID,'completed','legacy-source-hash','RW403B-50','/older-pair.pdf'));db.commit()
  self.payload['command']='print'
  result=type('Result',(),dict(returncode=0,stdout='request id is RW403B-994 (1 file(s))',stderr=''))()
  with patch.object(host.core.subprocess,'run',return_value=result) as run,patch.object(host.core,'job_status',return_value={'job-state':9,'job-media-sheets-completed':2}):
   self.assertEqual(host.handle(self.payload)['state'],'completed')
   self.assertIsNone(host.core.process(SOURCE,host.STATE))
   self.assertEqual(run.call_count,1)
  with host.core.connection(host.STATE) as db:
   self.assertEqual(db.execute('select state,hash,output from print_history where job=?',('RW403B-50',)).fetchone(),('completed','legacy-source-hash','/older-pair.pdf'))
   self.assertEqual(db.execute('select state from print_history where job=?',('RW403B-994',)).fetchone(),('completed',))
 def test_concurrent_same_request_submits_only_once(self):
  from concurrent.futures import ThreadPoolExecutor
  self.payload['command']='print'
  result=type('Result',(),dict(returncode=0,stdout='request id is RW403B-995 (1 file(s))',stderr=''))()
  with patch.object(host.core.subprocess,'run',return_value=result) as run,patch.object(host.core,'job_status',return_value={'job-state':9,'job-media-sheets-completed':2}):
   with ThreadPoolExecutor(max_workers=2) as pool:
    responses=list(pool.map(lambda _:host.handle(dict(self.payload)),range(2)))
   self.assertEqual(run.call_count,1)
   self.assertEqual({r['job'] for r in responses},{'RW403B-995'})
  with host.core.connection(host.STATE) as db:self.assertEqual(db.execute('select count(*) from print_requests').fetchone(),(1,))
 def test_same_request_cannot_be_rebound_to_another_order(self):
  self.payload['command']='print'
  result=type('Result',(),dict(returncode=0,stdout='request id is RW403B-996 (1 file(s))',stderr=''))()
  with patch.object(host.core.subprocess,'run',return_value=result) as run,patch.object(host.core,'job_status',return_value={'job-state':9,'job-media-sheets-completed':2}):
   host.handle(self.payload)
   other=Path(__file__).resolve().parent/'generated/other-order.pdf'
   self.payload['orderId']='TEST0002-ABCDEF-12345';self.payload['pdfBase64']=base64.b64encode(other.read_bytes()).decode()
   with self.assertRaisesRegex(host.Rejected,'REQUEST_ID_ORDER_MISMATCH'):host.handle(self.payload)
   self.assertEqual(run.call_count,1)
if __name__=='__main__':unittest.main()
