#!/usr/bin/env python3
"""Detach Windows files pointing into runners without traversing save links."""
import argparse
import os
from pathlib import Path
import shutil
import tempfile


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
            if not path.is_file():
                raise ValueError(f'broken runner file link: {path}')
            origin = path.resolve()
            fd, temporary = tempfile.mkstemp(prefix='.umu-detach-', dir=path.parent)
            os.close(fd)
            try:
                shutil.copy2(path, temporary)
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
