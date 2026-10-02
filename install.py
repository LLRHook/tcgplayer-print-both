#!/usr/bin/env python3
"""Per-user macOS installation. Does not print, change browser policy, or need sudo."""
from __future__ import annotations

import argparse
import base64
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid

SOURCE = Path(__file__).resolve().parent
HOST_NAME = 'com.victorivanov.tcgplayer_print'
OWNER_FILE = '.tcgprint-owner.json'
EXTENSION_ID = 'pidblibebfmenlpcbnajfcdoikdldhgj'
EXTENSION_FILES = ('manifest.json', 'background.js', 'core.js', 'content.js',
                   'content.css', 'pdf-bridge.js', 'popup.html', 'popup.js', 'build-state.js')
NATIVE_FILES = ('native_host.py', 'tcgprint.py', 'settings.py', 'printer.py', 'maintenance.py')
BROWSERS = ('net.imput.helium', 'Google/Chrome')
QUEUE = re.compile(r'^[A-Za-z0-9_.-]{1,127}$')


class InstallError(ValueError):
    pass


def extension_id(manifest):
    try:
        key = base64.b64decode(manifest['key'], validate=True)
    except (ValueError, KeyError, TypeError):
        raise InstallError('Extension public key is missing or invalid.') from None
    digest = hashlib.sha256(key).hexdigest()[:32]
    return ''.join(chr(ord('a') + int(char, 16)) for char in digest)


def regular_file(path):
    path = safe_path(path)
    if path.is_symlink() or not path.is_file():
        raise InstallError('A required file is missing or is a symbolic link.')
    return path


def safe_path(path):
    path = Path(os.path.abspath(os.path.expanduser(str(path))))
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise InstallError('Installation paths must not contain symbolic links.')
    return path


