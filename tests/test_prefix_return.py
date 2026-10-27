"""Exercise actual return copying without destroying matching directory roots."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = (ROOT / 'toolbox/overlay/bin/wine').read_text()


class PrefixReturnTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'materialized-prefixes/Forza'
        self.target = self.root / 'Forza.wine'
        for directory in (self.source, self.target):
            (directory / 'drive_c/windows').mkdir(parents=True)
            (directory / 'dosdevices').mkdir()
            (directory / 'user.reg').write_text('old registry')
            (directory / 'system.reg').write_text('system registry')
            (directory / 'dosdevices/c:').symlink_to('../drive_c')
        (self.target / 'drive_c/game/data/saves').mkdir(parents=True)
        (self.target / 'drive_c/game/azimuth.exe').write_bytes(b'game remains')
        (self.source / 'user.reg').write_text('new registry')
        (self.source / 'autorun.cmd').write_text('discard this old setting')
        (self.target / 'autorun.cmd').write_text('ENV=UMU_DIRECT_GAME=1')
        self.outside = self.root / 'external'
        self.outside.mkdir()
        (self.outside / 'save').write_text('external save remains')

    def persist(self, block_directory_removal=False):
        function = WRAPPER[WRAPPER.index('persist_split_wine_prefix() {'):
                           WRAPPER.index('# v3.9.2: every materialized-prefix session')]
        function = function.replace('/userdata/system/umu/materialized-prefixes/', str(self.source.parent) + '/')
        script = '''set -u
log() { printf '%s\\n' "$*"; }
is_prefix_root() { [ -f "$1/system.reg" ] && [ -f "$1/user.reg" ]; }
rm() {
    for argument in "$@"; do
        if [ "$BLOCK_ROOT" = 1 ] && [ "$argument" = "$ORIGINAL_PREFIX_CANON/dosdevices" ]; then
            printf 'rm: dosdevices: Directory not empty\\n' >&2
            return 1
        fi
    done
    command rm "$@"
}
''' + function + '\npersist_split_wine_prefix\n'
        return subprocess.run(['bash', '-c', script], capture_output=True, text=True,
            env=dict(os.environ, MATERIALIZED_PREFIX=str(self.source), ORIGINAL_PREFIX_CANON=str(self.target),
                     GAME_DIR='game', WINE_SPLIT_PREFIX='1', COMPRESSED_OVERLAY='0',
                     BLOCK_ROOT='1' if block_directory_removal else '0', LOG='/dev/stderr'))

    def test_dosdevices_root_is_kept_and_mapping_changes_are_mirrored(self):
        inode = (self.target / 'dosdevices').stat().st_ino
        (self.target / 'dosdevices/old:').symlink_to('/nonexistent/old-drive')
        (self.source / 'dosdevices/q:').symlink_to(self.outside)
        (self.target / 'drive_c/users/obsolete').mkdir(parents=True)
        (self.target / 'drive_c/users/obsolete/save').write_text('deleted in session')
        (self.source / 'drive_c/users').mkdir()
        (self.source / 'drive_c/users/new-save').write_text('new progress')
        result = self.persist(block_directory_removal=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.target / 'dosdevices').stat().st_ino, inode)
        self.assertFalse((self.target / 'dosdevices/old:').is_symlink())
        self.assertEqual(os.readlink(self.target / 'dosdevices/c:'), '../drive_c')
        self.assertEqual(os.readlink(self.target / 'dosdevices/q:'), str(self.outside))
        self.assertFalse((self.target / 'drive_c/users/obsolete').exists())
        self.assertEqual((self.target / 'drive_c/users/new-save').read_text(), 'new progress')
        self.assertEqual((self.target / 'user.reg').read_text(), 'new registry')
        self.assertEqual((self.target / 'autorun.cmd').read_text(), 'ENV=UMU_DIRECT_GAME=1')
        self.assertEqual((self.target / 'drive_c/game/azimuth.exe').read_bytes(), b'game remains')
        self.assertEqual((self.outside / 'save').read_text(), 'external save remains')
        self.assertEqual(list(self.target.glob('.umu-prefix-sync-*')), [])

    def test_replacements_do_not_follow_links_or_write_runner_hardlinks(self):
        runner = self.outside / 'runner.dll'
        runner.write_text('protected runner remains')
        os.link(runner, self.target / 'drive_c/windows/module.dll')
        (self.source / 'drive_c/windows/module.dll').write_text('private prefix DLL')
        (self.target / 'drive_c/windows/settings').symlink_to(self.outside)
        (self.source / 'drive_c/windows/settings').mkdir()
        (self.source / 'drive_c/windows/settings/save').write_text('private save')
        (self.target / 'user.reg').unlink()
        (self.target / 'user.reg').symlink_to(self.outside / 'save')
        result = self.persist()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(runner.read_text(), 'protected runner remains')
        self.assertEqual((self.outside / 'save').read_text(), 'external save remains')
        self.assertFalse((self.target / 'user.reg').is_symlink())
        self.assertEqual((self.target / 'drive_c/windows/settings/save').read_text(), 'private save')
        self.assertNotEqual(runner.stat().st_ino, (self.target / 'drive_c/windows/module.dll').stat().st_ino)

    def test_copy_failure_is_reported_and_runtime_remains_for_recovery(self):
        os.mkfifo(self.source / 'unsupported-entry')
        result = self.persist()
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assertIn('phase=sync-tree', result.stdout)
        self.assertNotIn('wine_persistence_result=success', result.stdout)
        self.assertEqual((self.source / 'user.reg').read_text(), 'new registry')
        self.assertEqual((self.target / 'drive_c/game/azimuth.exe').read_bytes(), b'game remains')
        self.assertEqual(list(self.target.glob('.umu-prefix-sync-*')), [])


if __name__ == '__main__':
    unittest.main()
