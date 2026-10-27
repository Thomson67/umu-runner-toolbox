#!/usr/bin/env python3
"""Inspect and explicitly discard individual owned, idle UMU working copies."""
import argparse
from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

HELPER = Path(__file__).resolve().parents[1] / 'overlay/umu-batocera/runtime-prefix.py'
SPEC = importlib.util.spec_from_file_location('runtime_prefix', HELPER)
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


def clean(value):
    return ''.join(c if c.isprintable() else ' ' for c in str(value))


def human_size(size):
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if size < 1024 or unit == 'TiB':
            return f'{size:.1f} {unit}'
        size /= 1024


def tree_revision(prefix):
    """Bind explicit discard to the files reviewed, without following links."""
    digest = hashlib.sha256()
    for folder, dirs, files in os.walk(prefix, followlinks=False):
        dirs.sort()
        for path in [Path(folder)] + [Path(folder) / name for name in sorted(dirs + files)]:
            s = path.lstat()
            digest.update(json.dumps([str(path.relative_to(prefix)), s.st_dev, s.st_ino,
                                     s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns]).encode())
    return digest.hexdigest()


class RecoveryManager:
    def __init__(self, base=Path('/userdata/system/umu')):
        self.store = runtime.PrefixStore(base)

    @contextmanager
    def locked(self):
        lock = self.store.base / '.materialized-prefix.lock'
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if not self.store.idle():
                raise ValueError('UMU prefix still active or mounted')
            yield
        finally:
            os.close(fd)

    def inventory(self):
        result = []
        for prefix in sorted(self.store.root.iterdir()):
            if not prefix.is_dir() or prefix.is_symlink():
                continue
            prefix = self.store.path(prefix)
            journal = self.store.record(prefix)
            if journal.is_symlink():
                journal_revision = 'redirected'
            elif journal.exists():
                journal_revision = hashlib.sha256(journal.read_bytes()).hexdigest()
            else:
                journal_revision = 'absent'
            try:
                data = self.store.read(prefix)
                known = True
            except (OSError, ValueError, KeyError, TypeError):
                data, known = {}, False
            if data.get('phase') == 'disposable':
                continue
            size = subprocess.run(['du', '-sx', '-B1', '--', str(prefix)],
                                  check=True, capture_output=True, text=True)
            size = int(size.stdout.split()[0])
            stamp = journal.stat().st_mtime if known else prefix.stat().st_mtime
            source = data.get('source', '')
            resumable = (known and data.get('phase') in ('running', 'recovery')
                         and bool(data.get('source_identity'))
                         and data.get('reason') not in ('source-changed', 'unverified-source')
                         and bool(data.get('game_dir')) and bool(source)
                         and (prefix / 'system.reg').is_file()
                         and (prefix / 'user.reg').is_file()
                         and (prefix / 'drive_c').is_dir())
            # Bind selection to the reviewed journal and directory instance.
            # A session started while a confirmation dialog was open must not
            # let that old confirmation discard its newer recovery copy.
            revision = json.dumps([prefix.name, tree_revision(prefix), data, stamp, journal_revision], sort_keys=True)
            result.append(dict(id=hashlib.sha256(revision.encode()).hexdigest(),
                               prefix=str(prefix), source=source,
                               game=Path(source).name if source else prefix.name,
                               size=size, date=datetime.fromtimestamp(stamp).strftime('%Y-%m-%d %H:%M'),
                               updated_at=stamp, phase=data.get('phase', 'unknown'),
                               runner=data.get('runner', ''), reason=data.get('reason', '') or
                               ('interrupted-or-unsynchronized' if known else 'unknown-journal'),
                               log=data.get('log', ''), resumable=bool(resumable), known=known))
        return result

    def selected(self, identity):
        if len(identity) != 64 or any(c not in '0123456789abcdef' for c in identity):
            raise ValueError('invalid recovery identity')
        for item in self.inventory():
            if item['id'] == identity:
                return item
        raise ValueError('recovery copy no longer exists')

    def discard(self, identity):
        # Caller holds the session lock. Revalidate ownership and activity at
        # action time rather than trusting the menu's earlier listing.
        if not self.store.idle():
            raise ValueError('UMU prefix still active or mounted')
        item = self.selected(identity)
        prefix = self.store.path(item['prefix'])
        # Explicit confirmation authorizes discarding an untracked local copy,
        # never an external/redirected journal or an unchecked active mount.
        journal = self.store.record(prefix)
        if journal.is_symlink():
            raise ValueError('redirected runtime journal; manual review required')
        if runtime.mounted(prefix):
            raise ValueError('UMU prefix still mounted')
        shutil.rmtree(prefix)
        journal.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('list', 'details', 'discard', 'fingerprint'))
    parser.add_argument('identity', nargs='?')
    args = parser.parse_args()
    manager = RecoveryManager()
    with manager.locked():
        if args.action in ('list', 'fingerprint'):
            entries = manager.inventory()
            if args.action == 'fingerprint':
                if entries:
                    print(hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest())
            else:
                for item in entries:
                    print(item['id'] + '\t' + clean(item['game']) + ' | ' + human_size(item['size']) + ' | ' + item['date'])
        elif args.action == 'details':
            item = manager.selected(args.identity or '')
            for value in (item['game'], item['source'], item['prefix'], human_size(item['size']),
                          item['date'], item['runner'], item['reason'],
                          '1' if item['resumable'] else '0', item['log'], '1' if item['known'] else '0'):
                print(clean(value) or '-')
        else:
            manager.discard(args.identity or '')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Recovery action refused: {clean(error)}')
