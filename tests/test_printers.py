"""Brand-independent 4x6 discovery, installation and paired submission."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native'))
import printer
import tcgprint as core
import native_host as host
from settings import validate_config
from fixtures import ensure_fixtures, OID
import test_install as installer_tests
installer = installer_tests.installer


class MediaTests(unittest.TestCase):
    def test_standard_media_names_without_vendor_options(self):
        for name in ['4x6', '4X6', 'w288h432', 'na_index-4x6_4x6in', 'oe_photo_101.6x152.4mm']:
            choices = {'PageSize': {name, 'Letter'}}
            conf = validate_config({'printer': 'Label_Queue', 'media': name, 'return_address': ['Example Store', '123 Example Street', 'Example City, VA 00000']})
            printer.validate_options(conf, choices)
            args = printer.submission_options(conf, 2)
            self.assertIn('media=' + name, args)
            self.assertIn('page-ranges=1-2', args)
            self.assertIn('number-up=1', args)
            self.assertIn('job-sheets=none', args)
            self.assertIn('page-set=all', args)
            self.assertIn('job-hold-until=no-hold', args)
            self.assertFalse(any('Darkness=' in arg or 'PrintSpeed=' in arg for arg in args))

    def test_paper_dimensions_verify_model_specific_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'Label_Queue.ppd').write_text('*PaperDimension Label102x152: "289.13 430.87"\n*PaperDimension WrongLabel: "612 792"\n')
            dimensions = printer.paper_dimensions('Label_Queue', Path(folder))
            choices = {'PageSize': {'Label102x152', 'WrongLabel'}}
            self.assertEqual(printer.supported_media(choices, dimensions), ['Label102x152'])
            # Metadata takes precedence even over a misleading canonical name.
            self.assertFalse(printer.four_by_six('4x6', {'4x6': (612, 792)}))

    def test_custom_media_requires_explicit_custom_driver_capability(self):
        self.assertEqual(printer.supported_media({'PageSize': {'Letter', 'Custom'}}), [])
        bounds = {'@Width': (72, 300), '@Height': (72, 600)}
        self.assertEqual(printer.supported_media({'PageSize': {'Custom'}}, bounds), ['Custom.4x6in'])
        self.assertEqual(printer.supported_media({'PageSize': {'Custom'}}, {**bounds, '@Width': (72, 144)}), [])
        self.assertEqual(printer.supported_media({'PageSize': {'Letter'}}), [])
        self.assertEqual(printer.supported_media({'PageSize': {'6x4', 'w432h288'}}), [])

    def test_custom_bounds_are_read_from_ppd_and_reject_narrow_printers(self):
        with tempfile.TemporaryDirectory() as folder:
            ppd = Path(folder, 'Label_Queue.ppd')
            ppd.write_text('*ParamCustomPageSize Width: 1 points 72 300\n*ParamCustomPageSize Height: 2 points 72 600\n')
            self.assertEqual(printer.supported_media({'PageSize': {'Custom'}}, printer.paper_dimensions('Label_Queue', Path(folder))), ['Custom.4x6in'])
            ppd.write_text('*ParamCustomPageSize Width: 1 points 72 144\n*ParamCustomPageSize Height: 2 points 72 600\n')
            self.assertEqual(printer.supported_media({'PageSize': {'Custom'}}, printer.paper_dimensions('Label_Queue', Path(folder))), [])
            ppd.unlink()
            self.assertEqual(printer.supported_media({'PageSize': {'Custom'}}, printer.paper_dimensions('Label_Queue', Path(folder))), [])

    def test_no_shell_or_cups_compound_option_can_enter_media(self):
        for media in ['4x6,Letter', '-o', '4x6;echo', '../4x6', '4x6\nInjected']:
            self.assertFalse(printer.four_by_six(media))
            with self.assertRaises(ValueError):
                validate_config({'printer': 'Label_Queue', 'media': media, 'return_address': ['Example', 'Street', 'City']})

    def test_existing_munbyn_config_retains_legacy_presets(self):
        conf = validate_config({'printer': 'Example_Queue', 'return_address': ['Example', 'Street', 'City']})
        self.assertEqual((conf['media'], conf['darkness'], conf['print_speed']), ('w288h432', 14, 30))

    def test_explicit_unsupported_overrides_fail_instead_of_being_silently_ignored(self):
        conf = validate_config({'printer': 'Label_Queue', 'media': '4x6', 'darkness': 14, 'return_address': ['Example', 'Street', 'City']})
        with self.assertRaisesRegex(printer.PrinterUnavailable, 'OPTIONS_UNSUPPORTED'):
            printer.validate_options(conf, {'PageSize': {'4x6'}})

    def test_configured_generic_queue_health(self):
        conf = validate_config({'printer': 'Label_Queue', 'media': '4x6', 'return_address': ['Example', 'Street', 'City']})
        replies = ['printer Label_Queue is idle. enabled', 'Label_Queue accepting requests', 'PageSize/Media: Letter *4x6']
        with patch.object(printer, '_run', side_effect=replies):
            receipt = printer.health(conf)
            self.assertEqual(receipt['printer'], 'Label_Queue')
            self.assertEqual(receipt['media'], '4x6')

    def test_generic_driver_one_click_produces_one_complete_two_page_job(self):
        import base64
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            state.joinpath('config.json').write_text(json.dumps({'printer': 'Label_Queue', 'media': 'na_index-4x6_4x6in', 'return_address': ['Example Store', '123 Example Street', 'Example City, VA 00000']}))
            source = ensure_fixtures() / 'native-default.pdf'
            message = {'command': 'print', 'orderId': OID, 'requestId': 'a712e9fa-35c3-4f84-8812-a4b69f8918b7', 'pdfBase64': base64.b64encode(source.read_bytes()).decode()}
            replies = ['printer Label_Queue is idle. enabled', 'Label_Queue accepting requests', 'PageSize/Media: *na_index-4x6_4x6in Letter']
            with patch.object(host, 'STATE', state), patch.object(printer, '_run', side_effect=replies), patch.object(core.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='request id is Label_Queue-123 (1 file(s))')) as submit, patch.object(core, 'job_status', return_value={'job-state': 9, 'job-media-sheets-completed': 2}), contextlib.redirect_stdout(io.StringIO()):
                result = host.handle(message)
                self.assertEqual((result['state'], result['pages'], result['sheets']), ('completed', 2, 2))
                submit.assert_called_once()
                args = submit.call_args.args[0]
                self.assertIn('media=na_index-4x6_4x6in', args)
                self.assertNotIn('Darkness=14', args)
                self.assertNotIn('PrintSpeed=30', args)
                self.assertEqual(len(core.PdfReader(args[-1]).pages), 2)


class GenericInstallerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = installer_tests.InstallerTests()
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def generic_run(self, command, **kwargs):
        import subprocess
        if command[0] == '/usr/bin/lpoptions':
            return subprocess.CompletedProcess(command, 0, 'PageSize/Media: Letter *na_index-4x6_4x6in', '')
        return self.fixture.run_command(command, **kwargs)

    def test_generic_driver_installs_without_munbyn_controls(self):
        f = self.fixture
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(f.args, source=f.source, home=f.home, run=self.generic_run)
        conf = json.loads((f.state / 'config.json').read_text())
        self.assertEqual(conf['media'], 'na_index-4x6_4x6in')
        self.assertIsNone(conf['darkness']); self.assertIsNone(conf['print_speed'])

    def test_upgrade_preserves_existing_media_and_vendor_presets(self):
        f = self.fixture
        f.install()
        conf = json.loads((f.state / 'config.json').read_text())
        conf.pop('media'); conf['darkness'] = 14; conf['print_speed'] = 30
        (f.state / 'config.json').write_text(json.dumps(conf))
        (f.state / 'ledger.sqlite3').write_bytes(b'fictional preserved history')
        args = installer.parser().parse_args(['--no-install-deps'])
        f.install(args)
        upgraded = json.loads((f.state / 'config.json').read_text())
        self.assertEqual((upgraded['media'], upgraded['darkness'], upgraded['print_speed']), ('w288h432', 14, 30))
        self.assertEqual((f.state / 'ledger.sqlite3').read_bytes(), b'fictional preserved history')

    def test_switching_printers_does_not_carry_incompatible_media_or_presets(self):
        import subprocess
        f = self.fixture; f.install()
        conf = json.loads((f.state / 'config.json').read_text())
        conf['darkness'] = 14; conf['print_speed'] = 30
        (f.state / 'config.json').write_text(json.dumps(conf))
        args = installer.parser().parse_args(['--printer', 'Other_Label', '--no-install-deps'])
        def run(command, **kwargs):
            if command[0] == '/usr/bin/lpstat':
                return subprocess.CompletedProcess(command, 0, 'printer Other_Label is idle.\n', '')
            return self.generic_run(command, **kwargs)
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(args, source=f.source, home=f.home, run=run)
        updated = json.loads((f.state / 'config.json').read_text())
        self.assertEqual((updated['printer'], updated['media'], updated['darkness'], updated['print_speed']), ('Other_Label', 'na_index-4x6_4x6in', None, None))


if __name__ == '__main__': unittest.main()
