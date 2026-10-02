#!/usr/bin/env python3
"""Fail closed on private artifacts or inconsistent public release metadata."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BAD_SUFFIXES = {'.pdf', '.jpg', '.jpeg', '.png', '.sqlite', '.sqlite3', '.db', '.log', '.pem', '.key', '.pyc'}
BAD_NAMES = {'config.json', 'installation.json', 'ledger.sqlite3', 'baseline.done'}
PATTERNS = [
    ("machine path", re.compile(rb'/Users/[A-Za-z0-9_.-]+/')),
    ("live order identifier", re.compile(rb'\b(?!TEST)[A-Z0-9]{8}-[A-Z0-9]{6}-[A-Z0-9]{5}\b')),
    ("private key", re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ("credential", re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16})')),
]


def scan(name, data):
    path = Path(name)
    if path.suffix.lower() in BAD_SUFFIXES or path.name in BAD_NAMES:
        raise ValueError(f'Private/binary artifact prohibited: {name}')
    if any(part in {'.venv', '__pycache__', 'generated', 'browser-inputs', 'browser-paired'} for part in path.parts):
        raise ValueError(f'Runtime directory prohibited: {name}')
    data.decode('utf-8')
    for label, pattern in PATTERNS:
        if pattern.search(data):
            # Never print the matched data, which could itself be a secret.
            raise ValueError(f'Publication gate: {label} in {name}')


def verify(root=ROOT, archive=None):
    raw = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root)
    paths = sorted({name.decode() for name in raw.split(b'\0') if name})
    for name in paths:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Only regular source files are allowed: {name}')
        scan(name, path.read_bytes())
    manifest = json.loads((root / 'extension/manifest.json').read_text())
    version = manifest['version']
    for file in ['background.js', 'content.js', 'popup.js']:
        if f"'{version}'" not in (root / 'extension' / file).read_text():
            raise ValueError('Build markers must match manifest version')
    key = hashlib.sha256(base64.b64decode(manifest['key'], validate=True)).hexdigest()[:32]
    extension_id = ''.join(chr(ord('a') + int(char, 16)) for char in key)
    if extension_id != 'pidblibebfmenlpcbnajfcdoikdldhgj':
        raise ValueError('Native origin migration required for changed extension key')
    if set(manifest['permissions']) != {'nativeMessaging', 'storage', 'downloads'}:
        raise ValueError('Extension permissions changed; review required')
    if manifest['host_permissions'] != ['https://sellerportal.tcgplayer.com/*']:
        raise ValueError('Extension must remain limited to seller portal')
    lock = (root / 'requirements.lock').read_text()
    pins = re.findall(r'^([A-Za-z0-9_.-]+)==([^\s\\]+)\s*\\', lock, re.M)
    if len(pins) != 10 or lock.count('--hash=sha256:') < len(pins):
        raise ValueError('Expected fully hashed ten-package runtime lock')
    if archive:
        from package import ROOT_FILES, DOC_FILES
        import importlib.util
        spec = importlib.util.spec_from_file_location('release_installer', root / 'install.py')
        installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)
        expected = set(ROOT_FILES) | {'native/' + name for name in installer.NATIVE_FILES} | {'extension/' + name for name in installer.EXTENSION_FILES} | {'docs/' + name for name in DOC_FILES}
        with zipfile.ZipFile(archive) as z:
            actual = {info.filename.removeprefix('TCGplayer-Print-Both/') for info in z.infolist()}
            if actual != expected: raise ValueError('Release ZIP does not match exact source allowlist')
            for info in z.infolist():
                name = info.filename.removeprefix('TCGplayer-Print-Both/')
                data = z.read(info)
                scan(name, data)
                if data != (root / name).read_bytes(): raise ValueError('Release ZIP differs from current source')
    print(f'PASS: {len(paths)} public source files; metadata, permissions, dependency lock and privacy gate' + ('; exact release ZIP' if archive else ''))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    verify(archive=args.archive)
