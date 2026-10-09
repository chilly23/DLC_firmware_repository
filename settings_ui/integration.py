"""Attach the supplied Frame 58 widget without replacing the v1 home model."""
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal

from .model import SettingsStore
from .window import SettingsWindow


class AttachedSettings(SettingsWindow):
    returned = Signal()
    valuesEdited = Signal(str)

    def __init__(self, data_dir):
        super().__init__(58, SettingsStore(Path(data_dir) / "settings.json"))
        self.setWindowTitle("NEXATOM v1.4 · Settings")
        self.timer.stop()

    def open_search(self):
        # Painted key taps must retain the native editor's cursor and selection.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        super().open_search()

    def close_overlay(self):
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        super().close_overlay()

    def activate(self, action):
        super().activate(action)
        if action[0] in ('toggle', 'choice') and action[1] in ('laser1', 'laser2', 'stabilisation', 'scan_rate'):
            self.valuesEdited.emit(action[1])
        if self.overlay == "keyboard":
            self.search.setFocus()

    def closeEvent(self, event):
        self.close_overlay()
        self.timer.stop()
        self.returned.emit()
        self.hide()
        event.ignore()


class SettingsHost(QObject):
    def __init__(self, app, home, controller, data_dir):
        super().__init__(app)
        self.home = home
        self.controller = controller
        self.applying = False
        self.window = AttachedSettings(data_dir)
        self.window.valuesEdited.connect(self.apply_function_settings)
        controller.changed.connect(self.sync_function_settings)
        self.sync_function_settings()
        self.window.returned.connect(self.return_home)
        controller.settingsRequested.connect(self.open)
        self.fullscreen = False

    def sync_function_settings(self):
        if self.applying:
            return
        lasers = self.controller.instrument.lasers
        self.window.store.values.update(laser1=lasers[0].emission, laser2=lasers[1].emission,
                                        stabilisation=all(l.stabilised for l in lasers),
                                        scan_rate=f'{round(1000/self.controller.timer.interval())} Hz')
        self.window.update()

    def apply_function_settings(self, key):
        values = self.window.store.values.copy()
        self.applying = True
        try:
            for i, laser in enumerate(self.controller.instrument.lasers):
                if key == f'laser{i+1}' and laser.emission != values[key]:
                    self.controller.toggleEmission(i)
                if key == 'stabilisation' and laser.stabilised != values[key]:
                    self.controller.toggleStabilisation(i)
            if key == 'scan_rate':
                rate = int(values[key].split()[0])
                self.controller.timer.setInterval(round(1000/max(1,min(60,rate))))
        finally:
            self.applying = False
        self.sync_function_settings()

    def open(self):
        self.fullscreen = self.home.visibility() == self.home.Visibility.FullScreen
        self.window.setGeometry(self.home.x(), self.home.y(), self.home.width(), self.home.height())
        self.window.timer.start()
        self.window.showFullScreen() if self.fullscreen else self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        self.home.hide()

    def return_home(self):
        self.home.showFullScreen() if self.fullscreen else self.home.show()
        self.home.requestActivate()

    def shutdown(self):
        self.window.timer.stop()
        self.window.hide()
