# Security audit baseline

2026-10-02, community release1.0.0. Scope: clean working source, first public Git history, runtime dependency lock, packaging, installation, extension-to-helper trust and CUPS submission/recovery. No private customer documents were used in the audit.

Known advisory scan: pip-audit2.10.1 against all11 pinned/hash-verified runtime packages returned zero known vulnerabilities. The extension has no runtime npm dependencies or remote executable code. CI actions are pinned to verified official commit SHAs.

Independent review found and corrected: programmatic page clicks could initiate printing; retention could delete an old cached PDF immediately before a reprint; an old receipt response could reinstate a resolved guard; localized CUPS output could hide an accepted job handle. Regression tests cover each. Installer review corrected shared/root destinations, rejected symlinks/unrelated state folders, and made interrupted first installs recoverable with a private ownership record.

Publication: the repository starts from sanitized code, documentation, and fictional fixture generators. Private Downloads, app state, actual PDFs, printer history, real order references, API keys and prior private development history are not imported. Source and release ZIP are checked before publication. Pattern checks complement manual review; they do not prove the absence of arbitrary personal information in future contributions.

Open critical/high findings:0 at this baseline. Accepted boundaries: user-installed unpacked source; local user account is trusted; no PDF-parser sandbox; no signed/notarized app; CUPS/OS spool records have independent retention; current seller page/export must remain compatible. See SECURITY.md and PRIVACY.md. A clean advisory audit is a point-in-time result, not a guarantee against unknown vulnerabilities.
