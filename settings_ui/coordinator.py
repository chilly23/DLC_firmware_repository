"""Application settings, asynchronous host actions, mode rollback and guided tour."""
from copy import deepcopy
import csv
import datetime
from pathlib import Path
import platform
import time
from PySide6.QtCore import QObject, Signal, Slot, Property, QRunnable, QThreadPool, QTimer, QEvent
from PySide6.QtGui import QFont
from .preferences import NEW_DEFAULTS, GRAPH_DEFAULTS
from .model import DEFAULTS


class JobSignals(QObject):
    finished=Signal(object,object)


class Job(QRunnable):
    def __init__(self,work):super().__init__();self.work=work;self.signals=JobSignals()
    def run(self):
        try:self.signals.finished.emit(self.work(),None)
        except Exception as exc:self.signals.finished.emit(None,str(exc))


from .tour import TOUR


class SettingsCoordinator(QObject):
    changed=Signal()
    message=Signal(str)
    navigateTour=Signal(int)
    levelFinished=Signal(str)
    def __init__(self,app,ctl,theme,device,parent=None):
        super().__init__(parent or app)
        self.app,self.ctl,self.theme,self.store,self.device=app,ctl,theme,theme.store,device
        self.host=None;self.jobs={};self.pool=QThreadPool(self);self.pool.setMaxThreadCount(1)
        self.caps=dict(modes=[],current=None,brightness=None,contrast=None,reasons={},target='Detecting display…')
        self.status='';self.probed=False;self.mode_before=None;self.mode_deadline=0;self.mode_changing=False
        self.idle_since=time.monotonic();self.power_deadline=0
        self._tour=-1;self._tour_play=True;self.tour_deadline=0
        self.timer=QTimer(self);self.timer.setInterval(100);self.timer.timeout.connect(self.tick);self.timer.start()
        app.installEventFilter(self)
        self.theme.changed.connect(self.apply_live)
        self.apply_live()

    @Property(bool,notify=changed)
    def busy(self):return bool(self.jobs)
    @Property(int,notify=changed)
    def modeSeconds(self):return max(0,int(self.mode_deadline-time.monotonic()+.999)) if self.mode_deadline else 0
    @Property(int,notify=changed)
    def powerSeconds(self):return max(0,int(self.power_deadline-time.monotonic()+.999)) if self.power_deadline else 0
    @Property(int,notify=changed)
    def tourIndex(self):return self._tour
    @Property(bool,notify=changed)
    def tourPlaying(self):return self._tour_play
    @Property('QVariantMap',notify=changed)
    def tour(self):
        if self._tour<0:return dict(title='',body='',rect=[0,0,0,0],section='',count=len(TOUR))
        info=TOUR[self._tour].copy()
        info.update(title=self.theme.trText(info['title']),body=self.theme.trText(info['body']),count=len(TOUR))
        return info

    def tell(self,text):self.status=text;self.message.emit(text);self.changed.emit()

    def submit(self,work,callback):
        job=Job(work);token=id(job);self.jobs[token]=job
        def finish(result,error):
            self.jobs.pop(token,None)
            callback(result,error)
            self.changed.emit()
        job.signals.finished.connect(finish);self.pool.start(job);self.changed.emit()

    def probe(self):
        if self.probed or self.busy:return
        self.probed=True
        def done(value,error):
            if error:self.probed=False;self.tell(error);return
            self.caps=value;self.tell('Display detected: '+value['target'])
        self.submit(self.device.probe,done)

    def set_level(self,key,value):
        if self.busy:self.levelFinished.emit(key);return
        def done(actual,error):
            if error:self.tell(error)
            else:self.caps[key]=actual;self.tell(f'{key.title()}: {actual}% (hardware readback)')
            self.levelFinished.emit(key)
        self.submit(lambda:self.device.set_level(key,value),done)

    def change_mode(self,mode):
        if self.busy or self.mode_deadline:return
        if list(mode) not in self.caps['modes']:self.tell('Mode is not reported by this display.');return
        self.mode_before=self.caps['current'];self.mode_changing=True
        def work():
            before=self.device.probe().get('current')
            if not before:raise RuntimeError('Cannot safely change mode without reading the current mode.')
            try:return before,self.device.set_mode(mode),None
            except Exception as exc:return before,None,str(exc)
        def done(result,error):
            self.mode_changing=False
            if result:self.mode_before,actual,error=result
            if error:
                self.tell(error)
                if self.mode_before:self.revert_mode()
            else:
                self.caps['current']=actual;self.mode_deadline=time.monotonic()+15;self.changed.emit()
        self.submit(work,done)

    @Slot()
    def keep_mode(self):
        self.mode_deadline=0;self.mode_before=None;self.tell('Display mode kept for this OS session.')

    @Slot()
    def revert_mode(self):
        if self.mode_before is None:return
        previous=self.mode_before;self.mode_deadline=0;self.mode_before=None
        def done(actual,error):
            if error:self.tell('Display restore failed: '+error)
            else:self.caps['current']=actual;self.tell('Previous display mode restored.')
        self.submit(lambda:self.device.set_mode(previous),done)

    def change_time(self,text):
        try:datetime.datetime.fromisoformat(text)
        except ValueError:self.tell('Use YYYY-MM-DD HH:MM:SS.');return
        self.submit(lambda:self.device.set_time(text),lambda value,error:self.tell(error or 'Host clock updated: '+value))

    def apply_live(self):
        self.app.setFont(QFont(self.theme.fontFamily))
        self.ctl.configure(self.store.values)
        if self.host:self.host.window.update()
        self.changed.emit()

    def set_graph(self,index,key,value):
        settings=deepcopy(self.store.values['graph'+str(index+1)])
        settings[key]=value
        for lo,hi in [('x_min','x_max'),('main_min','main_max'),('error_min','error_max')]:
            if settings[hi]-settings[lo]<(.4 if lo=='x_min' else .04):
                self.tell('Maximum must exceed minimum by a usable graph span.');return False
        if settings['x_max']-settings['x_min']>80:self.tell('Maximum X span is 80 V.');return False
        if any(settings[hi]-settings[lo]>400 for lo,hi in [('main_min','main_max'),('error_min','error_max')]):
            self.tell('Maximum Y span is 400 V (100 V/div).');return False
        self.theme.apply('graph'+str(index+1),settings);return True

    def calibrate(self,index,reset=False):
        from statistics import median
        laser=self.ctl.instrument.lasers[index]
        if not reset and (not laser.emission or laser.signal.level<.95):self.tell('Enable emission and wait for the signal before calibration.');return
        settings=deepcopy(self.store.values['graph'+str(index+1)])
        settings['baseline_main']=0. if reset else median(laser.signal.raw_s)
        settings['baseline_error']=0. if reset else median(laser.signal.raw_e)
        self.theme.apply('graph'+str(index+1),settings)
        self.tell('Baseline reset.' if reset else 'Baseline calibrated from the current frame.')

    def restore(self,factory=False):
        history=[] if factory else self.store.history[:]
        self.store.values=deepcopy(DEFAULTS);self.store.values.update(deepcopy(NEW_DEFAULTS));self.store.history=history
        if factory:
            from controller.model import Instrument
            self.ctl.instrument=Instrument()
            if self.ctl._live:
                for laser in self.ctl.instrument.lasers:laser.signal.emission(True)
        from controller.charts import ChartState
        for laser in self.ctl.instrument.lasers:laser.chart=ChartState()
        self.ctl.preferences={}
        self.store.save();self.theme.changed.emit();self.tell('Application factory settings restored.' if factory else 'Application defaults restored.')

    def export(self,frames=False):
        import json
        root=Path(__file__).resolve().parents[1]/'exports';root.mkdir(exist_ok=True)
        stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        path=root/(f'graph-frame-{stamp}.csv' if frames else f'settings-{stamp}.json')
        try:
            if frames:
                with path.open('w',newline='',encoding='utf8') as f:
                    writer=csv.writer(f);writer.writerow(['laser','x_V','spectroscopy_V','error_V'])
                    for laser in self.ctl.instrument.lasers:
                        for x in laser.signal.x_values:writer.writerow([laser.number,x,*laser.signal.sample(x)])
            else:path.write_text(json.dumps(dict(values=self.store.values,history=self.store.history),indent=2),encoding='utf8')
            self.tell('Saved '+str(path));return path
        except OSError as exc:self.tell(str(exc))

    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.TouchBegin,QEvent.Type.KeyPress,QEvent.Type.Wheel):
            self.idle_since=time.monotonic()
            if self.power_deadline:self.power_deadline=0;self.changed.emit()
        return False

    @Slot()
    def cancel_power(self):self.power_deadline=0;self.idle_since=time.monotonic();self.changed.emit()

    def tick(self):
        now=time.monotonic()
        if self.mode_deadline and now>=self.mode_deadline:self.revert_mode()
        if self._tour>=0 and self._tour_play and now>=self.tour_deadline:self.tourNext()
        minutes=self.store.values.get('idle_minutes',0)
        if minutes and not self.power_deadline and self._tour<0 and now-self.idle_since>=minutes*60:
            self.power_deadline=now+30
        if self.power_deadline and now>=self.power_deadline:
            self.power_deadline=0;self.idle_since=now
            action=self.store.values['idle_action']
            self.submit(lambda:self.device.power(action),lambda value,error:self.tell(error or 'Power action sent to host.'))
        if self.mode_deadline or self.power_deadline:self.changed.emit()

    @Slot()
    def startTour(self):
        self._tour_charts=[deepcopy(l.chart) for l in self.ctl.instrument.lasers]
        self._tour=0;self._tour_play=True;self.route_tour()
    def route_tour(self):
        self.tour_deadline=time.monotonic()+9;self.changed.emit()
        if self.host:
            self.host.window.close_overlay()
            self.host.window.editor.hide()
            section=TOUR[self._tour]['section']
            if section:
                self.host.open();self.host.window.prepare_tour(TOUR[self._tour])
            else:self.host.window.hide();self.host.return_home()
        self.navigateTour.emit(self._tour)
    @Slot()
    def tourNext(self):
        if self._tour>=len(TOUR)-1:self.stopTour()
        else:self._tour+=1;self.route_tour()
    @Slot()
    def tourPrevious(self):self._tour=max(0,self._tour-1);self.route_tour()
    @Slot()
    def tourPause(self):self._tour_play=not self._tour_play;self.tour_deadline=time.monotonic()+9;self.changed.emit()
    @Slot()
    def stopTour(self):
        self._tour=-1
        if hasattr(self,'_tour_charts'):
            for laser,chart in zip(self.ctl.instrument.lasers,self._tour_charts):laser.chart=chart
            del self._tour_charts
            self.ctl.changed.emit()
        if self.host:
            self.host.window.search.setEnabled(True);self.host.window.close_overlay()
        self.navigateTour.emit(-1);self.changed.emit();self.idle_since=time.monotonic()

    def shutdown(self):
        self.timer.stop()
        if self.mode_before:
            previous=self.mode_before;self.mode_before=None
            self.pool.waitForDone(20000)
            try:self.device.set_mode(previous)
            except Exception:pass
        self.pool.waitForDone(20000)
