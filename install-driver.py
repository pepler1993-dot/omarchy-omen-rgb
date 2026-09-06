#!/usr/bin/env python3
"""Install the reviewed, hardware-tested RGB module and its boot service."""
import os
from pathlib import Path
import shutil
import subprocess

if os.geteuid() != 0:
    raise SystemExit('This installer needs root privileges.')
source = Path(__file__).resolve().parent
if Path('/sys/class/dmi/id/board_name').read_text().strip() != '8C77':
    raise SystemExit('This driver is restricted to the tested board 8C77.')
if not Path('/sys/devices/platform/omen_rgb/rgb_zones/colors').exists():
    raise SystemExit('Load and test the module before installing it permanently.')

destination = Path('/usr/src/kevin-omen-rgb-0.4')
destination.mkdir(exist_ok=True)
for name in ['omen_rgb.c', 'Makefile', 'dkms.conf']:
    shutil.copyfile(source / 'driver' / name, destination / name)
    (destination / name).chmod(0o644)
shutil.copyfile(source / 'LICENSE', destination / 'LICENSE')

def run(*args):
    subprocess.run(args, check=True)

run('/usr/bin/dkms', 'install', '-m', 'kevin-omen-rgb', '-v', '0.4', '-k', os.uname().release)
Path('/etc/modules-load.d/kevin-omen-rgb.conf').write_text('omen_rgb\n')
service = Path('/etc/systemd/system/omen-rgb-restore.service')
shutil.copyfile(source / 'omen-rgb-restore.service', service)
service.chmod(0o644)
run('/usr/bin/systemctl', 'daemon-reload')
run('/usr/bin/systemctl', 'enable', '--now', 'omen-rgb-restore.service')
print('DKMS, module autoload and per-user color restore are installed.')
