#!/usr/bin/env python3
"""Own temporary prefixes; never reap an active or unsynchronized session.

Callers hold /userdata/system/umu/.materialized-prefix.lock across the session.
Journal records live outside prefixes so they are not copied into Wine bottles.
"""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time


def process_token(pid):
    try:
        start = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        return boot + ':' + start
    except (OSError, IndexError):
        return ''


def mounted(path):
    """Check all visible mount namespaces, including a surviving container."""
    seen = set()
    suffix = '/umu/materialized-prefixes/' + path.name
    for process in Path('/proc').glob('[0-9]*'):
        try:
            namespace = (process / 'ns/mnt').stat().st_ino
            if namespace in seen:
                continue
            lines = (process / 'mountinfo').read_text().splitlines()
        except (FileNotFoundError, ProcessLookupError):
            continue
        except OSError as error:
            if error.errno == errno.EINVAL and not (process / 'ns/mnt').exists():
                continue
            return True  # Cannot prove that deleting it is safe.
        seen.add(namespace)
        for line in lines:
            fields = line.split()
            if len(fields) < 5:
                return True
            root, target = (re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), x)
                            for x in fields[3:5])
            if (target == str(path) or target.startswith(str(path) + '/')
                    or root == str(path) or root.startswith(str(path) + '/')
                    or root.endswith(suffix) or suffix + '/' in root):
                return True
    return False


