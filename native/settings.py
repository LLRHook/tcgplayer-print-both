"""Validated, local-only printer settings shared by setup and the helper."""
import os
import re
from pathlib import Path

QUEUE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
DEFAULT_STATE = Path(os.environ.get('TCGPRINT_STATE', Path.home() / 'Library/Application Support/TCGplayerDirectPrint'))


def validate_config(config):
    if not isinstance(config, dict):
        raise ValueError('Configuration must be an object')
    printer = config.get('printer')
    if not isinstance(printer, str) or not QUEUE.fullmatch(printer):
        raise ValueError('Select a valid local printer queue')
    lines = config.get('return_address')
    if not isinstance(lines, list) or not 3 <= len(lines) <= 5:
        raise ValueError('Return address must have three to five lines')
    result = []
    for line in lines:
        if not isinstance(line, str) or not line.strip() or len(line) > 120 or any(ord(c) < 32 or ord(c) == 127 for c in line):
            raise ValueError('Return address lines must be printable, nonempty text')
        try:
            line.encode('cp1252')
        except UnicodeEncodeError as error:
            raise ValueError('This release supports Western European address characters') from error
        result.append(line.strip())
    legacy = 'media' not in config
    media = config.get('media', 'w288h432')
    if not isinstance(media, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', media):
        raise ValueError('Select a supported 4x6 printer media choice')
    darkness = config.get('darkness', 14 if legacy else None)
    speed = config.get('print_speed', 30 if legacy else None)
    retention = config.get('retention_days', 30)
    if darkness is not None and (type(darkness) is not int or not 1 <= darkness <= 16):
        raise ValueError('Darkness must be an integer from 1 to 16')
    if speed is not None and (type(speed) is not int or speed not in range(10, 81, 10)):
        raise ValueError('Print speed must be 10, 20, 30, 40, 50, 60, 70, or 80')
    if type(retention) is not int or not 1 <= retention <= 365:
        raise ValueError('Retention must be an integer from 1 to 365 days')
    return {'printer': printer, 'media': media, 'return_address': result, 'darkness': darkness,
            'print_speed': speed, 'retention_days': retention}
