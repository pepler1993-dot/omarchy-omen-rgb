#!/usr/bin/env python3
"""Install only the unprivileged Omarchy panel. Does not load/install drivers."""
from datetime import datetime
import json
from pathlib import Path
import shutil

source = Path(__file__).resolve().parent
config = Path.home() / '.config/omarchy'
destination = config / 'plugins/kevin.omen-rgb'
destination.mkdir(parents=True, exist_ok=True)
for name in ['manifest.json', 'BarWidget.qml', 'RgbPanel.qml', 'rgb.py']:
    shutil.copy2(source / name, destination / name)
shell = config / 'shell.json'
data = json.loads(shell.read_text())
layout = data.setdefault('bar', {}).setdefault('layout', {})
if not any(entry.get('id') == 'kevin.omen-rgb' for section in layout.values() for entry in section):
    backup = shell.with_name('shell.json.bak.omen-rgb.' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    shutil.copy2(shell, backup)
    right = layout.setdefault('right', [])
    index = next((i for i, entry in enumerate(right) if entry.get('id') == 'omarchy.monitor'), len(right))
    right.insert(index, {'id': 'kevin.omen-rgb'})
    temporary = shell.with_suffix('.omen-rgb.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(shell)
    print('Backup:', backup)
print('Panel installiert:', destination)
