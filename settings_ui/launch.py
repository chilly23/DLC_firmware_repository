"""Shared launcher; each public script selects one independent design."""

import argparse
import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

from .model import ROOT
from .window import SettingsWindow


def run(variant):
    parser = argparse.ArgumentParser(description=f"Nexatom Settings — Frame {variant}")
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--capture", metavar="PNG", help="Render a screenshot and exit")
    parser.add_argument(
        "--verify-startup",
        metavar="JSON",
        help="Verify a real desktop window, report, then exit",
    )
    parser.add_argument(
        "--keyboard", action="store_true", help="Open the Frame 60 keyboard on launch"
    )
    args = parser.parse_args()
    if args.capture:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv[:1])
    app.setApplicationName(f"Nexatom Settings {variant}")
    for font in ["Roboto-Regular.ttf", "Roboto-Medium.ttf"]:
        QFontDatabase.addApplicationFont(str(ROOT / "assets" / font))
    app.setWindowIcon(QIcon(str(ROOT / "assets" / "system.png")))
    window = SettingsWindow(variant)
    if args.fullscreen:
        window.showFullScreen()
    else:
        window.show()
    if args.keyboard:
        window.open_search()
    if args.verify_startup:

        def report_startup():
            handle = window.windowHandle()
            report = {
                "variant": variant,
                "visible": window.isVisible(),
                "exposed": bool(handle and handle.isExposed()),
                "platform": app.platformName(),
                "width": window.width(),
                "height": window.height(),
            }
            Path(args.verify_startup).write_text(json.dumps(report), encoding="utf8")
            app.quit()

        QTimer.singleShot(1200, report_startup)
    if args.capture:

        def capture():
            window.grab().save(args.capture)
            app.quit()

        QTimer.singleShot(250, capture)
    return app.exec()