def private_dir(path):
    safe_path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def atomic_write(path, data, mode=0o600):
    private_dir(path.parent)
    if path.is_symlink():
        raise InstallError('Refusing to replace a symbolic link.')
    fd, name = tempfile.mkstemp(prefix='.tcgprint-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data if isinstance(data, bytes) else data.encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def json_bytes(value):
    return (json.dumps(value, indent=2) + '\n').encode('utf-8')


def source_validation(source):
    manifest = json.loads(regular_file(source / 'extension/manifest.json').read_text())
    if extension_id(manifest) != EXTENSION_ID:
        raise InstallError('Extension identity does not match the native host.')
    for file in EXTENSION_FILES:
        regular_file(source / 'extension' / file)
    for file in NATIVE_FILES:
        regular_file(source / 'native' / file)
    regular_file(source / 'requirements.txt')
    regular_file(source / 'requirements.lock')
    spec = importlib.util.spec_from_file_location('tcgprint_install_settings', source / 'native/settings.py')
    settings = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(settings)
    return settings


def installed_identity(folder):
    manifest = regular_file(folder / 'manifest.json')
    return extension_id(json.loads(manifest.read_text())) == EXTENSION_ID


def printer_queues(run=subprocess.run):
    result = run(['/usr/bin/lpstat', '-p'], capture_output=True, text=True, timeout=15, env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode:
        raise InstallError('No printer queues found. Add the thermal printer in macOS settings first.')
    queues = re.findall(r'^printer ([A-Za-z0-9_.-]+)\s', result.stdout, re.M)
    if not queues:
        raise InstallError('No printer queues found. Add the thermal printer in macOS settings first.')
    return queues


def load_printer_module(source):
    spec = importlib.util.spec_from_file_location('tcgprint_install_printer', source / 'native/printer.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure_printer_options(conf, args, source, run=subprocess.run):
    driver = load_printer_module(source)
    try:
        options, dimensions = driver.driver_options(conf['printer'], run=run)
        media = driver.supported_media(options, dimensions)
        if not media:
            raise InstallError('The selected driver does not advertise 4×6 media. Set up the thermal printer with its supported driver first.')
        if args.media:
            conf['media'] = args.media
        elif conf.get('media') not in media:
            if conf.get('media') != 'auto' and conf.get('media') and not getattr(args, '_changed_printer', False):
                raise InstallError('The saved 4×6 paper size is no longer available. Select a supported media choice with --media.')
            conf['media'] = 'w288h432' if 'w288h432' in media else media[0]
        driver.validate_options(conf, options, dimensions)
    except driver.PrinterUnavailable as error:
        raise InstallError('Printer setup failed: ' + str(error) + '. Select advertised 4×6 media; optional darkness/speed overrides need matching driver controls.') from None
    return conf


def configuration(state, args, settings, queues, prompt=input):
    old = {}
    config_path = state / 'config.json'
    if config_path.exists():
        old = json.loads(regular_file(config_path).read_text())
    conf = dict(old)
    args._changed_printer = bool(args.printer and old.get('printer') and args.printer != old['printer'])
    if args._changed_printer:
        for key in ['media', 'darkness', 'print_speed']: conf.pop(key, None)
    if args.printer:
        conf['printer'] = args.printer
    elif not conf.get('printer'):
        for index, queue in enumerate(queues, 1):
            print(f'{index}. {queue}')
        choice = prompt('Thermal printer number: ').strip()
        if not choice.isdigit() or not 1 <= int(choice) <= len(queues):
            raise InstallError('Choose a printer from the displayed list.')
        conf['printer'] = queues[int(choice) - 1]
    if conf['printer'] not in queues or not QUEUE.fullmatch(conf['printer']):
        raise InstallError('The configured printer queue is not installed. Select an installed thermal printer.')
    if args.address_file:
        address_file = regular_file(safe_path(args.address_file))
        if address_file.stat().st_size > 4096:
            raise InstallError('Return-address file is too large.')
        conf['return_address'] = address_file.read_text().splitlines()
    elif not conf.get('return_address'):
        print('Enter your return address as 3–5 lines. Finish with an empty line.')
        lines = []
        while len(lines) < 6:
            line = prompt('Return-address line: ')
            if not line:
                break
            lines.append(line)
        conf['return_address'] = lines
    if args.darkness is not None:
        conf['darkness'] = args.darkness
    if args.speed is not None:
        conf['print_speed'] = args.speed
    if args.retention_days is not None:
        conf['retention_days'] = args.retention_days
    # New installs use driver defaults; legacy upgrades retain their presets.
    if not old or args._changed_printer:
        conf.setdefault('media', 'auto')
        conf.setdefault('darkness', None)
        conf.setdefault('print_speed', None)
    # Shared validation prevents installer and runtime settings drifting apart.
    return settings.validate_config(conf)


@contextlib.contextmanager
def install_lock(state):
    private_dir(state)
    lock = state / '.install.lock'
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except BlockingIOError:
        raise InstallError('Another installation is running. Try again after it finishes.') from None
    finally:
        os.close(fd)


def replace_tree(source, destination, files):
    safe_path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    stage = Path(tempfile.mkdtemp(prefix='.tcgprint-stage-', dir=destination.parent))
    backup = destination.parent / ('.tcgprint-backup-' + uuid.uuid4().hex)
    try:
        for filename in files:
            data = regular_file(source / filename).read_bytes()
            atomic_write(stage / filename, data)
        if destination.exists():
            os.replace(destination, backup)
        try:
            os.replace(stage, destination)
        except BaseException:
            if backup.exists():
                os.replace(backup, destination)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def validate_destinations(home, state, extension):
    protected = {home, home / 'Downloads', home / 'Documents', home / 'Desktop',
                 home / 'Library', home / 'Library/Application Support'}
    protected.update(home / 'Library/Application Support' / browser for browser in BROWSERS)
    if home not in state.parents or home not in extension.parents:
        raise InstallError('Installation folders must be dedicated folders inside your home directory.')
    if state in protected or extension in protected or state == extension or state in extension.parents or extension in state.parents:
        raise InstallError('Choose separate, dedicated application-state and extension folders.')
    if state.exists() and not state.is_dir():
        raise InstallError('Application-state destination is not a folder.')
    # Never claim an unrelated pre-existing folder merely because it is writable.
    if state.exists() and any(state.iterdir()):
        record = state / 'installation.json'
        legacy = home / 'Library/Application Support/TCGplayerDirectPrint'
        owner = state / OWNER_FILE
        if owner.exists():
            ownership = json.loads(regular_file(owner).read_text())
            if ownership != {'schema': 1, 'host': HOST_NAME}:
                raise InstallError('Application-state ownership marker is invalid.')
        elif record.exists():
            installed = json.loads(regular_file(record).read_text())
            if installed.get('schema') != 1 or installed.get('launcher') != str(state / 'browser-helper/native-host'):
                raise InstallError('Application-state folder belongs to another installation.')
        elif state != legacy or not (state / 'config.json').is_file():
            raise InstallError('Application-state folder contains unrelated files. Choose a dedicated empty folder.')


def install(args, *, source=SOURCE, home=None, run=subprocess.run, prompt=input):
    if sys.version_info < (3, 10):
        raise InstallError('Python 3.10 or newer is required.')
    home = safe_path(home or Path.home())
    state = safe_path(args.state or home / 'Library/Application Support/TCGplayerDirectPrint')
    extension = safe_path(args.extension_dir or home / 'Downloads/TCGplayer-Print-Both')
    source = safe_path(source)
    for destination in (state, extension):
        if destination == source or destination in source.parents or source in destination.parents:
            raise InstallError('Installed folders must be separate from the extracted installer source folder.')
    validate_destinations(home, state, extension)
    settings = source_validation(source)
    if extension.exists() and not installed_identity(extension):
        raise InstallError('Extension destination contains a different project. Choose another folder.')
    if args.dry_run:
        print('Validated source and extension identity. Would configure a local printer, install private Python dependencies, and register the browser helper. No changes made.')
        return
    queues = printer_queues(run)
    conf = configuration(state, args, settings, queues, prompt)
    conf = configure_printer_options(conf, args, source, run)
    safe_path(state / 'browser-helper')
    safe_path(state / 'venv')
    with install_lock(state):
        atomic_write(state / OWNER_FILE, json_bytes({'schema': 1, 'host': HOST_NAME}))
        runtime = state / 'venv'
        if not args.no_install_deps:
            print('Installing private Python dependencies…')
            if not (runtime / 'pyvenv.cfg').is_file() or not (runtime / 'bin/python3').exists():
                run([sys.executable, '-m', 'venv', str(runtime)], check=True)
            run([str(runtime / 'bin/python3'), '-m', 'pip', 'install', '--disable-pip-version-check', '--require-hashes',
                 '-r', str(source / 'requirements.lock')], check=True)
            python = runtime / 'bin/python3'
            run([str(python), '-c', 'import pypdf, pdfplumber, reportlab'], check=True)
        else:
            # Only for isolated installer development tests; releases use a private venv.
            python = Path(sys.executable)
        app = state / 'browser-helper'
        replace_tree(source / 'native', app, NATIVE_FILES)
        launcher = '#!/bin/sh\nexport TCGPRINT_STATE=' + shlex.quote(str(state)) + '\nexec ' + shlex.quote(str(python)) + ' ' + shlex.quote(str(app / 'native_host.py')) + ' "$@"\n'
        atomic_write(app / 'native-host', launcher, 0o700)
        replace_tree(source / 'extension', extension, EXTENSION_FILES)
        atomic_write(state / 'config.json', json_bytes(conf))
        manifest = {'name': HOST_NAME, 'description': 'Local TCGplayer paired-document printing',
                    'path': str(app / 'native-host'), 'type': 'stdio',
                    'allowed_origins': [f'chrome-extension://{EXTENSION_ID}/']}
        targets = []
        for browser in BROWSERS:
            target = home / 'Library/Application Support' / browser / 'NativeMessagingHosts' / (HOST_NAME + '.json')
            atomic_write(target, json_bytes(manifest))
            targets.append(str(target))
        atomic_write(state / 'installation.json', json_bytes({'schema': 1, 'extension_dir': str(extension),
                    'host_manifests': targets, 'launcher': str(app / 'native-host')}))
    print('Installed. Load the extension folder once in Helium or Chrome. After updates, click Reload on the extension and refresh TCGplayer. No print was submitted.')


def uninstall(args, *, home=None):
    home = safe_path(home or Path.home())
    state = safe_path(args.state or home / 'Library/Application Support/TCGplayerDirectPrint')
    record = state / 'installation.json'
    if not record.exists():
        raise InstallError('No installation record found. No files were removed.')
    data = json.loads(regular_file(record).read_text())
    app = state / 'browser-helper'
    safe_path(app)
    safe_path(state / 'venv')
    expected_launcher = str(app / 'native-host')
    extension = safe_path(data['extension_dir'])
    validate_destinations(home, state, extension)
    expected_targets = [home / 'Library/Application Support' / browser / 'NativeMessagingHosts' / (HOST_NAME + '.json') for browser in BROWSERS]
    if data.get('launcher') != expected_launcher or data.get('host_manifests') != [str(p) for p in expected_targets]:
        raise InstallError('Installation record does not match this user. No files were removed.')
    if extension.exists() and not installed_identity(extension):
        raise InstallError('Extension folder identity changed. No files were removed.')
    for target in expected_targets:
        if target.exists():
            manifest = json.loads(regular_file(safe_path(target)).read_text())
            if manifest.get('name') != HOST_NAME or manifest.get('path') != expected_launcher:
                raise InstallError('Browser helper registration changed. No files were removed.')
    if args.dry_run:
        print('Would remove application code and browser registrations. Return address, saved documents, and print history would remain. No changes made.')
        return
    with install_lock(state):
        for target in expected_targets:
            if target.exists():
                target.unlink()
        for folder in (app, state / 'venv', extension):
            if folder.exists():
                safe_path(folder)
                shutil.rmtree(folder)
        record.unlink()
    print('Uninstalled application code. Your private settings, saved documents, and print history remain. Remove the extension in your browser separately.')


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--state', type=Path, help='Custom private application-state folder')
    result.add_argument('--extension-dir', type=Path, help='Permanent unpacked-extension folder')
    result.add_argument('--printer', help='Installed CUPS thermal-printer queue name')
    result.add_argument('--address-file', type=Path, help='Private UTF-8 file containing 3–5 return-address lines')
    result.add_argument('--media', help='Advertised 4×6 paper-size choice; detected automatically by default')
    result.add_argument('--darkness', type=int, help='Optional override for drivers exposing Darkness')
    result.add_argument('--speed', type=int, help='Optional override for drivers exposing PrintSpeed')
    result.add_argument('--retention-days', type=int, help='Number of days to retain saved PDFs (1–365)')
    result.add_argument('--dry-run', action='store_true')
    result.add_argument('--uninstall', action='store_true')
    result.add_argument('--no-install-deps', action='store_true', help=argparse.SUPPRESS)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if sys.platform != 'darwin':
        print('This installer supports macOS only.', file=sys.stderr)
        return 1
    if args.no_install_deps:
        print('The dependency-skipping option is only for isolated developer tests. Normal installation requires the private Python environment.', file=sys.stderr)
        return 1
    try:
        if args.uninstall:
            uninstall(args)
        else:
            install(args)
    except InstallError as error:
        print(str(error) + ' No print was submitted.', file=sys.stderr)
        return 1
    except (ValueError, EOFError, OSError, subprocess.SubprocessError):
        # Never echo private addresses, arguments, paths, or a dependency traceback.
        print('Installation did not finish. Check Python, printer setup, folder permissions, and supplied settings, then retry. No print was submitted.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
