"""Exercise real save copying, persistence and failure recovery."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DirectSaveTests(unittest.TestCase):
    def run_case(self, body, enabled=1, copy_failure=0, busy=0, savedir='drive_c/game/data/saves/', compressed=0):
        source = (ROOT / 'toolbox/overlay/bin/wine').read_text()
        functions = source[source.index('DIRECT_SAVE_PATH=""'):source.index('cleanup_runtime_mounts() {')]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            prefix = root / 'game.wine'
            game = prefix / 'drive_c/game'
            (game / 'data').mkdir(parents=True)
            target = root / 'persistent/test'
            target.mkdir(parents=True)
            (target / 'keep.sav').write_text('original save')
            path = game / 'data/saves'
            path.symlink_to(target)
            (prefix / 'autorun.cmd').write_text('SAVEDIR=' + savedir + '\r\n')
            functions = functions.replace('/userdata/saves/windows/*', str(root / 'persistent') + '/*')
            script = '''set -eu
LOG=/dev/null
log() { :; }
FAKE_BOUND=0
mountpoint() { [ "$BUSY" -eq 1 ]; }
mount() { echo "unexpected mount" >&2; exit 99; }
cp() { [ "$COPY_FAILURE" -eq 0 ] || return 1; command cp "$@"; }
umount() { [ "$BUSY" -eq 0 ] || return 1; FAKE_BOUND=0; }
sleep() { :; }
ORIGINAL_PREFIX_CANON="$1"
GAME_SOURCE="$1/drive_c/game"
COMPRESSED_OVERLAY="$5"
ALIAS_MOUNT="$1"
[ "$COMPRESSED_OVERLAY" -eq 0 ] || ORIGINAL_PREFIX_CANON=/unavailable/original
UMU_DIRECT_GAME_ENABLED="$2"
COPY_FAILURE="$3"
BUSY="$4"
''' + functions + '\n' + body
            subprocess.run(['bash', '-c', script, '_', str(prefix), str(enabled), str(copy_failure), str(busy), str(compressed)], check=True)
            self.assertEqual((target / 'keep.sav').read_text(), 'original save')

    def test_enabled_copy_and_restore_original_link(self):
        self.run_case('''original="$(readlink "$GAME_SOURCE/data/saves")"
prepare_direct_save_copy
test "$DIRECT_SAVE_MOVED" = 1
test ! -L "$DIRECT_SAVE_PATH"
test -L "$DIRECT_SAVE_BACKUP"
restore_direct_save_link
test "$(readlink "$GAME_SOURCE/data/saves")" = "$original"
test ! -e "$DIRECT_SAVE_BACKUP"
restore_direct_save_link
''')

    def test_disabled_does_not_change_link(self):
        self.run_case('prepare_direct_save_copy; test -L "$GAME_SOURCE/data/saves"; test "$FAKE_BOUND" = 0; test "$DIRECT_SAVE_MOVED" = 0', enabled=0)

    def test_copy_failure_keeps_original_link(self):
        self.run_case('if prepare_direct_save_copy; then exit 1; fi; restore_direct_save_link; test -L "$GAME_SOURCE/data/saves"; test "$DIRECT_SAVE_MOVED" = 0', copy_failure=1)

    def test_busy_path_retains_backup_and_local_saves(self):
        self.run_case('prepare_direct_save_copy; if restore_direct_save_link; then exit 1; fi; test -L "$DIRECT_SAVE_BACKUP"; test -d "$DIRECT_SAVE_PATH"; test "$DIRECT_SAVE_MOVED" = 1', busy=1)

    def test_real_directory_unchanged(self):
        self.run_case('rm "$GAME_SOURCE/data/saves"; mkdir "$GAME_SOURCE/data/saves"; touch "$GAME_SOURCE/data/saves/local.sav"; prepare_direct_save_copy; test -f "$GAME_SOURCE/data/saves/local.sav"; test "$FAKE_BOUND" = 0')

    def test_outside_game_unchanged(self):
        self.run_case('prepare_direct_save_copy; test -L "$GAME_SOURCE/data/saves"; test "$FAKE_BOUND" = 0', savedir='drive_c/users/root')

    def test_traversal_unchanged(self):
        self.run_case('prepare_direct_save_copy; test "$FAKE_BOUND" = 0', savedir='../outside')

    def test_orphan_backup_refuses_new_launch(self):
        self.run_case('mv "$GAME_SOURCE/data/saves" "$GAME_SOURCE/data/saves.umu-direct-link"; mkdir "$GAME_SOURCE/data/saves"; if prepare_direct_save_copy; then exit 1; fi; test -L "$GAME_SOURCE/data/saves.umu-direct-link"; test "$FAKE_BOUND" = 0')

    def test_compressed_uses_merged_alias(self):
        self.run_case('prepare_direct_save_copy; test "$DIRECT_SAVE_MOVED" = 1; restore_direct_save_link; test -L "$GAME_SOURCE/data/saves"', compressed=1)

    def test_quoted_savedir(self):
        self.run_case('prepare_direct_save_copy; test "$DIRECT_SAVE_MOVED" = 1; restore_direct_save_link', savedir='"drive_c/game/data/saves/"')

    def test_unexpected_target_refused(self):
        self.run_case('rm "$GAME_SOURCE/data/saves"; ln -s /tmp "$GAME_SOURCE/data/saves"; if prepare_direct_save_copy; then exit 1; fi; test -L "$GAME_SOURCE/data/saves"; test "$FAKE_BOUND" = 0')

    def test_save_changes_and_deletions_are_synchronized(self):
        self.run_case('''prepare_direct_save_copy
printf 'new save' > "$DIRECT_SAVE_PATH/new.sav"
rm "$DIRECT_SAVE_PATH/keep.sav"
restore_direct_save_link
test -f "$DIRECT_SAVE_SOURCE/new.sav"
test ! -e "$DIRECT_SAVE_SOURCE/keep.sav"
test ! -e "$DIRECT_SAVE_SOURCE.umu-direct-previous"
# Restore fixture data after checking that deletion reached persistent saves.
printf "original save" > "$DIRECT_SAVE_SOURCE/keep.sav"
''')

    def test_sync_failure_retains_both_save_copies(self):
        self.run_case('''prepare_direct_save_copy
printf 'unsynced save' > "$DIRECT_SAVE_PATH/new.sav"
DIRECT_SAVE_SOURCE=/nonexistent/invalid-save-target
if restore_direct_save_link; then exit 1; fi
test -f "$DIRECT_SAVE_PATH/new.sav"
test -L "$DIRECT_SAVE_BACKUP"
test "$DIRECT_SAVE_MOVED" = 1
''')

    def test_previous_snapshot_inside_saves_without_recursive_copies(self):
        self.run_case('''prepare_direct_save_copy
printf 'first' > "$DIRECT_SAVE_PATH/new.sav"
restore_direct_save_link
prepare_direct_save_copy
test ! -e "$DIRECT_SAVE_PATH/.umu-direct-previous"
printf 'second' > "$DIRECT_SAVE_PATH/new.sav"
restore_direct_save_link
test "$(cat "$DIRECT_SAVE_SOURCE/new.sav")" = second
test "$(cat "$DIRECT_SAVE_SOURCE/.umu-direct-previous/new.sav")" = first
test ! -e "$DIRECT_SAVE_SOURCE/.umu-direct-previous/.umu-direct-previous"
test ! -e "$DIRECT_SAVE_SOURCE.umu-direct-previous"
''')
