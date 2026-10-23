from contextlib import redirect_stdout
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
    def test_legacy_dll_link_becomes_private_file_from_same_runner_and_arch(self):
        for arch in ('i386-windows', 'x86_64-windows'):
            with self.subTest(arch=arch), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                runners = root / 'runners'
                runner = runners / 'GE-Proton11-7-UMU'
                source = runner / 'files/lib/wine' / arch / 'ddraw.dll'
                source.parent.mkdir(parents=True)
                source.write_bytes(b'original DLL')
                windows = root / 'Game.wine/drive_c/windows/syswow64'
                windows.mkdir(parents=True)
                link = windows / 'ddraw.dll'
                old_target = runner / 'lib/wine' / arch / 'ddraw.dll'
                link.symlink_to(old_target)
                isolation.isolate(root / 'Game.wine', runners)
                self.assertFalse(link.is_symlink())
                self.assertEqual(link.read_bytes(), b'original DLL')
                link.write_bytes(b'private change')
                self.assertEqual(source.read_bytes(), b'original DLL')
                self.assertFalse(old_target.exists())

    def test_broken_dll_without_exact_local_replacement_is_refused(self):
        for layout in ('missing', 'wrong-arch', 'other-runner', 'outside-link', 'wrong-layout'):
            with self.subTest(layout=layout), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                runners = root / 'runners'
                runner = runners / 'GE-Proton11-7-UMU'
                runner.mkdir(parents=True)
                windows = root / 'Game.wine/drive_c/windows/syswow64'
                windows.mkdir(parents=True)
                target = runner / 'lib/wine/i386-windows/ddraw.dll'
                if layout == 'wrong-layout': target = runner / 'elsewhere/ddraw.dll'
                link = windows / 'ddraw.dll'
                link.symlink_to(target)
                candidate = runner / 'files/lib/wine/i386-windows/ddraw.dll'
                if layout == 'wrong-arch':
                    candidate = runner / 'files/lib/wine/x86_64-windows/ddraw.dll'
                if layout == 'other-runner':
                    candidate = runners / 'Other-UMU/files/lib/wine/i386-windows/ddraw.dll'
                candidate.parent.mkdir(parents=True)
                if layout == 'outside-link':
                    outside = root / 'external.dll'
                    outside.write_bytes(b'external')
                    candidate.symlink_to(outside)
                elif layout != 'missing':
                    candidate.write_bytes(b'different DLL')
                with self.assertRaisesRegex(ValueError, 'broken runner file link'):
                    isolation.isolate(root / 'Game.wine', runners)
                self.assertTrue(link.is_symlink())
                self.assertEqual(link.readlink(), target)

    def pe(self, machine):
        content = bytearray(134)
        content[:2] = b'MZ'
        content[60:64] = (128).to_bytes(4, 'little')
        content[128:132] = b'PE\0\0'
        content[132:134] = machine.to_bytes(2, 'little')
        return bytes(content)

    def test_removed_runner_links_use_selected_runner_same_file_and_arch_privately(self):
        for arch, machine in [('i386-windows', 0x14c), ('x86_64-windows', 0x8664)]:
            for layout in ('lib/wine', 'files/lib/wine', 'dist/lib/wine'):
                for name in ('winhlp32.exe', 'ddraw.dll'):
                    with self.subTest(arch=arch, layout=layout, name=name), tempfile.TemporaryDirectory() as folder:
                        root = Path(folder); runners = root / 'runners'
                        selected = runners / 'GE-Proton11-7-UMU'
                        replacement = selected / 'files/lib/wine' / arch / name
                        replacement.parent.mkdir(parents=True); replacement.write_bytes(self.pe(machine))
                        replacement.chmod(0o555)
                        prefix = root / 'Game.wine'; windows = prefix / 'drive_c/windows'; windows.mkdir(parents=True)
                        previous = runners / 'GE-Proton11-6-UMU' / layout / arch / name
                        link = windows / name; link.symlink_to(previous)
                        saves = root / 'saves'; saves.mkdir()
                        savedir = prefix / 'drive_c/save'; savedir.symlink_to(saves)
                        output = io.StringIO()
                        with redirect_stdout(output): isolation.isolate(prefix, runners, selected)
                        self.assertFalse(link.is_symlink())
                        self.assertEqual(link.read_bytes(), self.pe(machine))
                        self.assertTrue(link.stat().st_mode & 0o200)
                        link.write_bytes(b'private migration')
                        self.assertEqual(replacement.read_bytes(), self.pe(machine))
                        self.assertEqual(replacement.stat().st_mode & 0o777, 0o555)
                        self.assertFalse(previous.exists())
                        self.assertTrue(savedir.is_symlink())
                        self.assertIn('prefix_repaired_link=', output.getvalue())
                        self.assertIn(str(previous), output.getvalue())

    def test_selected_fallback_refuses_unknown_layout_wrong_arch_and_redirected_files(self):
        for invalid in ('wrong-arch', 'invalid-pe', 'outside-link', 'unknown-layout', 'wrong-name', 'absent'):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as folder:
                root = Path(folder); runners = root / 'runners'; selected = runners / 'current'
                replacement = selected / 'files/lib/wine/i386-windows/winhlp32.exe'
                replacement.parent.mkdir(parents=True)
                if invalid == 'outside-link':
                    outside = root / 'outside.exe'; outside.write_bytes(self.pe(0x14c))
                    replacement.symlink_to(outside)
                elif invalid != 'absent':
                    replacement.write_bytes(b'not PE' if invalid == 'invalid-pe' else self.pe(0x8664 if invalid == 'wrong-arch' else 0x14c))
                prefix = root / 'Game.wine'; windows = prefix / 'drive_c/windows'; windows.mkdir(parents=True)
                previous = runners / 'deleted/files/lib/wine/i386-windows/winhlp32.exe'
                if invalid == 'unknown-layout': previous = runners / 'deleted/unknown/i386-windows/winhlp32.exe'
                link = windows / ('different.exe' if invalid == 'wrong-name' else 'winhlp32.exe')
                link.symlink_to(previous)
                with self.assertRaisesRegex(ValueError, 'broken runner file link'):
                    isolation.isolate(prefix, runners, selected)
                self.assertTrue(link.is_symlink())
                self.assertEqual(link.readlink(), previous)
                self.assertFalse(list(windows.glob('.umu-detach-*')))

    def test_preflight_failure_leaves_all_prefix_links_and_hardlinks_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); runners = root / 'runners'; runners.mkdir()
            original = runners / 'private.dll'; original.write_bytes(b'unchanged')
            prefix = root / 'Game.wine'; windows = prefix / 'drive_c/windows'; windows.mkdir(parents=True)
            valid = windows / 'valid.dll'; valid.symlink_to(original)
            shared = windows / 'shared.dll'; shared.hardlink_to(original)
            inode = shared.stat().st_ino
            broken = windows / 'winhlp32.exe'; broken.symlink_to(runners / 'missing/files/lib/wine/i386-windows/winhlp32.exe')
            with self.assertRaisesRegex(ValueError, 'broken runner file link'):
                isolation.isolate(prefix, runners)
            self.assertTrue(valid.is_symlink())
            self.assertTrue(broken.is_symlink())
            self.assertEqual(shared.stat().st_ino, inode)
            self.assertEqual(original.read_bytes(), b'unchanged')
            self.assertFalse(list(windows.glob('.umu-detach-*')))

    def test_existing_old_runner_file_is_preserved_instead_of_using_selected_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); runners = root / 'runners'
            selected = runners / 'current'; selected.mkdir(parents=True)
            previous = runners / 'old/files/lib/wine/i386-windows/winhlp32.exe'
            previous.parent.mkdir(parents=True); previous.write_bytes(b'old valid contents')
            candidate = selected / 'files/lib/wine/i386-windows/winhlp32.exe'
            candidate.parent.mkdir(parents=True); candidate.write_bytes(self.pe(0x14c))
            prefix = root / 'Game.wine'; windows = prefix / 'drive_c/windows'; windows.mkdir(parents=True)
            link = windows / 'winhlp32.exe'; link.symlink_to(previous)
            isolation.isolate(prefix, runners, selected)
            self.assertEqual(link.read_bytes(), b'old valid contents')
            self.assertEqual(previous.read_bytes(), b'old valid contents')

    def test_selected_runner_outside_managed_root_or_alias_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); runners = root / 'runners'; runners.mkdir()
            external = root / 'external'; external.mkdir()
            alias = runners / 'alias'; alias.symlink_to(external, target_is_directory=True)
            prefix = root / 'Game.wine'; prefix.mkdir()
            for selected in (external, alias):
                with self.subTest(selected=selected), self.assertRaisesRegex(ValueError, 'selected runner'):
                    isolation.isolate(prefix, runners, selected)

    def test_managed_root_can_itself_be_a_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); physical = root / 'disk/runners'; physical.mkdir(parents=True)
            runners = root / 'custom'; runners.symlink_to(physical, target_is_directory=True)
            selected = runners / 'current'; selected.mkdir()
            prefix = root / 'Game.wine'; prefix.mkdir()
            isolation.isolate(prefix, runners, selected)

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
