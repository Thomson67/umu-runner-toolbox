#!/usr/bin/env python3
"""Minimal Batocera bridge for umu-launcher.

Normal path: only masks geteuid() exactly like the v0.5.2b bridge.
Compatibility path: on hosts whose Python lacks _lzma (notably Batocera 41),
prepares the Steam Runtime with curl + system tar/xz, then disables UMU's own
runtime updater for that launch. UMU remains responsible for launching Proton.
"""
import hashlib
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile

RUNTIMES = {
    "1391110": ("soldier", "steamrt2", "SteamLinuxRuntime_soldier.tar.xz"),
    "1628350": ("sniper", "steamrt3", "SteamLinuxRuntime_sniper.tar.xz"),
    "4183110": ("steamrt4", "steamrt4", "SteamLinuxRuntime_4.tar.xz"),
    "4185400": ("steamrt4-arm64", "steamrt4-arm64", "SteamLinuxRuntime_4.tar.xz"),
}


def log(msg):
    print(f"[umu-batocera] {msg}", file=sys.stderr, flush=True)


def have_lzma():
    try:
        import lzma  # noqa: F401
        return True
    except (ImportError, ModuleNotFoundError):
        return False


def required_runtime():
    proton = Path(os.environ.get("PROTONPATH", ""))
    manifest = proton / "toolmanifest.vdf"
    if not manifest.is_file():
        return None
    text = manifest.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'"require_tool_appid"\s*"?(\d+)"?', text)
    if not m:
        return None
    appid = m.group(1)
    item = RUNTIMES.get(appid)
    if not item:
        raise RuntimeError(f"runtime appid UMU non gere par le bridge Batocera: {appid}")
    return appid, *item


def get_text(url):
    # curl is already required by the Toolbox and negotiates HTTP/2 with Valve.
    # This also avoids urllib3/HTTP1 edge-cache failures seen with repo.steampowered.com.
    return subprocess.check_output(
        ["curl", "-fsSL", "--retry", "3", url], text=True
    ).strip()


def runtime_valid(path, codename):
    platform_name = codename.removesuffix("-arm64")
    return (
        path.is_dir()
        and (path / "mtree.txt.gz").is_file()
        and (path / "VERSIONS.txt").is_file()
        and (path / "pressure-vessel").is_dir()
        and (path / "_v2-entry-point").is_file()
        and any(p.is_dir() for p in path.glob(f"{platform_name}_platform_*"))
    )


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare_runtime_without_lzma():
    req = required_runtime()
    if req is None:
        log("Python _lzma absent, mais Proton ne declare aucun Steam Runtime requis; UMU reste en mode normal")
        return

    _appid, codename, variant, archive = req
    repo_variant = variant.removesuffix("-arm64")
    home = Path(os.environ.get("HOME", str(Path.home())))
    umu_local = home / ".local" / "share" / "umu"
    local = umu_local / variant
    marker_version = local / ".batocera-runtime-version"
    base_images = f"https://repo.steampowered.com/{repo_variant}/images"
    version = get_text(f"{base_images}/latest-public-beta.txt")

    if runtime_valid(local, codename) and marker_version.is_file():
        if marker_version.read_text(encoding="utf-8", errors="replace").strip() == version:
            (local / "umu").unlink(missing_ok=True)
            (local / "umu").symlink_to("_v2-entry-point")
            (local / ".installed.ok").write_text("ok\n", encoding="utf-8")
            os.environ["UMU_RUNTIME_UPDATE"] = "0"
            log(f"{variant} {version} deja prepare (workaround Batocera sans _lzma)")
            return

    base = f"{base_images}/{version}"
    sums = get_text(f"{base}/SHA256SUMS")
    digest = None
    for line in sums.splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2:
            continue
        name = fields[1].lstrip("* ").rsplit("/", 1)[-1]
        if name == archive and re.fullmatch(r"[0-9a-fA-F]{64}", fields[0]):
            digest = fields[0].lower()
            break
    if not digest:
        raise RuntimeError(f"SHA256 introuvable pour {archive}")

    if shutil.which("curl") is None or shutil.which("tar") is None or shutil.which("xz") is None:
        raise RuntimeError("curl, tar ou xz absent: workaround _lzma impossible")

    umu_local.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{variant}-batocera-", dir=umu_local))
    try:
        tarball = work / archive
        extracted = work / "extracted"
        extracted.mkdir()
        log(f"Python _lzma absent: preparation de {variant} {version} avec tar/xz systeme")
        subprocess.run(["curl", "-fL", "--retry", "3", "--progress-bar", f"{base}/{archive}", "-o", str(tarball)], check=True)
        actual = sha256_file(tarball)
        if actual != digest:
            raise RuntimeError(f"SHA256 invalide pour {archive}: attendu {digest}, obtenu {actual}")
        log(f"{archive}: SHA256 OK")

        # Valve's archive contains one top-level SteamLinuxRuntime_* directory.
        # Strip that directory so the destination matches UMU_LOCAL/<variant>.
        subprocess.run(["tar", "-xJf", str(tarball), "--strip-components=1", "-C", str(extracted)], check=True)
        if not runtime_valid(extracted, codename):
            sample = ", ".join(sorted(p.name for p in extracted.iterdir())[:20])
            raise RuntimeError(f"structure extraite invalide ({sample})")

        (extracted / "umu").unlink(missing_ok=True)
        (extracted / "umu").symlink_to("_v2-entry-point")
        (extracted / ".installed.ok").write_text("ok\n", encoding="utf-8")
        (extracted / ".batocera-runtime-version").write_text(version + "\n", encoding="utf-8")

        old = umu_local / f".{variant}.old"
        shutil.rmtree(old, ignore_errors=True)
        if local.exists() or local.is_symlink():
            local.rename(old)
        extracted.rename(local)
        shutil.rmtree(old, ignore_errors=True)
        os.environ["UMU_RUNTIME_UPDATE"] = "0"
        log(f"{variant} {version} installe; UMU reprendra maintenant le lancement normal")
    finally:
        shutil.rmtree(work, ignore_errors=True)



