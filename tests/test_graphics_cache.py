"""Exercise cache mount policy using the real wrapper shell block."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
KEYS = ('VKD3D_SHADER_CACHE_PATH', 'DXVK_STATE_CACHE_PATH',
        'DXVK_SHADER_CACHE_PATH', 'MESA_SHADER_CACHE_DIR',
        'MESA_GLSL_CACHE_DIR', '__GL_SHADER_DISK_CACHE_PATH')


class GraphicsCacheTests(unittest.TestCase):
    def mounts(self, settings, previous='/existing'):
        wrapper = (ROOT / 'toolbox/overlay/bin/wine').read_text()
        block = wrapper[wrapper.index('append_pv_rw() {'):
                        wrapper.index('if [ -n "${UMU_BATOCERA_EXTRA_RW-}" ]; then')]
        env = dict(os.environ)
        for key in KEYS:
            env.pop(key, None)
        env.update(settings, PV_RW=previous)
        script = 'set -eu\nlog() { :; }\n' + block + '\nprintf "%s" "$PV_RW"'
        return subprocess.check_output(['bash', '-c', script], env=env, text=True).split(':')

    def test_all_cache_types_preserve_paths_and_existing_mounts(self):
        with tempfile.TemporaryDirectory() as folder:
            dirs = [Path(folder) / f'cache {index}' for index in range(len(KEYS))]
            for path in dirs:
                path.mkdir()
            mounts = self.mounts(dict(zip(KEYS, map(str, dirs))))
            self.assertEqual(mounts[0], '/existing')
            for path in dirs:
                self.assertEqual(mounts.count(str(path)), 1)

    def test_shared_cache_is_not_mounted_multiple_times(self):
        with tempfile.TemporaryDirectory() as folder:
            mounts = self.mounts(dict.fromkeys(KEYS, folder), previous=folder)
            self.assertEqual(mounts.count(folder), 1)

    def test_symlink_shares_both_logical_path_and_target(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'real'
            target.mkdir()
            link = Path(folder) / 'link'
            link.symlink_to(target, target_is_directory=True)
            mounts = self.mounts({'VKD3D_SHADER_CACHE_PATH': str(link)})
            self.assertIn(str(link), mounts)
            self.assertIn(str(target), mounts)

    def test_disabled_missing_relative_and_broad_paths_are_skipped(self):
        with tempfile.TemporaryDirectory() as folder:
            for path in ('', '0', 'relative', str(Path(folder) / 'missing'), '/', '/tmp/..'):
                with self.subTest(path=path):
                    mounts = self.mounts({'VKD3D_SHADER_CACHE_PATH': path})
                    self.assertEqual([p for p in mounts if p != '/userdata/saves'], ['/existing'])

    def test_mount_delimiters_in_directory_names_are_skipped(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('cache:bad', 'cache\nbad'):
                path = Path(folder) / name
                path.mkdir()
                self.assertNotIn(str(path), self.mounts({'VKD3D_SHADER_CACHE_PATH': str(path)}))
