"""Lobby services and persisted navigation preferences, shared by touch and GPIO."""
from datetime import datetime
from pathlib import Path
import os
import platform
import shutil
import sys

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, QProcess, QProcessEnvironment, QUrl
from PySide6.QtGui import QGuiApplication, QDesktopServices

ROOT = Path(__file__).resolve().parents[1]
PANEL_BUTTONS = ['lock', 'emission', 'stabilise', 'shortcut', 'more']
BUTTON_LABELS = dict(lock='Lock', emission='Emission', stabilise='Stabilise', shortcut='Shortcut', more='More')


class Workspace(QObject):
    changed = Signal()
    filesChanged = Signal()
    metricsChanged = Signal()
    logsChanged = Signal()
    logsAboutToChange = Signal()
    pageRequested = Signal(str)
    logsRequested = Signal()
    closeLogsRequested = Signal()
    screenshotSaved = Signal(str)

    def __init__(self, controller, theme, parent=None):
        super().__init__(parent)
        self.ctl, self.theme = controller, theme
        self.home = None
        self._message = ''
        self._capture_busy = False
        self._files = []
        self._folder = theme.store.path.parent.resolve()
        self._metrics = []
        self._cpu_previous = None
        self._log_rows = []
        self._log_live = True
        self._log_level = 'all'
        self._logs_active = False
        self._capture_process = None
        self._capture_path = None
        self._capture_timeout = QTimer(self)
        self._capture_timeout.setSingleShot(True)
        self._capture_timeout.timeout.connect(self._capture_timed_out)
        self.monitor = QTimer(self)
        self.monitor.setInterval(1000)
        self.monitor.timeout.connect(self.sample_system)
        self.log_refresh = QTimer(self)
        self.log_refresh.setSingleShot(True)
        self.log_refresh.setInterval(120)
        self.log_refresh.timeout.connect(self.refresh_logs)
        controller.journal.changed.connect(self._journal_changed)
        theme.changed.connect(self.changed)

    @Property(str, notify=changed)
    def message(self): return self._message

    def report(self, message, failed=False):
        self._message = str(message)
        self.changed.emit()
        self.ctl.notifications.post(self._message, 'warning' if failed else 'normal')

    @Property(str, notify=changed)
    def graphSize(self): return self.theme.store.values['home_graph_size']

    @Property('QVariantMap', notify=changed)
    def graphLayout(self):
        return dict(zip(('x','y','width','height','gap'), {
            'Small':(132,112,644,490,12), 'Medium':(122,100,664,516,9),
            'Large':(116,96,678,526,6)}[self.graphSize]))

    @Slot(str)
    def setGraphSize(self, value):
        if value in ('Small', 'Medium', 'Large'):
            self.theme.apply('home_graph_size', value)

    @Property('QVariantList', notify=changed)
    def shortcutActions(self):
        from hardware.config import ACTIONS
        return [dict(key=key, name=value) for key, value in ACTIONS.items()]

    @Slot(int, result=str)
    def shortcut(self, side):
        return self.theme.store.values['shortcut_left' if side == 0 else 'shortcut_right']

    @Slot(int, str)
    def setShortcut(self, side, action):
        from hardware.config import ACTIONS
        if side in (0, 1) and action in ACTIONS:
            self.theme.apply('shortcut_left' if side == 0 else 'shortcut_right', action)

    @Slot(int, result='QVariantList')
    def panelOrder(self, side):
        return list(self.theme.store.values['panel_order_left' if side == 0 else 'panel_order_right'])

    @Slot(int, int, int)
    def moveButton(self, side, source, target):
        if side not in (0, 1) or not 0 <= source < 5 or not 0 <= target < 5 or source == target:
            return
        order = self.panelOrder(side)
        order.insert(target, order.pop(source))
        self.theme.apply('panel_order_left' if side == 0 else 'panel_order_right', order)

    @Slot()
    def resetButtons(self):
        self.theme.apply('panel_order_left', list(PANEL_BUTTONS))
        self.theme.apply('panel_order_right', list(PANEL_BUTTONS))

    @Slot()
    def toggleButtonLabels(self):
        self.theme.apply('button_labels', not self.theme.buttonLabels)

    @Property(bool, notify=logsChanged)
    def logsActive(self): return self._logs_active

    @Slot(str)
    def openPage(self, page): self.pageRequested.emit(page)

    @Slot(str, str)
    def openSettings(self, section, route):
        window = self.ctl.settings_host.window
        if section not in window.order:
            return
        self.ctl.openSection(section)
        if route:
            window.last_content = section
            window.navigate(route)

    @Slot()
    def openLogs(self): self.logsRequested.emit()

    @Property(bool, notify=changed)
    def captureBusy(self): return self._capture_busy

    @Property(str, notify=changed)
    def screenshotFolder(self): return str(self.theme.store.path.parent / 'screenshots')

    @Slot()
    def captureScreen(self):
        if self._capture_busy:
            return
        self._capture_busy = True
        self.changed.emit()
        # Capture after the activating touch/button release has been painted.
        QTimer.singleShot(100, self._capture_screen)

    def _capture_screen(self):
        try:
            folder = Path(self.screenshotFolder)
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / ('phototype_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.png')
            focused = QGuiApplication.focusWindow()
            screen = focused.screen() if focused else self.home.screen() if self.home else QGuiApplication.primaryScreen()
            if screen is None:
                raise RuntimeError('No display is available.')
            pixmap = screen.grabWindow(0)
            if not pixmap.isNull():
                if not pixmap.save(str(path), 'PNG'):
                    raise OSError('The screenshot could not be saved.')
                self._capture_complete(path)
                return
            # Qt's root-window capture is unavailable on Wayland. Raspberry Pi
            # OS labwc/Wayfire exposes the compositor screen capture used by grim.
            grim = shutil.which('grim')
            if sys.platform.startswith('linux') and os.environ.get('WAYLAND_DISPLAY') and grim:
                self._capture_path = path
                process = QProcess(self)
                self._capture_process = process
                process.finished.connect(self._grim_finished)
                process.errorOccurred.connect(self._grim_error)
                process.start(grim, ['-o', screen.name(), str(path)])
                self._capture_timeout.start(15000)
                return
            raise RuntimeError('Full-screen capture is unavailable. On Raspberry Pi Wayland, install grim and use the labwc desktop.')
        except (OSError, RuntimeError) as exc:
            self._capture_failed(str(exc))

    def _grim_finished(self, code, status):
        if not self._capture_process:
            return
        from PySide6.QtGui import QImage
        path = self._capture_path
        error = bytes(self._capture_process.readAllStandardError()).decode(errors='replace').strip()
        self._release_capture()
        if code == 0 and path and not QImage(str(path)).isNull():
            self._capture_complete(path)
        else:
            self._capture_failed(error or 'The compositor refused full-screen capture.')

    def _grim_error(self, error):
        if self._capture_process and error == QProcess.ProcessError.FailedToStart:
            message = self._capture_process.errorString()
            self._release_capture()
            self._capture_failed(message)

    def _capture_timed_out(self):
        if self._capture_process:
            self._capture_process.kill()
            self._release_capture()
            self._capture_failed('Screen capture timed out.')

    def _release_capture(self):
        self._capture_timeout.stop()
        if self._capture_process:
            self._capture_process.deleteLater()
        self._capture_process = None

    def _capture_complete(self, path):
        self._capture_busy = False
        self.report('Screenshot saved: ' + str(path))
        self.screenshotSaved.emit(str(path))
        if self._folder == path.parent:
            self.refreshFiles()

    def _capture_failed(self, error):
        self._capture_busy = False
        self.report('Screenshot failed: ' + error, True)

    @Property('QVariantList', notify=filesChanged)
    def files(self): return self._files

    @Property(str, notify=filesChanged)
    def folder(self): return str(self._folder)

    @Slot(str)
    def browse(self, folder):
        requested = {'data': self.theme.store.path.parent, 'screenshots': Path(self.screenshotFolder),
                     'exports': ROOT / 'exports', 'home': Path.home()}.get(folder, Path(folder))
        try:
            if folder in ('screenshots', 'exports'):
                requested.mkdir(parents=True, exist_ok=True)
            requested = requested.resolve(strict=True)
            if not requested.is_dir():
                return
            entries = sorted(requested.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold()))
            items = []
            for path in entries:
                try:
                    stat = path.stat()
                    items.append(dict(name=path.name, path=str(path), directory=path.is_dir(),
                                      size='' if path.is_dir() else f'{stat.st_size / 1024:,.1f} KB',
                                      modified=datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')))
                except OSError:
                    continue
            self._folder, self._files = requested, items
            self.filesChanged.emit()
        except OSError as exc:
            self.report('Cannot open folder: ' + str(exc), True)

    @Slot()
    def refreshFiles(self): self.browse(str(self._folder))

    @Slot()
    def parentFolder(self): self.browse(str(self._folder.parent))

    @Slot(str)
    def openFile(self, path):
        if Path(path).is_dir():
            self.browse(path)
        elif not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            self.report('No application could open this file.', True)

    @Property('QVariantList', notify=metricsChanged)
    def metrics(self): return self._metrics

    @Slot(bool)
    def monitorSystem(self, enabled):
        if enabled:
            self.sample_system()
            self.monitor.start()
        else:
            self.monitor.stop()

    def sample_system(self):
        cpu = 'Collecting…'
        memory = 'Unavailable'
        temperature = 'Unavailable'
        uptime = 'Unavailable'
        try:
            if sys.platform.startswith('linux'):
                values = [int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
                counters = (sum(values), values[3] + values[4])
                info = dict((line.split(':')[0], int(line.split()[1])) for line in Path('/proc/meminfo').read_text().splitlines())
                memory = f'{(info["MemTotal"] - info.get("MemAvailable", info["MemFree"])) / 1048576:.2f} / {info["MemTotal"] / 1048576:.2f} GB'
                seconds = float(Path('/proc/uptime').read_text().split()[0])
                uptime = f'{int(seconds // 3600)} h {int(seconds % 3600 // 60)} min'
                thermal = Path('/sys/class/thermal/thermal_zone0/temp')
                if thermal.exists(): temperature = f'{int(thermal.read_text()) / 1000:.1f} °C'
            elif sys.platform == 'win32':
                import ctypes
                from ctypes import wintypes
                idle, kernel, user = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
                if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
                    raise OSError('CPU counters unavailable')
                number = lambda ft: (ft.dwHighDateTime << 32) | ft.dwLowDateTime
                counters = (number(kernel) + number(user), number(idle))
                class Memory(ctypes.Structure):
                    _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [(name, ctypes.c_ulonglong) for name in ('total', 'available', 'page', 'page_available', 'virtual', 'virtual_available', 'extended')]
                state = Memory();state.length = ctypes.sizeof(state)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
                    memory = f'{(state.total-state.available)/2**30:.2f} / {state.total/2**30:.2f} GB'
                ctypes.windll.kernel32.GetTickCount64.restype = ctypes.c_ulonglong
                seconds = ctypes.windll.kernel32.GetTickCount64() / 1000
                uptime = f'{int(seconds // 3600)} h {int(seconds % 3600 // 60)} min'
            else:
                counters = None
            if counters and self._cpu_previous:
                elapsed = counters[0] - self._cpu_previous[0]
                if elapsed > 0:
                    cpu = f'{max(0, min(100, 100*(1-(counters[1]-self._cpu_previous[1])/elapsed))):.1f}%'
            self._cpu_previous = counters
        except (OSError, ValueError, KeyError):
            cpu = 'Unavailable'
        usage = shutil.disk_usage(self.theme.store.path.parent)
        self._metrics = [dict(name=name, value=value) for name, value in (
            ('CPU usage', cpu), ('Memory in use / total', memory), ('CPU temperature', temperature),
            ('Storage used / total', f'{usage.used/2**30:.1f} / {usage.total/2**30:.1f} GB'),
            ('System uptime', uptime), ('Control inputs', self.ctl.knobs.status),
            ('Operating system', platform.system() + ' ' + platform.release()), ('Architecture', platform.machine()))]
        self.metricsChanged.emit()

    @Property('QVariantList', notify=logsChanged)
    def logRows(self): return self._log_rows

    @Property(bool, notify=logsChanged)
    def logLive(self): return self._log_live

    @Property(str, notify=logsChanged)
    def logLevel(self): return self._log_level

    @Slot(bool)
    def activateLogs(self, active):
        self._logs_active = active
        if active: self.refresh_logs()
        else: self.log_refresh.stop();self.logsChanged.emit()

    def _journal_changed(self):
        if self._logs_active and self._log_live and not self.log_refresh.isActive(): self.log_refresh.start()

    def refresh_logs(self):
        self.logsAboutToChange.emit()
        self._log_rows = self.ctl.journal.rows(self._log_level, limit=self.ctl.journal.LIMIT)
        self.logsChanged.emit()

    @Slot()
    def toggleLogLive(self):
        self._log_live = not self._log_live
        if self._log_live: self.refresh_logs()
        else: self.log_refresh.stop();self.logsChanged.emit()

    @Slot(str)
    def setLogLevel(self, level):
        if level in ('all', 'default', 'warning', 'critical'):
            self._log_level = level
            self.refresh_logs()

    @Slot()
    def exportLogs(self):
        try:
            self.ctl.journal.export(ROOT / 'exports')
            self.report('Saved exports/logs.csv and exports/logs.md')
        except OSError as exc: self.report('Log export failed: ' + str(exc), True)

    @Slot()
    def clearLogs(self):
        self.ctl.journal.clear()
        self.refresh_logs()

    @Slot()
    def openDlcModel(self):
        # The existing model application keeps its own GPU backend and runtime.
        override = os.environ.get('NEXATOM_VIEWER_DIR')
        candidates = [Path(override).expanduser()] if override else [ROOT.parent / 'HMI-3D-RPi', ROOT.parent.parent / 'HMI-3D-RPi']
        viewer = next((path for path in candidates if (path / 'main.py').is_file()), candidates[0])
        python = viewer / ('.venv/Scripts/pythonw.exe' if sys.platform == 'win32' else '.venv/bin/python')
        if not (viewer / 'main.py').exists() or not python.exists():
            self.report('Install HMI-3D-RPi beside the application (or set NEXATOM_VIEWER_DIR), then run its setup.', True)
            return
        process = QProcess(self)
        environment = QProcessEnvironment.systemEnvironment()
        environment.remove('QT_QUICK_BACKEND')
        environment.insert('QSG_RHI_BACKEND', 'opengl')
        process.setProcessEnvironment(environment)
        process.setProgram(str(python))
        process.setArguments([str(viewer / 'main.py'), '--fullscreen', '--width', '1600', '--height', '720'])
        process.setWorkingDirectory(str(viewer))
        ok, _ = process.startDetached()
        process.deleteLater()
        if not ok: self.report('The 3D assembly viewer could not start.', True)

    def shutdown(self):
        self.monitor.stop();self.log_refresh.stop();self._capture_timeout.stop()
        if self._capture_process:
            self._capture_process.kill();self._release_capture()
