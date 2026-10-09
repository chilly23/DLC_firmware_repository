"""Panel input configuration, theme combinations and the notification inbox."""
from datetime import datetime
from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QPainter,QColor,QPen,QRegion
from .control_panel import KnobSettingsWindow
from .operational import CONTENT
from .drawing import text,box
from .preferences import ACCENTS,THEMES
from hardware.panel import PANEL_LABELS
from hardware.config import ACTIONS

class ExtendedSettingsWindow(KnobSettingsWindow):
    def __init__(self,theme,system):
        self.notifications=system.ctl.notifications
        super().__init__(theme,system)
        self.notifications.changed.connect(self.update)
    def notify(self,message):
        self.notifications.post(message,'warning' if any(w in message.lower() for w in ('unavailable','already assigned','not connected','invalid')) else 'normal')
        self.toast='';self.update()
    def rows(self):
        if self.content=='control' and self.route=='panel':
            return [('nav',label,'contact:'+key) for key,label in PANEL_LABELS.items()]+[
                ('choose','Lock shutdown countdown','lock_shutdown_seconds',[(f'{n} seconds',n) for n in (30,60,120,300)]),
                ('action','Configure Home buttons in Lobby','lobby_buttons'),
                ('action','Knob guide','knob_guide')]
        if self.content=='control' and self.route.startswith('contact:'):
            key=self.route.split(':')[1]
            return [('choose','GPIO pin','panel.'+key+'.pin',[(f'GPIO {n}',n) for n in range(28)]),
                ('choose','Input enabled','panel.'+key+'.enabled',[('Enabled',True),('Disabled',False)]),
                ('choose','Active electrical level','panel.'+key+'.active_level',[('LOW / connected to GND',0),('HIGH / released',1)]),
                ('choose','Contact debounce','panel.'+key+'.debounce_ms',[(f'{n} ms',n) for n in (10,20,25,30,40,50)]),
                ('action','Calibrate - release, then press','panel_calibrate:'+key),
                ('action','Cancel input calibration','panel_cancel')]
        if self.content=='notifications':return []
        rows=super().rows()
        if self.content=='display' and not self.route:
            colors=[('Automatic','Automatic'),('White','#FFFFFF'),('Dark ink','#111111')]+list(ACCENTS.items())
            rows=rows[:2]+[('choose','Recommended theme','theme_preset',[(k+(' - recommended' if k=='Lab Light' else ''),k) for k in THEMES]),
                          ('choose','Corner number color','corner_number_color',colors),('choose','Corner label / icon color','corner_detail_color',colors)]+rows[2:]
        return rows
    def value_label(self,key):
        if key=='lock_shutdown_seconds':return str(self.store.values[key])+' seconds'
        if key.startswith('panel.'):
            _,name,field=key.split('.');v=self.controls.store.config['panel'][name][field]
            if field=='pin':return 'GPIO '+str(v)
            if field=='enabled':return 'Enabled' if v else 'Disabled'
            if field=='active_level':return 'LOW / GND' if v==0 else 'HIGH'
            return str(v)+' ms'
        if key.startswith('shortcut_'):return ACTIONS.get(self.store.values[key],self.store.values[key])
        return super().value_label(key)
    def current_choice(self):
        if self.dropdown and self.dropdown['key'].startswith('panel.'):
            _,name,field=self.dropdown['key'].split('.');return self.controls.store.config['panel'][name][field]
        return super().current_choice()
    def apply_choice(self,key,value):
        if key.startswith('panel.'):
            _,name,field=key.split('.')
            try:self.controls.configure_panel(name,field,value)
            except ValueError as exc:self.notifications.post(str(exc),'warning','gpio-conflict')
            return
        super().apply_choice(key,value)
    def draw_control_home(self,p):
        super().draw_control_home(p)
        self.hits=[(r,a) for r,a in self.hits if a[0]!='knob_guide']
        box(p,QRectF(1210,580,318,65),self.theme.surface,5)
        self.action_button(p,QRectF(1211,581,315,62),'Buttons & lock',('panel_open',))
    def draw_assignment(self,p,index):
        super().draw_assignment(p,index)
        frame=self.controls.snapshots.get(index,{})
        text(p,680,649,852,25,f'Decoded steps: {frame.get("count",0)}   Dispatched actions: {self.controls.delivery.get(index,0)}   Lost edge batches: {frame.get("lost",0)}',16,self.theme.muted)
    def draw_content(self,p):
        if self.content=='notifications':
            self.draw_notifications(p);return
        if self.content!='control' or not (self.route=='panel' or self.route.startswith('contact:')):
            return super().draw_content(p)
        self.last_content='control';self.dropdown_anchor=None
        self.action_button(p,QRectF(655,111,130,54),'Back',('page_back',))
        title='Buttons & system lock' if self.route=='panel' else PANEL_LABELS[self.route.split(':')[1]]
        text(p,810,108,710,60,title,28,bold=True)
        p.save();p.setClipRect(CONTENT)
        if self.route.startswith('contact:'):
            key=self.route.split(':')[1];cfg=self.controls.store.config['panel'][key]
            level=self.controls.panel_snapshot.get('levels',{}).get(key)
            status=f'GPIO {cfg["pin"]} | '+('HIGH' if level==1 else 'LOW' if level==0 else 'Not reading')
            reason=self.controls.issues.get('panel:'+key)
            if reason:status+=' | '+reason
            if key=='left_shortcut' and cfg['pin']==8:status+=' | GPIO8 is assigned to Knob 2 D; choose a free pin.'
            if self.controls.panel_calibration:status+=' | Operate, then release to save.'
            text(p,680,185,854,48,status,18,self.theme.muted);top=240
        else:top=190
        rows=self.rows();self.content_height=top-185+len(rows)*82
        for i,row in enumerate(rows):
            y=top+i*82-self.scroll
            if y+82>185 and y<672:self.draw_row(p,row,y,82)
        if self.dropdown and self.dropdown_anchor:self.draw_dropdown(p)
        p.restore()
    def draw_notifications(self,p):
        self.last_content='notifications'
        text(p,680,108,620,60,'Notifications',30,bold=True)
        self.action_button(p,QRectF(1330,110,205,54),'Clear history',('notice_clear',))
        records=self.notifications.history;self.content_height=max(487,len(records)*93+90)
        p.save();p.setClipRect(CONTENT)
        self.action_button(p,QRectF(680,190-self.scroll,852,64),'Action updates: '+('On' if self.store.values['notification_actions'] else 'Off'),('notice_toggle',))
        if not records:text(p,680,285,850,60,'No notifications yet.',24,self.theme.muted)
        for i,e in enumerate(records):
            y=278+i*93-self.scroll
            if y+90<185 or y>672:continue
            color={'normal':self.theme.foreground,'warning':'#FFD60A','critical':'#FF453A'}[e['level']]
            box(p,QRectF(680,y,852,83),self.theme.surface,8);box(p,QRectF(680,y+12,4,59),color,2)
            stamp=datetime.fromtimestamp(e['time']).strftime('%H:%M:%S')
            text(p,700,y+3,810,27,stamp+'  '+e['level'].title(),16,color)
            self.multiline(p,QRectF(700,y+28,811,48),e['text'],20)
        p.restore()
    def activate(self,action):
        kind=action[0]
        if kind=='settings_action' and action[1]=='lobby_buttons':self.system.ctl.workspace.openPage('buttons')
        elif kind=='panel_open':self.navigate('panel')
        elif kind=='notice_body':return
        elif kind=='notice_close':self.notifications.dismissId(action[1]) if len(action)>1 else self.notifications.dismiss()
        elif kind=='notice_accept':self.notifications.acceptId(action[1]) if len(action)>1 else self.notifications.accept()
        elif kind=='notice_toggle':self.theme.apply('notification_actions',not self.store.values['notification_actions'])
        elif kind=='notice_clear':self.notifications.post('Clear notification history?','warning',decision=self.notifications.clear)
        elif kind=='settings_action' and action[1].startswith('panel_calibrate:'):
            try:self.controls.calibrate_panel(action[1].split(':')[1])
            except ValueError as exc:self.notify(str(exc))
        elif kind=='settings_action' and action[1]=='panel_cancel':self.controls.panel_calibration=None;self.notify('Input calibration cancelled.')
        elif kind=='settings_action' and action[1]=='knob_guide':self.system.startKnobTour()
        elif kind=='settings_action' and action[1] in ('restore','factory'):
            factory=action[1]=='factory'
            self.notifications.post('Factory reset application data?' if factory else 'Restore application defaults?','warning',decision=lambda:self.system.restore(factory))
        else:return super().activate(action)
        self.update()
    def back(self):
        self.controls.panel_calibration=None;super().back()
    def back_knob(self):
        if self.notifications.toast['decision']:
            self.notifications.dismiss();self.clear_knob_focus();return
        super().back_knob()
    def navigation_hits(self):
        if self.notifications.toast['decision']:return [(r,a) for r,a in self.hits if a[0] in ('notice_accept','notice_close')]
        return [(r,a) for r,a in super().navigation_hits() if a[0]!='notice_body']
    def notice_under_editor(self,pt):
        return not self.notifications.toast['decision'] and (
            (self.dropdown and self.drop_rect.contains(pt)) or
            (self.overlay and self.popup_rect().contains(pt)))
    def pointer_down(self,pt):
        notice=None if self.notice_under_editor(pt) else next(((r,a) for r,a in reversed(self.hits) if a[0] in ('notice_body','notice_close','notice_accept') and r.contains(pt)),None)
        self._notice_press=notice is not None
        if notice:
            self.tip_timer.stop();self.backspace_hold.stop();self.tip=None;self.tip_consumed=False
            self.pending=notice;self.gesture=None;self.dragged=False;self.content_pressed=False;self.content_moved=False;self.velocity=0
            return
        super().pointer_down(pt)
    def pointer_move(self,pt):
        if getattr(self,'_notice_press',False):return
        super().pointer_move(pt)
    def pointer_up(self,pt):
        if getattr(self,'_notice_press',False):
            self._notice_press=False;pending=self.pending;self.pending=None
            if pending and pending[0].contains(pt):self.activate(pending[1])
            return
        super().pointer_up(pt)
    def wheelEvent(self,event):
        if self.notice_under_editor(self.point(event.position())):super().wheelEvent(event);return
        if any(a[0]=='notice_body' and r.contains(self.point(event.position())) for r,a in self.hits):event.accept();return
        super().wheelEvent(event)
    def paintEvent(self,event):
        super().paintEvent(event)
        entries=self.notifications.cards
        if not entries or self.overlay=='keyboard' or self.system.tourIndex>=0:return
        from interaction.notification_art import buttons,metrics
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.translate(self.offset);p.scale(self.scale,self.scale)
        if not self.notifications.toast['decision']:
            editor=self.drop_rect if self.dropdown else self.popup_rect() if self.overlay else None
            if editor is not None:p.setClipRegion(QRegion(0,0,1600,720).subtracted(QRegion(editor.toAlignedRect())))
        positions=getattr(self,'_notice_positions',{});new_positions={}
        width,height,_=metrics(self.theme.notificationSize,True);left=1540-width
        for index,entry in enumerate(entries):
            target=708-height-(len(entries)-1-index)*(height+10)
            y=positions.get(entry['id'],target);y+=min(1,.24)*(target-y)
            if abs(target-y)<.3:y=target
            new_positions[entry['id']]=y
            focused=''
            if self.knob_focus and len(self.knob_focus[1])>1 and self.knob_focus[1][1]==entry['id']:
                focused={'notice_close':'close','notice_accept':'accept'}.get(self.knob_focus[1][0],'')
            image=self.notifications.renderer.image(entry,width,height,focused)
            p.setOpacity(entry['alpha']);p.drawImage(QRectF(left,y,width,height),image)
            self.notifications.renderer.paint_progress(p,entry,width,height,left,y)
            self.register(QRectF(left,y,width,height),('notice_body',entry['id']))
            for rect,action in buttons(width,height,entry['decision']):
                self.register(rect.translated(left,y),('notice_'+action if action=='accept' else 'notice_close',entry['id']))
        self._notice_positions=new_positions;p.end()
