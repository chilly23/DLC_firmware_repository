"""Keep the shipped Raspberry Pi launchers readable by Linux Bash."""
from pathlib import Path
import shutil
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ShellScriptTests(unittest.TestCase):
    def test_linux_launchers_have_unix_line_endings(self):
        for name in ("start.sh", "setup.sh", "bench.sh"):
            with self.subTest(script=name):
                content = (ROOT / name).read_bytes()
                self.assertTrue(content.startswith(b"#!/usr/bin/env bash\n"))
                self.assertNotIn(b"\r", content, "CRLF makes Linux read pipefail with a trailing carriage return")
                self.assertTrue(content.endswith(b"\n"))

    def test_launchers_parse_in_bash_without_running_setup(self):
        if sys.platform == "win32":
            candidate = Path("C:/Program Files/Git/bin/bash.exe")
            bash = str(candidate) if candidate.is_file() else None
        else:
            bash = shutil.which("bash")
        if not bash:
            self.skipTest("Bash is unavailable")
        for name in ("start.sh", "setup.sh", "bench.sh"):
            with self.subTest(script=name):
                result = subprocess.run(
                    [bash, "--noprofile", "--norc", "-n", str(ROOT / name)],
                    capture_output=True, text=True, timeout=15,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