def ensure_ldconfig_cache():
    """Create the cache expected by pressure-vessel on minimal Batocera hosts.

    Batocera 41 ships ldconfig and the libraries but no persistent ld.so cache.
    /var is tmpfs, so this is intentionally a cheap per-boot compatibility fix.
    Modern Batocera installations with an existing readable cache are untouched.
    """
    cache = Path("/var/cache/ldconfig/ld.so.cache")
    if cache.is_file() and os.access(cache, os.R_OK):
        return

    ldconfig = shutil.which("ldconfig")
    if ldconfig is None and Path("/sbin/ldconfig").is_file():
        ldconfig = "/sbin/ldconfig"
    if ldconfig is None:
        log("AVERTISSEMENT: cache ldconfig absent et ldconfig introuvable; pressure-vessel peut echouer")
        return

    cache.parent.mkdir(parents=True, exist_ok=True)
    log(f"cache ldconfig absent: generation de {cache}")
    proc = subprocess.run(
        [ldconfig, "-C", str(cache)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0 or not cache.is_file():
        detail = (proc.stderr or proc.stdout or f"code {proc.returncode}").strip()
        raise RuntimeError(f"generation du cache ldconfig impossible: {detail}")
    log(f"cache ldconfig genere ({cache.stat().st_size} octets)")

def main():
    if len(sys.argv) < 3:
        print("usage: umu-root-runner.py /path/to/umu-run /path/to/game.exe [args...]", file=sys.stderr)
        return 2

    umu = sys.argv[1]
    args = sys.argv[2:]

    # Batocera launches games as root. Keep the original v0.5.2b workaround:
    # mask only UMU's frontend UID check; the process remains in Batocera's
    # graphical/root context.
    os.geteuid = lambda: 1000

    # --version must stay a cheap UMU health check and must never bootstrap a runtime.
    if args != ["--version"]:
        try:
            # pressure-vessel/capsule expects this cache on Batocera 41, while
            # /var is tmpfs and Batocera does not create it itself.
            ensure_ldconfig_cache()
            if not have_lzma():
                prepare_runtime_without_lzma()
        except Exception as exc:
            log(f"ERREUR preparation compatibilite Batocera: {exc}")
            return 1

    sys.argv = [umu] + args
    try:
        runpy.run_path(umu, run_name="__main__")
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
