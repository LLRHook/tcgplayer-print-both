# Performance baseline

2026-10-02, Apple Silicon reference Mac, Python3.12, locked community dependencies. The benchmark generates fictional letter-sized packing slips with24 items per page and never submits a print.

| Original pages | Output pages | Warmed runs | Median seconds | Budget seconds |
|---|---|---|---|---|
| 3 | 4 | 3 | 0.041 | 5 |
| 30 | 31 | 3 | 0.415 | 30 |

PASS for both NFR-4 budgets. Reproduce with `python scripts/benchmark.py` in the configured environment. Hosted CI applies the same generous budgets to its different machines; exact durations will vary. This measures parse/address extraction/packing-slip scaling/address-page generation, excluding browser export, driver rasterization, USB transport and physical feed time.

Runtime inputs are limited to16MiB and64 native pages. Printer preflight commands have5-second timeouts, submission45 seconds, and IPP status queries10 seconds. The helper observes completion for up to18 seconds and otherwise returns a submitted receipt that can be checked later. This is not a worst-case bound for hostile PDF parsing; untrusted documents are outside the normal official-export input boundary documented in SECURITY.md.

Open critical/high performance findings:0 within the measured scoped budgets. Other printer/driver performance needs separate physical measurement.
