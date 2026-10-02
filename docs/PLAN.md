# Release plan

Prerequisites: a working one-click prototype, macOS CUPS access, a compatible Munbyn driver, Python, and GitHub publish access. Runtime records and customer downloads remain outside the clean source repository.

1. Establish a clean source tree with synthetic fixtures and a privacy publication gate.
2. Replace machine-specific setup with a reusable installer, pinned dependencies, own return-address configuration, and explicit upgrade/uninstall behavior.
3. Harden click authorization, configured-printer checks, request replay, delayed status, retention and recovery; remove the legacy download watcher from the community product.
4. Run automated conversion/capture/printing-state tests, a fresh isolated install, dependency audit and bounded performance checks. Independently review the printing and installation boundaries.
5. Perform one announced fictional two-sheet hardware test, then create the public GitHub repository. Run hosted CI before cutting the downloadable release and checksums.

Exit: requirements coverage is green within the documented Mac scope; no customer artifacts are published; current CI passes; a new user has complete install/use/recovery instructions and a versioned package.

Risks: TCGplayer can change PDF or page layouts; unsupported input must fail safely. CUPS completion cannot prove readable paper. OS privacy/security prompts and unpacked-extension loading remain normal user actions. A failed/uncertain job must never be silently retried. Pinned dependency updates require revalidation.

Rollback: keep the previous release ZIP; reinstall it into the same dedicated folders and reload the extension. Preserve settings/ledger during rollback. Do not delete print intents to recover a queue error. The community build does not modify the author’s working private installation during development.

Future, uncommitted scope: Windows helper, Chrome Web Store distribution, signed/notarized app, broader address fonts/formats, and additional physical printer/browser certification. Each needs its own acceptance tests before support is advertised.
