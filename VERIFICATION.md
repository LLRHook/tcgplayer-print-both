# Release verification

## 1.0.0 candidate — 2026-10-02

Verified locally against the sanitized community source and locked runtime dependencies. The public tag is cut only after the hosted **Community release checks** workflow succeeds; use the [Actions page](https://github.com/LLRHook/tcgplayer-print-both/actions) for the exact commit/run record.

| Gate | Evidence | Result |
|---|---|---|
| Python correctness | 55 unittest cases: installer, native framing, extraction, multi-page preservation, bounds, queue checks, per-click replay/reprints, recovery concurrency, retention, publication policy | PASS |
| Browser components | All five Node suites: background trust/serialization, PDF capture/suppression, content states/trusted click/accessibility, popup diagnostics/status, current-tab navigation regression | PASS |
| Fresh installation | Isolated new home and real hash-locked Python environment; installed helper bytes match source; framed native ping checks actual configured printer read-only | PASS |
| Upgrade/uninstall | Synthetic private configuration, ledger and PDF retained; only owned code and registrations replaced/removed | PASS |
| Dependency security | pip-audit 2.10.1, strict hashed lock, ten runtime packages, no advisory findings; no runtime npm dependencies | PASS |
| Source and ZIP privacy | Public-only source tree; no private history; fictional generated fixtures; exact ZIP code/document allowlist and secret/private-artifact gate | PASS |
| Performance | Warmed conversion medians: 3 original pages 0.041s; 30 original pages 0.415s; no print submission | PASS |
| Physical reference printer | Current community native helper, one fictional single-page order, one combined job, CUPS IPP state9, 2 output pages and 2 sheets completed | PASS |
| Independent review | Trusted-click, retention ordering, status/recovery locking, submission locale and installer-path findings fixed and regression-tested | PASS |

The hardware test used isolated private state and did not replace the user's working installed extension. Prior live Helium tests established the real TCGplayer button/export/native handoff and two-sheet workflow. The community candidate repeats that capture design with a trusted-click requirement and additional status/recovery protections; this validation combines the earlier real browser workflow, current synthetic component checks, fresh helper installation and current hardware submission. It is not a separate fresh live seller-account test in Chrome.

CUPS completion proves reported job completion, not physical darkness, paper orientation, or readability. The user confirmed the original workflow's physical output; the final fictional test records software completion. Additional printer models, macOS releases, international fonts/addresses, and future TCGplayer changes need further certification.

## Repeat the automated checks

Use the commands in CONTRIBUTING.md. They do not print. Hosted CI repeats Python checks on Python3.10/Linux, Python3.12/macOS14 and Python3.14/current macOS, Node24 component tests, advisory audit, performance budgets and ZIP publication checks. CI failures block cutting a release.
