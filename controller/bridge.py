"""Small QObject API between QML and the simulation; one authoritative state."""
import time
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, Qt
from .model import Instrument, PARAMETERS, PEAKS, MODULES


class Controller(QObject):
    changed = Signal()
    frame = Signal()
    settingsRequested = Signal()

    @Slot()
    def openSettings(self):
        self.settingsRequested.emit()

    @Slot(int, int)
    def moveGraph(self, source, destination):
        if source in (0, 1) and destination in (0, 1) and source != destination:
            if any(self.instrument.laser_for_view(side).locked for side in (source,destination)):
                return
            views = self.instrument.views
            views[source], views[destination] = views[destination], views[source]
            self.changed.emit()

    @Slot(str, result="QVariantList")
    def fields(self, module):
        return [dict(key=key, **self.parameter(key)) for key in MODULES.get(module, ())]

    @Slot(int, bool, str)
    def selectField(self, index, bottom, key):
        if index in (0, 1) and key in PARAMETERS:
            setattr(self.instrument.lasers[index], "bottom" if bottom else "top", key)
            self.changed.emit()

    def __init__(self, parent=None, *, animate=True):
        super().__init__(parent)
        self.instrument = Instrument()
        self.elapsed = 0.0
        self._started = time.monotonic()
        self._last_tick = self._started
        self._animate = animate
        self._live = False
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(50)  # 20 display updates/s; unrelated to a real servo rate.
        self.timer.timeout.connect(self.advance)
    @Slot()
    def startAcquisition(self):
        if self._live:
            return
        self._live = True
        self._started = self._last_tick = time.monotonic()
        for laser in self.instrument.lasers:
            laser.signal.emission(laser.emission)
        if self._animate:
            self.timer.start()

    @Slot()
    def advance(self):
        now = time.monotonic()
        dt = now-self._last_tick
        self._last_tick = now
        self.step(dt)

    def step(self, dt):
        if not self._live:
            return
        self.elapsed += max(0,dt)
        for laser in self.instrument.lasers:
            laser.signal.advance(max(0,dt),self.elapsed,laser.values,laser.stabilised)
        self.frame.emit()

    @Property(int, notify=changed)
    def leftChannel(self):
        return self.instrument.views[0]

    @Property(int, notify=changed)
    def rightChannel(self):
        return self.instrument.views[1]

    @Slot(int)
    def switchView(self, side):
        if side in (0, 1):
            self.instrument.switch_view(side)
            self.changed.emit()

    @Slot(int, result="QVariantMap")
    def channel(self, index):
        laser = self.instrument.lasers[index]
        return {"number": laser.number, "locked": laser.locked,
                "stabilised": laser.stabilised, "selected": laser.selected, "emission": laser.emission,
                "showError": laser.show_error, "top": laser.top_field(),
                "bottom": laser.bottom_field(), "values": laser.values.copy(),
                "status": ("View locked" if laser.locked else "Scanning" if laser.emission else "Idle") + "; Emission " + ("ON" if laser.emission else "OFF")}

    @Slot(str, result="QVariantMap")
    def parameter(self, key):
        p = PARAMETERS[key]
        return {"label": p.label, "unit": p.unit, "minimum": p.minimum,
                "maximum": p.maximum, "decimals": p.decimals, "module": p.module}

    @Slot(int, str, str, result=str)
    def setValue(self, index, key, value):
        error = self.instrument.lasers[index].set_value(key, value)
        if not error:
            self.changed.emit()
        return error

    @Slot(int)
    def toggleLock(self, index):
        laser = self.instrument.lasers[index]
        laser.locked = not laser.locked
        self.changed.emit()

    @Slot(int)
    def toggleEmission(self, index):
        laser = self.instrument.lasers[index]
        laser.emission = not laser.emission
        if self._live:
            laser.signal.emission(laser.emission)
        self.changed.emit()

    @Slot(int)
    def toggleStabilisation(self, index):
        laser = self.instrument.lasers[index]
        laser.stabilised = not laser.stabilised
        self.changed.emit()

    @Slot(int)
    def nextTarget(self, index):
        laser = self.instrument.lasers[index]
        laser.selected = (laser.selected + 1) % len(PEAKS)
        self.changed.emit()

    @Slot(int, int)
    def selectTarget(self, index, target):
        if 0 <= target < len(PEAKS):
            self.instrument.lasers[index].selected = target
            self.changed.emit()

    @Slot(int)
    def toggleError(self, index):
        laser = self.instrument.lasers[index]
        laser.show_error = not laser.show_error
        self.changed.emit()
