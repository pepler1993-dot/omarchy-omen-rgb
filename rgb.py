#!/usr/bin/env python3
"""OMEN four-zone RGB bridge. No root execution or automatic driver loading."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import sys

DEVICE = Path('/sys/devices/platform/omen_rgb/rgb_zones/colors')
STATE = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'omen-rgb/colors.json'


def validate(colors, brightness):
    if not isinstance(colors, list) or len(colors) != 4:
        raise ValueError('Es werden genau vier Farben benötigt.')
    if any(not isinstance(c, str) or not re.fullmatch(r'#?[0-9a-fA-F]{6}', c) for c in colors):
        raise ValueError('Farben bitte als sechsstelligen Hex-Code eingeben, z. B. #FF8800.')
    if type(brightness) is not int or not 0 <= brightness <= 100:
        raise ValueError('Die Helligkeit muss zwischen 0 und 100 liegen.')
    return [c.removeprefix('#').upper() for c in colors], brightness


def scaled(colors, brightness):
    return [''.join(f'{round(int(c[i:i+2], 16) * brightness / 100):02X}' for i in (0, 2, 4)) for c in colors]


def read_colors(device=DEVICE):
    colors = device.read_text().split()
    return validate(colors, 100)[0]


def status(device=DEVICE, state=STATE):
    result = dict(available=False, writable=False, colors=['FFFFFF'] * 4, brightness=100)
    if not device.exists():
        return result | {'message': 'RGB-Treiber noch nicht aktiviert. Farbauswahl und Vorschau sind bereits verfügbar.'}
    actual = read_colors(device)
    result.update(available=True, writable=os.access(device, os.W_OK), colors=actual, actual=actual)
    try:
        saved = json.loads(state.read_text())
        colors, brightness = validate(saved['colors'], saved['brightness'])
        if scaled(colors, brightness) == actual:
            result.update(colors=colors, brightness=brightness)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    result['message'] = 'Bereit' if result['writable'] else 'RGB erkannt; Schreibberechtigung fehlt noch.'
    return result


def apply(colors, brightness, device=DEVICE, state=STATE):
    colors, brightness = validate(colors, brightness)
    if not device.exists():
        raise ValueError('Der RGB-Treiber ist noch nicht aktiviert.')
    state.parent.mkdir(parents=True, exist_ok=True)
    with (state.parent / 'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        desired = scaled(colors, brightness)
        # Driver performs a single read-modify-write for all four zones.
        device.write_text(' '.join(desired) + '\n')
        if read_colors(device) != desired:
            raise ValueError('Die Firmware hat die Farben nicht bestätigt. Das Profil wurde nicht gespeichert.')
        temporary = state.with_suffix('.tmp')
        temporary.write_text(json.dumps(dict(colors=colors, brightness=brightness)) + '\n')
        temporary.replace(state)
    return status(device, state) | {'ok': True, 'message': 'Farben angewendet und gespeichert.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'apply', 'restore'])
    parser.add_argument('--colors', nargs=4)
    parser.add_argument('--brightness', type=int, default=100)
    args = parser.parse_args()
    try:
        if args.action == 'status':
            result = status()
        elif args.action == 'apply':
            result = apply(args.colors, args.brightness)
        elif STATE.exists():
            saved = json.loads(STATE.read_text())
            result = apply(saved['colors'], saved['brightness'])
        else:
            result = {'ok': True, 'message': 'Noch kein gespeichertes Profil.'}
        print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'ok': False, 'message': str(error)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
