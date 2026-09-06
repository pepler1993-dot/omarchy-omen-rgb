#!/usr/bin/env python3
"""Reload the installed module and verify boot-service restoration without reboot."""
import json
import os
from pathlib import Path
import re
import subprocess

if os.geteuid() != 0:
    raise SystemExit('Root is needed to reload the installed module.')

def run(*args):
    subprocess.run(args, check=True)

device = Path('/sys/devices/platform/omen_rgb/rgb_zones/colors')
state = Path('/home/kevin/.local/state/omen-rgb/colors.json')
run('/usr/bin/modprobe', '-r', 'omen_rgb')
try:
    run('/usr/bin/modprobe', 'omen_rgb')
    original = device.read_text().split()
    if len(original) != 4 or any(not re.fullmatch('[0-9A-Fa-f]{6}', c) for c in original):
        raise RuntimeError('Invalid hardware response after loading the installed driver.')
    test = original.copy()
    test[0] = f'{int(test[0], 16) ^ 0x202020:06X}'
    device.write_text(' '.join(test) + '\n')
    if device.read_text().split() != test:
        raise RuntimeError('Installed driver did not confirm the test colors.')
    print('Installed DKMS module loaded; color change confirmed.', flush=True)
finally:
    # Always restore the user's current saved profile, including after a failed test.
    run('/usr/bin/systemctl', 'restart', 'omen-rgb-restore.service')

saved = json.loads(state.read_text())
expected = [''.join(f'{round(int(c[i:i+2], 16) * saved["brightness"] / 100):02X}'
                    for i in (0, 2, 4)) for c in saved['colors']]
actual = device.read_text().split()
if actual != expected:
    raise RuntimeError(f'Restore mismatch: expected {expected}, got {actual}')
print('Saved profile restored and verified:', ' '.join(actual), flush=True)
run('/usr/bin/systemctl', 'is-enabled', 'omen-rgb-restore.service')
run('/usr/bin/systemctl', 'is-active', 'omen-rgb-restore.service')
