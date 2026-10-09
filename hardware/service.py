"""Small application-facing interface: status, mappings, calibration and semantic commands.

The hardware layer never imports controller, QML or settings widgets.
"""
from copy import deepcopy
import sys,time,logging
from PySide6.QtCore import QObject,Signal,Property,Slot,QTimer
from .config import ControlStore,ACTIONS,OPERATIONS,DIRECTIONS,default_knob
from .calibration import Calibration
LOG=logging.getLogger('nexatom.gpio')

class KnobService(QObject):
    changed=Signal()
    liveChanged=Signal()
    command=Signal(int,str,int)
    notice=Signal(str)
    def __init__(self,path,parent=None,*,worker_factory=None,autostart=True):
        super().__init__(parent);self.store=ControlStore(path);self.worker_factory=worker_factory
        self.worker=None;self.connected=False;self.status_text='GPIO is available on the Raspberry Pi; touch controls remain active.'
        self.snapshots={};self.calibration=None;self.navigation=False;self.last_action='';self.held={};self.pushes={}
        self.armed=set();self.quiet_since={};self.last_lost={};self.preview=False
        self.timer=QTimer(self);self.timer.setInterval(25);self.timer.timeout.connect(self.tick);self.timer.start()
        if self.store.error:self.status_text=self.store.error
        if autostart:QTimer.singleShot(0,self.retry)
    @Property(str,notify=changed)
    def status(self):return self.status_text
    @Property(bool,notify=changed)
    def online(self):return self.connected
    @Property(bool,notify=changed)
    def navigationMode(self):return self.navigation
    @Property('QVariantList',notify=changed)
    def knobs(self):return deepcopy(self.store.config['knobs'])
    @Property(str,notify=changed)
    def lastAction(self):return self.last_action
    @Slot()
    def retry(self):
        self.stop_worker();self.snapshots.clear();self.armed.clear();self.held.clear();self.pushes.clear()
        self.quiet_since.clear();self.last_lost.clear()
        if sys.platform!='linux' and self.worker_factory is None:
            self.set_status(False,'Desktop mode · no GPIO device. Configure mappings here; calibrate on the Pi.');return
        from .gpio import GPIOWorker
        self.worker=(self.worker_factory or GPIOWorker)(self.store.config)
        self.worker.frames.connect(self.receive);self.worker.status.connect(self.set_status);self.worker.start()
    def stop_worker(self):
        if self.worker:self.worker.stop();self.worker.deleteLater();self.worker=None
        self.connected=False
    def set_status(self,connected,text):
        if self.sender() is not None and self.sender()!=self.worker:return
        self.connected=connected;self.status_text=text+(' · '+self.store.error if self.store.error else '')
        LOG.info('%s | connected=%s',text,connected)
        if not connected:
            self.armed.clear();self.held.clear();self.pushes.clear();self.quiet_since.clear();self.snapshots.clear()
            if self.calibration:self.calibration.error='GPIO disconnected. Cancel, reconnect and choose Retry GPIO.'
        self.changed.emit()
    def receive(self,frames):
        if self.sender() is not None and self.sender()!=self.worker:return
        now=time.monotonic()
        for index,frame in frames.items():
            index=int(index);self.snapshots[index]=frame
            config=self.store.config['knobs'][index]
            if self.calibration:
                if self.calibration.index==index:self.calibration.feed(frame['levels'],frame['count'],now)
                continue
            lost=frame.get('lost',0)
            if lost!=self.last_lost.get(index,lost):
                self.armed.discard(index);self.held={k:v for k,v in self.held.items() if k[0]!=index};self.pushes.pop(index,None)
                self.quiet_since.pop(index,None);self.notice.emit(f'Knob {index+1}: missed GPIO edges; release controls to resume.')
            self.last_lost[index]=lost
            if not self.connected or not config['enabled'] or not config['calibrated']:continue
            # A held contact on startup/reconnect never generates a shortcut.
            if index not in self.armed:
                if not any(frame['switches'].values()):
                    if now-self.quiet_since.setdefault(index,now)>=.25:self.armed.add(index)
                else:self.quiet_since.pop(index,None)
                continue
            mapping={v:k for k,v in config['directions'].items()};mapping[config['push_contact']]='push'
            for name,value in frame.get('events',[]):
                if name=='rotation':
                    delta=value*(-1 if config['reverse_encoder'] else 1)
                    self.dispatch(index,'clockwise' if delta>0 else 'anticlockwise',abs(delta));continue
                operation=mapping[name]
                if operation=='push':
                    if value:self.pushes[index]=[now,False]
                    else:
                        press=self.pushes.pop(index,None)
                        if press and not press[1]:
                            if now-press[0]>=.7:self.toggle_navigation()
                            else:self.dispatch(index,'push')
                    continue
                key=(index,operation)
                if value:
                    # Opposing or diagonal contacts are not repeated as commands.
                    active=[d for d,c in config['directions'].items() if frame['switches'].get(c)]
                    if len(active)>1:continue
                    self.dispatch(index,operation);self.held[key]=now+.45
                else:self.held.pop(key,None)
        self.liveChanged.emit()
    def dispatch(self,index,operation,amount=1):
        if self.calibration:return
        action=self.store.config['knobs'][index]['mapping'][operation]
        if self.navigation:
            action={'clockwise':'focus.next','anticlockwise':'focus.previous','up':'focus.previous','down':'focus.next',
                    'left':'focus.back','right':'focus.activate','push':'focus.activate'}[operation]
        if action=='none':return
        self.last_action=f'Knob {index+1} · {ACTIONS.get(action,action)}'
        LOG.debug('knob=%s operation=%s command=%s steps=%s',index+1,operation,action,amount)
        self.command.emit(index,action,max(1,min(24,amount)));self.changed.emit()
    def tick(self):
        if self.calibration or not self.connected:return
        now=time.monotonic()
        for index,press in list(self.pushes.items()):
            if not press[1] and now-press[0]>=.7:press[1]=True;self.toggle_navigation()
        repeatable={'focus.next','focus.previous','cursor.left','cursor.right','graph.left','graph.right','graph.up','graph.down','value.increase','value.decrease'}
        for key,due in list(self.held.items()):
            index,operation=key
            if now<due:continue
            frame=self.snapshots.get(index,{});cfg=self.store.config['knobs'][index]
            active=[d for d,c in cfg['directions'].items() if frame.get('switches',{}).get(c)]
            if active!=[operation]:self.held.pop(key,None);continue
            if self.navigation or cfg['mapping'][operation] in repeatable:self.dispatch(index,operation)
            self.held[key]=now+.12
    @Slot()
    def toggle_navigation(self):
        self.navigation=not self.navigation
        self.command.emit(0,'navigation.enter' if self.navigation else 'navigation.exit',1)
        self.notice.emit('Knob navigation on: rotate to focus, press to choose, left to go back.' if self.navigation else 'Knob shortcuts restored.')
        self.changed.emit()
    def assign(self,index,operation,action):
        if operation not in OPERATIONS or action not in ACTIONS:raise ValueError('Unknown mapping')
        mapping=dict(self.store.config['knobs'][index]['mapping']);mapping[operation]=action
        self.store.update(index,'mapping',mapping);self.changed.emit()
    def set_target(self,index,target):self.store.update(index,'target',target);self.changed.emit()
    def enable(self,index,enabled):
        if not self.store.config['knobs'][index]['pins']:return
        self.store.update(index,'enabled',bool(enabled));self.retry();self.changed.emit()
    def start_calibration(self,index):
        if not self.connected or index not in self.snapshots:raise ValueError('Connect the knob GPIO first, then choose Retry GPIO.')
        self.calibration=Calibration(index,self.store.config['knobs'][index]);self.held.clear();self.pushes.clear()
        frame=self.snapshots[index];self.calibration.feed(frame['levels'],frame['count'],time.monotonic());self.changed.emit()
    def calibration_next(self):
        if self.calibration:self.calibration.next(time.monotonic());self.changed.emit()
    def save_calibration(self):
        calibration=self.calibration
        if not calibration:return
        cfg=deepcopy(self.store.config);cfg['knobs'][calibration.index]=calibration.result();self.store.commit(cfg)
        self.calibration=None;self.retry();self.notice.emit('Knob calibration saved.');self.changed.emit()
    def cancel_calibration(self):self.calibration=None;self.held.clear();self.pushes.clear();self.armed.clear();self.quiet_since.clear();self.changed.emit()
    def reset_calibration(self,index):
        cfg=deepcopy(self.store.config);old=cfg['knobs'][index];new=default_knob(index)
        for key in ('calibrated','directions','push_contact','released','reverse_encoder'):old[key]=new[key]
        self.store.commit(cfg);self.cancel_calibration();self.retry()
    def restore_mapping(self,index):self.store.update(index,'mapping',default_knob(index)['mapping']);self.changed.emit()
    def set_encoder_steps(self,index,value):self.store.update(index,'transitions_per_detent',value);self.retry();self.changed.emit()
    @Slot(int,str)
    def preview_action(self,index,operation):
        # Explicit software preview never pretends GPIO was detected or calibrated.
        if operation in OPERATIONS and not self.calibration:self.dispatch(index,operation)
    def shutdown(self):self.timer.stop();self.stop_worker()
