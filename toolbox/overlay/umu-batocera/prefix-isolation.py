#!/usr/bin/env python3
"""Detach Windows files pointing into runners without traversing save links."""
import argparse
import os
from pathlib import Path
import shutil
import tempfile


def runner_file_source(path, runners):
    origin = path.resolve()
    if origin.is_file():
        return origin
    # Batocera prefixes may retain Wine-layout links, whereas managed Proton
    # distributions store these DLLs under files/lib/wine. Resolve only this
    # exact layout difference, within the same referenced runner and arch.
    parts = origin.relative_to(runners).parts
    if (len(parts) == 5 and parts[1:3] == ('lib', 'wine')
            and parts[3] in ('i386-windows', 'x86_64-windows')
            and parts[4].endswith('.dll')):
        runner = runners / parts[0]
        candidate = runner / 'files' / Path(*parts[1:])
        if (runner.resolve() == runner and candidate.is_file()
                and candidate.resolve() == candidate):
            return candidate.resolve()
    raise ValueError(f'broken runner file link: {path} -> {origin}')


def isolate(prefix, runners):
    prefix = Path(prefix).resolve(strict=True)
    runners = Path(runners).resolve(strict=True)
    if prefix.is_relative_to(runners):
        raise ValueError('prefix is inside the runner tree')
    windows = prefix / 'drive_c/windows'
    if not windows.exists():
        return
    if not windows.resolve().is_relative_to(prefix):
        raise ValueError('Windows directory escapes the prefix')
    for root, dirs, files in os.walk(windows, followlinks=False):
        for name in dirs:
            path = Path(root) / name
            if path.is_symlink() and path.resolve().is_relative_to(runners):
                raise ValueError(f'runner directory link requires manual repair: {path}')
        for name in files:
            path = Path(root) / name
            linked = path.is_symlink() and path.resolve().is_relative_to(runners)
            shared = not path.is_symlink() and path.stat().st_nlink > 1
            if not linked and not shared:
                continue
            origin = runner_file_source(path, runners) if linked else path.resolve()
            fd, temporary = tempfile.mkstemp(prefix='.umu-detach-', dir=path.parent)
            os.close(fd)
            try:
                shutil.copy2(origin, temporary)
                os.chmod(temporary, os.stat(temporary).st_mode | 0o200)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            print(f'prefix_detached={path} previous_target={origin} hardlink={int(shared)}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('prefix')
    parser.add_argument('--runners', default='/userdata/system/wine/custom')
    args = parser.parse_args()
    isolate(args.prefix, args.runners)
