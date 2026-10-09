"""Panel input configuration, theme combinations and the notification inbox."""
from datetime import datetime
from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QPainter,QColor,QPen
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
                ('choose','Left shortcut','shortcut_left',list((v,k) for k,v in ACTIONS.items())),
                ('choose','Right shortcut','shortcut_right',list((v,k) for k,v in ACTIONS.items())),
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
        if kind=='panel_open':self.navigate('panel')
        elif kind=='notice_close':self.notifications.dismiss()
        elif kind=='notice_accept':self.notifications.accept()
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
        return super().navigation_hits()
    def paintEvent(self,event):
        super().paintEvent(event)
        entry=self.notifications.toast
        if not entry['text'] or self.overlay=='keyboard' or self.system.tourIndex>=0:return
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.translate(self.offset);p.scale(self.scale,self.scale)
        rect=QRectF(680,624,860,84);box(p,rect,self.theme.surface,12)
        color={'normal':self.theme.foreground,'warning':'#FFD60A','critical':'#FF453A'}[entry['level']]
        box(p,QRectF(680,637,4,58),color,2)
        # Vector warning symbol avoids platform-dependent emoji rendering.
        p.setPen(QPen(QColor(color),2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QPolygonF
        if entry['level']=='warning':p.drawPolygon(QPolygonF([QPointF(710,641),QPointF(725,669),QPointF(695,669)]))
        else:p.drawEllipse(QRectF(696,642,28,28))
        text(p,700,641,20,30,'!',19,color,align=Qt.AlignmentFlag.AlignCenter)
        self.multiline(p,QRectF(743,634,555 if entry['decision'] else 730,60),entry['text'],20)
        buttons=[(QRectF(1480,641,50,50),'×',('notice_close',))]
        if entry['decision']:buttons.insert(0,(QRectF(1310,642,137,48),'Confirm',('notice_accept',)))
        for rect,label,action in buttons:
            focused=self.knob_focus and self.knob_focus[1]==action
            box(p,rect,self.theme.active if focused else self.theme.raised,8)
            text(p,rect.x()+4,rect.y(),rect.width()-8,rect.height(),label,21,self.theme.activeInk if focused else self.theme.foreground,align=Qt.AlignmentFlag.AlignCenter,literal_color=True)
            self.register(rect,action)
        p.end()
