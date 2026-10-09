"""Operator logs and lock/startup settings, using the existing touch framework."""
from pathlib import Path
from PySide6.QtCore import QRectF,Qt
from .extended_controls import ExtendedSettingsWindow
from .operational import CONTENT
from .drawing import text,box
from interaction.icons import paint_icon

class ConsoleWindow(ExtendedSettingsWindow):
    def __init__(self,theme,system):
        self.journal=system.ctl.journal;self.log_level='all';self.log_live=True;self.log_cache=[];self.log_total=0;self.log_dirty=True
        super().__init__(theme,system);self.journal.changed.connect(self.logs_changed)
    def logs_changed(self):
        self.log_dirty=True
        if self.content=='logs' and self.log_live:self.update()
    def rows(self):
        if self.content=='system' and self.route=='lock':
            return [('action','Lock screen now','lock_now'),
                ('choose','Shutdown when locked','lock_shutdown_seconds',[('Never',0)]+[(f'{n} seconds',n) for n in (30,60,120,300)]),
                ('action','Digital lock input / calibration','lock_input')]
        if self.content=='system' and self.route=='startup':
            from startup import enabled
            return [('choose','Start on login','boot_enabled',[('Enabled',True),('Disabled',False)]),('action','Repair setup / dependencies','setup_repair')]
        rows=super().rows()
        if self.content=='system' and not self.route:rows=rows[:6]+[('nav','Lock screen','lock'),('nav','Startup','startup')]+rows[6:]
        return rows
    def value_label(self,key):
        if key=='lock_shutdown_seconds' and not self.store.values[key]:return 'Never'
        if key=='boot_enabled':
            from startup import enabled
            return 'Enabled' if enabled() else 'Disabled'
        return super().value_label(key)
    def current_choice(self):
        if self.dropdown and self.dropdown['key']=='boot_enabled':
            from startup import enabled
            return enabled()
        if self.dropdown and self.dropdown['key']=='log_level':return self.log_level
        return super().current_choice()
    def apply_choice(self,key,value):
        if key=='boot_enabled':
            try:
                from startup import configure
                configure(bool(value));self.notify('Automatic startup '+('enabled.' if value else 'disabled.'))
            except OSError as exc:self.notifications.post(str(exc),'critical')
        elif key=='log_level':self.log_level=value;self.scroll=0;self.refresh_logs()
        else:super().apply_choice(key,value)
    def action_button(self,p,rect,label,action):
        if action[0] in ('retry_display','gpio_retry'):
            box(p,rect,self.theme.surface,5);paint_icon(p,'retry',QRectF(rect.x()+12,rect.center().y()-13,26,26),self.theme.foreground)
            text(p,rect.x()+47,rect.y(),rect.width()-53,rect.height(),label,20);self.register(rect,action)
        else:super().action_button(p,rect,label,action)
    def draw_notifications(self,p):
        super().draw_notifications(p)
        self.action_button(p,QRectF(1035,110,278,54),'Size: '+self.theme.notificationSize,('choose_setting','Notification size','notification_size',[(s,s) for s in ('Small','Medium','Large')]))
        if self.dropdown and self.dropdown['key']=='notification_size':self.dropdown_anchor=QRectF(1035,110,278,54);self.draw_dropdown(p)
    def refresh_logs(self):
        old=self.log_cache[0]['id'] if self.log_cache else 0
        self.log_cache=self.journal.rows(self.log_level,limit=self.journal.LIMIT);self.log_total=len(self.log_cache);self.log_dirty=False
        if self.scroll>0 and old:self.scroll+=next((i for i,e in enumerate(self.log_cache) if e['id']==old),0)*104
        self.update()
    def draw_content(self,p):
        if self.content!='logs':return super().draw_content(p)
        if self.last_content!='logs':self.scroll=0;self.last_content='logs';self.refresh_logs()
        if self.log_live and self.log_dirty:self.refresh_logs()
        text(p,680,108,225,60,'User logs',30,bold=True)
        for x,width,label,action in [(918,160,'Live' if self.log_live else 'Paused',('log_live',)),(1088,200,'Export',('log_export',)),(1300,232,'Clear logs',('log_clear',))]:self.action_button(p,QRectF(x,110,width,54),label,action)
        self.action_button(p,QRectF(1100,181,432,54),'Level: '+self.log_level.title(),('choose_setting','Log level','log_level',[(s.title(),s) for s in ('all','default','warning','critical')]))
        text(p,680,181,400,54,f'{self.log_total} records',20,self.theme.muted)
        self.content_height=65+self.log_total*104
        p.save();p.setClipRect(QRectF(670,244,875,427))
        first=max(0,int(self.scroll//104)-1)
        for i in range(first,min(self.log_total,first+7)):
            entry=self.log_cache[i];y=248+i*104-self.scroll
            color={'default':self.theme.foreground,'warning':'#FFD60A','critical':'#FF453A'}[entry['level']]
            box(p,QRectF(680,y,852,94),self.theme.surface,8)
            text(p,694,y+5,488,28,entry['timestamp'].replace('T',' ')[:23],18,self.theme.muted)
            text(p,1170,y+5,180,28,entry['status'],18,color)
            text(p,1345,y+5,175,28,entry['level'].title(),18,color)
            self.multiline(p,QRectF(694,y+32,824,57),entry['description'],20)
        p.restore()
        if self.log_total>4:
            track=427;thumb=max(40,track*track/max(track,self.log_total*104));maximum=max(1,self.content_height-487)
            box(p,QRectF(1538,244+min(1,self.scroll/maximum)*(track-thumb),5,thumb),self.theme.active,2)
        if self.dropdown and self.dropdown['key']=='log_level':self.dropdown_anchor=QRectF(1100,181,432,54);self.draw_dropdown(p)
    def activate(self,action):
        kind=action[0]
        if kind=='log_live':self.log_live=not self.log_live;self.refresh_logs()
        elif kind=='log_export':
            try:
                paths=self.journal.export(Path(__file__).resolve().parents[1]/'exports');self.notify('Saved exports/logs.csv and exports/logs.md')
            except OSError as exc:self.notifications.post('Log export failed: '+str(exc),'critical')
        elif kind=='log_clear':self.notifications.post('Clear all user logs? Error reports are retained.','warning',decision=self.journal.clear)
        elif kind=='settings_action' and action[1]=='lock_now':self.system.ctl.session_lock.lock_now()
        elif kind=='settings_action' and action[1]=='lock_input':
            self.select(self.order.index('control'));self.last_content='control';self.navigate('contact:lock')
        elif kind=='settings_action' and action[1]=='setup_repair':
            from startup import repair
            try:repair();self.notify('Setup opened. Complete the OS authentication prompt.')
            except OSError as exc:self.notifications.post(str(exc),'critical')
        else:
            if kind in ('page_nav','knob_open','retry_display','gpio_retry','settings_action'):
                self.journal.record('Requested '+str(action[1] if len(action)>1 else kind),status='Requested',source='Settings')
            return super().activate(action)
        self.update()
