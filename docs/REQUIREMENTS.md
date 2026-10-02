# Community release requirements

Scope: a source-distributed macOS application consisting of an unpacked Chromium extension and a local printing helper. This specification records the requested one-click workflow and makes the community release boundaries explicit. It does not claim Windows, browser-store, signed-app, or independent certification support.

| ID | Priority | Requirement | Verification |
|---|---|---|---|
| FR-1 | Must | One compact button beside native Packing Slip; busy, success and error indicators | Content tests and prior live Helium check |
| FR-2 | Must | Capture official default PDF without Save As or per-order file selection | Bridge/background tests; prior live order print |
| FR-3 | Must | Preserve every original slip page on portrait 4×6 and append the same order’s address label | Native/product text, size, pagination and mismatch tests |
| FR-4 | Must | One direct configured thermal-printer job per accepted click with detected verified 4×6 media and optional vendor controls | Native tests; physical reference-printer check |
| FR-5 | Must | Distinct completed-order reprints work; request replay is idempotent; uncertain jobs block retry | Replay, two-click, failure and recovery tests |
| FR-6 | Must | A new user can install, upgrade and uninstall without Codex or private source paths | Isolated real dependency install; installer tests |
| FR-7 | Must | Public source/release omit customer information and machine state | Publication gate, release allowlist and independent review |
| FR-8 | Must | Check configured printer and read delayed-job status without printing | Queue health and receipt tests |
| FR-9 | Should, committed | PDF retention and explicit recoverable print history | Retention and resolution tests |
| FR-10 | Should, committed | Public documentation, license, CI and reproducible downloadable package | Release gate, package checks and GitHub CI |
| NFR-1 | Must | Fixed native origin; current-order, document, token, pagination and trusted-click checks | Browser/native rejection tests and security review |
| NFR-2 | Must | Private local files; no telemetry/AI/cloud printing; no browser-supplied path | Permission tests, code review, privacy policy |
| NFR-3 | Must | Size/page bounds: 16 MiB / 64 original pages; reject unsupported address characters and clipping | Native/product rejection tests |
| NFR-4 | Must | Three-page synthetic conversion ≤5 sec median; thirty-page ≤30 sec median on reference Mac, excluding printer/transport | Repeatable warmed benchmark |
| NFR-5 | Must | Keyboard-operable button, accessible name, busy state and live status | Content accessibility assertions; native HTML button |
| NFR-6 | Must | Fully pinned/hash-verified runtime dependencies, no known advisory findings at release | Lock install and dependency audit |

The release bar is all Must and committed Should verified, no known critical/high defects, green CI, a source-only package, an independent security/privacy review, and documented hardware/browser limitations. Pilot status can precede public release once the core workflow and safety checks pass. Full readiness is limited to this agreed product scope; proof on one printer does not certify all thermal-printer models or future TCGplayer page layouts.

Version 1.1 broadens FR-4/FR-6: a new user selects an installed 4×6 thermal printer regardless of brand, supplies a return address, loads the extension once, and prints the slip/address set with one button. New setups use saved driver preferences. Standard CUPS/PWG sizes, verified PPD dimensions and advertised Custom sizes are supported; incorrect or unverifiable media is rejected. Generic driver validation is simulated; physical compatibility must not be advertised for untested models.
