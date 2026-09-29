#!/bin/bash
set -eu

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="/userdata/system/umu/toolbox"
PORTS="/userdata/roms/ports"
PORT="$PORTS/UMU Runner Toolbox.sh"
PORT_KEYS="$PORTS/UMU Runner Toolbox.sh.keys"
BACKUPS="/userdata/system/umu/backups"

fail() { echo "ERREUR: $*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || fail "l'installation doit etre lancee en root (Batocera)."
[ -d "$SRC/toolbox" ] || fail "dossier toolbox absent du package."
[ -s "$SRC/toolbox/umu-toolbox.sh" ] || fail "umu-toolbox.sh absent du package."
[ -s "$SRC/toolbox/VERSION" ] || fail "VERSION absente du package."

VERSION="$(tr -d '\r\n[:space:]' < "$SRC/toolbox/VERSION")"
echo "== UMU Runner Toolbox v$VERSION - installation du package =="

mkdir -p "$BACKUPS" "$PORTS" "$(dirname "$DEST")"
TMP="/userdata/system/umu/.toolbox-local-install.$$"
rm -rf "$TMP"
cp -a "$SRC/toolbox" "$TMP" || fail "copie de la nouvelle Toolbox impossible."

# Preserve persistent configuration/overrides from the current installation.
if [ -d "$DEST/config" ]; then
    rm -rf "$TMP/config"
    cp -a "$DEST/config" "$TMP/config" || fail "conservation de config/ impossible."
fi

if [ -d "$DEST" ]; then
    TS="$(date '+%Y%m%d-%H%M%S')"
    OLDVER_FILE="$(tr -d '\r\n[:space:]' < "$DEST/VERSION" 2>/dev/null || true)"
    OLDVER_SCRIPT="$(sed -n 's/^TOOLBOX_VERSION="\([^"]*\)".*/\1/p' "$DEST/umu-toolbox.sh" 2>/dev/null | head -n1)"
    OLDVER="${OLDVER_SCRIPT:-${OLDVER_FILE:-unknown}}"
    if [ -n "$OLDVER_FILE" ] && [ -n "$OLDVER_SCRIPT" ] && [ "$OLDVER_FILE" != "$OLDVER_SCRIPT" ]; then
        echo "INFO: VERSION=$OLDVER_FILE mais umu-toolbox.sh annonce $OLDVER_SCRIPT; sauvegarde etiquetee v$OLDVER_SCRIPT."
    fi
    BACKUP="$BACKUPS/toolbox-v${OLDVER}-${TS}-before-update"
    echo "Sauvegarde de la Toolbox actuelle : $BACKUP"
    mv "$DEST" "$BACKUP" || fail "sauvegarde de la Toolbox actuelle impossible."
else
    BACKUP=""
fi

if ! mv "$TMP" "$DEST"; then
    [ -n "$BACKUP" ] && [ -d "$BACKUP" ] && mv "$BACKUP" "$DEST" 2>/dev/null || true
    fail "installation impossible; restauration de l'ancienne Toolbox tentee."
fi

chmod +x "$DEST/umu-toolbox.sh" 2>/dev/null || true

# Install/update Batocera Port launcher when provided by the package.
if [ -s "$SRC/toolbox/ports/UMU Runner Toolbox.sh" ]; then
    cp -a "$SRC/toolbox/ports/UMU Runner Toolbox.sh" "$PORT"
    chmod +x "$PORT" 2>/dev/null || true
elif [ ! -s "$PORT" ]; then
    cat > "$PORT" <<'PORTSCRIPT'
#!/bin/bash

if [ ! -x /usr/bin/xterm ]; then
    echo "ERREUR : /usr/bin/xterm est introuvable ou non executable." >&2
    echo "UMU Runner Toolbox necessite un terminal pour fonctionner depuis EmulationStation." >&2
    exit 1
fi

exec /usr/bin/xterm \
  -title "UMU Runner Toolbox" \
  -geometry 120x36 \
  -e /userdata/system/umu/toolbox/umu-toolbox.sh
PORTSCRIPT
    chmod +x "$PORT"
fi

# Always synchronize the bundled Pad2Key mapping.
if [ -s "$SRC/toolbox/ports/UMU Runner Toolbox.sh.keys" ]; then
    cp -a "$SRC/toolbox/ports/UMU Runner Toolbox.sh.keys" "$PORT_KEYS"
fi

echo
echo "Synchronisation de l integration sur les runners UMU geres existants..."
if ! UMU_TOOLBOX_INSTALL_SYNC=1 "$DEST/umu-toolbox.sh"; then
    echo "AVERTISSEMENT: migration automatique reportee ou incomplete."
    echo "Fermez tout jeu UMU puis utilisez Maintenance > Reparer / mettre a niveau l integration UMU."
fi

echo "Installation terminee : v$VERSION"
echo "Toolbox : $DEST"
echo "Port    : $PORT"
echo "Pad2Key : $PORT_KEYS"
echo
echo "Installation effectuee depuis le package local verifie."
