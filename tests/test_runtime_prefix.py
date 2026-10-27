import importlib.util
import errno
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('runtime_prefix', ROOT / 'toolbox/overlay/umu-batocera/runtime-prefix.py')
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)
WRAPPER = (ROOT / 'toolbox/overlay/bin/wine').read_text()


class RuntimePrefixTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.store = runtime.PrefixStore(self.base)
        self.prefix = self.store.root / 'Some Game.wine-123'
        self.source = self.base / 'Original.wine'
        self.source.mkdir()
        (self.source / 'save').write_text('original data')
        self.pid = os.getpid()
        # The execution service exposes a virtual /proc with host PIDs. Model
        # liveness explicitly here; test stat parsing separately below.
        token = patch.object(runtime, 'process_token', side_effect=lambda pid: 'current-start' if pid == self.pid else '')
        token.start()
        self.addCleanup(token.stop)
        self.mounts = patch.object(runtime, 'mounted', return_value=False)
        self.mounts.start()
        self.addCleanup(self.mounts.stop)

    def begin(self):
        self.store.begin(self.prefix, self.source, self.pid)
        (self.prefix / 'data').write_text('runtime data')

    def test_synchronized_prefix_is_removed_original_untouched(self):
        self.begin()
        self.store.phase(self.prefix, self.pid, 'running')
        self.store.finish(self.prefix, self.pid, True)
        self.assertFalse(self.prefix.exists())
        self.assertFalse(self.store.record(self.prefix).exists())
        self.assertEqual((self.source / 'save').read_text(), 'original data')

    def test_failed_persistence_is_retained_and_next_launch_cannot_overwrite_it(self):
        self.begin()
        self.store.phase(self.prefix, self.pid, 'running')
        self.store.finish(self.prefix, self.pid, False)
        with self.assertRaisesRegex(ValueError, 'recovery required'):
            self.store.begin(self.prefix, self.source, self.pid)
        self.assertEqual((self.prefix / 'data').read_text(), 'runtime data')

    def test_live_preparation_is_never_collected(self):
        self.begin()
        self.store.collect()
        self.assertTrue(self.prefix.exists())

    def test_killed_preparation_is_reclaimed_but_killed_game_requires_recovery(self):
        for phase, kept in (('preparing', False), ('running', True)):
            with self.subTest(phase=phase):
                self.begin()
                data = self.store.read(self.prefix)
                data.update(phase=phase, pid=99999999, process_token='old-process')
                self.store.write(self.prefix, data)
                self.store.collect()
                self.assertEqual(self.prefix.exists(), kept)
                if kept:
                    shutil.rmtree(self.prefix)
                    self.store.record(self.prefix).unlink()

    def test_pid_reuse_does_not_keep_an_abandoned_copy(self):
        self.begin()
        data = self.store.read(self.prefix)
        data['process_token'] = 'different-start-time'
        self.store.write(self.prefix, data)
        self.store.collect()
        self.assertFalse(self.prefix.exists())

    def test_busy_mount_is_kept_even_after_success_then_reclaimed_later(self):
        self.begin()
        with patch.object(runtime, 'mounted', return_value=True):
            self.store.finish(self.prefix, self.pid, True)
        self.assertTrue(self.prefix.exists())
        self.store.collect()
        self.assertFalse(self.prefix.exists())

    def test_legacy_copy_is_preserved_once_and_recovery_does_not_grow_on_retries(self):
        self.prefix.mkdir()
        (self.prefix / 'old-save').write_text('legacy save')
        self.begin()
        legacy = list(self.store.root.glob('.legacy-*'))
        self.assertEqual(len(legacy), 1)
        self.assertEqual((legacy[0] / 'old-save').read_text(), 'legacy save')
        self.store.finish(self.prefix, self.pid, False)
        for _ in range(3):
            with self.assertRaises(ValueError):
                self.store.begin(self.prefix, self.source, self.pid)
        self.assertEqual(list(self.store.root.glob('.legacy-*')), legacy)

    def test_unknown_directories_and_bad_journals_are_not_collected(self):
        self.prefix.mkdir()
        (self.prefix / 'important').write_text('keep')
        self.store.record(self.prefix).write_text('{broken')
        self.store.collect()
        self.assertEqual((self.prefix / 'important').read_text(), 'keep')

    def test_redirected_journal_and_prefix_are_refused(self):
        self.store.record(self.prefix).symlink_to(self.source / 'save')
        with self.assertRaises(ValueError):
            self.store.begin(self.prefix, self.source, self.pid)
        self.store.record(self.prefix).unlink()
        self.prefix.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.store.begin(self.prefix, self.source, self.pid)
        self.assertEqual((self.source / 'save').read_text(), 'original data')

    def test_external_prefix_in_forged_journal_cannot_authorize_deletion(self):
        self.store.record(self.prefix).write_text(json.dumps(dict(version=1, prefix=str(self.source), phase='disposable')))
        self.store.collect()
        self.assertTrue((self.source / 'save').is_file())

    def test_manual_removal_does_not_leave_a_permanent_recovery_block(self):
        self.begin()
        self.store.finish(self.prefix, self.pid, False)
        shutil.rmtree(self.prefix)
        self.store.begin(self.prefix, self.source, self.pid)
        self.assertEqual(self.store.read(self.prefix)['phase'], 'preparing')

    def test_wrong_owner_cannot_mark_copy_disposable(self):
        self.begin()
        with self.assertRaises(ValueError):
            self.store.finish(self.prefix, 99999999, True)
        self.assertTrue(self.prefix.exists())

    def test_hotkey_interruption_reuses_exact_owned_prefix_without_another_copy(self):
        self.store.begin(self.prefix, self.source, self.pid, 'Game')
        (self.prefix / 'drive_c').mkdir()
        (self.prefix / 'system.reg').write_text('registry')
        (self.prefix / 'user.reg').write_text('unique progression')
        inode = (self.prefix / 'user.reg').stat().st_ino
        self.store.phase(self.prefix, self.pid, 'running')
        # Model SIGKILL: owner gone, no exit handler or sync was possible.
        data = self.store.read(self.prefix)
        data.update(pid=99999999, process_token='previous-boot:123')
        self.store.write(self.prefix, data)
        self.assertTrue(self.store.begin(self.prefix, self.source, self.pid, 'Game'))
        self.assertEqual((self.prefix / 'user.reg').stat().st_ino, inode)
        self.assertEqual((self.prefix / 'user.reg').read_text(), 'unique progression')
        self.assertEqual(self.store.read(self.prefix)['phase'], 'running')
        self.store.finish(self.prefix, self.pid, False)
        self.assertTrue(self.store.begin(self.prefix, self.source, self.pid, 'Game'))
        self.assertEqual(len(list(self.store.root.iterdir())), 1)
        self.store.finish(self.prefix, self.pid, True)
        self.assertFalse(self.prefix.exists())

    def retained_complete(self, **settings):
        self.store.begin(self.prefix, self.source, self.pid, 'Game', 'Runner', **settings)
        (self.prefix / 'drive_c').mkdir()
        (self.prefix / 'system.reg').write_text('registry')
        (self.prefix / 'user.reg').write_text('unsynchronized progress')
        self.store.finish(self.prefix, self.pid, False)

    def test_changed_wine_source_or_mode_keeps_old_changes_separate_and_starts_fresh(self):
        for change in ('registry', 'mode', 'runner'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                self.store = runtime.PrefixStore(Path(folder))
                self.prefix = self.store.root / 'Test-123'
                self.retained_complete()
                if change == 'registry':
                    (self.source / 'user.reg').write_text('source changed outside UMU')
                reused = self.store.begin(self.prefix, self.source, self.pid, 'Game',
                    'OtherRunner' if change == 'runner' else 'Runner', mode='1' if change == 'mode' else '0')
                self.assertFalse(reused)
                self.assertFalse((self.prefix / 'user.reg').exists())
                old, = self.store.root.glob('.retained-*')
                self.assertEqual((old / 'user.reg').read_text(), 'unsynchronized progress')
                self.assertEqual(self.store.read(old)['reason'], 'source-changed')

    def test_replaced_archive_at_same_path_does_not_resume_previous_generation(self):
        archive = self.base / 'Forza Horizon 2.wsquashfs'
        archive.write_bytes(b'old archive')
        def identity(*args):
            return json.dumps(runtime.file_identity(archive))
        with patch.object(runtime, 'source_identity', side_effect=identity):
            self.retained_complete()
            replacement = archive.with_suffix('.new')
            replacement.write_bytes(b'older game version')
            replacement.replace(archive)
            self.assertFalse(self.store.begin(self.prefix, self.source, self.pid, 'Game', 'Runner'))
        old, = self.store.root.glob('.retained-*')
        self.assertEqual((old / 'user.reg').read_text(), 'unsynchronized progress')

    def test_old_journal_without_generation_is_preserved_but_never_resumed(self):
        self.retained_complete()
        data = self.store.read(self.prefix)
        data.pop('source_identity')
        self.store.write(self.prefix, data)
        self.assertFalse(self.store.begin(self.prefix, self.source, self.pid, 'Game', 'Runner'))
        old, = self.store.root.glob('.retained-*')
        self.assertEqual(self.store.read(old)['reason'], 'unverified-source')

    def test_direct_save_descriptor_is_journaled_before_mutation_and_verified_on_resume(self):
        self.retained_complete()
        self.assertTrue(self.store.begin(self.prefix, self.source, self.pid, 'Game', 'Runner'))
        self.store.direct_save(self.prefix, self.pid, '/game/data/saves', '/saves/Forza')
        self.assertEqual(self.store.read(self.prefix)['phase'], 'running')
        self.store.direct_save(self.prefix, self.pid, '/game/data/saves', '/saves/Forza', resume=True)
        with self.assertRaisesRegex(ValueError, 'unverified interrupted'):
            self.store.direct_save(self.prefix, self.pid, '/game/data/saves', '/saves/Other', resume=True)

    def test_checkpoint_can_read_live_view_after_original_mount_has_disappeared(self):
        original = self.base / 'unmounted.wsquashfs'
        self.store.begin(self.prefix, original, self.pid, 'Game', 'Runner', source_view=str(self.source))
        (self.prefix / 'drive_c').mkdir()
        (self.prefix / 'system.reg').write_text('registry')
        (self.prefix / 'user.reg').write_text('unsynchronized changes')
        (self.source / 'user.reg').write_text('known returned changes')
        self.store.checkpoint(self.prefix, self.pid, original, source_view=str(self.source))
        self.store.finish(self.prefix, self.pid, False)
        self.assertTrue(self.store.begin(self.prefix, original, self.pid, 'Game', 'Runner',
                                         source_view=str(self.source)))
        self.assertEqual(self.store.read(self.prefix)['source'], str(original))
        self.assertFalse(original.exists())

    def test_recovery_for_another_source_or_game_directory_is_never_reused(self):
        self.store.begin(self.prefix, self.source, self.pid, 'Game')
        (self.prefix / 'drive_c').mkdir()
        (self.prefix / 'system.reg').write_text('registry')
        (self.prefix / 'user.reg').write_text('keep')
        self.store.finish(self.prefix, self.pid, False)
        for source, game in ((self.base / 'Other.wine', 'Game'), (self.source, 'Other')):
            with self.assertRaisesRegex(ValueError, 'recovery required'):
                self.store.begin(self.prefix, source, self.pid, game)
        self.assertEqual((self.prefix / 'user.reg').read_text(), 'keep')

    def test_recovery_report_includes_legacy_data_but_not_active_session(self):
        legacy = self.store.root / 'Old copy'
        legacy.mkdir()
        (legacy / 'save').write_text('keep')
        self.begin()
        report = self.store.report()
        self.assertEqual(report, '1\n' + str(legacy))
        self.store.finish(self.prefix, self.pid, False)
        self.assertTrue(self.store.report().startswith('2\n'))
        self.assertEqual((legacy / 'save').read_text(), 'keep')

    def test_manual_cleanup_is_blocked_by_live_owner_or_orphaned_container_mount(self):
        self.begin()
        self.assertFalse(self.store.idle())
        self.store.finish(self.prefix, self.pid, False)
        self.assertTrue(self.store.idle())
        with patch.object(runtime, 'mounted', return_value=True):
            self.assertFalse(self.store.idle())


class SpacePreflightTests(unittest.TestCase):
    def test_estimate_excludes_game_and_owned_backup_and_refuses_full_disk(self):
        block = WRAPPER[WRAPPER.index('check_materialized_space() {'):WRAPPER.index('if ! protect_all_umu_runners_ro;', WRAPPER.index('check_materialized_space() {'))]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'Game.wine'
            for name in ('Game', 'Game.bak', 'windows', 'Unrelated.bak'):
                (source / 'drive_c' / name).mkdir(parents=True)
            (source / 'system.reg').write_text('registry')
            script = '''set -u
log() { :; }
du() { printf '%s\\n' "$@" > "$TRACE"; printf '1024 prefix\\n'; }
df() { printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\\nfake 100 50 %s 50%% /\\n' "$AVAILABLE"; }
''' + block + '\ncheck_materialized_space\n'
            for free, code in (('400000', 0), ('1024', 1)):
                result = subprocess.run(['bash', '-c', script], capture_output=True, text=True, env=dict(os.environ,
                    ORIGINAL_PREFIX_CANON=str(source), GAME_DIR='Game', UWT_GAME_BACKUP_NAME='Game.bak',
                    MATERIALIZED_PREFIX=str(root), LOG='/dev/null', TRACE=str(root / 'trace'), AVAILABLE=free))
                self.assertEqual(result.returncode, code, result.stderr)
                estimated = (root / 'trace').read_text().splitlines()
                self.assertNotIn(str(source / 'drive_c/Game'), estimated)
                self.assertNotIn(str(source / 'drive_c/Game.bak'), estimated)
                self.assertIn(str(source / 'drive_c/Unrelated.bak'), estimated)


class LifecycleOrderTests(unittest.TestCase):
    def test_both_copy_paths_are_guarded_and_no_longer_delete_old_runtime(self):
        self.assertEqual(WRAPPER.count('prepare_materialized_prefix && check_materialized_space'), 2)
        self.assertNotIn('rm -rf "$MATERIALIZED_PREFIX"', WRAPPER)
        launch = WRAPPER.index('python3 "$ROOT_BRIDGE" "$UMU_RUN" "$UMU_EXE"')
        self.assertLess(WRAPPER.index('RUNTIME_SAFE_TO_REMOVE=0', WRAPPER.index('log "umu_exe=')), launch)
        self.assertLess(launch, WRAPPER.index('        persist_split_wine_prefix', launch))
        self.assertLess(WRAPPER.index('        persist_split_wine_prefix', launch), WRAPPER.index('RUNTIME_SAFE_TO_REMOVE=1', launch))
        cleanup = WRAPPER[WRAPPER.index('cleanup_runtime_mounts() {'):WRAPPER.index('trap cleanup_runtime_mounts')]
        self.assertLess(cleanup.index('umount "$PFX_MOUNT"'), cleanup.index('"$RUNTIME_HELPER" finish'))
        self.assertIn('if ! restore_direct_save_link;', cleanup)


class CompressedPersistenceTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('findmnt'), 'util-linux findmnt required')
    def test_real_findmnt_space_encoding_does_not_reject_matching_fh2_layers(self):
        # Exercise util-linux's actual formatter against an isolated mountinfo
        # table. Raw output hex-escapes spaces; normal output decodes them.
        start = WRAPPER.index('        target_fstype=', WRAPPER.index('persist_split_wine_prefix() {'))
        guard = WRAPPER[start:WRAPPER.index('\n    else\n      case', start)]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            alias = root / 'alias'
            alias.mkdir()
            original = root / 'gone/FH2.wsquashfs'
            game = 'Forza Horizon 2[GE-Proton11-7-UMU].wsquashfs'
            upper = str(root / 'wine-bottles' / (game + '.wine'))
            lower = str(root / 'squashfs' / game)
            table = root / 'mountinfo'
            def escape(value):
                return value.replace('\\', r'\134').replace(' ', r'\040')
            table.write_text(f'100 1 0:99 / {alias} rw,relatime - overlay overlay '
                             f'rw,lowerdir={escape(lower)},upperdir={escape(upper)},workdir=/work\n')
            raw = subprocess.check_output(['findmnt', '-k', '-F', str(table), '-rn', '-M', str(alias),
                                           '-o', 'OPTIONS'], text=True)
            self.assertIn(r'Forza\x20Horizon\x202', raw)
            script = '''set -u
log() { printf '%s\\n' "$*"; }
findmnt() { command findmnt -k -F "$TABLE" "$@"; }
check_guard() {
    local target="$ORIGINAL_PREFIX_CANON" target_fstype alias_fstype alias_options
''' + guard + '''
    printf 'verified_target=%s\\n' "$target"
}
check_guard
'''
            result = subprocess.run(['bash', '-c', script], capture_output=True, text=True,
                env=dict(os.environ, TABLE=str(table), ORIGINAL_PREFIX_CANON=str(original),
                         ALIAS_BOUND='1', ALIAS_MOUNT=str(alias), OVERLAY_UPPERDIR=upper,
                         OVERLAY_LOWERDIR=lower))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('verified_target=' + str(alias), result.stdout)

    def test_return_uses_only_owned_matching_writable_alias_if_original_mount_is_gone(self):
        for failure in ('', 'upper', 'lower', 'readonly', 'fstype', 'unowned'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                materialized = root / 'materialized-prefixes/Test'
                alias = root / 'alias'
                original = root / 'gone/Game.wsquashfs'
                for directory in (materialized, alias):
                    (directory / 'drive_c/Game').mkdir(parents=True)
                    (directory / 'user.reg').write_text('initial registry')
                    (directory / 'system.reg').write_text('registry')
                (materialized / 'user.reg').write_text('updated registry')
                (alias / 'drive_c/Game/azimuth.exe').write_bytes(b'unchanged game')
                archive = root / 'Game.wsquashfs'
                archive.write_bytes(b'unchanged archive')
                upper = str(root / 'upper with spaces')
                lower = str(root / 'lower with spaces')
                options = f'rw,lowerdir={lower},upperdir={upper},workdir=/work'
                if failure == 'upper': options = options.replace(upper, '/different/upper')
                if failure == 'lower': options = options.replace(lower, '/different/lower')
                if failure == 'readonly': options = options.replace('rw,', 'ro,')
                block = WRAPPER[WRAPPER.index('persist_split_wine_prefix() {'):WRAPPER.index('# v3.9.2: every materialized-prefix session')]
                block = block.replace('/userdata/system/umu/materialized-prefixes/', str(materialized.parent) + '/')
                block = block.replace('/run/wine/*.wsquashfs', str(original.parent) + '/*.wsquashfs')
                script = '''set -u
log() { printf '%s\\n' "$*"; }
is_prefix_root() { [ -f "$1/system.reg" ] && [ -f "$1/user.reg" ]; }
findmnt() {
    case "$*" in
        *"$ORIGINAL_PREFIX_CANON"*) printf 'ext4\\n';;
        *FSTYPE*) printf '%s\\n' "$ALIAS_FSTYPE";;
        *OPTIONS*) printf '%s\\n' "$ALIAS_OPTS";;
        *) return 1;;
    esac
}
''' + block + '\npersist_split_wine_prefix\n'
                result = subprocess.run(['bash', '-c', script], capture_output=True, text=True,
                    env=dict(os.environ, MATERIALIZED_PREFIX=str(materialized), ORIGINAL_PREFIX_CANON=str(original),
                        COMPRESSED_OVERLAY='1', WINE_SPLIT_PREFIX='0', GAME_DIR='Game', LOG='/dev/null',
                        ALIAS_BOUND='0' if failure == 'unowned' else '1', ALIAS_MOUNT=str(alias),
                        ALIAS_FSTYPE='ext4' if failure == 'fstype' else 'overlay', ALIAS_OPTS=options,
                        OVERLAY_UPPERDIR=upper, OVERLAY_LOWERDIR=lower))
                self.assertEqual(result.returncode, 3 if failure else 0, result.stdout + result.stderr)
                self.assertEqual((alias / 'user.reg').read_text(), 'initial registry' if failure else 'updated registry')
                self.assertFalse(original.exists())
                self.assertEqual((alias / 'drive_c/Game/azimuth.exe').read_bytes(), b'unchanged game')
                self.assertEqual(archive.read_bytes(), b'unchanged archive')
                if not failure:
                    self.assertIn('wine_persistence_overlay_alias_fallback=', result.stdout)
                    self.assertIn('wine_persistence_result=success', result.stdout)

    def test_compressed_changes_return_to_bottle_and_game_and_archive_stay_intact(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            materialized = root / 'materialized-prefixes/Test'
            target = root / 'wine/Test.wsquashfs'
            archive = root / 'Test.wsquashfs'
            archive.write_bytes(b'original immutable archive')
            for directory in (materialized, target):
                (directory / 'drive_c/windows').mkdir(parents=True)
                (directory / 'drive_c/Game').mkdir()
                (directory / 'system.reg').write_text('registry')
                (directory / 'user.reg').write_text('registry')
            (target / 'drive_c/Game/game.exe').write_bytes(b'game data')
            inode = (target / 'drive_c/Game/game.exe').stat().st_ino
            (materialized / 'user.reg').write_text('updated progression')
            (target / 'autorun.cmd').write_text('ENV=current-user-choice')
            (materialized / 'autorun.cmd').write_text('ENV=old-recovered-choice')
            (materialized / 'drive_c/windows/added.dll').write_bytes(b'new DLL')
            external = root / 'saves'
            external.mkdir()
            (external / 'save').write_bytes(b'progression')
            (materialized / 'drive_c/save').symlink_to(external)
            block = WRAPPER[WRAPPER.index('persist_split_wine_prefix() {'):WRAPPER.index('# v3.9.2: every materialized-prefix session')]
            block = block.replace('/userdata/system/umu/materialized-prefixes/', str(materialized.parent) + '/')
            block = block.replace('/run/wine/*.wsquashfs', str(target.parent) + '/*.wsquashfs')
            script = '''set -u
log() { :; }
is_prefix_root() { [ -f "$1/system.reg" ] && [ -f "$1/user.reg" ]; }
findmnt() { printf '%s\\n' "$TEST_FSTYPE"; }
''' + block + '\npersist_split_wine_prefix\n'
            env = dict(os.environ, MATERIALIZED_PREFIX=str(materialized), ORIGINAL_PREFIX_CANON=str(target),
                       COMPRESSED_OVERLAY='1', WINE_SPLIT_PREFIX='0', GAME_DIR='Game', LOG='/dev/null')
            refused = subprocess.run(['bash', '-c', script], env=dict(env, TEST_FSTYPE='ext4'), capture_output=True, text=True)
            self.assertEqual(refused.returncode, 3, refused.stderr)
            self.assertEqual((target / 'user.reg').read_text(), 'registry')
            result = subprocess.run(['bash', '-c', script], env=dict(env, TEST_FSTYPE='overlay'), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((target / 'user.reg').read_text(), 'updated progression')
            self.assertEqual((target / 'autorun.cmd').read_text(), 'ENV=current-user-choice')
            self.assertEqual((target / 'drive_c/windows/added.dll').read_bytes(), b'new DLL')
            self.assertTrue((target / 'drive_c/save').is_symlink())
            self.assertEqual((external / 'save').read_bytes(), b'progression')
            self.assertEqual((target / 'drive_c/Game/game.exe').stat().st_ino, inode)
            self.assertEqual(archive.read_bytes(), b'original immutable archive')

    def test_persistence_failure_never_authorizes_runtime_deletion(self):
        tail = WRAPPER[WRAPPER.index('if [ "${WINE_SPLIT_PREFIX:-0}" -eq 1 ] || [ "$COMPRESSED_OVERLAY" -eq 1 ]; then', WRAPPER.index('log "umu_exe=')):]
        for kind in ('wine', 'compressed'):
            for failed, expected in ((True, '0'), (False, '1')):
                script = '''set -u
log() { :; }
persist_split_wine_prefix() { return "$TEST_RC"; }
RUNTIME_SAFE_TO_REMOVE=0
C_GAME_PATH_BOUND=0
rc=0
''' + tail.replace('exit "$rc"', 'printf "%s" "$RUNTIME_SAFE_TO_REMOVE"; exit "$rc"')
                result = subprocess.run(['bash', '-c', script], capture_output=True, text=True, env=dict(os.environ,
                    WINE_SPLIT_PREFIX='1' if kind == 'wine' else '0', COMPRESSED_OVERLAY='1' if kind == 'compressed' else '0',
                    MATERIALIZED_PREFIX='/not-deleted', TEST_RC='8' if failed else '0'))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected)


class ProcessIdentityTests(unittest.TestCase):
    def test_zombie_owner_is_not_considered_alive_for_cleanup_waiting(self):
        fields = ['Z'] + ['0'] * 18 + ['123456']
        with patch.object(Path, 'read_text', return_value='42 (wine) ' + ' '.join(fields)):
            self.assertEqual(runtime.process_token(42), '')

    def test_start_time_parsing_includes_boot_id_and_handles_parentheses_in_name(self):
        fields = ['S'] + ['0'] * 18 + ['123456'] + ['0'] * 10
        stat = '42 (wine (game)) ' + ' '.join(fields)
        with patch.object(Path, 'read_text', side_effect=[stat, 'boot-identity\n']):
            self.assertEqual(runtime.process_token(42), 'boot-identity:123456')


class MountNamespaceTests(unittest.TestCase):
    def test_gone_or_invalid_mount_namespace_is_handled_without_skipping_a_live_namespace(self):
        prefix = Path('/userdata/system/umu/materialized-prefixes/Game-123')
        with tempfile.TemporaryDirectory() as folder:
            process = Path(folder) / '123'
            (process / 'ns').mkdir(parents=True)
            (process / 'ns/mnt').touch()
            for number in (errno.EINVAL, errno.EACCES):
                with self.subTest(errno=number), patch.object(Path, 'glob', return_value=[process]), \
                        patch.object(Path, 'read_text', side_effect=OSError(number, 'unreadable')):
                    self.assertTrue(runtime.mounted(prefix))
            # Namespace vanished during mountinfo reading: another process in
            # the same namespace must still get checked (not marked seen early).
            with patch.object(Path, 'glob', return_value=[process, process]), \
                    patch.object(Path, 'read_text', side_effect=[FileNotFoundError(),
                        '10 1 8:1 /system/umu/materialized-prefixes/Game-123 /pfx rw - ext4 /dev/sda rw']), \
                    patch.object(Path, 'exists', return_value=False):
                self.assertTrue(runtime.mounted(prefix))

    def test_bind_root_in_another_namespace_prevents_deletion_with_spaces(self):
        prefix = Path('/userdata/system/umu/materialized-prefixes/Game with spaces-123')
        with tempfile.TemporaryDirectory() as folder:
            process = Path(folder) / '123'
            (process / 'ns').mkdir(parents=True)
            (process / 'ns/mnt').touch()
            for mountroot, target, expected in (
                ('/system/umu/materialized-prefixes/Game\\040with\\040spaces-123', '/compatdata/pfx', True),
                ('/system/umu/materialized-prefixes/Game\\040with\\040spaces-123/drive_c', '/container/view', True),
                ('/different/root', str(prefix / 'drive_c').replace(' ', '\\040'), True),
                ('/system/umu/materialized-prefixes/Game\\040with\\040spaces-123-other', '/other', False)):
                with self.subTest(root=mountroot, target=target):
                    (process / 'mountinfo').write_text(f'10 1 8:1 {mountroot} {target} rw - ext4 /dev/sda rw\n')
                    with patch.object(Path, 'glob', return_value=[process]):
                        self.assertEqual(runtime.mounted(prefix), expected)


class SourceIdentityTests(unittest.TestCase):
    def test_archive_identity_uses_loop_backing_file_not_overlay_mount_inode(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'Forza Horizon 2.wsquashfs'
            archive.write_bytes(b'archive v1')
            prefix = Path(folder) / 'merged.wsquashfs'
            prefix.mkdir()
            original = Path.read_text
            def read(path, *args, **kwargs):
                if str(path) == '/sys/class/block/loop7/loop/backing_file':
                    return str(archive).replace(' ', r'\040')
                return original(path, *args, **kwargs)
            with patch.object(runtime.subprocess, 'check_output', return_value='/dev/loop7\n'), \
                    patch.object(Path, 'read_text', read):
                first = runtime.source_identity(prefix, lowerdir='/mount/lower')
                self.assertIsNotNone(first)
                self.assertEqual(first, runtime.source_identity(prefix, lowerdir='/mount/lower'))
                alias = Path(folder) / 'merged-alias-123'
                alias.mkdir()
                self.assertEqual(first, runtime.source_identity(alias, lowerdir='/mount/lower'))
                archive.write_bytes(b'archive v2')
                self.assertNotEqual(first, runtime.source_identity(prefix, lowerdir='/mount/lower'))
            self.assertIsNone(runtime.source_identity(prefix))
            with patch.object(runtime.subprocess, 'check_output', return_value='/dev/sda1\n'):
                self.assertIsNone(runtime.source_identity(prefix, lowerdir='/mount/lower'))
