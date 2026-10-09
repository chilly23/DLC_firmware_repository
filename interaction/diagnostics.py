"""Lobby diagnostics. Calls the existing services without changing their drivers."""
from datetime import datetime
from pathlib import Path
import json
import os
import tempfile
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer


class Diagnostics(QObject):
    changed = Signal()

    def __init__(self, controller, workspace, parent=None):
        super().__init__(parent)
        self.ctl, self.workspace = controller, workspace
        self._rows = []
        self._busy = False
        self._summary = 'Run checks to inspect the application and host.'
        self.screen = None
        controller.knobs.changed.connect(self.changed)
        controller.system_settings.changed.connect(self.changed)

    @Property('QVariantList', notify=changed)
    def rows(self): return self._rows

    @Property(bool, notify=changed)
    def busy(self): return self._busy

    @Property(str, notify=changed)
    def summary(self): return self._summary

    @Property(str, notify=changed)
    def gpioStatus(self): return self.ctl.knobs.status

    @Property(str, notify=changed)
    def displayStatus(self):
        system = self.ctl.system_settings
        return 'Detecting display…' if system.busy else system.caps.get('target', 'Not detected')

    @Slot()
    def refresh(self):
        self.ctl.system_settings.probe()
        self.changed.emit()

    @Slot()
    def retryGpio(self):
        self.ctl.knobs.retry()
        self.ctl.journal.record('GPIO retry requested', 'Requested', source='Diagnostics')

    @Slot()
    def retryDisplay(self):
        self.ctl.system_settings.retry_display()

    @Slot()
    def screenCheck(self):
        from settings_ui.screen_check import ScreenCheck
        if self.screen and self.screen.isVisible():
            self.screen.raise_()
            return
        if self.screen:
            self.screen.deleteLater()
        self.screen = ScreenCheck()
        self.screen.setFont(self.ctl.theme.parent().font())
        self.screen.finished.connect(self._screen_result)
        home = self.workspace.home
        self.screen.setGeometry(home.geometry())
        self.screen.winId()
        self.screen.windowHandle().setTransientParent(home)
        self.screen.showFullScreen() if home.visibility() == home.Visibility.FullScreen else self.screen.show()
        self.screen.raise_()
        self.screen.activateWindow()

    def _screen_result(self, result):
        passed = all(result.values())
        self._summary = 'Screen check: ' + ', '.join(f'{key} {"passed" if value else "not completed"}' for key, value in result.items())
        self.ctl.journal.record(self._summary, 'Passed' if passed else 'Cancelled', source='Diagnostics')
        self.changed.emit()
        self.workspace.home.requestActivate()

    @Slot()
    def run(self):
        if self._busy:
            return
        self._busy = True
        self._summary = 'Checking application, storage, display and input services…'
        self.changed.emit()
        QTimer.singleShot(30, self._run)

    def _run(self):
        rows = []
        def add(name, state, detail):
            rows.append(dict(name=name, state=state, detail=detail))
        try:
            with tempfile.TemporaryFile(dir=self.workspace.dataRoot) as stream:
                stream.write(b'nexatom-check')
                stream.flush()
            add('Saved files', 'Passed', 'Data directory is writable')
        except OSError as exc:
            add('Saved files', 'Failed', str(exc))
        add('Settings', 'Passed' if not self.ctl.theme.store.error else 'Warning', self.ctl.theme.store.error or 'Preferences loaded')
        add('Event journal', 'Passed' if not self.ctl.journal.last_error else 'Failed', self.ctl.journal.last_error or f'{self.ctl.journal.count()} records available')
        add('Display', 'Passed' if self.workspace.home and self.workspace.home.screen() else 'Warning', self.displayStatus)
        add('GPIO inputs', 'Passed' if self.ctl.knobs.online else 'Warning', self.gpioStatus)
        add('Acquisition', 'Passed' if self.ctl._live else 'Warning', 'Simulated laser acquisition is running' if self.ctl._live else 'Acquisition has not started')
        add('Runtime', 'Passed', f'Application v1.17 · {os.name}')
        self._rows = rows
        issues = sum(row['state'] != 'Passed' for row in rows)
        self._summary = f'{len(rows)} checks completed · {issues} need attention'
        self._busy = False
        self.ctl.journal.record(self._summary, 'Passed' if not issues else 'Failed', 'default' if not issues else 'warning', 'Diagnostics', rows)
        self.changed.emit()

    @Slot()
    def export(self):
        if not self._rows:
            self.run()
            return
        try:
            folder = Path(self.workspace.dataRoot) / 'exports'
            folder.mkdir(exist_ok=True)
            path = folder / ('diagnostics_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
            path.write_text(json.dumps(dict(timestamp=datetime.now().astimezone().isoformat(), checks=self._rows), indent=2), encoding='utf8')
            self.workspace.report('Diagnostics report saved.')
        except OSError:
            self.workspace.report('Could not save the diagnostics report.', True)

    def shutdown(self):
        if self.screen:
            self.screen.hide()