def file_identity(path):
    """Cheap generation check: replacement and in-place writes change this."""
    path = Path(path).resolve(strict=True)
    s = path.stat()
    return [str(path), s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def source_identity(source, runner='', mode='0', lowerdir=''):
    """Verify the real archive, not the ephemeral /run/wine mount identity.

    Do not hash multi-GB archives. The backing file's inode/size/nanosecond
    timestamps identify its generation; registry/autorun contents also detect
    a changed bottle. Missing evidence disables automatic reuse.
    """
    source = Path(source)
    try:
        compressed = bool(lowerdir) or source.suffix.lower() in ('.wsquashfs', '.wtgz')
        if compressed:
            if not lowerdir:
                return None
            device = subprocess.check_output(
                ['findmnt', '-n', '-o', 'SOURCE', '-T', str(lowerdir)], text=True).strip().split('[', 1)[0]
            if not re.fullmatch(r'/dev/loop[0-9]+', device):
                return None
            backing = Path('/sys/class/block', Path(device).name, 'loop/backing_file').read_text().strip()
            backing = re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), backing)
            generation = file_identity('/' + backing.lstrip('/'))
        else:
            generation = file_identity(source)
        registry = {}
        for name in ('system.reg', 'user.reg', 'userdef.reg', 'autorun.cmd'):
            path = source / name
            registry[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        runner_identity = None
        if runner:
            root = Path(runner).resolve(strict=True)
            runner_identity = [str(root), [file_identity(root / name) for name in
                ('proton', 'version', 'toolmanifest.vdf', 'umu-batocera/runtime-prefix.py')
                if (root / name).is_file()]]
        payload = [generation, registry, runner_identity, str(mode)]
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


class PrefixStore:
    def __init__(self, base=Path('/userdata/system/umu')):
        self.base = Path(base)
        self.root = self.base / 'materialized-prefixes'
        self.records = self.base / 'runtime-prefix-state'
        for directory in (self.base, self.root, self.records):
            directory.mkdir(parents=True, exist_ok=True)
            if directory.is_symlink() or directory.resolve() != directory:
                raise ValueError(f'redirected runtime directory: {directory}')

    def path(self, prefix):
        prefix = Path(prefix)
        if prefix.parent != self.root or not prefix.name or prefix.is_symlink():
            raise ValueError(f'invalid runtime prefix: {prefix}')
        if prefix.exists() and prefix.resolve() != prefix:
            raise ValueError(f'redirected runtime prefix: {prefix}')
        return prefix

    def record(self, prefix):
        return self.records / (hashlib.sha256(prefix.name.encode()).hexdigest() + '.json')

    def read(self, prefix):
        record = self.record(prefix)
        if record.is_symlink():
            raise ValueError('redirected runtime journal')
        data = json.loads(record.read_text())
        if (not isinstance(data, dict) or data.get('version') != 1
                or data.get('prefix') != str(prefix)
                or data.get('phase') not in ('preparing', 'running', 'disposable', 'recovery')):
            raise ValueError('invalid runtime journal')
        return data

    def write(self, prefix, data):
        if self.record(prefix).is_symlink():
            raise ValueError('redirected runtime journal')
        data['updated_at'] = time.time()
        fd, temporary = tempfile.mkstemp(dir=self.records, prefix='.state-')
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(data, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.record(prefix))
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def collect(self):
        for record in self.records.glob('*.json'):
            try:
                if record.is_symlink():
                    continue
                raw = json.loads(record.read_text())
                prefix = self.path(raw['prefix'])
                if record != self.record(prefix):
                    continue
                data = self.read(prefix)
                pid = int(data.get('pid', 0))
                if pid and process_token(pid) == data.get('process_token'):
                    continue
                if not prefix.exists() and not mounted(prefix):
                    record.unlink()
                    continue
                if data['phase'] not in ('disposable', 'preparing') or mounted(prefix):
                    print(f'runtime_retained={prefix} phase={data["phase"]}', flush=True)
                    continue
                if prefix.exists():
                    shutil.rmtree(prefix)
                record.unlink()
                print(f'runtime_removed={prefix}', flush=True)
            except (OSError, ValueError, KeyError, TypeError):
                # Unknown/invalid journals never authorize recursive deletion.
                continue

    def begin(self, prefix, source, pid, game_dir='', runner='', log='', runner_root='', mode='0', lowerdir='', source_view=''):
        prefix = self.path(prefix)
        self.collect()
        if mounted(prefix):
            raise ValueError(f'runtime still mounted: {prefix}')
        identity = source_identity(source_view or source, runner_root, mode, lowerdir)
        if self.record(prefix).exists():
            data = self.read(prefix)
            old_pid = int(data.get('pid', 0))
            if old_pid and process_token(old_pid) == data.get('process_token'):
                raise ValueError(f'runtime owner still active: {prefix}')
            if (data['phase'] not in ('running', 'recovery') or data.get('source') != str(source)
                    or not game_dir or data.get('game_dir') != game_dir
                    or not (prefix / 'system.reg').is_file()
                    or not (prefix / 'user.reg').is_file()
                    or not (prefix / 'drive_c').is_dir()):
                raise ValueError(f'unsynchronized runtime retained; recovery required: {prefix}')
            if (identity and data.get('source_identity') == identity
                    and data.get('runner', '') == runner):
                token = process_token(pid)
                if not token:
                    raise ValueError('runtime owner is not alive')
                # Includes HK+Start/SIGKILL: resume only the verified generation.
                data.update(pid=pid, process_token=token, phase='running')
                if log: data['log'] = log
                self.write(prefix, data)
                print(f'runtime_reused_after_interruption={prefix}', flush=True)
                return True
            # A rollback/replacement at the same path must start fresh. Keep
            # unique old changes separately, never write them into the new game.
            reason = 'source-changed' if identity and data.get('source_identity') else 'unverified-source'
            self.retain_separately(prefix, data, reason)
        if prefix.exists():
            # Older integrations left no ownership/synchronization journal.
            # Preserve this one legacy copy rather than silently discarding it.
            legacy = prefix.with_name('.legacy-' + hashlib.sha256(prefix.name.encode()).hexdigest()[:16]
                                      + '-' + str(time.time_ns()))
            data = dict(version=1, prefix=str(legacy), source=str(source), pid=0,
                        process_token='', phase='recovery', reason='legacy-untracked')
            self.write(legacy, data)
            prefix.rename(legacy)
            print(f'runtime_legacy_retained={legacy}', flush=True)
        data = dict(version=1, prefix=str(prefix), source=str(source), pid=pid, runner=runner, log=log,
                    game_dir=game_dir, source_identity=identity,
                    process_token=process_token(pid), phase='preparing')
        if not data['process_token']:
            raise ValueError('runtime owner is not alive')
        self.write(prefix, data)
        prefix.mkdir()
        return False

    def retain_separately(self, prefix, data, reason):
        retained = prefix.with_name('.retained-' + hashlib.sha256(prefix.name.encode()).hexdigest()[:16]
                                    + '-' + str(time.time_ns()))
        data.update(prefix=str(retained), pid=0, process_token='', phase='recovery', reason=reason)
        self.write(retained, data)
        prefix.rename(retained)
        self.record(prefix).unlink()
        print(f'runtime_previous_generation_retained={retained} reason={reason}', flush=True)

    def direct_save(self, prefix, pid, path, source, resume=False):
        """Record before mutation; after SIGKILL only this exact pair may resume."""
        prefix = self.path(prefix)
        data = self.read(prefix)
        if data['pid'] != pid or data['process_token'] != process_token(pid):
            raise ValueError('runtime owner mismatch')
        descriptor = dict(path=str(path), source=str(source))
        if resume:
            if not data.get('source_identity') or data.get('direct_save') != descriptor:
                raise ValueError('unverified interrupted direct saves; manual recovery required')
        else:
            data.update(direct_save=descriptor, phase='running')
            self.write(prefix, data)

    def checkpoint(self, prefix, pid, source, runner_root='', mode='0', lowerdir='', source_view=''):
        # Return persistence itself changes the original prefix. If HK+Start
        # lands between prefix sync and direct-save sync, those known writes
        # must not masquerade as a source replaced by the user.
        prefix = self.path(prefix)
        data = self.read(prefix)
        if data['pid'] != pid or data['process_token'] != process_token(pid):
            raise ValueError('runtime owner mismatch')
        if data.get('source') != str(source):
            raise ValueError('runtime source mismatch')
        data['source_identity'] = source_identity(source_view or source, runner_root, mode, lowerdir)
        self.write(prefix, data)

    def phase(self, prefix, pid, phase):
        prefix = self.path(prefix)
        data = self.read(prefix)
        if data['pid'] != pid or data['process_token'] != process_token(pid):
            raise ValueError('runtime owner mismatch')
        data['phase'] = phase
        self.write(prefix, data)

    def finish(self, prefix, pid, safe, reason=''):
        prefix = self.path(prefix)
        self.phase(prefix, pid, 'disposable' if safe else 'recovery')
        data = self.read(prefix)
        data['pid'] = 0
        data['process_token'] = ''
        data['reason'] = '' if safe else (reason or 'interrupted-or-unsynchronized')
        self.write(prefix, data)
        self.collect()

    def report(self):
        # Read-only, bounded display; never walk game contents to build it.
        retained = []
        for prefix in sorted(self.root.iterdir()):
            if prefix.is_symlink() or not prefix.is_dir():
                continue
            try:
                data = self.read(self.path(prefix))
                if data['phase'] == 'disposable':
                    continue
                pid = int(data.get('pid', 0))
                if pid and process_token(pid) == data.get('process_token'):
                    continue
            except (OSError, ValueError, KeyError, TypeError):
                pass  # Legacy data with no verifiable journal needs review too.
            retained.append(prefix)
        if retained:
            return str(len(retained)) + '\n' + '\n'.join(str(p) for p in retained[:5])
        return ''

    def idle(self):
        for prefix in self.root.iterdir():
            if prefix.is_symlink():
                continue
            if mounted(prefix):
                return False
            try:
                data = self.read(self.path(prefix))
                pid = int(data.get('pid', 0))
                if pid and process_token(pid) == data.get('process_token'):
                    return False
            except (OSError, ValueError, KeyError, TypeError):
                pass
        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('begin', 'running', 'finish', 'collect', 'report', 'check-idle', 'direct-save', 'checkpoint'))
    parser.add_argument('prefix', nargs='?', type=Path)
    parser.add_argument('--source', default='')
    parser.add_argument('--pid', type=int, default=os.getppid())
    parser.add_argument('--game-dir', default='')
    parser.add_argument('--safe', action='store_true')
    parser.add_argument('--runner', default='')
    parser.add_argument('--log', default='')
    parser.add_argument('--reason', default='')
    parser.add_argument('--runner-root', default='')
    parser.add_argument('--mode', default='0')
    parser.add_argument('--lowerdir', default='')
    parser.add_argument('--source-view', default='')
    parser.add_argument('--save-path', default='')
    parser.add_argument('--save-source', default='')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    try:
        store = PrefixStore()
        if args.action == 'begin':
            reused = store.begin(args.prefix, args.source, args.pid, args.game_dir, args.runner, args.log,
                                 args.runner_root, args.mode, args.lowerdir, args.source_view)
            raise SystemExit(10 if reused else 0)
        elif args.action == 'direct-save':
            store.direct_save(args.prefix, args.pid, args.save_path, args.save_source, args.resume)
        elif args.action == 'checkpoint':
            store.checkpoint(args.prefix, args.pid, args.source, args.runner_root, args.mode, args.lowerdir, args.source_view)
        elif args.action == 'running': store.phase(args.prefix, args.pid, 'running')
        elif args.action == 'finish': store.finish(args.prefix, args.pid, args.safe, args.reason)
        elif args.action == 'collect': store.collect()
        elif args.action == 'report': print(store.report(), end='')
        else: raise SystemExit(0 if store.idle() else 2)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'Runtime prefix retained/refused: {error}\n')
