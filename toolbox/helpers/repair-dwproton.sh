#!/bin/bash
set -euo pipefail
HELPERS="$(cd "$(dirname "$0")" && pwd)"
RUNNER=/userdata/system/wine/custom/dwproton-11.0-14-UMU
CACHE=/userdata/system/umu/repair-cache
LOG_DIR=/userdata/system/logs/umu-runner
[ "$(id -u)" = 0 ] || { echo 'Run as root on Batocera.'; exit 1; }
mkdir -p "$CACHE" "$LOG_DIR"
WORK="$(mktemp -d "$CACHE/dwproton.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
LOG="$LOG_DIR/repair-dwproton-$(date +%Y%m%d-%H%M%S).log"
curl -fL --retry 3 --connect-timeout 15 \
    'https://github.com/dawn-winery/dwproton-mirror/releases/download/dwproton-11.0-14/dwproton-11.0-14-x86_64.tar.xz' \
    -o "$WORK/original.tar.xz"
printf '%s  %s\n' 'c563cc99d464fb19a767a0eb90dc723746bfcdd402a4fdaa0737b12af081f99a' "$WORK/original.tar.xz" | sha256sum -c -
python3 "$HELPERS/repair-runner-dlls.py" "$RUNNER" "$WORK/original.tar.xz" "$@" 2>&1 | tee "$LOG"
echo "Diagnostic and repair log: $LOG"
