#!/bin/bash
set -euo pipefail

DST="/userdata/system/umu/toolbox"
OLD_DST="/userdata/system/umu-runner-toolbox"
PORT="/userdata/roms/ports/UMU Runner Toolbox.sh"
PORT_KEYS="/userdata/roms/ports/UMU Runner Toolbox.sh.keys"

echo "Cette action retire uniquement la Toolbox."
echo "Les runners GE-Proton-UMU et GDK-Proton-UMU, UMU, jeux, bottles et sauvegardes sont conserves."
echo
printf "Continuer ? [y/N] "
read -r ans
case "$ans" in y|Y|o|O|oui|OUI|yes|YES) ;; *) exit 0 ;; esac

if [ -x /userdata/system/scripts/umu-runner-guard.sh ]; then
    /userdata/system/scripts/umu-runner-guard.sh gameStop windows || true
fi
rm -f /userdata/system/scripts/umu-runner-guard.sh
rm -rf "$DST"
# Nettoyage d une eventuelle ancienne installation pre-v0.5.2b.
[ ! -d "$OLD_DST" ] || rm -rf "$OLD_DST"
rm -f "$PORT" "$PORT_KEYS"

echo "Toolbox desinstallee."
