import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import rgb


class RgbTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.device = Path(self.temp.name) / 'colors'
        self.state = Path(self.temp.name) / 'state/colors.json'
        self.device.write_text('FF0000 00FF00 0000FF FFFFFF\n')

    def test_missing_driver_is_read_only(self):
        self.device.unlink()
        self.assertFalse(rgb.status(self.device, self.state)['available'])
        self.assertFalse(self.state.exists())
        with self.assertRaises(ValueError):
            rgb.apply(['FFFFFF'] * 4, 100, self.device, self.state)

    def test_apply_scales_and_preserves_base_color_across_restart(self):
        result = rgb.apply(['#ff0000', '00FF00', '0000FF', 'FFFFFF'], 50, self.device, self.state)
        self.assertTrue(result['ok'])
        self.assertEqual(self.device.read_text(), '800000 008000 000080 808080\n')
        self.assertEqual(rgb.status(self.device, self.state)['brightness'], 50)
        self.assertEqual(result['colors'][0], 'FF0000')

    def test_zero_brightness_preserves_colors(self):
        rgb.apply(['AB12CD'] * 4, 0, self.device, self.state)
        self.assertEqual(self.device.read_text().split(), ['000000'] * 4)
        self.assertEqual(rgb.status(self.device, self.state)['colors'], ['AB12CD'] * 4)

    def test_invalid_values_never_write(self):
        original = self.device.read_text()
        for colors, brightness in [(['FFFFFF'] * 3, 50), (['$(id)'] * 4, 50), (['FFFFFF'] * 4, -1), (['FFFFFF'] * 4, 101), (['FFFFFF'] * 4, True), (None, 50)]:
            with self.assertRaises(ValueError):
                rgb.apply(colors, brightness, self.device, self.state)
            self.assertEqual(self.device.read_text(), original)

    def test_firmware_mismatch_never_saves_profile(self):
        with patch('rgb.read_colors', return_value=['111111'] * 4):
            with self.assertRaises(ValueError):
                rgb.apply(['FFFFFF'] * 4, 100, self.device, self.state)
        self.assertFalse(self.state.exists())

    def test_permission_failure_never_saves_profile(self):
        with patch.object(Path, 'write_text', side_effect=PermissionError('Denied')):
            with self.assertRaises(PermissionError):
                rgb.apply(['FFFFFF'] * 4, 100, self.device, self.state)
        self.assertFalse(self.state.exists())

    def test_external_changes_override_saved_state(self):
        rgb.apply(['FFFFFF'] * 4, 50, self.device, self.state)
        self.device.write_text('AB12CD AB12CD AB12CD AB12CD\n')
        result = rgb.status(self.device, self.state)
        self.assertEqual(result['colors'], ['AB12CD'] * 4)
        self.assertEqual(result['brightness'], 100)

    def test_malformed_firmware_data_rejected(self):
        self.device.write_text('000000\n')
        with self.assertRaises(ValueError):
            rgb.status(self.device, self.state)

    def test_corrupt_profile_does_not_block_hardware_read(self):
        self.state.parent.mkdir()
        self.state.write_text('{broken')
        self.assertEqual(rgb.status(self.device, self.state)['colors'][0], 'FF0000')


if __name__ == '__main__':
    unittest.main()
