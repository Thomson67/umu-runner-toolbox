"""Exercise the real shell mount policy with isolated paths and mocked mounts."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = (ROOT / 'toolbox/overlay/bin/wine').read_text()
FUNCTIONS = WRAPPER[WRAPPER.index('expose_c_game_path() {'):WRAPPER.index('cleanup_runtime_mounts() {')]


class CGamePathTests(unittest.TestCase):
    def run_case(self, action, name='game', direct=0, enabled='1', existing=False, failed_mount=False, failed_unmount=False, split=True):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'original' / name
            source.mkdir(parents=True)
            (source / 'game.exe').write_text('game')
            (source / 'saves').symlink_to('/userdata/saves/windows/Game')
            pfx = root / 'compatdata/pfx'
            (pfx / 'drive_c').mkdir(parents=True)
            target = pfx / 'drive_c' / name
            if existing:
                target.mkdir()
                (target / 'preserve').write_text('existing data')
            script = '''set -u
log() { printf '%s\\n' "$*" >> "$TRACE"; }
mount() { printf 'mount:%s\\n' "$*" >> "$TRACE"; [ "$FAIL_MOUNT" = 0 ]; }
umount() { printf 'umount:%s\\n' "$*" >> "$TRACE"; [ "$FAIL_UNMOUNT" = 0 ]; }
mountpoint() { return 1; }
C_GAME_PATH_BOUND=0
C_GAME_PATH_CREATED=0
C_GAME_PATH_TARGET=''
''' + FUNCTIONS + '\n' + action
            env = dict(os.environ, TRACE=str(root / 'trace'), LOG='/dev/null',
                MATERIALIZED_PREFIX=str(root / 'materialized') if split else '',
                PFX_BOUND='1', PFX_MOUNT=str(pfx), GAMEVIEW=str(source),
                GAME_DIR=name, GAME_REL='drive_c/' + name,
                EXE_ABS=str(source / 'bin/game.exe'), UMU_CWD=str(source / 'bin'),
                UMU_DIRECT_GAME_ENABLED=str(direct), UMU_C_GAME_PATH=enabled,
                FAIL_MOUNT=str(int(failed_mount)), FAIL_UNMOUNT=str(int(failed_unmount)))
            result = subprocess.run(['bash', '-c', script], env=env, capture_output=True, text=True)
            trace = (root / 'trace').read_text() if (root / 'trace').exists() else ''
            self.assertEqual((source / 'game.exe').read_text(), 'game')
            self.assertEqual(os.readlink(source / 'saves'), '/userdata/saves/windows/Game')
            if existing:
                self.assertEqual((target / 'preserve').read_text(), 'existing data')
            return result, trace, str(source), str(target), target.exists()

    def test_normal_launch_uses_original_c_drive_directory_and_relative_cwd(self):
        for name in ('game', 'Game', 'Castle Storm'):
            result, trace, source, target, exists = self.run_case(
                'expose_c_game_path || exit 9; printf "%s|%s|%s" "$EXE_ABS" "$UMU_CWD" "$C_GAME_PATH_BOUND"', name=name)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, target + '/bin/game.exe|' + target + '/bin|1')
            self.assertIn('mount:--bind ' + source + ' ' + target, trace)
            self.assertIn('runtime_c_game_windows=C:\\' + name, trace)
            self.assertTrue(exists)

    def test_direct_mode_adds_c_view_without_rewriting_launch_paths(self):
        result, trace, source, target, _ = self.run_case(
            'expose_c_game_path || exit 9; printf "%s|%s" "$EXE_ABS" "$UMU_CWD"', direct=1)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, source + '/bin/game.exe|' + source + '/bin')
        self.assertIn('mount:--bind', trace)

    def test_opt_out_and_non_split_prefix_do_not_mount(self):
        for settings in ({'enabled': '0'}, {'split': False}):
            result, trace, _, _, exists = self.run_case('expose_c_game_path', **settings)
            self.assertEqual(result.returncode, 0)
            self.assertNotIn('mount:--bind', trace)
            self.assertFalse(exists)

    def test_existing_target_is_never_hidden_or_removed(self):
        result, trace, _, _, exists = self.run_case('expose_c_game_path; rc=$?; cleanup_c_game_path; exit "$rc"', existing=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('mount:--bind', trace)
        self.assertTrue(exists)

    def test_failed_bind_removes_only_new_empty_placeholder(self):
        result, trace, _, _, exists = self.run_case(
            'expose_c_game_path; rc=$?; cleanup_c_game_path; exit "$rc"', failed_mount=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(exists)
        self.assertNotIn('umount:', trace)

    def test_cleanup_unmounts_before_removing_placeholder(self):
        result, trace, _, target, exists = self.run_case(
            'expose_c_game_path || exit 9; cleanup_c_game_path; printf "%s" "$C_GAME_PATH_BOUND"')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '0')
        self.assertIn('umount:' + target, trace)
        self.assertFalse(exists)

    def test_failed_unmount_retains_mount_state_and_target(self):
        result, trace, _, _, exists = self.run_case(
            'expose_c_game_path || exit 9; cleanup_c_game_path; rc=$?; printf "%s" "$C_GAME_PATH_BOUND"; exit "$rc"', failed_unmount=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '1')
        self.assertTrue(exists)

    def test_mount_and_cleanup_order_around_launch_and_persistence(self):
        launch = WRAPPER.index('python3 "$ROOT_BRIDGE" "$UMU_RUN" "$UMU_EXE"')
        self.assertLess(WRAPPER.index('PFX_BOUND=1'), WRAPPER.index('if ! expose_c_game_path; then'))
        self.assertLess(WRAPPER.index('if ! expose_c_game_path; then'), launch)
        cleanup = WRAPPER.index('cleanup_c_game_path || log', launch)
        self.assertLess(cleanup, WRAPPER.index('        persist_split_wine_prefix', launch))
        cleanup_fn = WRAPPER[WRAPPER.index('cleanup_runtime_mounts() {'):WRAPPER.index('trap cleanup_runtime_mounts')]
        self.assertLess(cleanup_fn.index('cleanup_c_game_path'), cleanup_fn.index('umount "$PFX_MOUNT"'))

    def test_persistence_keeps_original_game_and_returns_configuration(self):
        block = WRAPPER[WRAPPER.index('persist_split_wine_prefix() {'):WRAPPER.index('# v3.9.2: every materialized-prefix session')]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            materialized_root = root / 'materialized-prefixes'
            source = materialized_root / 'Game'; target = root / 'Game.wine'
            for path in (source, target):
                (path / 'drive_c/game').mkdir(parents=True)
                (path / 'drive_c/windows').mkdir()
                (path / 'system.reg').write_text('registry')
            game = target / 'drive_c/game/rom.bin'; game.write_bytes(b'original ROM')
            inode = game.stat().st_ino
            (source / 'drive_c/game/should-not-copy').write_bytes(b'not prefix data')
            (source / 'user.reg').write_text('saved setting C:\\game\\rom.bin')
            block = block.replace('/userdata/system/umu/materialized-prefixes/', str(materialized_root) + '/')
            script = 'log() { :; }\nis_prefix_root() { [ -f "$1/system.reg" ]; }\n' + block + '\npersist_split_wine_prefix\n'
            subprocess.run(['bash', '-u', '-c', script], check=True, env=dict(os.environ,
                MATERIALIZED_PREFIX=str(source), ORIGINAL_PREFIX_CANON=str(target), WINE_SPLIT_PREFIX='1', GAME_DIR='game', LOG='/dev/null'))
            self.assertEqual(game.read_bytes(), b'original ROM')
            self.assertEqual(game.stat().st_ino, inode)
            self.assertFalse((target / 'drive_c/game/should-not-copy').exists())
            self.assertEqual((target / 'user.reg').read_text(), 'saved setting C:\\game\\rom.bin')


if __name__ == '__main__':
    unittest.main()
