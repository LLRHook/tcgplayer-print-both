"""Production edge cases use synthetic data and a simulated printer."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native'))
import tcgprint as core
import native_host as host
import printer
import maintenance
from settings import validate_config
from fixtures import make_pdf, ensure_fixtures, OID


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name)
        self.config = {'printer': 'Example_Queue', 'return_address': ['Example Store', '123 Example Street', 'Example City, VA 00000']}
        (self.state / 'config.json').write_text(json.dumps(self.config))
        self.source = ensure_fixtures() / 'native-default.pdf'

    def tearDown(self):
        self.tmp.cleanup()

    def test_complete_multi_page_slip_preserves_all_native_text(self):
        src = ensure_fixtures() / 'native-multiple.pdf'
        output = self.state / 'paired/out.pdf'
        core.build(src, output, core.parse(src), validate_config(self.config))
        old, new = core.PdfReader(src), core.PdfReader(output)
        self.assertEqual(len(new.pages), 4)
        for index in range(3):
            self.assertEqual(''.join(old.pages[index].extract_text().split()), ''.join(new.pages[index].extract_text().split()))
        self.assertTrue(all(tuple(page.mediabox[2:]) == (288, 432) for page in new.pages))
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertEqual(output.parent.stat().st_mode & 0o777, 0o700)

    def test_all_supported_address_layouts(self):
        for name in ['native-default.pdf', 'native-shipping.pdf', 'native-window.pdf']:
            with self.subTest(name=name):
                self.assertEqual(core.parse(ensure_fixtures() / name)[0]['address'], ['Example Customer', '123 Example Street', 'Example City, VA 00000'])

    def test_missing_continuation_is_rejected(self):
        source = make_pdf(self.state / 'bad.pdf', pages=2, page_numbers=[1, 3])
        with self.assertRaisesRegex(ValueError, 'continuation'):
            core.parse(source)

    def test_unsupported_return_glyphs_and_control_characters_are_rejected(self):
        for address in [['Example', 'Street\nInjected', 'City'], ['Example', 'Street', '東京']]:
            with self.subTest(address=address):
                with self.assertRaises(ValueError):
                    validate_config({**self.config, 'return_address': address})

    def test_invalid_queue_and_preset_rejected(self):
        for value in [{'printer': '-h'}, {'printer': 'queue;echo'}, {'darkness': True}, {'print_speed': 150}]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_config({**self.config, **value})

    def test_ready_checks_configured_queue_and_driver(self):
        responses = ['printer Example_Queue is idle. enabled since today', 'Example_Queue accepting requests since today', 'PageSize/Size: *w288h432\nDarkness/Density: 13 *14 15\nPrintSpeed/Speed: 20 *30 40']
        with patch.object(printer, '_run', side_effect=responses) as run:
            result = printer.health(validate_config(self.config))
            self.assertEqual(result['printer'], 'Example_Queue')
            self.assertTrue(all('Example_Queue' in x.args[0] for x in run.call_args_list))

    def test_disabled_offline_and_wrong_media_queues_are_not_ready(self):
        cases = [(['printer disabled'], 'DISABLED'), (['printer offline'], 'OFFLINE'), (['printer idle', 'queue not accepting requests'], 'NOT_ACCEPTING'), (['printer idle', 'queue accepting requests', 'PageSize: w144h72'], 'MEDIA_UNSUPPORTED')]
        for replies, error in cases:
            with self.subTest(error=error), patch.object(printer, '_run', side_effect=replies):
                with self.assertRaisesRegex(printer.PrinterUnavailable, error):
                    printer.health(validate_config(self.config))

    def test_failed_preflight_never_commits_print_intent(self):
        with patch.object(core, 'printer_health', side_effect=printer.PrinterUnavailable('PRINTER_OFFLINE')), patch.object(core.subprocess, 'run') as submit:
            with self.assertRaises(printer.PrinterUnavailable):
                core.process(self.source, self.state, expect=OID, request_id='d712e9fa-35c3-4f84-8812-a4b69f8918b7')
            submit.assert_not_called()
        with core.connection(self.state) as db:
            self.assertEqual(db.execute('select count(*) from print_requests').fetchone()[0], 0)

    def seed(self, state='submitted', job='Example_Queue-123'):
        token = 'd712e9fa-35c3-4f84-8812-a4b69f8918b7'
        with core.connection(self.state) as db:
            db.execute('insert into orders values (?,?,?,?,?)', (OID, state, 'hash', job, 'out'))
            db.execute('insert into print_requests values (?,?,?,?,?,?,?)', (token, OID, state, 'hash', job, 'out', '2026-01-01'))
            db.commit()
        return token

    def test_status_refresh_marks_delayed_job_complete_without_printing(self):
        token = self.seed()
        with patch.object(core, 'job_status', return_value={'job-state': 9, 'job-media-sheets-completed': 2}), patch.object(core.subprocess, 'run') as submit:
            r = maintenance.receipt(core, self.state, OID, token)
            self.assertEqual(r['state'], 'completed')
            self.assertEqual(r['sheets'], 2)
            submit.assert_not_called()

    def test_wrong_order_cannot_read_a_receipt(self):
        token = self.seed()
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_PRINT_REQUEST'):
            maintenance.receipt(core, self.state, 'TEST0002-ABCDEF-12345', token)

    def test_resolve_requires_explicit_ack_and_refuses_active_jobs(self):
        self.seed()
        with self.assertRaisesRegex(ValueError, 'ACKNOWLEDGEMENT'):
            maintenance.resolve(core, self.state, OID)
        with patch.object(core, 'job_status', return_value={'job-state': 5}):
            with self.assertRaisesRegex(ValueError, 'STILL_ACTIVE'):
                maintenance.resolve(core, self.state, OID, True)

    def test_resolve_cancelled_and_jobless_uncertain_preserves_history(self):
        token = self.seed('uncertain', None)
        result = maintenance.resolve(core, self.state, OID, True)
        self.assertEqual(result['state'], 'resolved')
        with core.connection(self.state) as db:
            self.assertEqual(db.execute('select state from print_requests where request_id=?', (token,)).fetchone()[0], 'resolved')
            self.assertEqual(db.execute('select count(*) from print_requests').fetchone()[0], 1)
            core.require_finished_prior_jobs(db, OID)

    def test_retention_keeps_pending_data_and_ledger(self):
        self.seed('uncertain', None)
        folder = self.state / 'browser-inputs'
        folder.mkdir()
        old = folder / 'old.pdf'; old.write_bytes(b'%PDF-EXAMPLE')
        os.utime(old, (0, 0))
        self.assertTrue(maintenance.cleanup(core, self.state, 30)['deferred'])
        self.assertTrue(old.exists())
        maintenance.resolve(core, self.state, OID, True)
        self.assertEqual(maintenance.cleanup(core, self.state, 30)['deleted'], 1)
        self.assertTrue((self.state / 'ledger.sqlite3').exists())

    def test_expired_completed_order_can_be_reprinted_after_retention(self):
        import base64, hashlib
        raw = self.source.read_bytes()
        incoming = self.state / 'browser-inputs'
        incoming.mkdir()
        cached = incoming / ('TCGplayer_PackingSlips_' + hashlib.sha256(raw).hexdigest()[:24] + '.pdf')
        cached.write_bytes(raw)
        os.utime(cached, (0, 0))
        self.seed('completed')
        def prepare(source, *args, **kwargs):
            self.assertTrue(source.exists())
            self.assertEqual(source.read_bytes(), raw)
            return 'Example_Queue-124'
        with patch.object(host, 'STATE', self.state), patch.object(core, 'process', side_effect=prepare), patch.object(core, 'job_status', return_value={'job-state': 9}):
            result = host.handle({'command': 'print', 'orderId': OID, 'requestId': 'e712e9fa-35c3-4f84-8812-a4b69f8918b7', 'pdfBase64': base64.b64encode(raw).decode()})
            self.assertEqual(result['state'], 'completed')

    def test_recovery_does_not_release_older_active_request(self):
        self.seed('completed')
        with core.connection(self.state) as db:
            db.execute('insert into print_requests values (?,?,?,?,?,?,?)', ('e712e9fa-35c3-4f84-8812-a4b69f8918b7', OID, 'submitted', 'hash', 'Example_Queue-122', 'out', '2026-01-01'))
            db.commit()
        with patch.object(core, 'job_status', return_value={'job-state': 5}):
            with self.assertRaisesRegex(ValueError, 'STILL_ACTIVE'):
                maintenance.resolve(core, self.state, OID, True)

    def test_status_and_recovery_are_serialized(self):
        import threading
        token = self.seed('printer_error')
        entered, release, resolved = threading.Event(), threading.Event(), threading.Event()
        errors = []
        def job_status(job):
            entered.set()
            if not release.wait(2): raise RuntimeError('test deadline')
            return {'job-state': 8}
        def check():
            try: maintenance.receipt(core, self.state, OID, token)
            except Exception as error: errors.append(error)
        def recover():
            try: maintenance.resolve(core, self.state, OID, True); resolved.set()
            except Exception as error: errors.append(error)
        with patch.object(core, 'job_status', side_effect=job_status):
            first = threading.Thread(target=check); first.start()
            self.assertTrue(entered.wait(2))
            second = threading.Thread(target=recover); second.start()
            self.assertFalse(resolved.wait(.03))
            release.set(); first.join(2); second.join(2)
        self.assertFalse(errors)
        self.assertTrue(resolved.is_set())
        with core.connection(self.state) as db:
            self.assertEqual(db.execute('select state from orders where id=?', (OID,)).fetchone()[0], 'resolved')

    def test_printer_submission_uses_stable_locale(self):
        from types import SimpleNamespace
        with patch.object(core, 'printer_health'), patch.object(core.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='request id is Example_Queue-125 (1 file(s))')) as submit, patch.dict(os.environ, {'LC_ALL': 'fr_FR.UTF-8'}):
            self.assertEqual(core.process(self.source, self.state, expect=OID, request_id='e712e9fa-35c3-4f84-8812-a4b69f8918b7'), 'Example_Queue-125')
            self.assertEqual(submit.call_args.kwargs['env']['LC_ALL'], 'C')

    def test_page_limit_rejects_before_build_or_submission(self):
        source = make_pdf(self.state / 'oversized.pdf', pages=65)
        with self.assertRaisesRegex(ValueError, 'between 1 and 64'):
            core.parse(source)

    def test_byte_limit_rejects_before_input_file_is_saved(self):
        import base64
        raw = b'%PDF-' + b' ' * host.MAX_PDF + b'%%EOF'
        with patch.object(host, 'STATE', self.state), patch.object(core.subprocess, 'run') as submit:
            with self.assertRaisesRegex(host.Rejected, 'INVALID_OR_INCOMPLETE_PDF'):
                host.handle({'command': 'print', 'orderId': OID, 'requestId': 'e712e9fa-35c3-4f84-8812-a4b69f8918b7', 'pdfBase64': base64.b64encode(raw).decode()})
            submit.assert_not_called()
        self.assertFalse((self.state / 'browser-inputs').exists())

    def test_label_overflow_fails_before_submission(self):
        with self.assertRaisesRegex(ValueError, 'width'):
            core.label(['W' * 200, '123 Example Street', 'Example City, VA 00000'], self.config['return_address'], OID)

    def test_native_frame_limit_is_terminal_without_parsing_or_printing(self):
        import io, struct
        with patch.object(host, 'handle') as handle:
            self.assertEqual(host.serve(host.EXPECTED_ORIGIN, io.BytesIO(struct.pack('=I', host.MAX_MESSAGE + 1)), io.BytesIO()), 1)
            handle.assert_not_called()


if __name__ == '__main__':
    unittest.main()
