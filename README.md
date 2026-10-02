# TCGplayer Print Both

One click on a TCGplayer order prints its official packing slip and a matching mailing-address label on your selected 4×6 thermal printer. No AI, API key, cloud printing service, or file selection is needed for each order.

The **Print both** button sits beside **Packing Slip**. It requests TCGplayer’s **Print Default** PDF, scales every original page to portrait 4×6, adds the address page, and sends one print job. A multi-page order produces all of its packing-slip pages plus one address page.

## Install

Download **TCGplayer-Print-Both.zip** from [Releases](https://github.com/LLRHook/tcgplayer-print-both/releases), unzip it, and follow [the installation guide](docs/INSTALL.md).

You need:

- macOS 13 or newer and Python 3.10 or newer.
- Chrome or Helium, with access to your TCGplayer seller account.
- An installed thermal printer whose macOS driver advertises a 4×6 paper size (or verified custom paper-size limits), with 4×6 labels loaded.

Run **Install.command** to select your printer and enter your own return address. Setup detects its advertised 4×6 paper size and uses your saved driver preferences. Darkness and speed overrides are optional; Munbyn-specific controls are not required. Then load the installed extension folder once through your browser’s **Load unpacked** control and refresh the order page. Subsequent updates reuse the same folder; reload the extension and refresh the page after installing an update.

The installer creates a private Python environment and installs hash-verified dependencies. It does not require Codex, administrator access, or a background download watcher. This release is distributed through GitHub; it is not a Chrome Web Store or notarized macOS app.

## Use

After the one-time setup, the normal workflow is **open the TCGplayer order → click Print both → collect both labels**. The official packing slip and address page are generated and sent together; no per-order file download, file selection, AI request, or print dialog is required.

Open one order and click **Print both**. The button is disabled while that click is processing. **Sent ✓** means the printer accepted the job; **Printed ✓** means CUPS reports completion. Confirm the actual labels are readable—software cannot detect upside-down thermal paper or faint output. The extension popup’s **Check job** refreshes a delayed job without printing again.

A new deliberate click can reprint a completed order. Re-delivery of the same click is deduplicated. If a previous submission is still pending or uncertain, another print is blocked until you inspect the printer queue and resolve it. See [recovery](docs/INSTALL.md#recovery).

The mailing label leaves space for a **physical stamp**. This product does not purchase postage or provide tracking. Weigh and check your finished envelope using your normal shipping process.

## Supported scope

The native default slip is the standard input. Address extraction also has tests for the shipping-address and envelope-window layouts. US city/state/ZIP addresses with Windows-1252 characters are supported; unsupported characters or layouts fail before submission. PDFs are limited to 16 MiB and 64 original pages. Shrinking preserves the original layout and text; very small original text can remain difficult to read on a 203 dpi printer.

The physical reference printer is a Munbyn USB 203 dpi model with a macOS CUPS driver. The printing path also supports compatible drivers from other brands: paper choices such as `4x6`, `na_index-4x6_4x6in`, model-specific sizes verified from driver dimensions, and `Custom.4x6in` when the driver advertises Custom and its width/height limits cover 4×6. Unsupported sizes fail before submission. Other brands have simulated-driver coverage, not physical certification. Helium is the live-tested browser; Chrome uses the same extension/native-messaging interfaces and installer registration, but has not had a separate live seller-account test. Windows, Linux printing, international address formats, automatic unattended order polling, and browser-store installation are outside this release.

## Privacy and development

Buyer information stays in the local printing workflow. The public repository and release ZIP contain no customer PDFs, addresses, printer history, or local configuration. Read [Privacy](PRIVACY.md) and [Security](SECURITY.md).

For automated checks and contributions, see [Contributing](CONTRIBUTING.md). [Requirements](docs/REQUIREMENTS.md), [release verification](VERIFICATION.md), and [readiness](docs/READINESS.md) describe the tested scope and remaining limitations.

MIT licensed. This community project is not affiliated with TCGplayer or Munbyn.
