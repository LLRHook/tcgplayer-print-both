"""Installer isolation, upgrades, identity, and data-preservation checks."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name).resolve()
        self.home = self.folder / "User's home $(never-run)"
        self.home.mkdir()
        self.source = self.folder / 'source'
        self.source.mkdir()
        for directory, files in [('extension', installer.EXTENSION_FILES), ('native', installer.NATIVE_FILES)]:
            (self.source / directory).mkdir()
            for name in files:
                shutil.copyfile(ROOT / directory / name, self.source / directory / name)
        shutil.copyfile(ROOT / 'requirements.txt', self.source / 'requirements.txt')
        lock = ROOT / 'requirements.lock'
        if lock.exists():
            shutil.copyfile(lock, self.source / 'requirements.lock')
        else:
            (self.source / 'requirements.lock').write_text('# Isolated mocked dependency-install fixture only\n')
        self.address = self.folder / 'private-address.txt'
        self.address.write_text('Community Cards\n123 Example Street\nExample Town, VA 00000\n')
        self.state = self.home / 'Library/Application Support/TCGplayerDirectPrint'
        self.extension = self.home / 'Downloads/TCGplayer-Print-Both'
        self.args = installer.parser().parse_args(['--printer', 'Thermal_Test', '--address-file', str(self.address), '--no-install-deps'])
        self.commands = []

    def tearDown(self):
        self.temp.cleanup()

    def run_command(self, command, **kwargs):
        self.commands.append(command)
        if command[:2] == ['/usr/bin/lpstat', '-p']:
            return subprocess.CompletedProcess(command, 0, 'printer Thermal_Test is idle.\n', '')
        if command[0] == '/usr/bin/lpoptions':
            return subprocess.CompletedProcess(command, 0, 'PageSize/Media: *w288h432\nDarkness/Density: 1 2 3 14 16\nPrintSpeed/Speed: 10 20 *30 40 80\n', '')
        raise AssertionError('Unexpected subprocess: ' + repr(command))

    def install(self, args=None, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(args or self.args, source=self.source, home=self.home, run=self.run_command, **kwargs)

    def test_clean_install_reinstall_and_data_preserving_uninstall(self):
        self.install()
        self.assertEqual(installer.extension_id(json.loads((self.extension / 'manifest.json').read_text())), installer.EXTENSION_ID)
        config = json.loads((self.state / 'config.json').read_text())
        self.assertEqual(config['printer'], 'Thermal_Test')
        self.assertEqual(config['darkness'], 14)
        self.assertEqual(config['print_speed'], 30)
        self.assertEqual((self.state / 'config.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.state / 'browser-helper/native-host').stat().st_mode & 0o777, 0o700)
        for browser in installer.BROWSERS:
            manifest_path = self.home / 'Library/Application Support' / browser / 'NativeMessagingHosts' / (installer.HOST_NAME + '.json')
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(manifest['allowed_origins'], ['chrome-extension://' + installer.EXTENSION_ID + '/'])
        (self.state / 'ledger.sqlite3').write_bytes(b'preserve-ledger')
        (self.state / 'saved.pdf').write_bytes(b'preserve-private-document')
        # Existing settings survive an upgrade without explicit update arguments.
        args = installer.parser().parse_args(['--no-install-deps'])
        old = (self.state / 'config.json').read_bytes()
        self.install(args)
        self.assertEqual((self.state / 'config.json').read_bytes(), old)
        with contextlib.redirect_stdout(io.StringIO()):
            installer.uninstall(args, home=self.home)
        self.assertFalse(self.extension.exists())
        self.assertFalse((self.state / 'browser-helper').exists())
        self.assertEqual((self.state / 'ledger.sqlite3').read_bytes(), b'preserve-ledger')
        self.assertEqual((self.state / 'saved.pdf').read_bytes(), b'preserve-private-document')
        self.assertEqual((self.state / 'config.json').read_bytes(), old)
        self.assertTrue(all(cmd[0] in {'/usr/bin/lpstat', '/usr/bin/lpoptions'} for cmd in self.commands))

    def test_explicit_configuration_update(self):
        self.install()
        args = installer.parser().parse_args(['--darkness', '16', '--speed', '80', '--no-install-deps'])
        self.install(args)
        config = json.loads((self.state / 'config.json').read_text())
        self.assertEqual((config['darkness'], config['print_speed']), (16, 80))

    def test_missing_printer_or_unsupported_driver_does_not_install(self):
        self.args.printer = 'Missing'
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertFalse(self.state.exists())
        self.args.printer = 'Thermal_Test'
        def generic_driver(command, **kwargs):
            if command[0] == '/usr/bin/lpoptions':
                return subprocess.CompletedProcess(command, 0, 'PageSize/Media: Letter\n', '')
            return self.run_command(command, **kwargs)
        with self.assertRaises(installer.InstallError), contextlib.redirect_stdout(io.StringIO()):
            installer.install(self.args, source=self.source, home=self.home, run=generic_driver)
        self.assertFalse(self.state.exists())

    def test_invalid_address_not_printed_or_installed(self):
        self.address.write_text('Private Name\nInvalid\x00 Line\nExample Town\n')
        output = io.StringIO()
        with self.assertRaises(ValueError), contextlib.redirect_stdout(output):
            installer.install(self.args, source=self.source, home=self.home, run=self.run_command)
        self.assertNotIn('Private Name', output.getvalue())
        self.assertFalse(self.state.exists())

    def test_dry_run_makes_no_changes_or_subprocess_calls(self):
        self.args.dry_run = True
        self.install()
        self.assertFalse(self.state.exists())
        self.assertFalse(self.extension.exists())
        self.assertEqual(self.commands, [])

    def test_unrelated_extension_folder_and_changed_key_rejected(self):
        self.extension.mkdir(parents=True)
        (self.extension / 'other-data.txt').write_text('keep')
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertEqual((self.extension / 'other-data.txt').read_text(), 'keep')
        shutil.rmtree(self.extension)
        manifest_path = self.source / 'extension/manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['key'] = 'AAAA'
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertFalse(self.state.exists())

    def test_symlink_destination_or_source_rejected(self):
        self.extension.parent.mkdir(parents=True)
        victim = self.folder / 'keep-me'
        victim.mkdir()
        self.extension.symlink_to(victim)
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertTrue(victim.exists())
        self.extension.unlink()
        source_file = self.source / 'native/settings.py'
        source_file.unlink()
        source_file.symlink_to(ROOT / 'native/settings.py')
        with self.assertRaises(installer.InstallError):
            self.install()

    def test_shell_launcher_handles_spaces_quotes_and_metacharacters(self):
        fake_python = self.folder / "python ' with $(metacharacters)"
        log = self.folder / 'argv.txt'
        fake_python.write_text('#!/bin/sh\nprintf "%s\\n" "$TCGPRINT_STATE" "$@" > "$TEST_ARGV_LOG"\n')
        fake_python.chmod(0o700)
        with mock.patch.object(installer.sys, 'executable', str(fake_python)):
            self.install()
        result = subprocess.run([str(self.state / 'browser-helper/native-host'), 'chrome-extension://test/'], env={**os.environ, 'TEST_ARGV_LOG': str(log)}, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(log.read_text().splitlines(), [str(self.state), str(self.state / 'browser-helper/native_host.py'), 'chrome-extension://test/'])
        self.assertFalse((self.folder / 'metacharacters').exists())

    def test_dependency_install_uses_selected_python_and_owned_environment(self):
        self.args.no_install_deps = False
        def run(command, **kwargs):
            if command[0] in {'/usr/bin/lpstat', '/usr/bin/lpoptions'}:
                return self.run_command(command, **kwargs)
            self.commands.append(command)
            if command[1:3] == ['-m', 'venv']:
                runtime = Path(command[3]); (runtime / 'bin').mkdir(parents=True)
                (runtime / 'bin/python3').write_text('')
                (runtime / 'pyvenv.cfg').write_text('test')
            return subprocess.CompletedProcess(command, 0, '', '')
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(self.args, source=self.source, home=self.home, run=run)
        pip = [cmd for cmd in self.commands if 'pip' in cmd]
        self.assertEqual(len(pip), 1)
        self.assertEqual(pip[0][0], str(self.state / 'venv/bin/python3'))
        self.assertIn(str(self.source / 'requirements.lock'), pip[0])
        self.assertIn('--require-hashes', pip[0])
        self.assertFalse(any(cmd[0] in {'/usr/bin/lp', 'sudo'} for cmd in self.commands))

    def test_modified_uninstall_registration_does_not_delete_files(self):
        self.install()
        path = self.home / 'Library/Application Support' / installer.BROWSERS[0] / 'NativeMessagingHosts' / (installer.HOST_NAME + '.json')
        manifest = json.loads(path.read_text()); manifest['path'] = '/another/app'
        path.write_text(json.dumps(manifest))
        with self.assertRaises(installer.InstallError):
            installer.uninstall(self.args, home=self.home)
        self.assertTrue(self.extension.exists())
        self.assertTrue((self.state / 'browser-helper/native-host').exists())

    def test_interactive_setup_requires_explicit_queue_selection(self):
        args = installer.parser().parse_args(['--no-install-deps'])
        responses = iter(['1', 'Community Cards', '123 Example Street', 'Example Town, VA 00000', ''])
        self.install(args, prompt=lambda _: next(responses))
        self.assertEqual(json.loads((self.state / 'config.json').read_text())['printer'], 'Thermal_Test')

    def test_tree_replace_rolls_back_if_atomic_publish_fails(self):
        self.install()
        old = (self.extension / 'content.js').read_bytes()
        original = installer.os.replace
        def fail_publish(source, destination):
            if Path(source).name.startswith('.tcgprint-stage-') and Path(destination) == self.extension:
                raise OSError('simulated rename failure')
            return original(source, destination)
        with mock.patch.object(installer.os, 'replace', side_effect=fail_publish), self.assertRaises(OSError):
            installer.replace_tree(self.source / 'extension', self.extension, installer.EXTENSION_FILES)
        self.assertEqual((self.extension / 'content.js').read_bytes(), old)

    def test_failed_dependency_bootstrap_is_recoverable_without_touching_documents(self):
        self.args.no_install_deps = False
        failed_once = False
        def run(command, **kwargs):
            nonlocal failed_once
            if command[0] in {'/usr/bin/lpstat', '/usr/bin/lpoptions'}:
                return self.run_command(command, **kwargs)
            self.commands.append(command)
            if command[1:3] == ['-m', 'venv']:
                runtime = Path(command[3]); (runtime / 'bin').mkdir(parents=True, exist_ok=True)
                (runtime / 'bin/python3').write_text('')
                (runtime / 'pyvenv.cfg').write_text('test')
            if 'pip' in command and not failed_once:
                failed_once = True
                raise subprocess.CalledProcessError(1, command)
            return subprocess.CompletedProcess(command, 0, '', '')
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(subprocess.CalledProcessError):
            installer.install(self.args, source=self.source, home=self.home, run=run)
        self.assertFalse(self.extension.exists())
        self.assertFalse((self.state / 'config.json').exists())
        self.assertTrue((self.state / installer.OWNER_FILE).exists())
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(self.args, source=self.source, home=self.home, run=run)
        self.assertTrue(self.extension.exists())
        self.assertTrue((self.state / 'config.json').exists())

    def test_filesystem_roots_shared_folders_and_unrelated_state_rejected(self):
        for path in (Path('/'), Path('/usr'), self.home, self.home / 'Documents', self.home / 'Downloads', self.home / 'Library/Application Support'):
            self.args.state = path
            with self.assertRaises(installer.InstallError):
                self.install()
        self.args.state = self.home / 'unrelated-state'
        self.args.state.mkdir(); (self.args.state / 'keep.txt').write_text('untouched')
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertEqual((self.args.state / 'keep.txt').read_text(), 'untouched')
        self.assertFalse((self.args.state / 'config.json').exists())

    def test_custom_dedicated_state_and_extension_paths(self):
        self.args.state = self.home / 'custom-state'
        self.args.extension_dir = self.home / 'custom-extension'
        self.install()
        record = json.loads((self.args.state / 'installation.json').read_text())
        self.assertEqual(record['extension_dir'], str(self.args.extension_dir))
        with contextlib.redirect_stdout(io.StringIO()):
            installer.uninstall(self.args, home=self.home)
        self.assertTrue((self.args.state / 'config.json').exists())
        self.assertFalse(self.args.extension_dir.exists())
        self.install()
        self.assertTrue(self.args.extension_dir.exists())

    def test_cli_refuses_development_dependency_skip(self):
        output = io.StringIO()
        with mock.patch.object(installer.sys, 'platform', 'darwin'), contextlib.redirect_stderr(output):
            result = installer.main(['--no-install-deps'])
        self.assertEqual(result, 1)
        self.assertIn('isolated developer tests', output.getvalue())
        self.assertFalse(self.state.exists())

    def test_uninstall_rejects_symlink_app_before_changing_registrations(self):
        self.install()
        app = self.state / 'browser-helper'
        shutil.rmtree(app)
        victim = self.folder / 'another-app'; victim.mkdir()
        app.symlink_to(victim)
        with self.assertRaises(installer.InstallError):
            installer.uninstall(self.args, home=self.home)
        manifest = self.home / 'Library/Application Support' / installer.BROWSERS[0] / 'NativeMessagingHosts' / (installer.HOST_NAME + '.json')
        self.assertTrue(manifest.exists())
        self.assertTrue(self.extension.exists())

    def test_typical_downloaded_zip_extract_install_has_no_destination_collision(self):
        spec = importlib.util.spec_from_file_location('packager', ROOT / 'scripts/package.py')
        packager = importlib.util.module_from_spec(spec); spec.loader.exec_module(packager)
        archive_path = self.folder / 'download.zip'
        packager.package(archive_path, root=ROOT)
        downloads = self.home / 'Downloads'; downloads.mkdir()
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(downloads)
        extracted = downloads / packager.ARCHIVE_ROOT
        self.assertNotEqual(extracted, self.extension)
        self.assertTrue((extracted / 'install.py').exists())
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(self.args, source=extracted, home=self.home, run=self.run_command)
        self.assertTrue((self.extension / 'manifest.json').exists())
        self.assertTrue((extracted / 'install.py').exists())
        self.assertTrue((extracted / 'native/native_host.py').exists())
        self.assertFalse((extracted / 'config.json').exists())

    def test_source_overlap_rejected_before_any_install_mutation(self):
        self.args.extension_dir = self.source
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertFalse(self.state.exists())
        self.assertEqual(self.commands, [])
        self.args.extension_dir = self.source / 'extension'
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertFalse(self.state.exists())
        self.args.extension_dir = None
        self.args.state = self.source / 'private-state'
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertFalse(self.args.state.exists())

    def test_package_is_deterministic_and_excludes_private_or_generated_data(self):
        spec = importlib.util.spec_from_file_location('packager', ROOT / 'scripts/package.py')
        packager = importlib.util.module_from_spec(spec); spec.loader.exec_module(packager)
        shutil.copyfile(ROOT / 'install.py', self.source / 'install.py')
        for file in packager.ROOT_FILES:
            if not (self.source / file).exists():
                (self.source / file).write_text('Public documentation\n')
        (self.source / 'docs').mkdir()
        for file in packager.DOC_FILES:
            (self.source / 'docs' / file).write_text('Public installation guide\n')
        (self.source / 'config.json').write_text('PRIVATE')
        (self.source / 'buyer.pdf').write_text('PRIVATE')
        (self.source / 'native/ledger.sqlite3').write_text('PRIVATE')
        out = self.folder / 'release.zip'
        packager.package(out, root=self.source)
        first = hashlib.sha256(out.read_bytes()).hexdigest()
        packager.package(out, root=self.source)
        self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(), first)
        with zipfile.ZipFile(out) as archive:
            self.assertFalse(any(name.endswith(('.pdf', '.sqlite3')) or name.endswith('config.json') for name in archive.namelist()))
            self.assertTrue(all(info.date_time == (2026, 1, 1, 0, 0, 0) for info in archive.infolist()))
            self.assertEqual(archive.getinfo(packager.ARCHIVE_ROOT + '/Install.command').external_attr >> 16 & 0o777, 0o755)


if __name__ == '__main__':
    unittest.main()
