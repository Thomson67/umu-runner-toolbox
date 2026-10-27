"""Real shell + journal recovery across SIGKILL, without privileged mounts.

The compressed case models the writable merged bottle with a directory and a
mocked findmnt; the same shell copy/sync/EXIT paths run for both formats.
"""
import os
from pathlib import Path
import signal
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = (ROOT / 'toolbox/overlay/bin/wine').read_text()


class DirectRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / 'umu'
        self.prefix = self.root / 'Forza.wine'
        self.game = self.prefix / 'drive_c/game'
        (self.game / 'data').mkdir(parents=True)
        self.saves = self.root / 'saves/Forza'
        self.saves.mkdir(parents=True)
        (self.saves / 'progress').write_text('external previous progress')
        (self.game / 'data/saves').symlink_to(self.saves)
        (self.game / 'azimuth.exe').write_bytes(b'game unchanged')
        for name in ('user.reg', 'system.reg'):
            (self.prefix / name).write_text('original registry')
        (self.prefix / 'autorun.cmd').write_text('SAVEDIR=drive_c/game/data/saves\nENV=UMU_DIRECT_GAME=1\n')
        self.materialized = self.base / 'materialized-prefixes/Forza-123'
        self.helper = self.root / 'runtime-prefix.py'
        helper = (ROOT / 'toolbox/overlay/umu-batocera/runtime-prefix.py').read_text()
        helper = helper.replace("Path('/userdata/system/umu')", f'Path({str(self.base)!r})')
        # The execution service virtualizes /proc. Use deterministic shell owner
        # identities here, while production /proc parsing has separate tests.
        helper = helper.replace("if __name__ == '__main__':", '''
def process_token(pid):
    return 'owner:' + str(pid) if pid == os.getppid() else ''
def mounted(path):
    return False
if __name__ == '__main__':
''')
        self.helper.write_text(helper)
        block = WRAPPER[WRAPPER.index('DIRECT_SAVE_PATH=""'):WRAPPER.index('trap cleanup_runtime_mounts EXIT')]
        prepare = WRAPPER[WRAPPER.index('prepare_materialized_prefix() {'):WRAPPER.index('check_materialized_space() {')]
        persist = WRAPPER[WRAPPER.index('persist_split_wine_prefix() {'):WRAPPER.index('# v3.9.2: every materialized-prefix session')]
        block = block.replace('/userdata/saves/windows/*', str(self.root / 'saves') + '/*')
        prepare = prepare.replace('/userdata/system/umu/.materialized-prefix.lock', str(self.base / '.materialized-prefix.lock'))
        persist = persist.replace('/userdata/system/umu/materialized-prefixes/', str(self.materialized.parent) + '/')
        persist = persist.replace('/run/wine/*.wsquashfs', str(self.prefix))
        self.functions = block + prepare + persist

    def script(self, body, compressed=0, resume=False):
        self.base.mkdir(exist_ok=True)
        script = '''set -eu
LOG="$TEST_ROOT/launch.log"
log() { printf '%s\\n' "$*" >>"$LOG"; }
unprotect_umu_runners() { :; }
notify_runtime_recovery() { echo notified >>"$LOG"; }
mountpoint() { return 1; }
findmnt() { printf 'overlay\\n'; }
is_prefix_root() { [ -f "$1/system.reg" ] && [ -f "$1/user.reg" ]; }
RUNTIME_TRACKED=0
RUNTIME_SAFE_TO_REMOVE=1
RUNTIME_REUSED=0
RUNTIME_RECOVERY_REASON=interrupted-or-unsynchronized
RUNNER_DIR="$TEST_ROOT"
GAME_DIR=game
GAME_SOURCE="$TEST_ROOT/Forza.wine/drive_c/game"
ORIGINAL_PREFIX_CANON="$TEST_ROOT/Forza.wine"
ALIAS_MOUNT="$ORIGINAL_PREFIX_CANON"
WINE_SPLIT_PREFIX=1
UMU_DIRECT_GAME_ENABLED=1
''' + f'COMPRESSED_OVERLAY={compressed}\n' + self.functions + '''
trap cleanup_runtime_mounts EXIT
prepare_materialized_prefix || exit $?
if [ "$RUNTIME_REUSED" = 0 ]; then
    cp "$ORIGINAL_PREFIX_CANON/"*.reg "$MATERIALIZED_PREFIX/"
fi
''' + body
        return ['bash', '-c', script]

    def environment(self):
        return dict(os.environ, TEST_ROOT=str(self.root), RUNTIME_HELPER=str(self.helper),
                    MATERIALIZED_PREFIX=str(self.materialized))

    def run_shell(self, body, compressed=0):
        result = subprocess.run(self.script(body, compressed), env=self.environment(),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + (self.root / 'launch.log').read_text())

    def interrupt(self, compressed=0, after_prefix_sync=False):
        body = '''prepare_direct_save_copy
printf 'newest local progress' > "$DIRECT_SAVE_PATH/progress"
printf 'new registry' > "$MATERIALIZED_PREFIX/user.reg"
'''
        if after_prefix_sync:
            body += 'persist_split_wine_prefix\n'
        body += '''
sleep 60 &
touch "$TEST_ROOT/ready"
wait
'''
        process = subprocess.Popen(self.script(body, compressed), env=self.environment(), start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 5
            while not (self.root / 'ready').exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue((self.root / 'ready').exists(), (self.root / 'launch.log').read_text())
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
        self.assertEqual(process.returncode, -signal.SIGKILL)
        self.assertTrue(self.materialized.exists())
        self.assertFalse((self.game / 'data/saves').is_symlink())
        self.assertEqual((self.saves / 'progress').read_text(), 'external previous progress')

    def test_hotkey_kills_entire_group_then_resumes_and_syncs_direct_saves(self):
        # Both modes use the same save compatibility implementation. Test the
        # compressed path separately below with a new fixture.
        self.check_interrupted_recovery(compressed=0)

    def test_compressed_bottle_direct_recovery_after_entire_group_is_killed(self):
        self.check_interrupted_recovery(compressed=1)

    def check_interrupted_recovery(self, compressed, after_prefix_sync=False):
        self.interrupt(compressed, after_prefix_sync)
        self.run_shell('''test "$RUNTIME_REUSED" = 1
prepare_direct_save_copy
test "$(cat "$DIRECT_SAVE_PATH/progress")" = 'newest local progress'
persist_split_wine_prefix
RUNTIME_SAFE_TO_REMOVE=1
''', compressed)
        self.assertFalse(self.materialized.exists())
        self.assertEqual((self.prefix / 'user.reg').read_text(), 'new registry')
        self.assertTrue((self.game / 'data/saves').is_symlink())
        self.assertEqual((self.saves / 'progress').read_text(), 'newest local progress')
        self.assertFalse((self.game / 'data/saves.umu-direct-link').exists())
        self.assertEqual((self.game / 'azimuth.exe').read_bytes(), b'game unchanged')

    def test_hotkey_between_prefix_sync_and_direct_save_sync_can_still_resume(self):
        self.check_interrupted_recovery(compressed=1, after_prefix_sync=True)

    def test_normal_direct_exit_syncs_before_deleting_working_copy(self):
        self.run_shell('''prepare_direct_save_copy
printf 'newest local progress' > "$DIRECT_SAVE_PATH/progress"
persist_split_wine_prefix
RUNTIME_SAFE_TO_REMOVE=1
''', compressed=1)
        self.assertFalse(self.materialized.exists())
        self.assertEqual((self.saves / 'progress').read_text(), 'newest local progress')
        self.assertTrue((self.game / 'data/saves').is_symlink())

    def test_changed_source_after_hotkey_never_overwrites_local_direct_saves(self):
        self.interrupt(compressed=1)
        (self.prefix / 'autorun.cmd').write_text('SAVEDIR=drive_c/game/data/saves\nENV=UMU_DIRECT_GAME=0\n')
        self.run_shell('''test "$RUNTIME_REUSED" = 0
if prepare_direct_save_copy; then exit 99; fi
''', compressed=1)
        self.assertEqual((self.game / 'data/saves/progress').read_text(), 'newest local progress')
        self.assertEqual((self.saves / 'progress').read_text(), 'external previous progress')
        old, = self.materialized.parent.glob('.retained-*')
        self.assertEqual((old / 'user.reg').read_text(), 'new registry')

    def test_direct_sync_failure_retains_runtime_and_both_save_copies(self):
        self.run_shell('''prepare_direct_save_copy
printf 'newest local progress' > "$DIRECT_SAVE_PATH/progress"
persist_split_wine_prefix
RUNTIME_SAFE_TO_REMOVE=1
DIRECT_SAVE_SOURCE=/nonexistent/invalid-save-target
''', compressed=1)
        self.assertTrue(self.materialized.exists())
        self.assertEqual((self.game / 'data/saves/progress').read_text(), 'newest local progress')
        self.assertEqual((self.saves / 'progress').read_text(), 'external previous progress')
        self.assertIn('notified', (self.root / 'launch.log').read_text())

    def test_native_prelaunch_save_copy_and_link_restore_after_kill_are_recognized(self):
        self.interrupt(compressed=1)
        # Native saveFilesToUserdata runs before the UMU wrapper. Model its
        # cp -r into external saves, removal of local saves, and ln -s.
        local = self.game / 'data/saves'
        shutil.copytree(local, self.saves, dirs_exist_ok=True, symlinks=True)
        shutil.rmtree(local)
        local.symlink_to(self.saves)
        self.run_shell('''test "$RUNTIME_REUSED" = 1
prepare_direct_save_copy
test "$(cat "$DIRECT_SAVE_PATH/progress")" = 'newest local progress'
persist_split_wine_prefix
RUNTIME_SAFE_TO_REMOVE=1
''', compressed=1)
        self.assertEqual((self.saves / 'progress').read_text(), 'newest local progress')
        self.assertTrue(local.is_symlink())
        self.assertFalse((local.parent / 'saves.umu-direct-link').exists())
        self.assertFalse(self.materialized.exists())
        self.assertIn('direct_save_native_link_already_restored=', (self.root / 'launch.log').read_text())


if __name__ == '__main__':
    unittest.main()
