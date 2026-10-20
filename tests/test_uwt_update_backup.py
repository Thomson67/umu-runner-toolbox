"""Exercise copy and return persistence with UWT's real update journal schema."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

WRAPPER = (Path(__file__).resolve().parents[1] / 'toolbox/overlay/bin/wine').read_text()
DETECT = WRAPPER[WRAPPER.index('uwt_update_backup_name() {'):WRAPPER.index('UWT_GAME_BACKUP_NAME=""')]
START = WRAPPER.index('    for COPY_ITEM in "$ORIGINAL_PREFIX_CANON/drive_c"', WRAPPER.index('UWT_GAME_BACKUP_NAME=""'))
COPY = WRAPPER[START:WRAPPER.index('    COPY_END=', START)]
PERSIST = WRAPPER[WRAPPER.index('persist_split_wine_prefix() {'):WRAPPER.index('# v3.9.2: every materialized-prefix session')]


class UwtUpdateBackupTests(unittest.TestCase):
    def exercise(self, case='active'):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            prefix = root / 'Game.wine'
            runtime = root / 'materialized-prefixes/Game'
            state_dir = root / 'state'
            state_dir.mkdir()
            for path in (prefix, runtime):
                (path / 'drive_c/windows').mkdir(parents=True)
                (path / 'system.reg').write_text('registry')
            game = prefix / 'drive_c/Game'
            backup = prefix / 'drive_c/Game.bak'
            for path in (game, backup, prefix / 'drive_c/Unrelated.bak'):
                path.mkdir()
                (path / 'payload').write_text(path.name)
            inode = (backup / 'payload').stat().st_ino
            metadata = state_dir / 'wsquashfs-update-test.json'
            state = dict(mode='update', prefix=str(prefix), metadata=str(metadata))
            data = dict(prefix=str(prefix), game_dir='drive_c/Game', game_backup=str(backup))
            if case == 'other-prefix': state['prefix'] = str(runtime)
            if case == 'other-manifest-prefix': data['prefix'] = str(runtime)
            if case == 'other-backup': data['game_backup'] = str(prefix / 'drive_c/Unrelated.bak')
            if case == 'committed': data['committed'] = True
            if case == 'removed': data['game_backup_removed'] = True
            if case == 'not-update': state['mode'] = 'create'
            if case == 'outside-manifest':
                metadata = root / 'wsquashfs-update-test.json'
                state['metadata'] = str(metadata)
            metadata.write_text(json.dumps(data))
            if case == 'symlink-manifest':
                actual = root / 'actual.json'
                metadata.rename(actual)
                metadata.symlink_to(actual)
            state_path = state_dir / 'wsquashfs-builder.json'
            state_path.write_text(json.dumps(state))
            if case == 'bad-json': state_path.write_text('{')
            if case == 'bad-shape': state_path.write_text('[]')
            if case == 'missing-state': state_path.unlink()
            detect = DETECT.replace('/userdata/system/ultimate-wine-toolbox/state', str(state_dir))
            persist = PERSIST.replace('/userdata/system/umu/materialized-prefixes/', str(runtime.parent) + '/')
            # Excluded backups must also survive an unexpected runtime namesake.
            command = '''set -u
log() { :; }
is_prefix_root() { [ -f "$1/system.reg" ]; }
''' + detect + '\nUWT_GAME_BACKUP_NAME="$(uwt_update_backup_name)"\n' + COPY + '''
printf '%s' "$UWT_GAME_BACKUP_NAME"
if [ -n "$UWT_GAME_BACKUP_NAME" ]; then
    [ ! -e "$MATERIALIZED_PREFIX/drive_c/$UWT_GAME_BACKUP_NAME" ] || exit 88
    mkdir "$MATERIALIZED_PREFIX/drive_c/$UWT_GAME_BACKUP_NAME"
    echo unexpected > "$MATERIALIZED_PREFIX/drive_c/$UWT_GAME_BACKUP_NAME/payload"
fi
echo new-prefix-data > "$MATERIALIZED_PREFIX/drive_c/windows/new.dll"
''' + persist + '\npersist_split_wine_prefix\n'
            result = subprocess.run(['bash', '-c', command], capture_output=True, text=True,
                env=dict(os.environ, ORIGINAL_PREFIX_CANON=str(prefix), GAME_DIR='Game',
                         MATERIALIZED_PREFIX=str(runtime), WINE_SPLIT_PREFIX='1', LOG='/dev/null'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            self.assertEqual((backup / 'payload').read_text(), 'Game.bak')
            self.assertEqual((game / 'payload').read_text(), 'Game')
            self.assertEqual((prefix / 'drive_c/Unrelated.bak/payload').read_text(), 'Unrelated.bak')
            self.assertEqual((prefix / 'drive_c/windows/new.dll').read_text(), 'new-prefix-data\n')
            if case == 'active':
                self.assertEqual(result.stdout, 'Game.bak')
                self.assertEqual((backup / 'payload').stat().st_ino, inode)
            else:
                self.assertEqual(result.stdout, '')
                self.assertTrue((runtime / 'drive_c/Game.bak/payload').is_file())

    def test_owned_backup_is_not_copied_removed_or_overwritten_on_return(self):
        self.exercise()

    def test_unverified_backups_keep_normal_copy_and_persistence(self):
        for case in ('other-prefix', 'other-manifest-prefix', 'other-backup', 'committed',
                     'removed', 'not-update', 'outside-manifest', 'symlink-manifest',
                     'bad-json', 'bad-shape', 'missing-state'):
            with self.subTest(case=case):
                self.exercise(case)
