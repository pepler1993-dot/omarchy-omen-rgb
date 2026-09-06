import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('install_driver', Path(__file__).with_name('install-driver.py'))
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def test_non_root_account_and_custom_home(self):
        user = SimpleNamespace(pw_name='alice', pw_uid=1001, pw_dir='/srv/users/alice')
        with patch.object(installer.pwd, 'getpwnam', return_value=user):
            service = installer.render_service(installer.desktop_user('alice'))
        self.assertIn('User=alice\n', service)
        self.assertIn('XDG_STATE_HOME=/srv/users/alice/.local/state', service)
        self.assertIn('chown alice /sys/devices/platform/omen_rgb/rgb_zones/colors', service)
        self.assertNotIn('/home/kevin', service)
        self.assertNotIn('@USER@', service)
        self.assertNotIn('@HOME@', service)

    def test_system_accounts_and_invalid_names_rejected(self):
        with patch.object(installer.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=0)):
            with self.assertRaises(ValueError):
                installer.desktop_user('root')
        for name in ['alice\nExecStart=/bin/false', '-root', 'alice;id', 'alice%u']:
            with self.assertRaises(ValueError):
                installer.desktop_user(name)

    def test_unit_value_escaping(self):
        user = SimpleNamespace(pw_name='alice', pw_dir='/srv/percent%/a"b\\c')
        service = installer.render_service(user)
        self.assertIn('XDG_STATE_HOME=/srv/percent%%/a\\"b\\\\c/.local/state', service)

    def test_bad_home_rejected(self):
        for home in ['relative/path', '/srv/alice\nUser=root']:
            user = SimpleNamespace(pw_name='alice', pw_uid=1001, pw_dir=home)
            with patch.object(installer.pwd, 'getpwnam', return_value=user):
                with self.assertRaises(ValueError):
                    installer.desktop_user('alice')

    def test_dry_run_does_not_write_or_start_processes(self):
        user = SimpleNamespace(pw_name='alice', pw_uid=1001, pw_dir='/srv/alice')
        with patch.object(installer, 'desktop_user', return_value=user), \
                patch('sys.argv', ['install-driver.py', '--user', 'alice', '--dry-run']), \
                patch.object(installer, 'write_owned') as write, \
                patch.object(installer.subprocess, 'run') as run, patch('builtins.print'):
            installer.main()
        write.assert_not_called()
        run.assert_not_called()

    def test_existing_file_is_backed_up(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(installer.os, 'chown'):
            path = Path(directory) / 'service'
            path.write_bytes(b'old configuration')
            installer.write_owned(path, b'new configuration')
            self.assertEqual(path.read_bytes(), b'new configuration')
            backups = list(Path(directory).glob('service.bak.*'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), b'old configuration')

    def test_symlink_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'target'
            target.write_bytes(b'preserve')
            link = Path(directory) / 'link'
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                installer.write_owned(link, b'new')
            self.assertEqual(target.read_bytes(), b'preserve')


if __name__ == '__main__':
    unittest.main()
