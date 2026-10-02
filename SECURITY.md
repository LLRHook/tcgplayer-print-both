# Security

## Report a vulnerability

Use this repository’s **Security → Report a vulnerability** for private reports. Include reproduction steps with fictional data. Do not post credentials, buyer details, or real packing slips in public issues. Only the latest release is maintained.

## Printing boundary

The helper listens through browser native messaging on standard input/output; there is no HTTP listener or network print endpoint. Its registration permits one fixed extension origin. The extension is limited to TCGplayer’s seller portal and requires a trusted user click, a top-frame content-script sender, a current matching order tab, a request token, and a matching document for PDF handoff. The helper accepts PDF bytes, not a caller-selected filesystem path. It checks the PDF framing, size, order identity, complete pagination, address format, and fit before submitting.

Each click has a unique identifier. A durable intent is recorded before printer submission. Replaying that identifier cannot submit a second job. A new click may repeat a completed order, while pending or uncertain submissions block retries. Recovery is an explicit local action after inspecting the queue; it preserves old receipts and refuses known active jobs.

The application runs as your user. It is not a sandbox against malicious software already running as that user, a compromised browser/TCGplayer page, or a hostile PDF parser exploit. The fixed public extension key provides a stable ID, not publisher authentication for arbitrary unpacked code. Install only reviewed release files. Native PDFs come from the official export in normal use; do not feed untrusted documents to the helper.

## Supply chain and release checks

Runtime dependencies are fully pinned and artifact-hashed in `requirements.lock`. CI uses pinned action commits, a dependency advisory audit, synthetic Python/JavaScript tests, and a publication gate that rejects private data artifacts and suspicious secret patterns. Release ZIPs use a code/document allowlist and exclude configuration, PDFs, ledgers, and development environments. These checks reduce disclosure risk; a maintainer must still review new fixtures and documentation for personal information.

The installer registers the helper only in supported browsers and never changes browser extension policies or bypasses their management controls. Unpacked installation requires a user’s normal browser action. Local private state must stay outside the repository.
