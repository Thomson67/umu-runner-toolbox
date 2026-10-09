#!/usr/bin/env python3
"""Restore only mismatching Wine DLLs verified against the existing manifest."""
import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile
import time


def digest(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def repair(runner, archive, apply=False):
    runner = Path(runner).resolve(strict=True)
    manifest = runner / 'umu-batocera/integrity.sha256'
    expected = {}
    for line in manifest.read_text().splitlines():
        sha, relative = line.split(None, 1)
        relative = relative.lstrip('*')
        path = PurePosixPath(relative)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('unsafe manifest path')
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('invalid digest')
        expected[relative] = sha
    bad = {name: sha for name, sha in expected.items()
           if not (runner / name).is_file() or digest(runner / name) != sha}
    if not bad:
        print('Runner already matches the manifest.'); return
    for name in bad:
        parts = PurePosixPath(name).parts
        if (len(parts) != 5 or parts[:3] != ('files', 'lib', 'wine')
                or parts[3] not in ('x86_64-windows', 'i386-windows')
                or not parts[4].endswith('.dll')):
            raise ValueError(f'non-DLL integrity failure; repair refused: {name}')
        destination = runner / name
        if destination.is_symlink() or not destination.parent.resolve().is_relative_to(runner):
            raise ValueError(f'unsafe runner destination: {name}')
    # Record the current fingerprints and compare them with other distributions.
    for name in bad:
        damaged = runner / name
        if damaged.is_file():
            fingerprint = digest(damaged)
            print(f'before {fingerprint} {name}', flush=True)
            for peer in runner.parent.iterdir():
                if peer == runner or not peer.is_dir():
                    continue
                for candidate in (peer / name, peer / name.removeprefix('files/')):
                    if candidate.is_file() and digest(candidate) == fingerprint:
                        print(f'matching_source={candidate}', flush=True)
    with tempfile.TemporaryDirectory(prefix='.verified-dlls-', dir=runner.parent) as temporary:
        prepared = {}
        with tarfile.open(archive, 'r|*') as bundle:
            for entry in bundle:
                parts = PurePosixPath(entry.name).parts
                if '..' in parts or entry.name.startswith('/'):
                    continue
                for name, sha in bad.items():
                    if tuple(parts[-5:]) != PurePosixPath(name).parts:
                        continue
                    if not entry.isfile() or name in prepared or entry.size > 128 * 1024 * 1024:
                        raise ValueError(f'unsafe or duplicate archive DLL: {entry.name}')
                    target = Path(temporary) / str(len(prepared))
                    with bundle.extractfile(entry) as source, target.open('wb') as output:
                        shutil.copyfileobj(source, output)
                    if digest(target) != sha:
                        raise ValueError(f'archive DLL does not match original manifest: {name}')
                    os.chmod(target, entry.mode & 0o777)
                    prepared[name] = target
        if set(prepared) != set(bad):
            raise ValueError('archive does not contain every required original DLL')
        print(f'Verified {len(prepared)} original DLLs. Manifest remains unchanged.')
        if not apply:
            return
        # Refuse runtime/host mounts and any active Wine process before writing.
        if subprocess.run(['findmnt', '-rn', '-M', str(runner)], stdout=subprocess.DEVNULL).returncode == 0:
            raise ValueError('runner mounted; close the game and release protection first')
        for process in Path('/proc').glob('[0-9]*/comm'):
            try:
                name = process.read_text().strip().lower()
            except OSError:
                continue
            if name.startswith(('wine', 'wineserver')):
                raise ValueError(f'Wine process active: {name}')
        backup = runner.parent.parent / 'runner-repair-backups' / f'{runner.name}-{time.time_ns()}'
        backup.mkdir(parents=True)
        shutil.copy2(manifest, backup / 'integrity.sha256')
        for name in bad:
            current = runner / name
            if current.exists():
                saved = backup / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current, saved)
        # Each replacement is atomic and every original is already backed up.
        for name, source in prepared.items():
            destination = runner / name
            fd, staged = tempfile.mkstemp(prefix='.repair-', dir=destination.parent)
            os.close(fd)
            try:
                shutil.copy2(source, staged)
                os.replace(staged, destination)
            finally:
                if os.path.exists(staged):
                    os.unlink(staged)
        if any(digest(runner / name) != sha for name, sha in expected.items()):
            raise ValueError(f'post-repair verification failed; backup: {backup}')
        print(f'Repair successful. Backup: {backup}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('runner')
    parser.add_argument('archive')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    repair(args.runner, args.archive, args.apply)
