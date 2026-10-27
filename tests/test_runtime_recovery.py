import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('recovery', ROOT / 'toolbox/helpers/runtime-recovery.py')
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.manager = recovery.RecoveryManager(self.base / 'umu')
        self.store = self.manager.store
        self.pid = os.getpid()
        self.addCleanup(patch.stopall)
        patch.object(recovery.runtime, 'mounted', return_value=False).start()
        patch.object(recovery.runtime, 'process_token', side_effect=lambda pid: 'alive' if pid == self.pid else '').start()

    def retained(self, name='Zelda.wsquashfs-123', reason='persistence-failed:6'):
        prefix = self.store.root / name
        source = '/run/wine/Zelda.wsquashfs'
        with patch.object(recovery.runtime, 'source_identity', return_value='verified-source'):
            self.store.begin(prefix, source, self.pid, 'game', 'GE-Proton10-25-UMU', '/logs/runner.log')
        (prefix / 'drive_c').mkdir()
        (prefix / 'system.reg').write_text('system registry')
        (prefix / 'user.reg').write_text('user changes')
        self.store.finish(prefix, self.pid, False, reason)
        return prefix

    def test_inventory_records_cause_runner_time_size_and_resume_even_with_unmounted_source(self):
        prefix = self.retained()
        item = self.manager.inventory()[0]
        self.assertEqual(item['source'], '/run/wine/Zelda.wsquashfs')
        self.assertEqual(item['runner'], 'GE-Proton10-25-UMU')
        self.assertEqual(item['reason'], 'persistence-failed:6')
        self.assertGreater(item['size'], 0)
        self.assertGreater(item['updated_at'], 0)
        self.assertTrue(item['resumable'])
        self.assertEqual(item['log'], '/logs/runner.log')
        self.assertTrue(prefix.exists())

    def test_discard_is_targeted_preserves_external_saves_original_and_other_recovery(self):
        selected = self.retained()
        other = self.retained('Resonance.wine-456')
        save = self.base / 'external-save'; save.mkdir()
        (save / 'progress.dat').write_text('progress')
        (selected / 'drive_c/save').symlink_to(save, target_is_directory=True)
        original = self.base / 'Game.wsquashfs'; original.write_text('archive')
        identity = next(x['id'] for x in self.manager.inventory() if x['prefix'] == str(selected))
        with self.manager.locked(): self.manager.discard(identity)
        self.assertFalse(selected.exists())
        self.assertFalse(self.store.record(selected).exists())
        self.assertTrue(other.exists())
        self.assertEqual((save / 'progress.dat').read_text(), 'progress')
        self.assertEqual(original.read_text(), 'archive')

    def test_live_owner_mount_or_competing_lock_refuses_actions(self):
        prefix = self.retained()
        identity = self.manager.inventory()[0]['id']
        with self.manager.locked():
            with self.assertRaises(BlockingIOError):
                with self.manager.locked(): pass
            with patch.object(recovery.runtime, 'mounted', return_value=True):
                with self.assertRaises(ValueError): self.manager.discard(identity)
        data = self.store.read(prefix)
        data.update(pid=self.pid, process_token='alive')
        self.store.write(prefix, data)
        with self.assertRaises(ValueError):
            with self.manager.locked(): pass
        self.assertTrue(prefix.exists())

    def test_legacy_can_be_inspected_and_explicitly_discarded_but_not_automatically_resumed(self):
        prefix = self.retained('.legacy-example', reason='legacy-untracked')
        data = self.store.read(prefix); data['game_dir'] = ''; self.store.write(prefix, data)
        item = self.manager.inventory()[0]
        self.assertFalse(item['resumable'])
        with self.manager.locked(): self.manager.discard(item['id'])
        self.assertFalse(prefix.exists())

    def test_explicit_discard_accepts_untracked_local_copy_but_refuses_redirected_journal(self):
        for kind in ('missing', 'invalid', 'foreign-prefix', 'symlink'):
            with self.subTest(kind=kind):
                prefix = self.retained()
                record = self.store.record(prefix)
                if kind == 'missing': record.unlink()
                elif kind == 'invalid': record.write_text('{broken')
                elif kind == 'foreign-prefix':
                    data = json.loads(record.read_text()); data['prefix'] = str(self.base); record.write_text(json.dumps(data))
                else:
                    external = self.base / 'journal.json'; external.write_text(record.read_text())
                    record.unlink(); record.symlink_to(external)
                item = self.manager.inventory()[0]
                self.assertFalse(item['known'])
                if kind == 'symlink':
                    with self.manager.locked(), self.assertRaises(ValueError): self.manager.discard(item['id'])
                    self.assertTrue(prefix.exists())
                    self.assertTrue(external.exists())
                    record.unlink()
                    import shutil
                    shutil.rmtree(prefix)
                else:
                    with self.manager.locked(): self.manager.discard(item['id'])
                    self.assertFalse(prefix.exists())
                    self.assertFalse(record.exists())

    def test_stale_id_and_traversal_are_refused(self):
        self.retained()
        for identity in ('../outside', '0' * 64):
            with self.assertRaises(ValueError): self.manager.discard(identity)

    def test_nested_file_changed_during_confirmation_invalidates_discard_for_untracked_copy(self):
        prefix = self.retained()
        self.store.record(prefix).unlink()
        saves = prefix / 'drive_c/users/saves'
        saves.mkdir(parents=True)
        (saves / 'progress').write_text('first')
        before = self.manager.inventory()[0]['id']
        (saves / 'progress').write_text('later progress')
        with self.manager.locked(), self.assertRaises(ValueError):
            self.manager.discard(before)
        self.assertEqual((saves / 'progress').read_text(), 'later progress')

    def test_changed_generation_is_not_advertised_as_resumable(self):
        prefix = self.retained()
        data = self.store.read(prefix)
        data['reason'] = 'source-changed'
        self.store.write(prefix, data)
        self.assertFalse(self.manager.inventory()[0]['resumable'])

    def test_repeated_failure_at_same_path_changes_notice_fingerprint_data(self):
        prefix = self.retained()
        before = self.manager.inventory()[0]
        data = self.store.read(prefix); data['reason'] = 'persistence-failed:15'; self.store.write(prefix, data)
        after = self.manager.inventory()[0]
        self.assertNotEqual(before, after)
        with self.manager.locked(), self.assertRaises(ValueError):
            self.manager.discard(before['id'])
        self.assertTrue(prefix.exists())

    def test_recovery_menu_cancel_and_rejected_confirmation_do_not_discard(self):
        shell = (ROOT / 'toolbox/umu-toolbox.sh').read_text()
        function = shell[shell.index('runtime_recovery_menu() {'):shell.index('clean_umu_runtime_data() (')]
        for choices, confirmation in (('cancel', 0), ('1\n3\n0\n', 1), ('1\n2\n0\n', 0), ('1\n1\n0\n', 0)):
            with self.subTest(choices=choices):
                trace = self.base / 'trace'; trace.write_text('')
                decisions = self.base / 'choices'; decisions.write_text(choices)
                setup = '''set -u
ROOT=/unused; LOG=/dev/null
i18n() { printf '%s' "$1"; }
msg() { :; }
python3() {
    echo "$2" >>"$TRACE"
    case "$2" in
        list) printf 'id\tZelda | 4.7 GiB\n';;
        details) printf 'Zelda\n/run/wine/Zelda\n/copy\n4.7 GiB\ndate\nGE\ninterrupted-or-unsynchronized\n1\n/log\n1\n';;
    esac
}
menu_choice() {
    [ "$(head -n 1 "$CHOICES")" != cancel ] || return 1
    head -n 1 "$CHOICES"
    sed -i '1d' "$CHOICES"
}
yesno() { return "$CONFIRMATION"; }
'''
                result = subprocess.run(['bash', '-c', setup + function + '\nruntime_recovery_menu'],
                                        capture_output=True, text=True,
                                        env=dict(os.environ, TRACE=str(trace), CHOICES=str(decisions), CONFIRMATION=str(confirmation)))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn('discard', trace.read_text())

    def test_failed_notification_is_bounded_localized_and_does_not_fail_cleanup(self):
        shell = (ROOT / 'toolbox/overlay/bin/wine').read_text()
        function = shell[shell.index('notify_runtime_recovery() {'):shell.index('# Direct mode only:')]
        toolbox = self.base / 'toolbox'; (toolbox / 'config').mkdir(parents=True); (toolbox / 'lang').mkdir()
        for language in ('en', 'fr'):
            (toolbox / 'config/language').write_text(language)
            (toolbox / f'lang/{language}.sh').write_text((ROOT / f'toolbox/lang/{language}.sh').read_text())
            trace = self.base / 'notify-trace'
            result = subprocess.run(['bash', '-c', 'set -u\nLOG=/dev/null\ncurl() { printf "%s\\n" "$@" >"$TRACE"; return 22; }\n' +
                                     function.replace('/userdata/system/umu/toolbox', str(toolbox)) + '\nnotify_runtime_recovery'],
                                    capture_output=True, text=True, env=dict(os.environ, TRACE=str(trace)))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--max-time\n2\n', trace.read_text())
            self.assertIn('http://127.0.0.1:1234/notify', trace.read_text())
            self.assertIn('modifications' if language == 'fr' else 'changes', trace.read_text())

    def test_bulk_cleanup_cannot_delete_recovery_data(self):
        shell = (ROOT / 'toolbox/umu-toolbox.sh').read_text()
        function = shell[shell.index('clean_umu_runtime_data_locked() {'):shell.index('toolbox_files_cleanup() {')]
        trace = self.base / 'bulk-trace'
        setup = '''set -u
ROOT=/unused; UMU_DIR=/unused; LOG=/dev/null
umu_game_active() { return 1; }
i18n() { printf '%s' "$1"; }
msg() { printf '%s\\n' "$*" >>"$TRACE"; }
python3() { printf '1\\n/retained/recovery\\n'; }
clear_dir_contents() { echo UNEXPECTED-DELETE >>"$TRACE"; }
'''
        result = subprocess.run(['bash', '-c', setup + function + '\nclean_umu_runtime_data_locked'],
                                capture_output=True, text=True, env=dict(os.environ, TRACE=str(trace)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('runtime_recovery_bulk_protected', trace.read_text())
        self.assertNotIn('UNEXPECTED-DELETE', trace.read_text())


if __name__ == '__main__':
    unittest.main()
