"""Small QObject API between QML and the simulation; one authoritative state."""
import time
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, Qt
from .model import Instrument, PARAMETERS, PEAKS, MODULES
from .charts import axis_parameter, AXIS_DEFAULTS
from .alarms import AlarmMonitor


class Controller(QObject):
    changed = Signal()
    frame = Signal()
    settingsRequested = Signal()
    notice = Signal(str)
    shortcutRequested=Signal(int,str)

    @Slot(str)
    def notify(self,message):self.notice.emit(message)
    def action_notice(self,text,key):
        if getattr(self,'notifications',None) and self.preferences.get('notification_actions',True):self.notifications.post(text,key=key)
    def gesture_notice(self,index,action):
        """Announce continuous changes once they settle, never once per edge/frame."""
        if not hasattr(self,'_gesture_timers'):self._gesture_timers={}
        if index not in self._gesture_timers:
            timer=QTimer(self);timer.setSingleShot(True);timer.setInterval(650)
            timer.timeout.connect(lambda i=index,t=timer:self.action_notice(f'Laser {i+1} '+t.property('action'),'graph-gesture-'+str(i)))
            self._gesture_timers[index]=timer
        timer=self._gesture_timers[index];timer.setProperty('action',action);timer.start()
    @Slot(int,result=str)
    def shortcutLabel(self,side):
        from hardware.config import ACTIONS
        key=self.preferences.get('shortcut_left' if side==0 else 'shortcut_right','none')
        return 'Not set' if key=='none' else ACTIONS.get(key,'Not set')
    @Slot(int)
    def runShortcut(self,side):
        key=self.preferences.get('shortcut_left' if side==0 else 'shortcut_right','none')
        if key=='none':self.notify('Shortcut not set. Assign it in Control Settings.')
        else:self.shortcutRequested.emit(side,key)

    def configure(self,values):
        previous=getattr(self,'preferences',{})
        self.preferences=values.copy()
        rate=int(values.get('sampling_rate',20));self.timer.setInterval(round(1000/rate))
        for i,laser in enumerate(self.instrument.lasers):
            loaded = values.get('alarms'+str(i+1), {})
            if isinstance(loaded, dict):
                laser.alarms.update({k: loaded[k] for k in laser.alarms if k in loaded})
            key='graph'+str(i+1);config=values[key]
            laser.signal.configure(dict(config,sampling_rate=rate))
            if self._live and not laser.signal.ready:laser.signal.advance(0,self.elapsed,laser.values,laser.stabilised)
            for prefix,low,high in [('main','main_min','main_max'),('error','error_min','error_max')]:
                old=previous.get(key,{})
                if old.get(low)!=config[low] or old.get(high)!=config[high]:
                    laser.chart.axes[prefix+'_position']=(config[low]+config[high])/2
                    laser.chart.axes[prefix+'_scale']=(config[high]-config[low])/4
        self.changed.emit();self.frame.emit()

    @Slot()
    def openSettings(self):
        self.settingsRequested.emit()
    @Slot(str)
    def openSection(self,key):
        self.openSettings();window=self.settings_host.window
        if key in window.order:
            window.select(window.order.index(key));window.motion.position=window.selected;window.motion.target=None;window.motion.velocity=0
    @Slot(result=bool)
    def settingsVisible(self):return self.settings_host.window.isVisible()
    @Slot()
    def closeSettings(self):self.settings_host.window.close()

    @Slot(int, int)
    def moveGraph(self, source, destination):
        if source in (0, 1) and destination in (0, 1) and source != destination:
            if any(self.instrument.laser_for_view(side).locked for side in (source,destination)):
                return
            views = self.instrument.views
            views[source], views[destination] = views[destination], views[source]
            self.changed.emit()
            self.action_notice('Laser panels swapped','chart-move')

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
        self.alarm_monitors = [AlarmMonitor(), AlarmMonitor()]
        self._alarm_elapsed = 0.
        for laser in self.instrument.lasers:
            laser.alarms = {'enabled': False, 'main_high': 8.5, 'error_high': 2.0}
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
        self._alarm_elapsed += max(0,dt)
        if self._alarm_elapsed >= .1:
            changed = False
            for laser, monitor in zip(self.instrument.lasers,self.alarm_monitors):
                samples = [laser.signal.sample(x) for x in laser.signal.x_values]
                main = max((s[0] for s in samples),default=0.)
                error = max((abs(s[1]) for s in samples),default=0.)
                changed |= monitor.update(laser.alarms,laser.emission,main,error,self._alarm_elapsed)
            self._alarm_elapsed = 0.
            if changed:self.changed.emit()
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
            self.action_notice(('Left' if side==0 else 'Right')+' panel switched to Laser '+str(self.instrument.views[side]+1),'view-'+str(side))

    @Slot(int, result="QVariantMap")
    def channel(self, index):
        laser = self.instrument.lasers[index]
        return {"number": laser.number, "locked": laser.locked,
                "stabilised": laser.stabilised, "selected": laser.selected, "emission": laser.emission,
                "showError": laser.chart.error_visible, "chart": laser.chart.snapshot(), "top": laser.top_field(),
                "bottom": laser.bottom_field(), "values": laser.values.copy(),
                "status": self.theme.trText("View locked" if laser.locked else "Scanning" if laser.emission else "Idle") + "; " + self.theme.trText("Emission") + " " + self.theme.trText("ON" if laser.emission else "OFF")}

    @Slot(str, result="QVariantMap")
    def parameter(self, key):
        if key == 'alarm_main_high':
            return {'label':'Spectroscopy high limit', 'unit':'V', 'minimum':-1000., 'maximum':1000., 'decimals':3, 'module':'ALARM'}
        if key == 'alarm_error_high':
            return {'label':'Error high limit', 'unit':'V', 'minimum':0., 'maximum':1000., 'decimals':3, 'module':'ALARM'}
        axis = axis_parameter(key)
        if axis is not None:
            return axis
        p = PARAMETERS[key]
        return {"label": p.label, "unit": p.unit, "minimum": p.minimum,
                "maximum": p.maximum, "decimals": p.decimals, "module": p.module}

    @Slot(int, str, str, result=str)
    def setValue(self, index, key, value):
        laser = self.instrument.lasers[index]
        if key.startswith('alarm_'):
            try:
                numeric = float(value)
            except ValueError:
                return 'Enter a number'
            if key not in ('alarm_main_high', 'alarm_error_high') or not -1000 <= numeric <= 1000:
                return 'Range: -1000 to 1000 V'
            if key == 'alarm_error_high' and numeric < 0:return 'Range: 0 to 1000 V'
            laser.alarms[key.removeprefix('alarm_')] = round(numeric, 3)
            self._save_alarm(index)
            self.changed.emit()
            return ''
        error = laser.chart.set_axis(key, value) if key.startswith('chart_') else laser.set_value(key, value)
        if not error:
            self.changed.emit()
        return error

    @Slot(int)
    def toggleLock(self, index):
        laser = self.instrument.lasers[index]
        laser.locked = not laser.locked
        self.changed.emit()
        self.action_notice(f'Laser {index+1} graph '+('locked' if laser.locked else 'unlocked'),'graph-lock-'+str(index))

    @Slot(int)
    def toggleEmission(self, index):
        self.setEmission(index,not self.instrument.lasers[index].emission)
    @Slot(int,bool)
    def setEmission(self,index,enabled):
        if getattr(self,'session_lock',None) and self.session_lock.locked:return
        laser = self.instrument.lasers[index]
        if laser.emission==enabled:return
        laser.emission = enabled
        if self._live:
            laser.signal.emission(laser.emission)
        self.changed.emit()
        self.action_notice(f'Laser {index+1} emission '+('enabled' if enabled else 'disabled'),'emission-'+str(index))

    @Slot(int)
    def toggleStabilisation(self, index):
        laser = self.instrument.lasers[index]
        laser.stabilised = not laser.stabilised
        self.changed.emit()
        self.action_notice(f'Laser {index+1} stabilisation '+('enabled' if laser.stabilised else 'disabled'),'stabilise-'+str(index))

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
        if key.startswith('alarm_'):
            return laser.alarms[key.removeprefix('alarm_')]
        return laser.chart.axes[key[6:]] if key.startswith('chart_') else laser.values[key]

    @Slot(int, result='QVariantMap')
    def alarm(self, index):
        return dict(self.instrument.lasers[index].alarms, **self.alarm_monitors[index].snapshot())

    @Slot(int)
    def acknowledgeAlarm(self,index):
        self.alarm_monitors[index].acknowledge();self.changed.emit()

    @Slot(int)
    def clearAlarmHistory(self,index):
        self.alarm_monitors[index].events.clear();self.changed.emit()

    @Slot(int)
    def toggleAlarm(self, index):
        laser = self.instrument.lasers[index]
        laser.alarms['enabled'] = not laser.alarms['enabled']
        self._save_alarm(index)
        self.changed.emit()

    def _save_alarm(self, index):
        if not hasattr(self, 'theme'):
            return
        self.theme.store.values['alarms'+str(index+1)] = dict(self.instrument.lasers[index].alarms)
        self.theme.store.save()

    @Slot(int, str)
    def setChartMode(self, index, mode):
        if mode in ('combined', 'split'):
            self.instrument.lasers[index].chart.mode = mode
            self.changed.emit()
            self.action_notice(f'Laser {index+1} charts: {mode}','chart-mode-'+str(index))

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
            self.action_notice(f'Laser {index+1} spectroscopy/error positions swapped','chart-move')

    @Slot(int, bool)
    def toggleSignal(self, index, error):
        chart = self.instrument.lasers[index].chart
        attr = 'error_visible' if error else 'main_visible'
        setattr(chart, attr, not getattr(chart, attr))
        self.changed.emit()
        self.action_notice(f'Laser {index+1} '+('error' if error else 'spectroscopy')+(' visible' if getattr(chart,attr) else ' hidden'),'signal-'+str(index))

    @Slot(int, float)
    def setChartRatio(self, index, ratio):
        from math import isfinite
        if isfinite(ratio):
            self.instrument.lasers[index].chart.main_ratio = max(.2, min(.8, ratio))
            self.changed.emit()
            self.gesture_notice(index,'chart height ratio adjusted')

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
