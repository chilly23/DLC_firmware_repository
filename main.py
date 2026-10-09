#!/usr/bin/env python3
"""Launch the self-contained QML mock. Hardware I/O is deliberately absent."""
import argparse
import os
from pathlib import Path
import sys

from PySide6.QtCore import QUrl, Qt, QCoreApplication, QEvent
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from controller.bridge import Controller
from controller.plot import SpectrumPlot

ROOT = Path(__file__).resolve().parent


def create_application(*, skip_boot=False, animate=True):
    os.environ.setdefault('QT_QPA_FONTDIR', str(ROOT / 'assets'))
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    app.setApplicationName("NEXATOM mock1")
    QFontDatabase.addApplicationFont(str(ROOT / "assets" / "Roboto-Regular.ttf"))
    app.setFont(QFont("Roboto"))
    controller = Controller(animate=animate)
    SpectrumPlot.controller = controller
    qmlRegisterType(SpectrumPlot, "Nexatom", 1, 0, "SpectrumPlot")
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("ctl", controller)
    engine.rootContext().setContextProperty("skipBoot", skip_boot)
    engine.load(QUrl.fromLocalFile(str(ROOT / "qml" / "Main.qml")))
    if not engine.rootObjects():
        raise RuntimeError("QML failed to load; see the messages above")
    return app, engine, controller, engine.rootObjects()[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windowed", action="store_true", help="1600x720 desktop window instead of fullscreen")
    parser.add_argument("--skip-boot", action="store_true", help="Developer convenience; normal boot is always 3 seconds")
    parser.add_argument("--software", action="store_true", help="Use Qt Quick's software renderer for display-driver troubleshooting")
    args = parser.parse_args()
    if args.software:
        os.environ["QT_QUICK_BACKEND"] = "software"
    app, engine, controller, window = create_application(skip_boot=args.skip_boot)
    if not args.windowed:
        app.setOverrideCursor(Qt.CursorShape.BlankCursor)
        window.showFullScreen()
    result = app.exec()
    controller.timer.stop()
    engine.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
