"""Read-only CUPS checks for the configured 4x6 Munbyn queue."""
import os
import re
import subprocess


class PrinterUnavailable(ValueError):
    pass


def _run(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=5,
                                env={**os.environ, 'LC_ALL': 'C'})
    except (OSError, subprocess.TimeoutExpired) as error:
        raise PrinterUnavailable('PRINTER_QUEUE_UNAVAILABLE') from error
    if result.returncode:
        raise PrinterUnavailable('PRINTER_QUEUE_UNAVAILABLE')
    return result.stdout


def health(config):
    queue = config['printer']
    status = _run(['/usr/bin/lpstat', '-p', queue, '-l']).lower()
    if 'disabled' in status:
        raise PrinterUnavailable('PRINTER_QUEUE_DISABLED')
    if any(reason in status for reason in ['offline', 'not connected', 'unreachable']):
        raise PrinterUnavailable('PRINTER_OFFLINE')
    accepting = _run(['/usr/bin/lpstat', '-a', queue]).lower()
    if 'not accepting' in accepting or 'accepting requests' not in accepting:
        raise PrinterUnavailable('PRINTER_NOT_ACCEPTING')
    choices = {}
    for line in _run(['/usr/bin/lpoptions', '-p', queue, '-l']).splitlines():
        key, _, values = line.partition(':')
        choices[key.split('/')[0]] = {word.lstrip('*') for word in values.split()}
    if 'w288h432' not in choices.get('PageSize', set()):
        raise PrinterUnavailable('PRINTER_MEDIA_UNSUPPORTED')
    if str(config['darkness']) not in choices.get('Darkness', set()) or str(config['print_speed']) not in choices.get('PrintSpeed', set()):
        raise PrinterUnavailable('PRINTER_OPTIONS_UNSUPPORTED')
    return {'ok': True, 'state': 'ready', 'printer': queue, 'media': '4x6',
            'darkness': config['darkness'], 'printSpeed': config['print_speed']}
