"""Native -w must hold Batocera cleanup until the host return has ended."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
WINE_SERVER = (ROOT / 'toolbox/overlay/bin/wineserver').read_text()


class StopBarrierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runner = self.root / 'runner'
        for path in ('bin', 'files/bin', 'umu-batocera'):
            (self.runner / path).mkdir(parents=True)
        self.original = self.root / 'original.wsquashfs'
        self.materialized = self.root / 'materialized'
        self.original.mkdir()
        self.materialized.mkdir()
        (self.materialized / 'unique-save').write_text('retained changes')
        self.work = self.root / 'overlay-work'
        (self.work / 'work').mkdir(parents=True)
        self.flag = self.root / 'owner-alive'
        self.flag.touch()
        self.addCleanup(lambda: self.flag.unlink(missing_ok=True))
        self.state_dir = self.root / 'state'
        self.state_dir.mkdir()
        self.state = self.state_dir / 'session-test.state'
        self.state.write_text('\n'.join(map(str, [self.original, self.original, '', self.materialized,
                                                self.runner, os.getpid(), 'test-owner'])) + '\n')
        self.log_dir = self.root / 'logs'
        script = WINE_SERVER
        script = script.replace('/run/umu-batocera', str(self.state_dir))
        script = script.replace('/userdata/system/logs/umu-runner', str(self.log_dir))
        self.server = self.runner / 'bin/wineserver'
        self.server.write_text(script)
        self.server.chmod(0o755)
        real = self.runner / 'files/bin/wineserver'
        real.write_text('#!/bin/bash\necho "native Wine completed"\nexit "${SERVER_RC:-0}"\n')
        real.chmod(0o755)
        helper = (ROOT / 'toolbox/overlay/umu-batocera/runtime-prefix.py').read_text()
        # /proc is virtualized by the execution service. Model liveness with a
        # shared flag here; production process parsing has separate coverage.
        helper = helper.replace("if __name__ == '__main__':", f'''
def process_token(pid):
    return 'test-owner' if pid == {os.getpid()} and Path({str(self.flag)!r}).exists() else ''
if __name__ == '__main__':
''')
        (self.runner / 'umu-batocera/runtime-prefix.py').write_text(helper)

    def run_server(self, args=('-w',), original=None, rc=0):
        return subprocess.run([str(self.server), *args], capture_output=True, text=True, timeout=3,
                              env=dict(os.environ, WINEPREFIX=str(original or self.original), SERVER_RC=str(rc)))

    def test_native_cleanup_waits_until_prefix_and_direct_saves_have_returned(self):
        errors = []
        def complete_return():
            if not (self.work / 'work').is_dir():
                errors.append('OverlayFS workdir was removed before return copy')
            (self.original / 'returned-prefix').write_text('complete')
            (self.original / 'returned-direct-saves').write_text('complete')
            self.state.unlink()
            # Mapping removal is not the end of the owner's mount cleanup.
            time.sleep(0.1)
            if not (self.work / 'work').is_dir():
                errors.append('workdir removed while owner still releasing mounts')
            self.flag.unlink()
        timer = threading.Timer(0.2, complete_return)
        timer.start()
        self.addCleanup(timer.join)
        result = self.run_server()
        # Native cleanAndExit runs only after -w has returned.
        shutil.rmtree(self.work)
        timer.join()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(errors, [])
        self.assertTrue((self.original / 'returned-prefix').is_file())
        self.assertTrue((self.original / 'returned-direct-saves').is_file())
        log = (self.log_dir / 'wineserver-stop.log').read_text()
        self.assertIn('runtime_wait_begin', log)
        self.assertIn('runtime_wait_end', log)

    def test_killed_owner_releases_wait_without_deleting_unreturned_runtime(self):
        timer = threading.Timer(0.2, self.flag.unlink)
        timer.start()
        self.addCleanup(timer.join)
        result = self.run_server()
        timer.join()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.materialized / 'unique-save').read_text(), 'retained changes')
        self.assertTrue(self.state.exists())
        self.assertIn('owner-ended', (self.log_dir / 'wineserver-stop.log').read_text())

    def test_internal_wait_and_kill_only_requests_do_not_wait_for_their_parent(self):
        for args, prefix in ((('-w',), self.materialized), (('-k',), self.original)):
            with self.subTest(args=args, prefix=prefix):
                result = self.run_server(args, original=prefix)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(self.flag.exists())
                self.assertNotIn('runtime_wait_begin', (self.log_dir / 'wineserver-stop.log').read_text())

    def test_native_error_code_is_preserved_after_wait(self):
        timer = threading.Timer(0.2, self.flag.unlink)
        timer.start()
        self.addCleanup(timer.join)
        result = self.run_server(rc=9)
        timer.join()
        self.assertEqual(result.returncode, 9, result.stderr)


if __name__ == '__main__':
    unittest.main()
