#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
if command -v python3 >/dev/null 2>&1; then
  python3 install.py "$@"
else
  printf '%s\n' 'Install Python 3.10 or newer from python.org, then run this installer again.'
  exit 1
fi
