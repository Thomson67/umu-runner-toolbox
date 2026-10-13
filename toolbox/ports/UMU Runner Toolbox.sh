#!/bin/bash
# Persistent, independent xterm font and window preferences.
CONFIG="/userdata/system/umu/toolbox/config"
FONT_SIZE=11
GEOMETRY="120x36"
FULLSCREEN=0
case "$(head -n 1 "$CONFIG/display-mode" 2>/dev/null)" in
    handheld) FONT_SIZE=16; GEOMETRY="88x28" ;; # Legacy preset
    fullscreen) FULLSCREEN=1 ;;
esac
case "$(head -n 1 "$CONFIG/font-size" 2>/dev/null)" in
    11|13|16|18|20) FONT_SIZE="$(head -n 1 "$CONFIG/font-size")" ;;
esac
XTERM_ARGS=(-geometry "$GEOMETRY")
if [ "$FULLSCREEN" -eq 1 ]; then XTERM_ARGS=(-fullscreen); fi
exec /usr/bin/xterm -fa "DejaVu Sans Mono" -fs "$FONT_SIZE" "${XTERM_ARGS[@]}" \
    -T "UMU Runner Toolbox" -e /userdata/system/umu/toolbox/umu-toolbox.sh
