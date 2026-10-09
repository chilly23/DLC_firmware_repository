"""Attach the supplied Frame 58 widget without replacing the v1 home model."""
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal

from .model import SettingsStore
from .window import SettingsWindow


class AttachedSettings(SettingsWindow):
    returned = Signal()

    def __init__(self, data_dir):
        super().__init__(58, SettingsStore(Path(data_dir) / "settings.json"))
        self.setWindowTitle("NEXATOM v1.2 · Settings")
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
        self.window = AttachedSettings(data_dir)
        self.window.returned.connect(self.return_home)
        controller.settingsRequested.connect(self.open)
        self.fullscreen = False

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
