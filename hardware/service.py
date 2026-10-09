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
    panelAction=Signal(str)
    lockChanged=Signal(bool)
    def __init__(self,path,parent=None,*,worker_factory=None,autostart=True):
        super().__init__(parent);self.store=ControlStore(path);self.worker_factory=worker_factory
        self.worker=None;self.connected=False;self.status_text='GPIO is available on the Raspberry Pi; touch controls remain active.'
        self.snapshots={};self.calibration=None;self.navigation=False;self.last_action='';self.held={};self.pushes={}
        self.armed=set();self.quiet_since={};self.last_lost={};self.preview=False;self.direction_gestures=set()
        self.suspended=False;self.panel_snapshot={};self.panel_calibration=None;self.panel_armed=set();self.delivery={}
        self.context_handler=None;self.navigation_sides=set()
        self.presentation=QTimer(self);self.presentation.setSingleShot(True);self.presentation.setInterval(33)
        self.presentation.timeout.connect(self.changed)
        self.issues={};self.reconnect_attempt=0;self.stopping=False;self.reconfiguring=False
        self.reconnect=QTimer(self);self.reconnect.setSingleShot(True);self.reconnect.timeout.connect(self.retry)
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
        if self.stopping:return
        self.reconnect.stop()
        from .gpio import GPIOWorker
        if self.worker and hasattr(self.worker,'submit') and self.worker.isRunning():
            if self.worker.config!=self.store.config:
                self.reconfiguring=True
                self.worker.reconfigure(self.store.config)
            else:self.worker.submit('retry')
            return
        self.stop_worker();self.reset_delivery()
        if sys.platform!='linux' and self.worker_factory is None:
            self.set_status(False,'Desktop mode ? no GPIO device. Configure mappings here; calibrate on the Pi.');return
        self.worker=(self.worker_factory or GPIOWorker)(self.store.config)
        self.worker.frames.connect(self.receive);self.worker.status.connect(self.set_status)
        if hasattr(self.worker,'panelFrames'):self.worker.panelFrames.connect(self.receive_panel)
        if hasattr(self.worker,'availability'):self.worker.availability.connect(self.set_availability)
        if hasattr(self.worker,'reset'):self.worker.reset.connect(self.reset_delivery)
        if hasattr(self.worker,'fault'):self.worker.fault.connect(self.hardware_fault)
        if hasattr(self.worker,'finished'):self.worker.finished.connect(self.worker_finished)
        self.worker.start()
    def worker_finished(self):
        if self.sender() is not None and self.sender()!=self.worker:return
        if self.stopping:return
        self.set_status(False,'GPIO owner stopped; reconnecting with a new owner.')
    def reset_delivery(self):
        self.snapshots.clear();self.armed.clear();self.held.clear();self.pushes.clear()
        self.panel_armed.clear();self.panel_snapshot={};self.issues={}
        self.quiet_since.clear();self.last_lost.clear();self.direction_gestures.clear()
        self.reconfiguring=False
    def hardware_fault(self, fault):
        message=f"{fault['group']}: {fault['message']}"
        if fault['group'].startswith('knob:'):
            index=int(fault['group'].split(':')[1])
            self.armed.discard(index);self.pushes.pop(index,None);self.snapshots.pop(index,None)
            self.held={key:value for key,value in self.held.items() if key[0]!=index}
            self.direction_gestures.discard(index);self.quiet_since.pop(index,None)
        LOG.warning(message)
        self.notice.emit(message)
    def metrics(self):
        return self.worker.snapshot() if self.worker and hasattr(self.worker,'snapshot') else {}
    def set_availability(self,issues):
        if self.sender() is not None and self.sender()!=self.worker:return
        self.issues=dict(issues);self.changed.emit()
    def stop_worker(self):
        if self.worker:self.worker.stop();self.worker.deleteLater();self.worker=None
        self.connected=False
    def set_status(self,connected,text):
        if self.sender() is not None and self.sender()!=self.worker:return
        self.connected=connected;self.status_text=text+(' · '+self.store.error if self.store.error else '')
        LOG.info('%s | connected=%s',text,connected)
        if not connected:
            self.direction_gestures.clear()
            self.armed.clear();self.held.clear();self.pushes.clear();self.quiet_since.clear();self.snapshots.clear()
            if self.calibration:self.calibration.error='GPIO disconnected. Cancel, reconnect and choose Retry GPIO.'
            self.panel_snapshot={}
            if not self.stopping and (sys.platform=='linux' or self.worker_factory is not None) and not (self.worker and hasattr(self.worker,'submit') and self.worker.isRunning()):
                self.reconnect_attempt+=1
                delay=min(8000,1000*2**min(3,self.reconnect_attempt-1))
                self.reconnect.start(delay);self.status_text+=f' Retrying in {delay//1000}s.'
        else:
            self.reconnect_attempt=0
            # The worker keeps partial inputs live and watches blocked pins.
            self.reconnect.stop()
        self.changed.emit()
    def receive(self,frames):
        if self.sender() is not None and self.sender()!=self.worker:return
        for index,frame in frames.items():
            index=int(index)
            if frame.get('initial'):
                self.armed.discard(index);self.quiet_since.pop(index,None);self.pushes.pop(index,None)
                self.held={k:v for k,v in self.held.items() if k[0]!=index}
                self.direction_gestures.discard(index);self.last_lost.pop(index,None)
            self.snapshots[index]=frame
            now=frame.get('captured_ns',int(time.monotonic()*1e9))/1e9
            config=self.store.config['knobs'][index]
            if self.calibration:
                if self.calibration.index==index:self.calibration.feed(frame['levels'],frame['count'],now)
                continue
            if self.suspended or self.panel_calibration or self.reconfiguring:continue
            lost=frame.get('lost',0)
            if lost!=self.last_lost.get(index,lost):
                self.direction_gestures.discard(index)
                self.armed.discard(index);self.held={k:v for k,v in self.held.items() if k[0]!=index};self.pushes.pop(index,None)
                self.quiet_since.pop(index,None);self.notice.emit(f'Knob {index+1}: missed GPIO edges; release controls to resume.')
            self.last_lost[index]=lost
            if not self.connected or not config['enabled'] or not config['calibrated']:continue
            if index not in self.armed:
                if not any(frame['switches'].values()):
                    if now-self.quiet_since.setdefault(index,now)>=.25:self.armed.add(index)
                else:self.quiet_since.pop(index,None)
                continue
            mapping={v:k for k,v in config['directions'].items()};mapping[config['push_contact']]='push'
            # Reconstruct the start of this batch, then replay transitions in
            # capture order. The final snapshot is not every event's state.
            state=dict(frame['switches'])
            for name,value in reversed(frame.get('events',[])):
                if name!='rotation':state[name]=not bool(value)
            times=frame.get('event_times',[])
            events=[]
            for pos,(name,value) in enumerate(frame.get('events',[])):
                stamp=times[pos]/1e9 if pos<len(times) else now
                # Lossless same-direction addition only; never cross a contact
                # edge or direction reversal. Carry the oldest capture time.
                if name=='rotation' and events and events[-1][0]=='rotation' and events[-1][1]*value>0:
                    old=events[-1];events[-1]=(name,old[1]+value,old[2])
                else:events.append((name,value,stamp))
            for name,value,stamp in events:
                if name=='rotation':
                    delta=value*(-1 if config['reverse_encoder'] else 1)
                    self.dispatch(index,'clockwise' if delta>0 else 'anticlockwise',abs(delta));continue
                state[name]=bool(value)
                operation=mapping[name]
                directions=[d for d,c in config['directions'].items() if state.get(c)]
                if directions:
                    self.direction_gestures.add(index)
                    if index in self.pushes:self.pushes[index][1]=True
                if operation=='push':
                    if value:self.pushes[index]=[stamp,index in self.direction_gestures]
                    else:
                        press=self.pushes.pop(index,None)
                        if press and not press[1]:
                            if stamp-press[0]>=.7:self.toggle_navigation(index)
                            else:self.dispatch(index,'push')
                else:
                    key=(index,operation)
                    if value and len(directions)==1:
                        self.dispatch(index,operation);self.held[key]=stamp+.45
                    elif not value:self.held.pop(key,None)
                if not any(state.values()):self.direction_gestures.discard(index)
        self.liveChanged.emit()
    def present_status(self):
        if not self.presentation.isActive():self.presentation.start()
    def dispatch(self,index,operation,amount=1):
        if self.calibration or self.suspended or self.panel_calibration or self.reconfiguring:return
        if self.context_handler and self.context_handler(index,operation,amount):
            self.delivery[index]=self.delivery.get(index,0)+amount;self.present_status();return
        action=self.store.config['knobs'][index]['mapping'][operation]
        if (0 if index<2 else 1) in self.navigation_sides:
            action={'clockwise':'focus.next','anticlockwise':'focus.previous','up':'focus.previous','down':'focus.next',
                    'left':'focus.back','right':'focus.activate','push':'focus.activate'}[operation]
        if action=='none':return
        self.last_action=f'Knob {index+1} · {ACTIONS.get(action,action)}'
        LOG.debug('knob=%s operation=%s command=%s steps=%s',index+1,operation,action,amount)
        amount=max(1,int(amount));self.delivery[index]=self.delivery.get(index,0)+amount
        self.command.emit(index,action,amount);self.present_status()
    def tick(self):
        if self.calibration or self.panel_calibration or self.suspended or self.reconfiguring or not self.connected:return
        if self.worker and hasattr(self.worker,'mailbox') and self.worker.mailbox.snapshot()['pending']:return
        now=time.monotonic()
        for index,press in list(self.pushes.items()):
            if not press[1] and now-press[0]>=.7:press[1]=True;self.toggle_navigation(index)
        repeatable={'focus.next','focus.previous','cursor.left','cursor.right','graph.left','graph.right','graph.up','graph.down','value.increase','value.decrease'}
        for key,due in list(self.held.items()):
            index,operation=key
            if now<due:continue
            frame=self.snapshots.get(index,{});cfg=self.store.config['knobs'][index]
            active=[d for d,c in cfg['directions'].items() if frame.get('switches',{}).get(c)]
            if active!=[operation]:self.held.pop(key,None);continue
            if (0 if index<2 else 1) in self.navigation_sides or cfg['mapping'][operation] in repeatable:self.dispatch(index,operation)
            self.held[key]=now+.12
    @Slot()
    def toggle_navigation(self,index=0):
        side=0 if index<2 else 1
        if side in self.navigation_sides:self.navigation_sides.remove(side)
        else:self.navigation_sides.add(side)
        self.navigation=bool(self.navigation_sides)
        self.command.emit(index,'navigation.enter' if side in self.navigation_sides else 'navigation.exit',1)
        self.notice.emit(('Left' if side==0 else 'Right')+(' knob navigation on: rotate to focus, press to choose, left to go back.' if side in self.navigation_sides else ' knob shortcuts restored.'))
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
        if not self.connected or index not in self.snapshots:
            reason=self.issues.get('knob:'+str(index),self.status_text)
            raise ValueError(f'Knob {index+1} GPIO is not ready: {reason}')
        self.calibration=Calibration(index,self.store.config['knobs'][index]);self.held.clear();self.pushes.clear();self.direction_gestures.clear()
        frame=self.snapshots[index];self.calibration.feed(frame['levels'],frame['count'],time.monotonic());self.changed.emit()
    def calibration_next(self):
        if self.calibration:self.calibration.next(time.monotonic());self.changed.emit()
    def save_calibration(self):
        calibration=self.calibration
        if not calibration:return
        cfg=deepcopy(self.store.config);cfg['knobs'][calibration.index]=calibration.result();self.store.commit(cfg)
        self.calibration=None;self.retry();self.notice.emit('Knob calibration saved.');self.changed.emit()
    def cancel_calibration(self):self.calibration=None;self.held.clear();self.pushes.clear();self.direction_gestures.clear();self.armed.clear();self.quiet_since.clear();self.changed.emit()
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
    def shutdown(self):self.stopping=True;self.reconnect.stop();self.timer.stop();self.presentation.stop();self.stop_worker()

    def receive_panel(self,frame):
        if self.sender() is not None and self.sender()!=self.worker:return
        newly_seen=set(frame.get('active',{}))-set(self.panel_snapshot.get('active',{}))
        for field in ('levels','active'):
            self.panel_snapshot.setdefault(field,{}).update(frame.get(field,{}))
        if frame.get('initial') or frame.get('resync'):
            self.panel_armed.difference_update(frame.get('active',{}))
        # Calibrating an emission/shortcut contact must not suppress the lock.
        # Only the lock's own explicit polarity capture bypasses its action.
        if not self.panel_calibration or self.panel_calibration['key']!='lock':
            lock_events=[active for name,active in frame.get('events',[]) if name=='lock']
            if lock_events:
                for active in lock_events:self.lockChanged.emit(bool(active))
            elif 'lock' in frame.get('active',{}):self.lockChanged.emit(bool(frame['active']['lock']))
        if self.panel_calibration:
            cal=self.panel_calibration;key=cal['key'];cfg=self.store.config['panel'][key]
            if key not in frame.get('active',{}):return
            value=cfg['active_level'] if frame.get('active',{}).get(key) else 1-cfg['active_level']
            if value is not None and value!=cal['released']:cal['pressed']=value
            if cal.get('pressed') is not None and value==cal['released']:
                cfg=deepcopy(self.store.config);cfg['panel'][key].update(active_level=cal['pressed'],calibrated=True)
                self.store.commit(cfg);self.panel_calibration=None;self.notice.emit('Panel contact calibrated.');self.retry()
            self.liveChanged.emit();return
        events=frame.get('events',[])
        state=dict(frame.get('active',{}))
        for key,active in reversed(events):state[key]=not bool(active)
        for key,active in state.items():
            if not active:self.panel_armed.add(key)
        for key,active in events:
            if not active:
                self.panel_armed.add(key)
            elif key!='lock' and key in self.panel_armed and key not in newly_seen:
                self.panel_armed.discard(key)
                if not self.suspended and not self.reconfiguring and self.store.config['panel'][key].get('calibrated'):
                    self.panelAction.emit(key)
        self.liveChanged.emit()

    def configure_panel(self,key,field,value):
        cfg=deepcopy(self.store.config);cfg['panel'][key][field]=value
        self.store.commit(cfg);self.panel_armed.clear();self.retry();self.changed.emit()

    def calibrate_panel(self,key):
        if not self.connected or key not in self.panel_snapshot.get('levels',{}):
            reason=self.issues.get('panel:'+key,self.status_text)
            raise ValueError('Panel input is not ready: '+reason)
        self.panel_calibration=dict(key=key,released=self.panel_snapshot['levels'][key],pressed=None)
        self.held.clear();self.pushes.clear();self.notice.emit('Released level captured. Operate this control once, then release it.');self.changed.emit()
