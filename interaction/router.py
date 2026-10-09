"""Knob commands use the same visible controls and validated values as touch.

Focus collection is constrained to the topmost panel and its clipped viewport.
No GPIO numbers or edge decoding appear in this module.
"""
import time
from PySide6.QtCore import QObject,Signal,Slot,Property,QPointF,QRectF,QEvent,QCoreApplication,QTimer,Qt
from PySide6.QtGui import QMouseEvent
from shiboken6 import isValid
from .numeric import step_value,digit_power,cursor_for_power

class InputRouter(QObject):
    changed=Signal()
    def __init__(self,controller,knobs,parent=None):
        super().__init__(parent);self.ctl=controller;self.knobs=knobs;self.window=None;self.host=None
        self.target=None;self.adjusting=False;self._focus={};self._corner=-1;self._power={};self._edit_until=0
        self.side=0;self.side_targets={};knobs.context_handler=self.operation
        self.timer=QTimer(self);self.timer.setInterval(60);self.timer.timeout.connect(self.refresh_focus);self.timer.start()
        knobs.command.connect(self.handle);knobs.notice.connect(controller.notify)
    def attach(self,window,host):self.window=window;self.host=host;self.logs=window.findChild(QObject,'logsWindow')
    def surface(self):return self.logs if getattr(self,'logs',None) and self.logs.isVisible() else self.window
    @Property('QVariantMap',notify=changed)
    def focus(self):return dict(x=0,y=0,width=0,height=0,label='',active=False,**self._focus) if not self._focus else self._focus
    @Property(int,notify=changed)
    def editCorner(self):return self._corner if time.monotonic()<self._edit_until else -1
    @Property(int,notify=changed)
    def digitPower(self):return self._power.get(self._corner,-3)
    @Slot(int,result=int)
    def powerFor(self,corner):return self._power.get(corner,-3)
    def native(self):return self.host and self.host.window.isVisible()
    def diagnostic_screen(self):
        screen=getattr(getattr(self.ctl.workspace,'diagnostics',None),'screen',None)
        return screen if screen and screen.isVisible() else None
    def find(self,name,root=None):
        if not self.window:return None
        stack=[root or self.surface().contentItem()]
        while stack:
            item=stack.pop()
            if item.objectName()==name:return item
            stack.extend(item.childItems())
    def scope(self):
        if self.surface()!=self.window:
            confirmation=self.find('logsClearConfirmation')
            return confirmation if confirmation and confirmation.isVisible() else self.surface().contentItem()
        if self.ctl.notifications.toast['decision']:
            notice=self.find('notificationToast')
            if notice and notice.isVisible():return notice
        for name in ('powerCountdown','tourOverlay','tooltipOverlay','emissionConfirm','keypad','alarmPanel','signalsPanel','radialMenu','selector','lobby'):
            item=self.find(name)
            if item and item.isVisible():return item
        return self.window.contentItem()
    def rect(self,item):
        rect=item.mapRectToScene(QRectF(0,0,item.width(),item.height()))
        parent=item.parentItem()
        while parent:
            if parent.clip():rect=rect.intersected(parent.mapRectToScene(QRectF(0,0,parent.width(),parent.height())))
            parent=parent.parentItem()
        return rect.intersected(QRectF(0,0,self.surface().width(),self.surface().height()))
    def targets(self):
        scope=self.scope();stack=[scope];found=[]
        while stack:
            item=stack.pop()
            if not item.isVisible() or not item.isEnabled():continue
            label=item.property('navLabel')
            if label and item.property('navEnabled') is not False:
                r=self.rect(item)
                home=scope==self.window.contentItem() and self.window.property('fullscreenSide')<0
                within_side=not home or ((r.center().x()<self.window.width()/2)==(self.side==0))
                if r.width()>=24 and r.height()>=24 and within_side:found.append((item,r,str(label)))
            stack.extend(item.childItems())
        return sorted(found,key=lambda e:(round(e[1].top()/36),e[1].left()))
    def clear_focus(self):self.target=None;self.adjusting=False;self._focus={};self.changed.emit()
    def refresh_focus(self):
        if self._corner>=0 and time.monotonic()>=self._edit_until:self._corner=-1;self.changed.emit()
        if self.target is not None:
            if not isValid(self.target) or not self.target.isVisible() or self.native():self.clear_focus();return
            r=self.rect(self.target)
            self._focus=dict(x=r.x(),y=r.y(),width=r.width(),height=r.height(),label=('Adjust · ' if self.adjusting else '')+str(self.target.property('navLabel')),active=True)
            self.changed.emit()
    def move_focus(self,direction,amount=1):
        if self.diagnostic_screen():self.clear_focus();self.diagnostic_screen().navigate(direction*amount);return
        if self.native():self.clear_focus();self.host.window.navigate_knob(direction,amount);return
        if self.adjusting and self.target:
            self.target.stepFromKnob(direction*amount);return
        entries=self.targets()
        if not entries:return
        current=next((i for i,e in enumerate(entries) if e[0]==self.target),-1)
        origin=current if current>=0 else (-1 if direction>0 else 0)
        index=(origin+direction*amount)%len(entries)
        self.target=entries[index][0];self.refresh_focus()
    def activate(self):
        if self.diagnostic_screen():self.diagnostic_screen().activate();return
        if self.native():self.host.window.activate_knob();return
        if not self.target or not isValid(self.target):self.move_focus(1);return
        if self.target.property('navKind') in ('slider','choice'):self.adjusting=not self.adjusting;self.refresh_focus();return
        previous=self.target;r=self.rect(previous);p=r.center();self.clear_focus()
        for typ,buttons in ((QEvent.Type.MouseButtonPress,Qt.MouseButton.LeftButton),(QEvent.Type.MouseButtonRelease,Qt.MouseButton.NoButton)):
            event=QMouseEvent(typ,p,self.surface().mapToGlobal(p.toPoint()),Qt.MouseButton.LeftButton,buttons,Qt.KeyboardModifier.NoModifier)
            QCoreApplication.sendEvent(self.surface(),event)
        entries=self.targets()
        if any(obj==previous for obj,rect,label in entries):self.target=previous;self.refresh_focus()
        elif self.scope().objectName() not in ('radialMenu','emissionConfirm'):self.move_focus(1)
    def back(self):
        if self.diagnostic_screen():self.diagnostic_screen().close();self.clear_focus();return
        if self.adjusting:self.adjusting=False;self.refresh_focus();return
        if self.native():self.host.window.back_knob();return
        if self.surface()!=self.window:
            if self.logs.property('confirmClear'):self.logs.setProperty('confirmClear',False)
            else:self.logs.dismiss()
            self.clear_focus();return
        if self.ctl.notifications.toast['decision']:self.ctl.notifications.dismiss();self.clear_focus();return
        self.clear_focus();self.window.dismissKnobPanel()
    def selection(self,corner):
        side=0 if corner<2 else 1;index=self.ctl.instrument.views[side];laser=self.ctl.instrument.lasers[index]
        key=laser.bottom_field() if corner%2 else laser.top_field()
        return index,key,self.ctl.parameter(key)
    @Slot(int,int)
    def moveDigit(self,corner,direction):
        index,key,spec=self.selection(corner);value=self.ctl.value(index,key)
        whole=len(str(abs(int(value))))-1
        power=self._power.get(corner,-spec['decimals'])+direction
        self._power[corner]=max(-spec['decimals'],min(whole,power));self._corner=corner;self._edit_until=time.monotonic()+5;self.changed.emit()
    @Slot(int,int)
    def adjustCorner(self,corner,delta):
        index,key,spec=self.selection(corner)
        whole=len(str(abs(int(self.ctl.value(index,key)))))-1
        power=max(-spec['decimals'],min(whole,self._power.get(corner,-spec['decimals'])))
        self._power[corner]=power
        value=step_value(self.ctl.value(index,key),delta,power,spec['minimum'],spec['maximum'],spec['decimals'])
        error=self.ctl.setValue(index,key,value)
        if error:self.ctl.notify(error)
        self._corner=corner;self._edit_until=time.monotonic()+5;self.changed.emit()
    @Slot(str,str,int,int,result='QVariantMap')
    def stepDraft(self,key,text,cursor,delta):
        spec=self.ctl.parameter(key)
        try:
            power=digit_power(text,cursor,spec['decimals']);updated=step_value(text,delta,power,spec['minimum'],spec['maximum'],spec['decimals'])
            return dict(text=updated,cursor=cursor_for_power(updated,power),error='')
        except ValueError as exc:return dict(text=text,cursor=cursor,error=str(exc))
    @Slot(int,str,int)
    def handle(self,index,action,amount):
        if not self.window:return
        if getattr(self.ctl,'session_lock',None) and self.ctl.session_lock.locked:return
        self.set_side(index)
        self.ctl.system_settings.idle_since=time.monotonic()
        if action=='navigation.enter':self.move_focus(1);return
        if action=='navigation.exit':
            if self.native():self.host.window.clear_knob_focus()
            self.clear_focus();return
        if action in ('focus.next','focus.previous'):self.move_focus(1 if action.endswith('next') else -1,amount);return
        if action=='focus.activate':self.activate();return
        if action=='focus.back':self.back();return
        if self.native() and self.host.window.input_knob(action,amount):return
        corner=self.knobs.store.config['knobs'][index]['target']
        if action=='settings.open':self.ctl.openSettings();return
        if action=='capture.frame':self.ctl.system_settings.export(True);return
        if action=='capture.screenshot':self.ctl.workspace.captureScreen();return
        if action=='lobby.open':self.ctl.workspace.openPage('lobby');return
        if action=='logs.open':self.ctl.workspace.openLogs();return
        if self.native() and action in ('more.open','signals.open','view.fullscreen','editor.open'):
            self.host.window.close()
        self.window.performKnob(action,corner,amount)
    def set_side(self,index):
        side=0 if index<2 else 1
        if side!=self.side:
            self.side_targets[self.side]=self.target;self.target=self.side_targets.get(side);self.side=side;self.adjusting=False
            self.refresh_focus()
    def operation(self,index,operation,amount):
        if not self.window:return False
        if getattr(self.ctl,'session_lock',None) and self.ctl.session_lock.locked:return True
        self.set_side(index);self.ctl.system_settings.idle_since=time.monotonic()
        delta=amount*(1 if operation=='clockwise' else -1)
        if self.native():
            native=self.host.window
            if operation in ('clockwise','anticlockwise'):
                if not native.input_knob('value.increase' if delta>0 else 'value.decrease',abs(delta)):native.navigate_knob(1 if delta>0 else -1,abs(delta))
            elif operation=='push':native.activate_knob()
            elif operation=='left':native.back_knob()
            elif operation=='right':native.activate_knob()
            else:native.navigate_knob(-1 if operation=='up' else 1,amount)
            return True
        scope=self.scope();name=scope.objectName()
        if scope==self.window.contentItem():return False
        owner=scope.property('ownerSide')
        if owner is None:owner=scope.property('side')
        if owner is not None and int(owner)!=self.side:return True
        if name=='radialMenu':
            if operation in ('clockwise','anticlockwise'):self.move_focus(1 if delta>0 else -1,abs(delta))
            elif operation=='push':scope.dismiss('')
            elif operation in ('left','right'):self.activate()
            else:self.move_focus(-1 if operation=='up' else 1,amount)
        elif name=='emissionConfirm':
            if operation in ('clockwise','anticlockwise'):scope.rotateSteps(delta)
            elif operation=='push':scope.knobConfirm()
            elif operation=='left':scope.cancel()
            else:scope.rotateSteps(-amount if operation=='down' else amount)
        elif name=='keypad' and self.side not in self.knobs.navigation_sides:
            if operation in ('clockwise','anticlockwise','left','right'):
                action={'clockwise':'value.increase','anticlockwise':'value.decrease','left':'cursor.left','right':'cursor.right'}[operation]
                self.window.performKnob(action,self.knobs.store.config['knobs'][index]['target'],amount)
            elif operation=='push':scope.key('enter')
            elif operation=='down':scope.key('close')
            elif operation=='up':scope.key('-')
        elif operation in ('clockwise','anticlockwise'):self.move_focus(1 if delta>0 else -1,abs(delta))
        elif operation in ('push','right'):self.activate()
        elif operation=='left':self.back()
        else:self.move_focus(-1 if operation=='up' else 1,amount)
        return True
    def shutdown(self):self.timer.stop()
