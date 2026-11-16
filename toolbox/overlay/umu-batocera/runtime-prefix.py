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
import shlex
import shutil
import subprocess
import sys
import tempfile
import time


def process_token(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        if fields[0] in ('Z', 'X'):
            return ''
        start = fields[19]
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        return boot + ':' + start
    except (OSError, IndexError):
        return ''


def wait_owner(state_file, pid, token):
    """Keep native wineserver -w open until return copying has finished.

    Batocera removes the OverlayFS workdir after -w. A surviving bind of the
    merged view cannot protect that directory against the native rm -rf.
    Only an exact, verified session may hold this barrier; dead/reused PIDs
    must release it, including a wrapper killed with Hotkey + Start.
    """
    state_file = Path(state_file)
    try:
        lines = state_file.read_text().splitlines()
    except FileNotFoundError:
        lines = []  # Owner may already be releasing its last mounts.
    if not token or (lines and (len(lines) < 7 or lines[5] != str(pid) or lines[6] != token)):
        raise ValueError('unverified return-copy owner')
    while process_token(pid) == token:
        # Removing the mapping precedes mount release and runtime cleanup.
        # Wait for the verified process to end, including the zombie case.
        time.sleep(0.05)
    print('runtime_wait_complete=owner-ended', flush=True)


NATIVE_WINE_STOP = '/usr/bin/batocera-wine windows stop'
HOTKEY_CONTEXT_FILES = (Path('/run/hotkeygen.state'), Path('/run/hotkeygen.context'))


def wine_hotkey_context():
    for path in HOTKEY_CONTEXT_FILES:
        try:
            saved = json.loads(path.read_text())
        except FileNotFoundError:
            continue
        # Older hotkeygen stores the effective keys, including common actions.
        # Its successor stores the original keys and the common-actions flag.
        context = saved.get('context', saved)
        if context.get('name') == 'wine' and isinstance(context.get('keys'), dict):
            return context['keys'], saved.get('include_common', False)
        break
    return None


def update_hotkey(state_file, pid, token, log, restore=False):
    context = wine_hotkey_context()
    if context is None:
        if not restore:
            print('runtime_hotkey=skipped reason=no-wine-context', flush=True)
        return
    keys, common = context
    command = shlex.join([sys.executable, str(Path(__file__).resolve()), 'stop-hotkey',
                          '--state-file', str(state_file), '--pid', str(pid), '--owner-token', token])
    command += ' >>' + shlex.quote(log) + ' 2>&1'
    previous, replacement = (command, NATIVE_WINE_STOP) if restore else (NATIVE_WINE_STOP, command)
    if keys.get('exit') != previous:
        if not restore:
            print('runtime_hotkey=skipped reason=custom-exit', flush=True)
        return
    args = ['hotkeygen', '--new-context', 'wine', json.dumps(dict(keys, exit=replacement))]
    if not common:
        args.append('--disable-common')
    rc = subprocess.run(args, timeout=5).returncode
    if rc:
        raise ValueError(f'hotkeygen exited with status {rc}')
    print('runtime_hotkey=' + ('restored' if restore else 'registered'), flush=True)


def stop_hotkey(state_file, pid, token):
    try:
        lines = state_file.read_text().splitlines()
    except FileNotFoundError:
        return 0  # A repeated hotkey may arrive after normal shutdown.
    runner = Path(__file__).resolve().parents[1]
    if (len(lines) < 7 or lines[4:7] != [str(runner), str(pid), token]
            or not token or process_token(pid) != token):
        return 0
    prefix = Path(lines[3])
    if not prefix.is_absolute() or not prefix.is_dir():
        raise ValueError('active wineserver prefix unavailable')
    # Ask only this wineserver to stop. The foreground launcher stays alive,
    # so Batocera cannot enter its signal handler and tear down the overlay.
    env = dict(os.environ, WINEPREFIX=str(prefix))
    try:
        owner_env = Path(f'/proc/{pid}/environ').read_bytes().split(b'\0')
    except FileNotFoundError:
        return 0
    for entry in owner_env:
        key, _, value = os.fsdecode(entry).partition('=')
        if key in ('LD_LIBRARY_PATH', 'HOME', 'XDG_RUNTIME_DIR', 'TMPDIR'):
            env[key] = value
    if process_token(pid) != token:
        return 0
    rc = subprocess.run([str(runner / 'files/bin/wineserver'), '-k'], env=env, timeout=10).returncode
    print(f'runtime_hotkey_wineserver_rc={rc}', flush=True)
    return rc


def mount_table():
    """Read every visible namespace; unreadable evidence must stop recovery."""
    seen = set()
    entries = []
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
            raise ValueError(f'unreadable mount namespace: {process}') from error
        seen.add(namespace)
        for line in lines:
            fields = line.split()
            if len(fields) < 10 or '-' not in fields[6:]:
                raise ValueError('invalid mountinfo record')
            root, target = (re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), x)
                            for x in fields[3:5])
            entries.append((namespace, root, target))
    return entries


