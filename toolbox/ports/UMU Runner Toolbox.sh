#!/bin/bash
# UMU display profile. Kept in persistent config across upgrades.
MODE_FILE="/userdata/system/umu/toolbox/config/display-mode"
FONT_SIZE=11
GEOMETRY="120x36"
if [ -r "$MODE_FILE" ] && [ "$(head -n 1 "$MODE_FILE")" = handheld ]; then
    FONT_SIZE=16
    GEOMETRY="88x28"
elif [ -r "$MODE_FILE" ] && [ "$(head -n 1 "$MODE_FILE")" = fullscreen ]; then
    FULLSCREEN=1
fi
XTERM_ARGS=(-geometry "$GEOMETRY")
if [ "${FULLSCREEN:-0}" -eq 1 ]; then
    XTERM_ARGS=(-fullscreen)
fi
exec /usr/bin/xterm -fa "DejaVu Sans Mono" -fs "$FONT_SIZE" "${XTERM_ARGS[@]}" \
    -T "UMU Runner Toolbox" -e /userdata/system/umu/toolbox/umu-toolbox.sh
