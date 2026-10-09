#!/usr/bin/env python3
"""Launch the laser HMI: simulated signals, native host display/system controls."""
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
from settings_ui.model import SettingsStore
from settings_ui.preferences import Appearance
from settings_ui.coordinator import SettingsCoordinator
from device.platform import make_device
from hardware.service import KnobService
from interaction.router import InputRouter
from interaction.icons import IconProvider
from interaction.notifications import Notifications
from interaction.notification_art import NotificationArt,NotificationImageProvider
from interaction.session_lock import SessionLock

ROOT = Path(__file__).resolve().parent


def configure_logging(data_dir=None):
    import logging
    from logging.handlers import RotatingFileHandler
    logdir=Path(data_dir)/'logs' if data_dir else ROOT/'logs';logdir.mkdir(parents=True,exist_ok=True)
    logger=logging.getLogger('nexatom');logger.setLevel(logging.DEBUG if os.environ.get('NEXATOM_GPIO_DEBUG')=='1' else logging.INFO)
    if not logger.handlers:
        handler=RotatingFileHandler(logdir/'controls.log',maxBytes=1_000_000,backupCount=2,encoding='utf8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s'));logger.addHandler(handler)

def create_application(*, skip_boot=False, animate=True, data_dir=None, device=None, gpio_factory=None, gpio_autostart=True):
    os.environ.setdefault('QT_QPA_FONTDIR', str(ROOT / 'assets'))
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("NEXATOM v1.8")
    app.setApplicationVersion("1.8.0")
    app.setCursorFlashTime(1000)
    QFontDatabase.addApplicationFont(str(ROOT / "assets" / "Roboto-Regular.ttf"))
    QFontDatabase.addApplicationFont(str(ROOT / "assets" / "Roboto-Medium.ttf"))
    app.setFont(QFont("Roboto"))
    controller = Controller(animate=animate)
    store=SettingsStore(Path(data_dir or ROOT/'data')/'settings.json')
    theme=Appearance(store,app)
    controller.theme=theme
    notifications=Notifications(Path(data_dir or ROOT/'data')/'notifications.json',app);controller.notifications=notifications
    notifications.renderer=NotificationArt(notifications,theme)
    controller.notice.connect(lambda text:notifications.post(text))
    system=SettingsCoordinator(app,controller,theme,device or make_device())
    controller.system_settings=system
    system.message.connect(lambda text:notifications.post(text,'critical' if 'failed' in text.lower() else 'normal'))
    knobs=KnobService(Path(data_dir or ROOT/'data')/'controls.json',app,worker_factory=gpio_factory,autostart=gpio_autostart)
    navigation=InputRouter(controller,knobs,app)
    controller.knobs=knobs;controller.navigation=navigation
    SpectrumPlot.controller = controller
    qmlRegisterType(SpectrumPlot, "Nexatom", 1, 0, "SpectrumPlot")
    engine = QQmlApplicationEngine()
    engine.addImageProvider('outline',IconProvider())
    engine.addImageProvider('notices',NotificationImageProvider(notifications.renderer))
    engine.rootContext().setContextProperty("ctl", controller)
    engine.rootContext().setContextProperty("theme", theme)
    engine.rootContext().setContextProperty("systemSettings", system)
    engine.rootContext().setContextProperty("skipBoot", skip_boot)
    engine.rootContext().setContextProperty("knobs",knobs)
    engine.rootContext().setContextProperty("navigation",navigation)
    engine.rootContext().setContextProperty("notifications",notifications)
    engine.load(QUrl.fromLocalFile(str(ROOT / "qml" / "Main.qml")))
    if not engine.rootObjects():
        raise RuntimeError("QML failed to load; see the messages above")
    controller.settings_host = SettingsHost(app, engine.rootObjects()[0], controller, data_dir or ROOT / "data",theme,system)
    system.host=controller.settings_host
    navigation.attach(engine.rootObjects()[0],controller.settings_host)
    guard=SessionLock(app,controller);controller.session_lock=guard;knobs.lockChanged.connect(guard.set_locked)
    knobs.panelAction.connect(lambda key:engine.rootObjects()[0].panelInput(key))
    controller.shortcutRequested.connect(lambda side,action:navigation.handle(0 if side==0 else 3,action,1))
    app.aboutToQuit.connect(guard.shutdown);app.aboutToQuit.connect(notifications.timer.stop)
    app.aboutToQuit.connect(knobs.shutdown)
    app.aboutToQuit.connect(navigation.shutdown)
    return app, engine, controller, engine.rootObjects()[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windowed", action="store_true", help="1600x720 desktop window instead of fullscreen")
    parser.add_argument("--fullscreen", action="store_true", help="Fullscreen (the default); retained for existing launch commands")
    parser.add_argument("--skip-boot", action="store_true", help="Developer convenience; normal boot is always 3 seconds")
    parser.add_argument("--software", action="store_true", help="Use Qt Quick's software renderer for display-driver troubleshooting")
    parser.add_argument("--verify-startup", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument('--list-gpio',action='store_true',help='List GPIO chips and ownership of configured pins, without requesting them')
    args = parser.parse_args()
    if args.list_gpio:
        import json
        from hardware.gpio import gpio_module,discover
        from hardware.config import ControlStore
        try:
            gpiod=gpio_module();chips=discover(gpiod)
            config=ControlStore(Path(args.data_dir or ROOT/'data')/'controls.json').config
            pins=sorted({p for k in config['knobs'] if k['enabled'] for p in k['pins'].values()} |
                        {contact['pin'] for contact in config.get('panel',{}).values() if contact['enabled']})
            for chip in chips:
                if chip['lines']<28:continue
                with gpiod.Chip(chip['path']) as handle:
                    chip['pins']=[dict(bcm=p,name=handle.get_line_info(p).name,used=handle.get_line_info(p).used,consumer=handle.get_line_info(p).consumer) for p in pins]
            print(json.dumps(chips,indent=2));return 0
        except (ImportError,OSError,RuntimeError) as exc:print(str(exc),file=sys.stderr);return 1
    if args.software:
        os.environ["QT_QUICK_BACKEND"] = "software"
    configure_logging(args.data_dir)
    app, engine, controller, window = create_application(skip_boot=args.skip_boot, data_dir=args.data_dir)
    if not args.windowed:
        app.setOverrideCursor(Qt.CursorShape.BlankCursor)
        window.showFullScreen()
    if args.verify_startup:
        def report_startup():
            import json
            args.verify_startup.write_text(json.dumps({"visible": window.isVisible(), "fullscreen":window.visibility()==window.Visibility.FullScreen, "exposed": window.isExposed(), "booting": window.property("booting"), "platform": app.platformName(), "width": window.width(), "height": window.height(), "acquiring": controller._live, "timer_active": controller.timer.isActive(), "signal_levels": [l.signal.level for l in controller.instrument.lasers], "elapsed": controller.elapsed}), encoding="utf8")
            app.quit()
        QTimer.singleShot(4200, report_startup)
    result = app.exec()
    controller.timer.stop()
    knobs=controller.knobs;knobs.shutdown();controller.navigation.shutdown()
    controller.settings_host.shutdown()
    system=controller.system_settings
    system.shutdown()
    engine.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
