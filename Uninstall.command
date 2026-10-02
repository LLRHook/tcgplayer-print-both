#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
if command -v python3 >/dev/null 2>&1; then
  python3 install.py --uninstall "$@"
else
  printf '%s\n' 'Python 3.10 or newer is required to run the uninstaller.'
  exit 1
fi
