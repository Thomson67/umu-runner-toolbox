import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


BRIDGE = (
    Path(__file__).resolve().parents[1]
    / "toolbox/overlay/umu-batocera/umu-root-runner.py"
)


class UmuCpuAffinityTests(unittest.TestCase):
    def test_game_launch_inherits_only_requested_available_cpus(self):
        available = sorted(os.sched_getaffinity(0))
        if len(available) < 2:
            self.skipTest("requires at least two available CPUs")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "fake-umu.py"
            target.write_text(
                "import json, os, subprocess, sys\n"
                "print(json.dumps(sorted(os.sched_getaffinity(0))))\n"
                "subprocess.run([sys.executable, '-c', "
                "'import json, os; print(json.dumps(sorted(os.sched_getaffinity(0))))'], "
                "check=True)\n",
                encoding="utf-8",
            )
            driver = (
                "import runpy, sys; "
                "bridge = runpy.run_path(sys.argv.pop(1)); "
                "entry = bridge['main']; "
                "entry.__globals__['ensure_ldconfig_cache'] = lambda: None; "
                "entry.__globals__['have_lzma'] = lambda: True; "
                "sys.exit(entry())"
            )
            first = available[0]
            unavailable = available[-1] + 1
            result = subprocess.run(
                [sys.executable, "-c", driver, str(BRIDGE), str(target), "game.exe"],
                env={**os.environ, "UMU_CPU_AFFINITY": f"{first},{unavailable}-{unavailable + 1}"},
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual([json.loads(line) for line in result.stdout.splitlines()], [[first], [first]])
        self.assertIn(f"cpu_affinity_effective={first}", result.stderr)

    def test_unset_and_invalid_options_preserve_inherited_affinity(self):
        apply_cpu_affinity = runpy.run_path(str(BRIDGE))["apply_cpu_affinity"]
        for value in ("", "0-2,bad", "4-2", "9-1000000000"):
            with self.subTest(value=value):
                with (
                    patch.dict(os.environ, {"UMU_CPU_AFFINITY": value}),
                    patch.object(os, "sched_getaffinity", return_value={0, 1, 2}),
                    patch.object(os, "sched_setaffinity") as set_affinity,
                ):
                    apply_cpu_affinity()
                set_affinity.assert_not_called()
