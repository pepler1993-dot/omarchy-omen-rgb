#!/usr/bin/env python3
"""Explicit, board-limited DKMS setup for one selected desktop user."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess

SOURCE = Path(__file__).resolve().parent
DEVICE = Path('/sys/devices/platform/omen_rgb/rgb_zones/colors')


def desktop_user(name):
    if not re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}', name):
        raise ValueError('Use a regular local Linux login name.')
    user = pwd.getpwnam(name)
    if user.pw_uid < 1000:
        raise ValueError('Select a desktop user, not root or a system account.')
    home = Path(user.pw_dir)
    if not home.is_absolute() or any(ord(c) < 32 for c in user.pw_dir):
        raise ValueError('The account needs an absolute home path without control characters.')
    return user


def render_service(user):
    # Escape systemd quotes, backslashes and percent specifiers, not shell text.
    home = user.pw_dir.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
    return (SOURCE / 'omen-rgb-restore.service').read_text().replace(
        '@USER@', user.pw_name).replace('@HOME@', home)


def write_owned(path, data):
    if path.is_symlink():
        raise ValueError(f'Refusing symlink: {path}')
    if path.exists():
        backup = path.with_name(path.name + '.bak.' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        shutil.copy2(path, backup)
    path.write_bytes(data)
    path.chmod(0o644)
    os.chown(path, 0, 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user', required=True, help='Local desktop account receiving RGB access')
    parser.add_argument('--dry-run', action='store_true', help='Show the service without changing the system')
    args = parser.parse_args()
    user = desktop_user(args.user)
    unit = render_service(user)
    if args.dry_run:
        print(unit, end='')
        return
    if os.geteuid() != 0:
        raise ValueError('Run this installer explicitly with root privileges after the hardware test.')
    if Path('/sys/class/dmi/id/board_name').read_text().strip() != '8C77':
        raise ValueError('This driver is restricted to the tested board 8C77.')
    if not DEVICE.exists():
        raise ValueError('Load and test the module before installing it permanently; see README.')
    for program in ('dkms', 'systemctl', 'python3'):
        if not Path('/usr/bin', program).is_file():
            raise ValueError(f'Missing dependency: {program}')

    destination = Path('/usr/src/kevin-omen-rgb-0.4')
    adapter = Path('/usr/lib/kevin-omen-rgb')
    for directory in (destination, adapter):
        if directory.is_symlink():
            raise ValueError(f'Refusing symlink: {directory}')
        directory.mkdir(mode=0o755, exist_ok=True)
        os.chown(directory, 0, 0)
        directory.chmod(0o755)
    for name in ('omen_rgb.c', 'Makefile', 'dkms.conf'):
        write_owned(destination / name, (SOURCE / 'driver' / name).read_bytes())
    write_owned(destination / 'LICENSE', (SOURCE / 'LICENSE').read_bytes())
    write_owned(adapter / 'rgb.py', (SOURCE / 'rgb.py').read_bytes())
    subprocess.run(['/usr/bin/dkms', 'install', '--force', '-m', 'kevin-omen-rgb',
                    '-v', '0.4', '-k', os.uname().release], check=True)
    write_owned(Path('/etc/modules-load.d/kevin-omen-rgb.conf'), b'omen_rgb\n')
    write_owned(Path('/etc/systemd/system/omen-rgb-restore.service'), unit.encode())
    subprocess.run(['/usr/bin/systemctl', 'daemon-reload'], check=True)
    subprocess.run(['/usr/bin/systemctl', 'enable', '--now', 'omen-rgb-restore.service'], check=True)
    subprocess.run(['/usr/bin/systemctl', 'restart', 'omen-rgb-restore.service'], check=True)
    print(f'Driver and color restoration installed for {user.pw_name}.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
