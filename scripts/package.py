#!/usr/bin/env python3
"""Build a deterministic, source-only community release ZIP."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = 'TCGplayer-Print-Both-Installer'
ROOT_FILES = ('README.md', 'LICENSE', 'SECURITY.md', 'PRIVACY.md', 'requirements.txt',
              'requirements.lock', 'install.py', 'Install.command', 'Uninstall.command')
DOC_FILES = ('INSTALL.md',)


def package(output, root=ROOT):
    spec = importlib.util.spec_from_file_location('tcgprint_installer', root / 'install.py')
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    installer.source_validation(root)
    paths = [Path(file) for file in ROOT_FILES]
    paths += [Path('native') / file for file in installer.NATIVE_FILES]
    paths += [Path('extension') / file for file in installer.EXTENSION_FILES]
    paths += [Path('docs') / file for file in DOC_FILES]
    for path in paths:
        installer.regular_file(root / path)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + '.tmp')
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(paths):
                info = zipfile.ZipInfo(ARCHIVE_ROOT + '/' + path.as_posix(), (2026, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (0o100755 if path.name in {'Install.command', 'Uninstall.command'} else 0o100644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, (root / path).read_bytes())
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/TCGplayer-Print-Both.zip')
    args = parser.parse_args()
    package(args.output)
    print('Source-only release ZIP created. No local settings or print documents were included.')


if __name__ == '__main__':
    main()
