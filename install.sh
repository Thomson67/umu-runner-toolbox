#!/bin/bash
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DST="/userdata/system/umu/toolbox"
OLD_DST="/userdata/system/umu-runner-toolbox"
OLD_EXPORTS="/userdata/system/umu-runner-exports"
NEW_EXPORTS="/userdata/system/umu/exports"
PORT="/userdata/roms/ports/UMU Runner Toolbox.sh"

if [ "$(id -u)" -ne 0 ]; then
    echo "ERREUR: lancez install.sh en root sur Batocera."
    exit 1
fi

echo "============================================================"
echo " Installation UMU Runner Toolbox v0.5.2b"
echo "============================================================"
echo

mkdir -p "$DST" "$NEW_EXPORTS"
rm -rf "$DST/overlay"
cp -a "$SRC/toolbox/overlay" "$DST/overlay"
cp -a "$SRC/toolbox/umu-toolbox.sh" "$DST/umu-toolbox.sh"
cp -a "$SRC/toolbox/gamepad-nav.py" "$DST/gamepad-nav.py"
cp -a "$SRC/VERSION" "$DST/VERSION"
cp -a "$SRC/README.md" "$DST/README.md" 2>/dev/null || true
cp -a "$SRC/docs/GUIDE_PARTAGE_ET_INSTALLATION.txt" "$DST/GUIDE_PARTAGE_ET_INSTALLATION.txt" 2>/dev/null || true

chmod +x "$DST/umu-toolbox.sh"
chmod +x "$DST/gamepad-nav.py"
chmod +x "$DST/overlay/bin/wine" "$DST/overlay/bin/wine64" "$DST/overlay/bin/wineserver" 2>/dev/null || true
chmod +x "$DST/overlay/umu-batocera/umu-root-runner.py" 2>/dev/null || true

mkdir -p /userdata/roms/ports

cat > "$PORT" <<'PORT_EOF'
#!/bin/bash

TOOL="/userdata/system/umu/toolbox/umu-toolbox.sh"
export TERM=xterm-256color

if [ ! -x "$TOOL" ]; then
    echo "UMU Runner Toolbox introuvable : $TOOL"
    sleep 5
    exit 1
fi

# A terminal graphique rend le menu dialog utilisable directement depuis Ports.
PADNAV="/userdata/system/umu/toolbox/gamepad-nav.py"

cleanup_padnav() {
    [ -n "${PADPID-}" ] && kill "$PADPID" 2>/dev/null || true
}
trap cleanup_padnav EXIT INT TERM

if [ -x "$PADNAV" ]; then
    "$PADNAV" >/userdata/system/logs/umu-toolbox/gamepad-nav.log 2>&1 &
    PADPID=$!
fi

if command -v xterm >/dev/null 2>&1 && [ -n "${DISPLAY-}" ]; then
    xterm -fa "DejaVu Sans Mono" -fs 10 -T "UMU Runner Toolbox" -geometry 125x42 -e "$TOOL"
    exit $?
fi

"$TOOL"
PORT_EOF

chmod +x "$PORT"

# Migration v0.5.2b : regroupe les composants UMU sous /userdata/system/umu.
# L'ancien dossier Toolbox ne contient que l'application et peut etre retire
# une fois la nouvelle installation et le lanceur ecrits avec succes.
if [ -d "$OLD_EXPORTS" ]; then
    find "$OLD_EXPORTS" -mindepth 1 -maxdepth 1 -exec mv -n {} "$NEW_EXPORTS"/ \; 2>/dev/null || true
    rmdir "$OLD_EXPORTS" 2>/dev/null || true
fi
if [ -d "$OLD_DST" ] && [ "$OLD_DST" != "$DST" ]; then
    rm -rf "$OLD_DST"
fi

mkdir -p /userdata/system/logs/umu-toolbox
mkdir -p /userdata/system/umu/backups

echo "[OK] Toolbox installee : $DST"
echo "[OK] Lanceur Ports     : $PORT"
echo
echo "Redemarrez EmulationStation/Batocera si le nouveau Port"
echo "n'apparait pas immediatement."
echo
echo "Vous pourrez ensuite lancer :"
echo "  Ports -> UMU Runner Toolbox"
