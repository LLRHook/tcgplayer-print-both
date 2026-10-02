# Changelog

## 1.1.0 — Brand-independent printer setup

- Renamed the extension to TCGplayer Print Both while preserving its fixed identity.
- Select the user’s installed thermal queue and detect its verified 4×6 media; support standard media names, PPD dimensions, and advertised custom paper sizes.
- Use the printer’s saved defaults for new installations; vendor-specific darkness/speed overrides are optional. Preserve existing Munbyn presets on upgrade and clear incompatible presets when switching printers.
- Submit all slip/address pages with one copy, one page per sheet, no banners, portrait media and no driver scaling, protecting the pair from unrelated queue defaults.
- Added generic-driver install, health, media rejection, upgrade and complete two-page handoff regressions.

## 1.0.0 — Community release

- One TCGplayer button captures the official default slip and prints all portrait 4×6 slip pages plus a matching physical-stamp address page.
- Configurable local Munbyn queue, return address, darkness, speed and PDF retention.
- Durable per-click deduplication, deliberate completed-order reprints, delayed-job checks and explicit uncertain-job recovery.
- Mac installer, browser native-host registration, reusable update folder, data-preserving uninstall and hash-locked dependencies.
- Fictional tests, independent review, CI, privacy publication checks, reproducible ZIP and community documentation.

Validation details are maintained in VERIFICATION.md. Source version remains 1.0.0, matching the working prototype’s manifest; the public repository starts with sanitized source and no private development history.
