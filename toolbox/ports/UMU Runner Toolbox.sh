#!/bin/bash
# UMU display profile. Kept in persistent config across upgrades.
MODE_FILE="/userdata/system/umu/toolbox/config/display-mode"
FONT_SIZE=11
GEOMETRY="120x36"
if [ -r "$MODE_FILE" ] && [ "$(head -n 1 "$MODE_FILE")" = handheld ]; then
    FONT_SIZE=16
    GEOMETRY="88x28"
fi
exec /usr/bin/xterm -fa "DejaVu Sans Mono" -fs "$FONT_SIZE" -geometry "$GEOMETRY" \
    -T "UMU Runner Toolbox" -e /userdata/system/umu/toolbox/umu-toolbox.sh
