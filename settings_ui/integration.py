"""Attach the supplied Frame 58 widget without replacing the v1 home model."""
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal

from .model import SettingsStore
from .console import ConsoleWindow


class AttachedSettings(ConsoleWindow):
    returned = Signal()
    valuesEdited = Signal(str)

    def __init__(self, data_dir,theme,system):
        super().__init__(theme,system)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowTitle("NEXATOM v1.15 · Settings")
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
        self.controls.panel_calibration=None
        if self.controls.calibration:self.controls.cancel_calibration()
        if self.screen_test and self.screen_test.isVisible():self.screen_test.close()
        self.clear_knob_focus()
        if self.system.mode_deadline:self.system.revert_mode()
        self.close_overlay()
        self.timer.stop()
        self.returned.emit()
        self.hide()
        event.ignore()


class SettingsHost(QObject):
    def __init__(self, app, home, controller, data_dir,theme,system):
        super().__init__(app)
        self.home = home
        self.controller = controller
        self.applying = False
        self.window = AttachedSettings(data_dir,theme,system)
        # Keep the existing home surface mapped underneath the native settings
        # surface. Hiding/re-showing fullscreen windows exposed the desktop and
        # triggered the window manager's own transition on each navigation.
        self.window.winId()
        self.window.windowHandle().setTransientParent(home)
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
        self.controller.system_settings.probe()
        if self.window.isVisible():
            self.window.raise_();self.window.activateWindow();return
        self.window.slide.stop();self.window.transition=0
        self.window.motion.position=self.window.selected
        self.window.motion.target=None;self.window.motion.velocity=0
        self.window.last_index=self.window.selected
        self.fullscreen = self.home.visibility() == self.home.Visibility.FullScreen
        self.window.setGeometry(self.home.x(), self.home.y(), self.home.width(), self.home.height())
        self.window.timer.start()
        self.window.showFullScreen() if self.fullscreen else self.window.show()
        self.window.repaint()
        self.window.raise_()
        self.window.activateWindow()

    def return_home(self):
        if not self.home.isVisible():
            self.home.showFullScreen() if self.fullscreen else self.home.show()
        self.home.requestActivate()

    def shutdown(self):
        self.window.timer.stop()
        self.window.hide()
        if getattr(self.controller,'journal',None):self.controller.journal.close()
