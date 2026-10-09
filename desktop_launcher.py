"""Windowless launch with a visible error message if startup fails."""
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QPA_FONTDIR", str(ROOT / "assets"))

if __name__ == "__main__":
    (ROOT / "logs").mkdir(exist_ok=True)
    with (ROOT / "logs" / "startup.log").open("w", encoding="utf8", buffering=1) as log:
        sys.stdout = sys.stderr = log
        try:
            from main import main
            code = main()
        except Exception:
            traceback.print_exc()
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, "Nexatom could not start. Details are in logs/startup.log.\n\n" + traceback.format_exc()[-1600:], "Nexatom v1.12", 0x10)
            code = 1
    raise SystemExit(code)
