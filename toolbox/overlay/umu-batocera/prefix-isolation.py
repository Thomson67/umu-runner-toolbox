#!/usr/bin/env python3
"""Detach Windows files pointing into runners without traversing save links."""
import argparse
import os
from pathlib import Path
import shutil
import tempfile


def pe_machine(path):
    """Read the PE architecture before using a different runner's replacement."""
    with path.open('rb') as source:
        header = source.read(64)
        if len(header) != 64 or header[:2] != b'MZ':
            return None
        offset = int.from_bytes(header[60:64], 'little')
        if offset < 64 or offset > 16 * 1024 * 1024:
            return None
        source.seek(offset)
        pe = source.read(6)
        return int.from_bytes(pe[4:6], 'little') if pe[:4] == b'PE\0\0' and len(pe) == 6 else None


def runner_file_source(path, runners, selected_runner=None):
    origin = path.resolve()
    if origin.is_file():
        return origin
    parts = origin.relative_to(runners).parts
    layout = parts[1:]
    if layout[:1] in (('files',), ('dist',)):
        layout = layout[1:]
    # The architecture directory contains PE modules with many extensions:
    # themes (.msstyles), drivers (.drv/.sys), control panels (.cpl), etc.
    # For a different runner, the PE header below is authoritative.
    recognized = (len(layout) == 4 and layout[:2] == ('lib', 'wine')
                  and layout[2] in ('i386-windows', 'x86_64-windows')
                  and layout[3].casefold() == path.name.casefold())
    if recognized:
        runner = runners / parts[0]
        # Preserve the existing same-runner Wine -> Proton layout repair.
        candidate = runner / 'files' / Path(*layout)
        if (parts[1:3] == ('lib', 'wine') and runner.resolve() == runner
                and candidate.is_file() and candidate.resolve() == candidate):
            return candidate
        if selected_runner is not None:
            expected = 0x14c if layout[2] == 'i386-windows' else 0x8664
            for base in (selected_runner / 'files', selected_runner, selected_runner / 'dist'):
                candidate = base / Path(*layout)
                if (candidate.is_file() and candidate.resolve() == candidate
                        and pe_machine(candidate) == expected):
                    return candidate
    raise ValueError(f'broken runner file link: {path} -> {origin}')


def missing_runner_font(path, windows, runners):
    """Only identify dangling font links in Wine's Fonts directory."""
    if path.parent != windows / 'Fonts' or path.suffix.lower() not in ('.ttf', '.ttc', '.otf'):
        return False
    origin = path.resolve()
    if origin.exists() or not origin.is_relative_to(runners):
        return False
    parts = origin.relative_to(runners).parts
    layout = parts[1:]
    if layout[:1] in (('files',), ('dist',)):
        layout = layout[1:]
    return (layout[:-1] in (('share', 'fonts'), ('share', 'wine', 'fonts'))
            and layout[-1].casefold() == path.name.casefold())


def replacement_font(path, selected_runner):
    for base in (selected_runner / 'files', selected_runner, selected_runner / 'dist'):
        for directory in ('share/fonts', 'share/wine/fonts'):
            candidate = base / directory / path.name
            if candidate.is_file() and candidate.resolve() == candidate:
                with candidate.open('rb') as source:
                    signature = source.read(4)
                if signature in (b'\x00\x01\x00\x00', b'OTTO', b'true', b'typ1', b'ttcf'):
                    return candidate
                raise ValueError(f'invalid replacement font: {candidate}')
    return None


def isolate(prefix, runners, selected_runner=None):
    prefix = Path(prefix).resolve(strict=True)
    runners = Path(runners).resolve(strict=True)
    if selected_runner is not None:
        selected_path = Path(selected_runner).absolute()
        selected_runner = selected_path.resolve(strict=True)
        if (selected_path.is_symlink() or selected_runner.parent != runners or not selected_runner.is_dir()):
            raise ValueError('selected runner must be a real direct child of the runner tree')
    if prefix.is_relative_to(runners):
        raise ValueError('prefix is inside the runner tree')
    windows = prefix / 'drive_c/windows'
    if not windows.exists():
        return
    if not windows.resolve().is_relative_to(prefix):
        raise ValueError('Windows directory escapes the prefix')
    plan, problems = [], []
    def scan_error(error):
        problems.append(str(error))
    for root, dirs, files in os.walk(windows, followlinks=False, onerror=scan_error):
        for name in dirs:
            path = Path(root) / name
            try:
                if path.is_symlink() and path.resolve().is_relative_to(runners):
                    problems.append(f'runner directory link requires manual repair: {path}')
            except (OSError, RuntimeError) as error:
                problems.append(f'{path}: {error}')
        for name in files:
            path = Path(root) / name
            try:
                linked = path.is_symlink() and path.resolve().is_relative_to(runners)
                shared = not path.is_symlink() and path.stat().st_nlink > 1
                if not linked and not shared:
                    continue
                if linked and selected_runner is not None and missing_runner_font(path, windows, runners):
                    # An absent font link has no data to preserve. If the current
                    # runner does not ship it, let Wine use its font fallbacks.
                    origin = replacement_font(path, selected_runner)
                else:
                    origin = runner_file_source(path, runners, selected_runner) if linked else path.resolve()
                plan.append((path, origin, shared, path.resolve()))
            except (OSError, ValueError, RuntimeError) as error:
                problems.append(str(error))
    if problems:
        raise ValueError(f'prefix isolation preflight failed ({len(problems)} unresolved entries):\n'
                         + '\n'.join(problems))
    # Validate every link before detaching files. An unknown missing component
    # must not leave a partially repaired maintenance prefix.
    for path, origin, shared, previous in plan:
        if origin is None:
            path.unlink()
            print(f'prefix_removed_stale_font_link={path} previous_target={previous}', flush=True)
            continue
        fd, temporary = tempfile.mkstemp(prefix='.umu-detach-', dir=path.parent)
        os.close(fd)
        try:
            shutil.copy2(origin, temporary)
            os.chmod(temporary, os.stat(temporary).st_mode | 0o200)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        if previous != origin:
            print(f'prefix_repaired_link={path} previous_target={previous} replacement={origin}', flush=True)
        print(f'prefix_detached={path} previous_target={previous} hardlink={int(shared)}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('prefix')
    parser.add_argument('--runners', default='/userdata/system/wine/custom')
    parser.add_argument('--selected-runner')
    args = parser.parse_args()
    isolate(args.prefix, args.runners, args.selected_runner)
