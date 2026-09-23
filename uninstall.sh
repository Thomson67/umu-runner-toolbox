#!/bin/bash
set -euo pipefail

DST="/userdata/system/umu/toolbox"
OLD_DST="/userdata/system/umu-runner-toolbox"
PORT="/userdata/roms/ports/UMU Runner Toolbox.sh"

echo "Cette action retire uniquement la Toolbox."
echo "Les runners GE-Proton-UMU, UMU, jeux, bottles et sauvegardes sont conserves."
echo
printf "Continuer ? [y/N] "
read -r ans
case "$ans" in y|Y|o|O|oui|OUI|yes|YES) ;; *) exit 0 ;; esac

rm -rf "$DST"
# Nettoyage d une eventuelle ancienne installation pre-v0.5.2b.
[ ! -d "$OLD_DST" ] || rm -rf "$OLD_DST"
rm -f "$PORT"

echo "Toolbox desinstallee."
