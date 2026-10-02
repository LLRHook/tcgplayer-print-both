"""Read-only CUPS discovery and verified 4x6 media for any compatible driver."""
import math
import os
from pathlib import Path
import re
import subprocess

QUEUE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
MEDIA = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
PPD_DIR = Path('/etc/cups/ppd')


class PrinterUnavailable(ValueError):
    pass


def _run(args, run=None):
    try:
        result = (run or subprocess.run)(args, capture_output=True, text=True, timeout=5,
                                        env={**os.environ, 'LC_ALL': 'C'})
    except (OSError, subprocess.TimeoutExpired) as error:
        raise PrinterUnavailable('PRINTER_QUEUE_UNAVAILABLE') from error
    if result.returncode:
        raise PrinterUnavailable('PRINTER_QUEUE_UNAVAILABLE')
    return result.stdout


def parse_options(text):
    choices = {}
    for line in text.splitlines():
        key, separator, values = line.partition(':')
        if separator:
            choices[key.split('/')[0]] = {word.lstrip('*') for word in values.split()}
    return choices


def paper_dimensions(queue, ppd_dir=None):
    if not QUEUE.fullmatch(queue):
        raise PrinterUnavailable('PRINTER_QUEUE_UNAVAILABLE')
    try:
        text = ((ppd_dir or PPD_DIR) / (queue + '.ppd')).read_text(errors='replace')
    except OSError:
        return {}
    dimensions = {}
    for name, width, height in re.findall(r'^\*PaperDimension\s+([^\s/:]+)(?:/[^:]*)?:\s*"([\d.]+)\s+([\d.]+)"', text, re.M):
        try: dimensions[name] = (float(width), float(height))
        except ValueError: continue
    for axis, low, high in re.findall(r'^\*ParamCustomPageSize\s+(Width|Height):\s*\d+\s+points\s+([-+\d.eE]+)\s+([-+\d.eE]+)', text, re.M):
        try:
            limits = (float(low), float(high))
            if all(math.isfinite(value) for value in limits): dimensions['@' + axis] = limits
        except ValueError: continue
    return dimensions


def four_by_six(name, dimensions=None):
    if not isinstance(name, str) or not MEDIA.fullmatch(name):
        return False
    if name in (dimensions or {}):
        width, height = dimensions[name]
        return math.isclose(width, 288, abs_tol=2) and math.isclose(height, 432, abs_tol=2)
    return name.lower() in {'w288h432', '4x6', '4x6in', '4x6inch', '4x6inches'} or bool(re.search(r'_(?:4x6in|101\.6x152\.4mm|102x152mm)$', name.lower()))


def supported_media(choices, dimensions=None):
    pages = choices.get('PageSize', set())
    names = sorted(name for name in pages if four_by_six(name, dimensions))
    limits = dimensions or {}
    if 'Custom' in pages and all(axis in limits and limits[axis][0] <= size <= limits[axis][1] for axis, size in [('@Width', 288), ('@Height', 432)]):
        names.append('Custom.4x6in')
    return names


def validate_options(config, choices, dimensions=None):
    if config['media'] not in supported_media(choices, dimensions):
        raise PrinterUnavailable('PRINTER_MEDIA_UNSUPPORTED')
    for setting, option in [('darkness', 'Darkness'), ('print_speed', 'PrintSpeed')]:
        if config[setting] is not None and str(config[setting]) not in choices.get(option, set()):
            raise PrinterUnavailable('PRINTER_OPTIONS_UNSUPPORTED')


def driver_options(queue, run=None):
    if not QUEUE.fullmatch(queue):
        raise PrinterUnavailable('PRINTER_QUEUE_UNAVAILABLE')
    return parse_options(_run(['/usr/bin/lpoptions', '-p', queue, '-l'], run=run)), paper_dimensions(queue)


def health(config):
    queue = config['printer']
    if not QUEUE.fullmatch(queue):
        raise PrinterUnavailable('PRINTER_QUEUE_UNAVAILABLE')
    status = _run(['/usr/bin/lpstat', '-p', queue, '-l']).lower()
    if 'disabled' in status:
        raise PrinterUnavailable('PRINTER_QUEUE_DISABLED')
    if any(reason in status for reason in ['offline', 'not connected', 'unreachable']):
        raise PrinterUnavailable('PRINTER_OFFLINE')
    accepting = _run(['/usr/bin/lpstat', '-a', queue]).lower()
    if 'not accepting' in accepting or 'accepting requests' not in accepting:
        raise PrinterUnavailable('PRINTER_NOT_ACCEPTING')
    choices, dimensions = driver_options(queue)
    validate_options(config, choices, dimensions)
    return {'ok': True, 'state': 'ready', 'printer': queue, 'media': config['media'],
            'darkness': config['darkness'], 'printSpeed': config['print_speed']}


def submission_options(config, page_count):
    # Force the two pages to separate labels even if queue defaults include
    # n-up, banner sheets, page ranges or duplex settings from other jobs.
    options = ['media=' + config['media'], 'orientation-requested=3', 'sides=one-sided',
               'number-up=1', 'job-sheets=none', 'page-set=all', 'job-hold-until=no-hold', 'outputorder=normal', 'page-ranges=1-' + str(page_count), 'print-scaling=none', 'fit-to-page=false']
    for setting, option in [('darkness', 'Darkness'), ('print_speed', 'PrintSpeed')]:
        if config[setting] is not None:
            options.append(option + '=' + str(config[setting]))
    return [arg for value in options for arg in ['-o', value]]
