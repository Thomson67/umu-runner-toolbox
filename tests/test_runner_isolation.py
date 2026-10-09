import hashlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


isolation = module('isolation', 'toolbox/overlay/umu-batocera/prefix-isolation.py')
repair = module('repair', 'toolbox/helpers/repair-runner-dlls.py')


class IsolationTests(unittest.TestCase):
    def test_maintenance_detaches_before_wine_and_waits_before_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            custom = root / 'custom'; custom.mkdir()
            current = custom / 'current-UMU'
            old = custom / 'old-UMU'
            for runner in (current, old):
                (runner / 'umu-batocera').mkdir(parents=True)
                (runner / 'proton').write_bytes(b'good')
                (runner / 'umu-batocera/integrity.sha256').write_text(
                    f'{hashlib.sha256(b"good").hexdigest()}  proton\n')
            original = old / 'kernel32.dll'; original.write_bytes(b'original')
            prefix = root / 'prefix'
            windows = prefix / 'drive_c/windows/system32'; windows.mkdir(parents=True)
            (prefix / 'system.reg').touch(); (prefix / 'user.reg').touch()
            linked = windows / 'kernel32.dll'; linked.symlink_to(original)
            helper = current / 'umu-batocera/prefix-isolation.py'
            helper.write_text((ROOT / 'toolbox/overlay/umu-batocera/prefix-isolation.py').read_text())
            binaries = current / 'files/bin'; binaries.mkdir(parents=True)
            wine = binaries / 'wine'
            wine.write_text('#!/bin/bash\necho wine >>"$TRACE"\nprintf changed >"$WINEPREFIX/drive_c/windows/system32/kernel32.dll"\n')
            wine.chmod(0o755)
            server = binaries / 'wineserver'
            server.write_text('#!/bin/bash\necho "wait:$*" >>"$TRACE"\n')
            server.chmod(0o755)
            script = (ROOT / 'toolbox/overlay/bin/wine').read_text()
            protection = script[script.index('UMU_PROTECTED_MOUNTS=()'):script.index('unprotect_umu_runners()')]
            protection = protection.replace('/userdata/system/wine/custom', str(custom))
            prefix_check = script[script.index('is_prefix_root()'):script.index('find_embedded_prefix()')]
            fallback = script[script.index('if [ -z "$exe" ]; then'):script.index('args=("$@")')]
            trace = root / 'trace'
            setup = f'''set -u
export TRACE="{trace}" WINEPREFIX="{prefix}"
RUNNER_DIR="{current}"; REAL_WINE="{wine}"; ORIGINAL_WINEPREFIX="$WINEPREFIX"; LOG=/dev/null; exe=""
log() {{ :; }}
mountpoint() {{ return 1; }}
findmnt() {{ return 0; }}
mount() {{ echo protect >>"$TRACE"; }}
unprotect_umu_runners() {{ echo cleanup >>"$TRACE"; }}
'''
            result = subprocess.run(['bash', '-c', setup + protection + prefix_check + fallback,
                                     '_', 'wineboot.exe'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(original.read_bytes(), b'original')
            self.assertEqual(linked.read_bytes(), b'changed')
            events = trace.read_text().splitlines()
            self.assertEqual(events[-3:], ['wine', 'wait:-w', 'cleanup'])
            self.assertIn('protect', events[:-3])

    def test_runner_links_and_hardlinks_become_private_save_links_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runners = root / 'runners'; runners.mkdir()
            original = runners / 'kernel32.dll'; original.write_bytes(b'original')
            prefix = root / 'prefix'
            windows = prefix / 'drive_c/windows/system32'; windows.mkdir(parents=True)
            linked = windows / 'kernel32.dll'; linked.symlink_to(original)
            shared = windows / 'shared.dll'; shared.hardlink_to(original)
            saves = root / 'saves'; saves.mkdir()
            save_link = prefix / 'drive_c/save'; save_link.symlink_to(saves)
            isolation.isolate(prefix, runners)
            self.assertFalse(linked.is_symlink())
            linked.write_bytes(b'new'); shared.write_bytes(b'new')
            self.assertEqual(original.read_bytes(), b'original')
            self.assertTrue(save_link.is_symlink())

    def test_runner_directory_alias_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runners = root / 'runners'; runners.mkdir()
            windows = root / 'prefix/drive_c/windows'; windows.mkdir(parents=True)
            (windows / 'system32').symlink_to(runners)
            with self.assertRaises(ValueError):
                isolation.isolate(root / 'prefix', runners)

    def test_corrupt_unrelated_runner_protected_but_selected_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, valid in [('bad-UMU', False), ('good-UMU', True)]:
                runner = root / name
                (runner / 'umu-batocera').mkdir(parents=True)
                (runner / 'proton').write_bytes(b'good' if valid else b'bad')
                sha = hashlib.sha256(b'good').hexdigest()
                (runner / 'umu-batocera/integrity.sha256').write_text(f'{sha}  proton\n')
            script = (ROOT / 'toolbox/overlay/bin/wine').read_text()
            functions = script[script.index('UMU_PROTECTED_MOUNTS=()'):script.index('unprotect_umu_runners()')]
            functions = functions.replace('/userdata/system/wine/custom', str(root))
            setup = 'set -u\nlog() { echo "$*"; }; mountpoint() { return 1; }; mount() { return 0; }; findmnt() { return 0; }; LOG=/dev/null\n'
            for selected, expected in [('good-UMU', 0), ('bad-UMU', 90)]:
                result = subprocess.run(['bash', '-c', setup + f'RUNNER_DIR="{root / selected}"\n' + functions + '\nprotect_all_umu_runners_ro'], capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)
                if not expected:
                    self.assertIn(f'runner_protected_ro={root / "bad-UMU"}', result.stdout)

    def test_repair_verifies_all_archive_dlls_before_modifying(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runner = root / 'bad-UMU'
            (runner / 'umu-batocera').mkdir(parents=True)
            name = 'files/lib/wine/x86_64-windows/kernel32.dll'
            dll = runner / name; dll.parent.mkdir(parents=True); dll.write_bytes(b'damaged')
            manifest = runner / 'umu-batocera/integrity.sha256'
            manifest.write_text(f'{hashlib.sha256(b"original").hexdigest()}  {name}\n')
            archive = root / 'source.tar.xz'
            for content, valid in [(b'wrong', False), (b'original', True)]:
                with tarfile.open(archive, 'w:xz') as bundle:
                    entry = tarfile.TarInfo('upstream/' + name); entry.size = len(content)
                    bundle.addfile(entry, io.BytesIO(content))
                if valid:
                    repair.repair(runner, archive)
                else:
                    with self.assertRaises(ValueError):
                        repair.repair(runner, archive, apply=True)
                self.assertEqual(dll.read_bytes(), b'damaged')
                self.assertIn(hashlib.sha256(b'original').hexdigest(), manifest.read_text())


if __name__ == '__main__':
    unittest.main()
