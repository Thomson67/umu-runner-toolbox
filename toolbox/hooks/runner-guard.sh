#!/bin/bash
# Covers Batocera's preparation/wineboot and classic Wine as well as UMU.
set -u
[ "${2:-}" = windows ] || exit 0
ROOT=/userdata/system/wine/custom
STATE=/run/umu-batocera/guard-mounts
LOG=/userdata/system/logs/umu-runner/runner-guard.log
HELPER=/userdata/system/umu/toolbox/overlay/umu-batocera/prefix-isolation.py
mkdir -p "${STATE%/*}" "${LOG%/*}"
exec 9>"$STATE.lock"
flock -x 9 || exit 1
touch "$STATE"
if [ -f "$LOG" ] && [ "$(stat -c %s "$LOG")" -gt 1048576 ]; then
    mv "$LOG" "$LOG.previous"
fi
log() { printf '%s %s\n' "$(date -Is)" "$*" >>"$LOG"; }
mounted() { findmnt -rn -M "$1" >/dev/null 2>&1; }
case "${1:-}" in
gameStart)
    # Keep ownership records after an interrupted launch: never stack binds.
    touch "$STATE"
    for r in "$ROOT"/*-UMU; do
        [ -d "$r" ] || continue
        if mounted "$r"; then
            opts="$(findmnt -rn -o OPTIONS -M "$r")"
            case ",$opts," in *,ro,*) continue;; esac
            log "ERROR existing writable mount: $r"; exit 1
        fi
        mount --bind "$r" "$r" 2>>"$LOG" || exit 1
        if ! mount -o remount,bind,ro "$r" 2>>"$LOG"; then
            umount "$r"; exit 1
        fi
        printf '%s\n' "$r" >>"$STATE"
        log "protected=$r rom=${5:-}"
    done
    # Detach old runner DLL links before classic Wine's prefix migration.
    rom="${5:-}"
    for prefix in "$rom" /userdata/system/wine-bottles/windows/*/"${rom##*/}.wine"; do
        [ -d "$prefix/drive_c/windows" ] || continue
        python3 "$HELPER" "$prefix" >>"$LOG" 2>&1 || { log "ERROR isolation=$prefix"; exit 1; }
    done
    ;;
gameStop)
    # Snapshot integrity before releasing the mounts, including classic games.
    while IFS= read -r r; do
        [ -d "$r" ] || continue
        if [ -s "$r/umu-batocera/integrity.sha256" ]; then
            (cd "$r" && sha256sum -c umu-batocera/integrity.sha256) >>"$LOG" 2>&1 || log "WARNING integrity=$r"
        fi
        if mounted "$r"; then
            umount "$r" 2>>"$LOG" || { log "WARNING guard kept active (busy): $r"; continue; }
        fi
        log "released=$r"
    done <"$STATE"
    temporary="$STATE.$$"
    : >"$temporary"
    while IFS= read -r r; do mounted "$r" && printf '%s\n' "$r" >>"$temporary"; done <"$STATE"
    mv "$temporary" "$STATE"
    ;;
esac
