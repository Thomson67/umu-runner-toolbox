"""Exercise both path selection blocks without privileged mounts."""
from pathlib import Path
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[1]
class DirectGameTests(unittest.TestCase):
    def test_both_formats_keep_standard_mount_and_bypass_only_when_enabled(self):
        source = (ROOT/'toolbox/overlay/bin/wine').read_text()
        marker = '    if [ "$UMU_DIRECT_GAME_ENABLED" -eq 1 ]; then'
        positions = [i for i in range(len(source)) if source.startswith(marker,i)]
        self.assertEqual(len(positions),2)
        for index in positions:
            end = source.index('\n    EXE_ABS=', index)
            block = source[index:end]
            for value in (0,1):
                cmd = '''set -eu
log() { :; }
mkdir() { :; }
mount() { printf 'MOUNT\\n'; }
GAME_SOURCE='/merged/game'
GAME_DIR=game
alias_safe=archive
wine_safe=bottle
RUNTIME_KEY=123
GAMEVIEW_BOUND=0
LOG=/dev/null
UMU_DIRECT_GAME_ENABLED=''' + str(value) + '\n' + block + '\nprintf "%s|%s" "$GAMEVIEW" "$GAMEVIEW_BOUND"'
                result = subprocess.check_output(['bash','-c',cmd],text=True)
                if value:
                    self.assertEqual(result,'/merged/game|0')
                else:
                    self.assertTrue(result.startswith('MOUNT\n/userdata/system/umu/gameviews/'))
                    self.assertTrue(result.endswith('|1'))
