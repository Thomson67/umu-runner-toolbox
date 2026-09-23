#!/usr/bin/env python3
import os
import runpy
import sys

if len(sys.argv) < 3:
    print("usage: umu-root-runner.py /path/to/umu-run /path/to/game.exe [args...]", file=sys.stderr)
    sys.exit(2)

umu = sys.argv[1]
args = sys.argv[2:]

# Batocera launches its graphical session/games as root. umu-launcher normally
# refuses UID 0. We only mask geteuid() for umu's frontend check; the process
# otherwise remains in Batocera's original graphical context.
os.geteuid = lambda: 1000

sys.argv = [umu] + args
runpy.run_path(umu, run_name="__main__")
