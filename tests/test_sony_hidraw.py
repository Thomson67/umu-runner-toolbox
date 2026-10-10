"""Verify controller policy using the actual wrapper initialization block."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SonyHidrawTests(unittest.TestCase):
    def test_native_default_and_explicit_settings_with_recent_winebus(self):
        wrapper = (ROOT / 'toolbox/overlay/bin/wine').read_text()
        block = wrapper[wrapper.index('# Batocera builds may omit'):wrapper.index('# v3.7.1: runner isolation.')]
        with tempfile.TemporaryDirectory() as folder:
            runner = Path(folder)
            bus = runner / 'files/lib/wine/x86_64-unix/winebus.so'
            bus.parent.mkdir(parents=True)
            bus.write_bytes(b'hidraw handles native reports')
            for hidraw, explicit in [('1', None), ('1', '0'), ('1', '1'), ('0', None), ('0', '1')]:
                with self.subTest(hidraw=hidraw, explicit=explicit):
                    env = dict(os.environ, WINE_ENABLE_HIDRAW=hidraw, RUNNER_DIR=str(runner))
                    env.pop('PROTON_SONY_HIDRAW_XINPUT', None)
                    if explicit is not None:
                        env['PROTON_SONY_HIDRAW_XINPUT'] = explicit
                    cmd = 'set -u\n' + block + '\nprintf "%s" "${PROTON_SONY_HIDRAW_XINPUT-ABSENT}"'
                    actual = subprocess.check_output(['bash', '-c', cmd], env=env, text=True)
                    self.assertEqual(actual, explicit if explicit is not None else 'ABSENT')


if __name__ == '__main__':
    unittest.main()
