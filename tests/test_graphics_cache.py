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
    def mounts(self, settings, previous='/existing', saved=None):
        wrapper = (ROOT / 'toolbox/overlay/bin/wine').read_text()
        block = wrapper[wrapper.index('append_pv_rw() {'):
                        wrapper.index('if [ -n "${UMU_BATOCERA_EXTRA_RW-}" ]; then')]
        env = dict(os.environ)
        for key in KEYS:
            env.pop(key, None)
        env.pop('UMU_GRAPHICS_CACHE_SHARING', None)
        env.update(settings, PV_RW=previous)
        script = 'set -eu\nlog() { :; }\n' + block + '\nprintf "%s" "$PV_RW"'
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'graphics-cache-sharing'
            if saved is not None:
                config.write_text(saved)
            script = script.replace('/userdata/system/umu/toolbox/config/graphics-cache-sharing', str(config))
            return subprocess.check_output(['bash', '-c', script], env=env, text=True).split(':')

    def test_disable_restores_previous_mounts_without_deleting_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / 'pipelines.bin'
            cache.write_bytes(b'cached pipelines')
            for settings, saved in (({'UMU_GRAPHICS_CACHE_SHARING': '0'}, None), ({}, '0\n')):
                mounts = self.mounts(dict(settings, VKD3D_SHADER_CACHE_PATH=folder), saved=saved)
                self.assertNotIn(folder, mounts)
                self.assertIn('/existing', mounts)
                self.assertEqual(cache.read_bytes(), b'cached pipelines')
            # Explicit shares from the caller remain authoritative, even off.
            self.assertIn(folder, self.mounts({'UMU_GRAPHICS_CACHE_SHARING': '0'}, previous=folder))

    def test_per_game_setting_overrides_global_setting_and_invalid_defaults_on(self):
        with tempfile.TemporaryDirectory() as folder:
            for local, saved, enabled in (('1', '0', True), ('0', '1', False),
                                          (None, '1', True), (None, 'invalid', True),
                                          ('invalid', '0', True)):
                settings = {'VKD3D_SHADER_CACHE_PATH': folder}
                if local is not None:
                    settings['UMU_GRAPHICS_CACHE_SHARING'] = local
                self.assertEqual(folder in self.mounts(settings, saved=saved), enabled)

    def test_settings_menu_saves_both_choices_and_back_preserves_setting(self):
        source = (ROOT / 'toolbox/umu-toolbox.sh').read_text()
        block = source[source.index('graphics_cache_menu() {'):source.index('settings_menu() {')]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for language in ('fr', 'en'):
                for choice, expected in (('0', '0'), ('1', '1'), ('back', '1')):
                    script = 'log() { :; }\nmenu_choice() { printf "%s" "$TEST_CHOICE"; }\n' + block + '\ngraphics_cache_menu\n'
                    subprocess.run(['bash', '-eu', '-c', script], check=True,
                        env=dict(os.environ, ROOT=folder, TOOLBOX_LANGUAGE=language, TEST_CHOICE=choice))
                    self.assertEqual((root / 'config/graphics-cache-sharing').read_text().strip(), expected)

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