def references_prefix(path, root, target):
    suffix = '/umu/materialized-prefixes/' + path.name
    return (target == str(path) or target.startswith(str(path) + '/')
            or root == str(path) or root.startswith(str(path) + '/')
            or root.endswith(suffix) or suffix + '/' in root)


def mounted(path):
    """Check all visible mount namespaces, including a surviving container."""
    try:
        return any(references_prefix(path, root, target) for _, root, target in mount_table())
    except (OSError, ValueError):
        return True  # Cannot prove that deleting it is safe.


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
        if mounted(prefix):
            self.recover_adapter_mounts(prefix)
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

    def recover_adapter_mounts(self, prefix):
        """Release only abandoned host compatdata/pfx binds of this runtime.

        Called under the wrapper's session-wide inherited lock. Never use a
        lazy/forced unmount: busy mounts and surviving container namespaces
        keep the original refusal and all unsynchronized runtime data.
        """
        data = self.read(prefix)  # Untracked/invalid journals authorize nothing.
        owner = int(data.get('pid', 0))
        if owner and process_token(owner) == data.get('process_token'):
            raise ValueError(f'runtime owner still active: {prefix}')
        entries = mount_table()
        namespace = Path('/proc/self/ns/mnt').stat().st_ino
        references = [(ns, root, Path(target)) for ns, root, target in entries
                      if references_prefix(prefix, root, target)]
        targets = []
        for ns, root, target in references:
            compat = self.base / 'compatdata'
            if (ns != namespace or target.name != 'pfx'
                    or target.parent.parent != compat
                    or target.resolve() != target
                    or not target.samefile(prefix)
                    or sum(t == str(target) for n, _, t in entries if n == ns) != 1
                    or any(t.startswith(str(target) + '/') for n, _, t in entries if n == ns)):
                raise ValueError(f'runtime mount requires recovery: {target} namespace={ns} root={root}')
            targets.append(target)
        # Validate the whole set before touching anything. A bind whose root
        # merely contains the runtime, or a different namespace, is not ours.
        for target in targets:
            result = subprocess.run(['umount', '--', str(target)], capture_output=True, text=True)
            if result.returncode:
                raise ValueError(f'runtime adapter unmount failed: {target}: {result.stderr.strip()}')
            print(f'runtime_stale_adapter_unmounted={target} prefix={prefix}', flush=True)
        if mounted(prefix):
            raise ValueError(f'runtime still mounted after adapter recovery: {prefix}')

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
    parser.add_argument('action', choices=('begin', 'running', 'finish', 'collect', 'report', 'check-idle',
                                          'direct-save', 'checkpoint', 'token', 'wait-owner',
                                          'register-hotkey', 'restore-hotkey', 'stop-hotkey'))
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
    parser.add_argument('--state-file', type=Path)
    parser.add_argument('--owner-token', default='')
    args = parser.parse_args()
    try:
        if args.action == 'token':
            print(process_token(args.pid))
            raise SystemExit(0)
        if args.action == 'wait-owner':
            wait_owner(args.state_file, args.pid, args.owner_token)
            raise SystemExit(0)
        if args.action in ('register-hotkey', 'restore-hotkey'):
            update_hotkey(args.state_file, args.pid, args.owner_token, args.log, args.action == 'restore-hotkey')
            raise SystemExit(0)
        if args.action == 'stop-hotkey':
            raise SystemExit(stop_hotkey(args.state_file, args.pid, args.owner_token))
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
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f'Runtime prefix retained/refused: {error}\n')
