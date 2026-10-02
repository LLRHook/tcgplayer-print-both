# Install on macOS

This release supports macOS, a compatible 4×6 thermal-printer driver, and Helium or Google Chrome. It is an unpacked extension paired with a small private Python printing helper. Windows and Linux installations are not supported by this installer.

## Before installing

1. Install **Python 3.10 or newer** from [python.org](https://www.python.org/downloads/macos/). Confirm that `python3 --version` works in Terminal. The installer creates its own Python environment; it does not use Codex or change your system packages.
2. Add your thermal printer in macOS **System Settings → Printers & Scanners**. Install the compatible manufacturer driver and confirm a printer self-test works on correctly oriented direct-thermal labels.
3. The driver must advertise **4×6-inch media** or verified **Custom** size limits. Configure your preferred darkness and speed in the printer’s own settings. The installer detects the selected queue’s 4×6 media and uses the saved driver defaults; brand-specific darkness and speed controls are optional.
4. Download and extract the public release ZIP. It expands into `TCGplayer-Print-Both-Installer`, separate from the installed extension folder. Keep the extracted source folder if you want to use its uninstaller later. No buyer data is included in this distribution.

## Install

Open Terminal in the extracted `TCGplayer-Print-Both-Installer` folder and run:

```sh
python3 install.py
```

Alternatively, run `Install.command` from that folder. macOS may ask you to confirm opening a downloaded command. This release is not a signed or notarized macOS app; inspect the source before running it. If macOS blocks opening the command, use the Terminal command above. The installer never needs administrator privileges.

Choose the installed thermal-printer queue and enter your own return address as **3–5 lines**, ending with an empty line. Address lines must be printable Western European characters supported by the printer PDF fonts. Your return address remains in your private application settings. The installer validates it and does not echo it in error messages.

Installation creates:

- An unpacked extension at `~/Downloads/TCGplayer-Print-Both`.
- A private helper, Python environment, and settings at `~/Library/Application Support/TCGplayerDirectPrint`.
- Native-host registrations for Helium and Chrome, allowing only this extension's fixed identity.

It does not print a test, change orders, buy postage, or modify browser policy.

## Load the extension once

1. In Helium or Chrome, open the browser's **Extensions** management page.
2. Enable **Developer mode**.
3. Choose **Load unpacked** and select `~/Downloads/TCGplayer-Print-Both`.
4. Open or refresh a TCGplayer seller order. The **Print both** button appears beside the native packing-slip action.
5. Open the extension popup and check the helper before the first live print. Verify your printer is ready, then click **Print both** once to print the packing slip and address label together. The label reserves space for a **physical stamp**; it is not paid postage.

A new deliberate click can print another set. Repeated delivery of the same click does not submit another job. A pending or uncertain earlier submission must be checked before printing again.

## Update

Version 1.1 keeps the fixed extension identity and installation folders. Your 1.0 Munbyn preset (including darkness/speed), return address and history migrate without resetting them. No browser extension reinstall is needed after updating; reload the existing entry.

Extract a new release and run its installer. It preserves existing return-address settings, print history, and saved documents. It replaces only the extension and helper code and installs the release's pinned, hash-verified dependencies in its private environment.

After installation, click **Reload** for this extension in the browser's Extensions page, then refresh TCGplayer. A page refresh by itself does not reload updated extension code. Keep the same permanent extension folder so you do not need to install the extension again.

To change settings explicitly, provide the relevant options. For unattended setup, put your return address in a private UTF-8 file, one line per row, and use `--address-file`; avoid putting addresses directly in shell commands or shared logs.

```sh
python3 install.py --printer YOUR_QUEUE --address-file /path/to/private-return-address.txt
```

Queue names come from `lpstat -p`. Media is detected automatically; `--media` can select an advertised 4×6 choice explicitly. New setups use driver defaults, and existing installations retain saved overrides. Changing printers clears incompatible media and vendor overrides before detecting the new queue. Optional `--darkness` supports values 1–16 and `--speed` supports 10, 20, 30, 40, 50, 60, 70, or 80, when the selected driver exposes the matching Darkness or PrintSpeed control. Omit these options on drivers without those controls. The driver units are not millimeters per second. Re-running without explicit changes keeps existing settings. Saved PDFs use a 30-day retention setting by default; `--retention-days` accepts 1–365. Print-history records are retained to preserve protection against duplicate submissions.

Use `python3 install.py --dry-run` for a source and destination check that changes nothing. This does not prove that your printer or browser is ready.

## Uninstall

Run the extracted release's `Uninstall.command`, or:

```sh
python3 install.py --uninstall
```

The uninstaller removes the helper, its Python environment, browser native-host registrations, and the unpacked extension folder. **It preserves your settings, print history, and saved order documents** in the private application-state folder. Remove the extension entry in your browser separately. To delete retained private data permanently, review and delete the application-state folder yourself after uninstalling.

If installation used a custom `--state` folder, give the same option to uninstall. A custom `--extension-dir` is recorded automatically. Custom folders must be dedicated folders inside your home directory; shared folders and unrelated existing folders are refused. Do not move installed folders manually.

## Recovery

For a delayed print, open the extension popup and choose **Check job**. This is a read-only printer query; it does not submit another job. For a failed or uncertain print, inspect the Mac print queue and the physical output first. Cancel an unwanted active job using the normal Mac print-queue controls and wait until it is no longer active. If submission was uncertain and no job handle was recorded, check the queue carefully for an accepted job before allowing another print.

Use the installed helper for diagnosis and explicit recovery:

```sh
print_state="$HOME/Library/Application Support/TCGplayerDirectPrint"
"$print_state/venv/bin/python3" "$print_state/browser-helper/tcgprint.py" --state "$print_state" doctor
"$print_state/venv/bin/python3" "$print_state/browser-helper/tcgprint.py" --state "$print_state" status
"$print_state/venv/bin/python3" "$print_state/browser-helper/tcgprint.py" --state "$print_state" resolve YOUR_ORDER_REFERENCE --acknowledge-queue-inspected
```

Replace `YOUR_ORDER_REFERENCE` with the full reference for the affected order. The acknowledgement confirms you actually inspected the queue; it is not an instruction to skip that inspection. Resolution refuses known active jobs, preserves receipts, and never prints. Once it succeeds, a new **Print both** click can submit another set. If CUPS no longer has a recorded job, resolution fails safely; inspect/recover with the maintainer using sanitized diagnostics rather than deleting history.

To remove expired private PDFs after resolving outstanding jobs:

```sh
"$print_state/venv/bin/python3" "$print_state/browser-helper/tcgprint.py" --state "$print_state" cleanup
```

Use your custom state path if installation used `--state`. These local commands can display order references; redact them before sharing terminal output.

## Troubleshooting

- **Interrupted install or failed download:** rerun the installer from the complete extracted release. It records ownership before dependency bootstrap so an incomplete first install can be repaired. Private settings, saved documents, and history are not deleted by this retry.
- **Installer stops:** confirm Python is at least 3.10, the thermal queue is installed, and the driver advertises a supported 4×6 size. Remove optional darkness/speed overrides if that driver does not support them. Use a folder your user owns. Installation paths cannot include symbolic links.
- **Helper unavailable:** rerun the installer, then reload the extension and refresh TCGplayer. The browser and helper must belong to the same macOS user.
- **Button asks for a reload:** reload the extension, then refresh the order page. The extension rejects mismatched code versions instead of mixing old and new printing logic.
- **Job submitted but paper did not emerge:** inspect macOS's print queue and the printer's power, connection, lid, media orientation, and self-test. Computer completion is not a physical inspection of a readable label.
- **Uncertain earlier job:** inspect the queue before retrying. Do not delete print history to force a retry; that removes the protection against accidental duplicate jobs.
- **Installed Python later removed:** reinstall Python, then rerun the installer to repair its private environment.
- **Shared screenshots or bug reports:** redact buyer addresses and order documents. Do not attach your private configuration, ledger, or saved PDFs.

## Printer compatibility

Setup recognizes explicit 4×6 CUPS/PWG paper names, verifies model-specific paper codes against the driver’s PPD dimensions where available, and uses `Custom.4x6in` only when the driver advertises Custom and its width/height limits cover 4×6. It rejects Letter, rotated 6×4 choices, and unknown sizes that cannot be verified. A paper size supplied through `--media` must pass the same checks. No arbitrary driver options are accepted.

A compatible macOS driver and correctly configured thermal printer are prerequisites. Installing this product does not install printer firmware or manufacturer drivers. Physical validation uses the reference Munbyn; drivers from other brands are covered by synthetic integration tests and should be tested locally before fulfilling real orders.
