"""Small QObject API between QML and the simulation; one authoritative state."""
import time
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, Qt
from .model import Instrument, PARAMETERS, PEAKS, MODULES
from .charts import axis_parameter, AXIS_DEFAULTS


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
        self.presentation_busy = False
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(50)  # 20 display updates/s; unrelated to a real servo rate.
        self.timer.timeout.connect(self.advance)

    @Slot(bool)
    def setPresentationBusy(self, busy):
        """Keep acquisition live while a brief menu reveal uses cached chart pixels."""
        was_busy = self.presentation_busy
        self.presentation_busy = busy
        if was_busy and not busy:
            self.frame.emit()
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
                "showError": laser.chart.error_visible, "chart": laser.chart.snapshot(), "top": laser.top_field(),
                "bottom": laser.bottom_field(), "values": laser.values.copy(),
                "status": ("View locked" if laser.locked else "Scanning" if laser.emission else "Idle") + "; Emission " + ("ON" if laser.emission else "OFF")}

    @Slot(str, result="QVariantMap")
    def parameter(self, key):
        axis = axis_parameter(key)
        if axis is not None:
            return axis
        p = PARAMETERS[key]
        return {"label": p.label, "unit": p.unit, "minimum": p.minimum,
                "maximum": p.maximum, "decimals": p.decimals, "module": p.module}

    @Slot(int, str, str, result=str)
    def setValue(self, index, key, value):
        laser = self.instrument.lasers[index]
        error = laser.chart.set_axis(key, value) if key.startswith('chart_') else laser.set_value(key, value)
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
        laser.chart.error_visible = not laser.chart.error_visible
        self.changed.emit()

    @Slot(int, str, result=float)
    def value(self, index, key):
        laser = self.instrument.lasers[index]
        return laser.chart.axes[key[6:]] if key.startswith('chart_') else laser.values[key]

    @Slot(int, str)
    def setChartMode(self, index, mode):
        if mode in ('combined', 'split'):
            self.instrument.lasers[index].chart.mode = mode
            self.changed.emit()

    @Slot(int, bool, bool)
    def placeSignal(self, index, error, upper):
        self.instrument.lasers[index].chart.main_upper = upper != error
        self.changed.emit()

    @Slot(int)
    def swapLocal(self, index):
        laser = self.instrument.lasers[index]
        if not laser.locked and laser.chart.mode == 'split':
            laser.chart.main_upper = not laser.chart.main_upper
            self.changed.emit()

    @Slot(int, bool)
    def toggleSignal(self, index, error):
        chart = self.instrument.lasers[index].chart
        attr = 'error_visible' if error else 'main_visible'
        setattr(chart, attr, not getattr(chart, attr))
        self.changed.emit()

    @Slot(int, float)
    def setChartRatio(self, index, ratio):
        from math import isfinite
        if isfinite(ratio):
            self.instrument.lasers[index].chart.main_ratio = max(.2, min(.8, ratio))
            self.changed.emit()

    @Slot(int)
    def restoreChartAxes(self, index):
        self.instrument.lasers[index].chart.restore_axes()
        self.changed.emit()

    @Slot(int, str, int)
    def stepAxis(self, index, key, direction):
        current = self.value(index, key)
        if key.endswith('_scale'):
            steps = [.01,.02,.05,.1,.2,.5,1,1.25,2,2.75,5,10,20,50,100]
            options = [n for n in steps if n > current+1e-6] if direction>0 else [n for n in steps if n < current-1e-6]
            value = (min(options) if direction>0 else max(options)) if options else current
        else:
            scale = self.value(index, key.replace('position','scale'))
            value = max(-1000, min(1000, current+direction*scale))
        self.setValue(index, key, str(value))
