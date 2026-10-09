#!/usr/bin/env python3
"""Launch the self-contained QML mock. Hardware I/O is deliberately absent."""
import argparse
import os
from pathlib import Path
import sys

from PySide6.QtCore import QUrl, Qt, QCoreApplication, QEvent, QTimer
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from controller.bridge import Controller
from controller.plot import SpectrumPlot
from settings_ui.integration import SettingsHost

ROOT = Path(__file__).resolve().parent


def create_application(*, skip_boot=False, animate=True, data_dir=None):
    os.environ.setdefault('QT_QPA_FONTDIR', str(ROOT / 'assets'))
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("NEXATOM v1.6")
    app.setApplicationVersion("1.6.0")
    app.setCursorFlashTime(1000)
    QFontDatabase.addApplicationFont(str(ROOT / "assets" / "Roboto-Regular.ttf"))
    QFontDatabase.addApplicationFont(str(ROOT / "assets" / "Roboto-Medium.ttf"))
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
    controller.settings_host = SettingsHost(app, engine.rootObjects()[0], controller, data_dir or ROOT / "data")
    return app, engine, controller, engine.rootObjects()[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windowed", action="store_true", help="1600x720 desktop window instead of fullscreen")
    parser.add_argument("--skip-boot", action="store_true", help="Developer convenience; normal boot is always 3 seconds")
    parser.add_argument("--software", action="store_true", help="Use Qt Quick's software renderer for display-driver troubleshooting")
    parser.add_argument("--verify-startup", type=Path)
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args()
    if args.software:
        os.environ["QT_QUICK_BACKEND"] = "software"
    app, engine, controller, window = create_application(skip_boot=args.skip_boot, data_dir=args.data_dir)
    if not args.windowed:
        app.setOverrideCursor(Qt.CursorShape.BlankCursor)
        window.showFullScreen()
    if args.verify_startup:
        def report_startup():
            import json
            args.verify_startup.write_text(json.dumps({"visible": window.isVisible(), "exposed": window.isExposed(), "booting": window.property("booting"), "platform": app.platformName(), "width": window.width(), "height": window.height(), "acquiring": controller._live, "timer_active": controller.timer.isActive(), "signal_levels": [l.signal.level for l in controller.instrument.lasers], "elapsed": controller.elapsed}), encoding="utf8")
            app.quit()
        QTimer.singleShot(4200, report_startup)
    result = app.exec()
    controller.timer.stop()
    controller.settings_host.shutdown()
    engine.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
