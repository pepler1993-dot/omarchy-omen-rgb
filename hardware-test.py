#!/usr/bin/env python3
"""Brief color test; always restore the initial hardware colors."""
import json
from pathlib import Path
import tempfile
import time
import rgb

original = rgb.read_colors()
backup = Path(__file__).resolve().parent / 'original-colors.json'
if not backup.exists():
    backup.write_text(json.dumps({'colors': original, 'brightness': 100}) + '\n')
print('Initial colors:', ' '.join(original), flush=True)
with tempfile.TemporaryDirectory(prefix='omen-rgb-test-') as directory:
    state = Path(directory) / 'colors.json'
    try:
        result = rgb.apply(['FF0000', '00FF00', '0000FF', 'FFFFFF'], 50, state=state)
        print('Test readback:', ' '.join(result['actual']), flush=True)
        time.sleep(2)
    finally:
        rgb.DEVICE.write_text(' '.join(original) + '\n')
        if rgb.read_colors() != original:
            raise RuntimeError('Original colors could not be verified after restore.')
        print('Original colors restored and verified.', flush=True)
