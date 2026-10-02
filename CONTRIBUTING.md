# Contributing

Use fictional orders and addresses for every fixture. Do not add customer PDFs, screenshots, printer history, authentication data, or machine-specific paths. Generate examples with `tests/fixtures.py`.

With Python 3.10+ and Node 24:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node scripts/test-js.mjs
.venv/bin/python scripts/check_release.py
.venv/bin/python scripts/benchmark.py
.venv/bin/python scripts/package.py
```

Automated tests simulate print submission. Fresh-install checks must use an isolated temporary home and state directory, never a contributor’s live config or ledger. A physical printer test should be announced, use a fictional order, and send exactly one controlled job. Record software completion separately from physical readability.

Before releasing, run the same CI checks, review both the staged files and ZIP for private information, and obtain an independent review of changes to capture, submission, reprint, or recovery rules. Bump the manifest and all build markers together. Preserve the stable public extension key and native host origin; replacing either is a migration requiring an installer change.

Dependency updates must verify official package docs, current stable releases, supported Python/macOS versions, advisories, and hashes. Do not add unpinned dependencies or remotely loaded extension code. Issues and pull requests should include a sanitized error code and a synthetic reproduction.
