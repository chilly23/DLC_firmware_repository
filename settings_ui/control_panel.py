"""Control Settings frontend: wiring status, assignment, calibration and touch checks."""
import math,time
from PySide6.QtCore import QRectF,QPointF,Qt,QTimer
from PySide6.QtGui import QColor,QPainter,QPen,QFont
from .refined import RefinedSettingsWindow
from .operational import CONTENT
from .drawing import box,text,line
from .controls import switch
from .screen_check import ScreenCheck
from hardware.config import ACTIONS,OPERATIONS,LOCATIONS,CONTACTS

OP_LABELS=dict(clockwise='Rotate clockwise',anticlockwise='Rotate anticlockwise',up='Joystick up',down='Joystick down',
               left='Joystick left',right='Joystick right',push='Short push')

class KnobSettingsWindow(RefinedSettingsWindow):
    def __init__(self,theme,system):
        self.controls=system.ctl.knobs;self.screen_test=None;self.knob_pose={};self.knob_focus=None;self.knob_adjust=False
        self.control_confirm=None;self.touch_results=None
        super().__init__(theme,system)
        self.controls.changed.connect(self.update)
        self.controls.liveChanged.connect(self.live_input)
        self.controls.notice.connect(self.notify)
    def live_input(self):
        if self.isVisible() and self.content=='control':self.update()
    def select(self,index,absolute=None):
        if getattr(self,'controls',None) and self.controls.calibration:self.controls.cancel_calibration()
        self.clear_knob_focus();super().select(index,absolute)
    def control_rows(self,index):
        choices=list((label,key) for key,label in ACTIONS.items())
        return [('choose','Target corner',f'knob.{index}.target',[(v,i) for i,v in enumerate(LOCATIONS)]),
                ('action','Calibrate directions and push',f'knob_calibrate:{index}'),
                ('choose','Encoder steps per click',f'knob.{index}.steps',[(str(n),n) for n in (1,2,4)]),
                ('knob_toggle','Enable this knob',str(index))]+[
                    ('choose',OP_LABELS[op],f'knob.{index}.{op}',choices) for op in OPERATIONS]+[
                ('action','Restore shortcut defaults',f'knob_defaults:{index}'),
                ('action','Reset calibration',f'knob_reset:{index}')]
    def draw_content(self,p):
        if self.content!='control':
            super().draw_content(p)
            if self.content=='display' and not self.route:
                self.action_button(p,QRectF(1320,110,218,54),'Detecting…' if self.system.busy else 'Retry display',('retry_display',))
            return
        if self.last_content!='control':
            self.route='';self.scroll=0;self.dropdown=None;self.last_content='control'
        if self.route:
            self.action_button(p,QRectF(655,111,130,54),'Back',('page_back',))
            title='Knob calibration' if self.route.startswith('calibrate:') else 'Confirm reset' if self.route=='control-confirm' else f'Knob {int(self.route.split(":")[1])+1} · {LOCATIONS[int(self.route.split(":")[1])]}'
            text(p,810,108,710,60,title,28,bold=True)
        else:text(p,680,108,840,60,'Control Settings',28,bold=True)
        self.dropdown_anchor=None
        p.save();p.setClipRect(CONTENT);p.translate(self.transition,0)
        if self.route.startswith('knob:'):self.draw_assignment(p,int(self.route.split(':')[1]))
        elif self.route.startswith('calibrate:'):self.draw_calibration(p)
        elif self.route=='control-confirm':self.draw_control_confirmation(p)
        else:self.draw_control_home(p)
        p.restore()
        if self.content_height>CONTENT.height():
            h=max(40,CONTENT.height()**2/self.content_height);y=CONTENT.y()+self.scroll/max(1,self.content_height-CONTENT.height())*(CONTENT.height()-h)
            box(p,QRectF(1555,y,5,h),self.theme.muted,2)
    def multiline(self,p,rect,value,size=18,color=None):
        f=QFont(self.theme.fontFamily);f.setPixelSize(round(size*self.theme.fontScale));p.setFont(f);p.setPen(QColor(color or self.theme.foreground))
        p.drawText(rect,Qt.TextFlag.TextWordWrap|Qt.AlignmentFlag.AlignVCenter,value)
    def draw_control_home(self,p):
        self.content_height=487
        for index,x,y in ((0,680,190),(2,1115,190),(1,680,350),(3,1115,350)):
            cfg=self.controls.store.config['knobs'][index];wired=bool(cfg['pins']);rect=QRectF(x,y,411,148)
            box(p,rect,self.theme.surface,12)
            self.draw_knob(p,QRectF(x+10,y+25,100,100),index)
            text(p,x+122,y+10,278,38,f'Knob {index+1} · {LOCATIONS[index]}',24,bold=True)
            status='Not connected' if not wired else 'Disabled' if not cfg['enabled'] else 'Calibrated' if cfg['calibrated'] else 'Calibration needed'
            text(p,x+122,y+48,275,35,status,18,self.theme.muted)
            if wired:self.action_button(p,QRectF(x+122,y+88,273,48),'Configure',('knob_open',index))
        self.multiline(p,QRectF(680,514,850,54),self.controls.status,18,self.theme.muted)
        self.action_button(p,QRectF(680,581,230,62),'Retry GPIO',('gpio_retry',))
        self.action_button(p,QRectF(928,581,265,62),'Screen check',('screen_check',))
        self.action_button(p,QRectF(1211,581,315,62),'Knob guide',('knob_guide',))
    def draw_knob(self,p,rect,index):
        cfg=self.controls.store.config['knobs'][index];frame=self.controls.snapshots.get(index,{})
        raw=frame.get('levels',{});released=cfg['released'];mapping=cfg['directions']
        pressed=lambda name:raw.get(name,released.get(name,1))!=released.get(name,1)
        dx=int(pressed(mapping['right']))-int(pressed(mapping['left']))
        dy=int(pressed(mapping['down']))-int(pressed(mapping['up']))
        angle=frame.get('count',0)*12*(-1 if cfg['reverse_encoder'] else 1)
        target=(dx,dy,angle);pose=self.knob_pose.setdefault(index,list(target))
        for i in range(3):pose[i]+=(target[i]-pose[i])*.3
        c=rect.center();r=rect.width()*.42
        p.setPen(QPen(QColor(self.theme.muted),2));p.setBrush(QColor(self.theme.background));p.drawEllipse(c,r,r)
        for deg in range(0,360,30):
            a=math.radians(deg);line(p,c.x()+math.cos(a)*r*.84,c.y()+math.sin(a)*r*.84,c.x()+math.cos(a)*r*.95,c.y()+math.sin(a)*r*.95,self.theme.muted,1.5)
        center=c+QPointF(pose[0]*r*.22,pose[1]*r*.22)
        push=pressed(cfg['push_contact']) and not any(pressed(c) for c in mapping.values())
        p.setBrush(QColor(self.theme.active if push else self.theme.raised));p.setPen(QPen(QColor(self.theme.foreground),2));p.drawEllipse(center,r*.62,r*.62)
        a=math.radians(pose[2]-90);line(p,center.x()+math.cos(a)*r*.25,center.y()+math.sin(a)*r*.25,center.x()+math.cos(a)*r*.53,center.y()+math.sin(a)*r*.53,self.theme.activeInk if push else self.theme.foreground,3)
        if not cfg['pins']:
            p.setPen(QPen(QColor(self.theme.muted),2));p.drawLine(c+QPointF(-r*.8,r*.8),c+QPointF(r*.8,-r*.8))
    def draw_assignment(self,p,index):
        cfg=self.controls.store.config['knobs'][index]
        ci,key,spec=self.system.ctl.navigation.selection(cfg['target']);value=self.system.ctl.value(ci,key)
        y=190-self.scroll
        text(p,680,y,855,46,f'{LOCATIONS[cfg["target"]]} · {spec["label"]}: {value:.{spec["decimals"]}f} {spec["unit"]}',24)
        rows=self.control_rows(index);height=82*self.theme.uiScale;self.content_height=62+len(rows)*height
        for i,row in enumerate(rows):
            top=247+i*height-self.scroll
            if top+height<185 or top>672:continue
            self.draw_row(p,row,top,height)
        if self.dropdown and self.dropdown_anchor:self.draw_dropdown(p)
    def draw_row(self,p,row,y,height):
        if row[0]!='knob_toggle':return super().draw_row(p,row,y,height)
        index=int(row[2]);on=self.controls.store.config['knobs'][index]['enabled']
        text(p,685,y+8,510,height-16,row[1],24)
        r=QRectF(1430,y+(height-44)/2,82,44);switch(p,r,on,self.theme)
        self.register(QRectF(1115,y+5,415,height-10).intersected(CONTENT),('knob_enable',index))
    def value_label(self,key):
        if key.startswith('knob.'):
            _,index,field=key.split('.');cfg=self.controls.store.config['knobs'][int(index)]
            if field=='target':return LOCATIONS[cfg['target']]
            if field=='steps':return str(cfg['transitions_per_detent'])
            return ACTIONS[cfg['mapping'][field]]
        return super().value_label(key)
    def current_choice(self):
        if self.dropdown and self.dropdown['key'].startswith('knob.'):
            _,index,field=self.dropdown['key'].split('.');cfg=self.controls.store.config['knobs'][int(index)]
            return cfg['target'] if field=='target' else cfg['transitions_per_detent'] if field=='steps' else cfg['mapping'][field]
        return super().current_choice()
    def apply_choice(self,key,value):
        if not key.startswith('knob.'):return super().apply_choice(key,value)
        _,index,field=key.split('.');index=int(index)
        if field=='target':self.controls.set_target(index,value)
        elif field=='steps':self.controls.set_encoder_steps(index,value)
        else:self.controls.assign(index,field,value)
    def draw_calibration(self,p):
        self.content_height=0;cal=self.controls.calibration
        if not cal:
            self.multiline(p,QRectF(680,205,850,170),'Calibration ended. Use Back to return to knob configuration.',24);return
        for i in range(9):box(p,QRectF(680+i*95,190,84,6),self.theme.accent if i<=cal.stage else self.theme.raised,3)
        text(p,680,217,855,50,f'{cal.stage+1}/9 · {cal.title}',28,bold=True)
        self.multiline(p,QRectF(680,269,845,62),cal.detail,18,self.theme.muted)
        self.draw_knob(p,QRectF(700,333,250,250),cal.index)
        frame=self.controls.snapshots.get(cal.index,{});cfg=self.controls.store.config['knobs'][cal.index]
        if cal.stage==8:
            for i,(name,contact) in enumerate(cal.contacts.items()):text(p,1025,335+i*36,500,34,f'{name.title()} → GPIO {cfg["pins"][contact]}',24)
            text(p,1025,515,500,36,'Clockwise → increase',24)
        else:
            for i,(name,pin) in enumerate(cfg['pins'].items()):
                level=frame.get('levels',{}).get(name)
                text(p,1025,334+i*32,270,32,f'{name.replace("encoder_","Encoder ")} · GPIO {pin}',18)
                text(p,1320,334+i*32,210,32,'—' if level is None else 'HIGH · 1' if level else 'LOW · 0',18,self.theme.muted)
        if cal.error:self.multiline(p,QRectF(680,548,850,42),cal.error,16,'#FF9F0A')
        self.action_button(p,QRectF(680,604,230,58),'Cancel',('calibration_cancel',))
        if cal.stage in (0,6,7,8):
            title='Capture released' if cal.stage==0 else 'Save calibration' if cal.stage==8 else 'Next'
            self.action_button(p,QRectF(1130,604,395,58),title,('calibration_save',) if cal.stage==8 else ('calibration_next',))
    def draw_control_confirmation(self,p):
        self.content_height=0;kind,index=self.control_confirm
        message=f'Reset calibration for Knob {index+1}? It will need calibration before its shortcuts can operate.' if kind=='reset' else f'Restore the default shortcuts for Knob {index+1}? Wiring and calibration are preserved.'
        self.multiline(p,QRectF(680,230,830,180),message,28)
        self.action_button(p,QRectF(680,460,400,70),'Cancel',('page_back',))
        self.action_button(p,QRectF(1120,460,400,70),'Confirm',('knob_confirm',))
    def activate(self,action):
        try:
            kind=action[0]
            if kind=='retry_display':self.system.retry_display()
            elif kind=='gpio_retry':self.controls.retry()
            elif kind=='knob_open':self.navigate('knob:'+str(action[1]))
            elif kind=='knob_enable':
                i=action[1];self.controls.enable(i,not self.controls.store.config['knobs'][i]['enabled'])
            elif kind=='settings_action' and action[1].startswith('knob_'):
                name,index=action[1].split(':');index=int(index)
                if name=='knob_calibrate':self.controls.start_calibration(index);self.navigate('calibrate:'+str(index))
                else:self.control_confirm=(name.removeprefix('knob_'),index);self.navigate('control-confirm')
            elif kind=='knob_confirm':
                name,index=self.control_confirm
                self.controls.reset_calibration(index) if name=='reset' else self.controls.restore_mapping(index)
                self.back()
            elif kind=='calibration_next':self.controls.calibration_next()
            elif kind=='calibration_save':self.controls.save_calibration();self.back()
            elif kind=='calibration_cancel':self.controls.cancel_calibration();self.back()
            elif kind=='screen_check':
                self.screen_test=ScreenCheck(self);self.screen_test.finished.connect(self.screen_result);self.screen_test.open(self)
            elif kind=='knob_guide':self.system.startKnobTour()
            else:return super().activate(action)
        except (ValueError,OSError) as exc:self.notify(str(exc))
        self.update()
    def screen_result(self,result):self.touch_results=result;self.notify('Screen check complete. '+', '.join(k+': '+('passed' if v else 'not completed') for k,v in result.items()));self.raise_()
    def back(self):
        if self.controls.calibration:self.controls.cancel_calibration()
        self.clear_knob_focus();super().back()
    def clear_knob_focus(self):
        if self.knob_adjust and self.knob_focus and self.knob_focus[1][0]=='hardware_slider':
            self.display_preview.pop(self.knob_focus[1][1],None)
        self.knob_focus=None;self.knob_adjust=False
        if hasattr(self,'update'):self.update()
    def navigation_hits(self):
        if self.system.powerSeconds:return [(r,a) for r,a in self.hits if a[0]=='cancel_power']
        if self.system.modeSeconds:return [(r,a) for r,a in self.hits if a[0] in ('keep_mode','revert_mode')]
        if self.system.tourIndex>=0:return [(r,a) for r,a in self.hits if a[0].startswith('tour_')]
        if self.dropdown:
            if self.number_drop:return [(r,a) for r,a in self.hits if a[0]=='inline_key']
            # Materialize every dropdown option; focus navigation scrolls it into view.
            return [(QRectF(),('dropdown_value',v)) for label,v in self.dropdown['items']]
        if self.overlay:return [(r,a) for r,a in self.hits if (a[0] in ('key','suggest','clear') if self.overlay=='keyboard' else a[0] in ('clear_history','history','result'))]
        hits=[(QRectF(15,306,577,108),('knob_menu',))]
        hits.extend((r,a) for r,a in self.hits if a[0] not in ('hardware_slider',) or not self.system.busy)
        if self.content_height>487:hits.append((QRectF(1525,185,35,480),('knob_scroll',)))
        return sorted(hits,key=lambda item:(round(item[0].top()/36),item[0].left()))
    def navigate_knob(self,direction,amount=1):
        if self.screen_test and self.screen_test.isVisible():self.screen_test.navigate(direction*amount);return
        if self.knob_adjust and self.knob_focus:
            action=self.knob_focus[1]
            if action[0]=='knob_menu':
                absolute=round(self.motion.target if self.motion.target is not None else self.motion.position)+direction*amount
                super().select(absolute%len(self.order),absolute);self.knob_focus=(QRectF(15,306,577,108),('knob_menu',));self.knob_adjust=True
            elif action[0]=='knob_scroll':self.scroll=self.clamp_scroll(self.scroll+direction*amount*75)
            elif action[0]=='hardware_slider':
                key=action[1];self.display_preview[key]=max(1,min(100,self.display_preview.get(key,self.system.caps[key])+direction*amount))
            self.update();return
        entries=self.navigation_hits()
        if not entries:return
        old=next((i for i,(r,a) in enumerate(entries) if self.knob_focus and repr(a)==repr(self.knob_focus[1])),-1)
        origin=old if old>=0 else (-1 if direction>0 else 0)
        i=(origin+direction*amount)%len(entries)
        r,a=entries[i]
        if self.dropdown and not self.number_drop:
            h=self.drop_rect.height()-12
            self.drop_scroll=max(0,min(max(0,len(entries)*52-h),i*52-h/2+26));self.repaint()
            r=next((r for r,act in reversed(self.hits) if act==a),self.drop_rect)
        self.knob_focus=(r,a);self.update()
    def activate_knob(self):
        if self.screen_test and self.screen_test.isVisible():self.screen_test.activate();return
        if not self.knob_focus:self.navigate_knob(1);return
        action=self.knob_focus[1]
        if action[0] in ('knob_menu','knob_scroll','hardware_slider'):
            if self.knob_adjust and action[0]=='hardware_slider':self.system.set_level(action[1],self.display_preview.get(action[1],self.system.caps[action[1]]))
            self.knob_adjust=not self.knob_adjust;self.update();return
        self.clear_knob_focus();self.activate(action);self.repaint()
        matches=[(r,a) for r,a in self.navigation_hits() if a==action]
        if matches:self.knob_focus=matches[0];self.update()
        else:self.navigate_knob(1)
    def back_knob(self):
        if self.screen_test and self.screen_test.isVisible():self.screen_test.close();return
        if self.knob_adjust:
            if self.knob_focus and self.knob_focus[1][0]=='hardware_slider':self.display_preview.pop(self.knob_focus[1][1],None)
            self.knob_adjust=False;self.update();return
        if self.system.tourIndex>=0:self.system.stopTour()
        elif self.dropdown:self.close_dropdown()
        elif self.overlay:self.close_overlay()
        elif self.route:self.back()
        else:self.close()
        self.clear_knob_focus()
    def input_knob(self,action,amount):
        editor=self.editor if self.editor.isVisible() else self.search if self.overlay=='keyboard' else None
        if editor is None:return False
        if action in ('cursor.left','cursor.right'):
            editor.setCursorPosition(max(0,min(len(editor.text()),editor.cursorPosition()+amount*(1 if action.endswith('right') else -1))));return True
        if action in ('value.increase','value.decrease') and editor is self.editor and (self.editor_spec or {}).get('key')!='clock':
            from interaction.numeric import digit_power,step_value,cursor_for_power
            try:
                power=digit_power(editor.text(),editor.cursorPosition(),3)
                value=step_value(editor.text(),amount*(1 if action.endswith('increase') else -1),power,-1000,1000,3)
                editor.setText(value);editor.setCursorPosition(cursor_for_power(value,power))
            except ValueError as exc:self.notify(str(exc))
            return True
        return False
    def prepare_tour(self,info):
        super().prepare_tour(info)
        if info.get('control_row') is not None:
            h=82*self.theme.uiScale;row=info['control_row']
            self.content_height=62+13*h
            self.scroll=min(max(0,row*h-100),max(0,self.content_height-487))
            self.guide_focus=QRectF(672,247+row*h-self.scroll,868,h)
            self.repaint()
    def show_tip(self):
        super().show_tip()
        if not self.tip:return
        rect,title,body=self.tip
        action=str(self.tip_target[1]) if self.tip_target else ''
        descriptions={
            'knob_open':('Configure knob','Choose a target corner and assign clockwise, anticlockwise, stick and push actions. Calibration is separate from shortcuts.'),
            'knob_calibrate':('Calibrate knob','Record released contacts, each stick direction, the centre press and both encoder directions. Save applies only to this knob.'),
            'knob_reset':('Reset calibration','Clear the learned directions and encoder sign. Shortcuts and wiring are preserved. Calibration will be required again.'),
            'knob_defaults':('Restore shortcuts','Restore the supplied operation mappings for this knob without erasing its calibration.'),
            'screen_check':('Screen check','Check corner taps, a continuous trace, dragging and solid colors. Close returns here; skipped checks are not marked passed.'),
            'gpio_retry':('Retry GPIO','Release controls and retry after reconnecting. Only one GPIO app can own these pins; close the separate RKJXT demo first.'),
            'retry_display':('Detect display again','Retry native backlight and monitor DDC controls after connecting the display or correcting OS permissions.'),
            'knob_guide':('Knob guide','Open the interactive guide at the hardware controls section. It starts paused so you can read at your own pace.'),
        }
        for key,(title,body) in descriptions.items():
            if key in action:self.tip=(rect,title,body);break
    def paintEvent(self,event):
        super().paintEvent(event)
        if self.knob_focus and self.knob_focus[1][0] not in ('notice_accept','notice_close'):
            p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.translate(self.offset);p.scale(self.scale,self.scale)
            r,action=self.knob_focus
            label=str(action[1]) if len(action)>1 else {'knob_menu':'Rotate to choose category','knob_scroll':'Rotate to scroll','close':'Close settings','search':'Search','history':'Search history'}.get(action[0],action[0].replace('_',' ').title())
            if action[0]=='hardware_slider':
                key=action[1];value=self.display_preview.get(key,self.system.caps.get(key,0))
                label=f'{key.title()} : {value}%'
            elif action[0]=='choose_setting':label=self.value_label(action[2])
            box(p,r,self.theme.active,8)
            text(p,r.x()+8,r.y(),r.width()-16,r.height(),label,20,self.theme.activeInk,align=Qt.AlignmentFlag.AlignCenter,literal_color=True)
            label='Rotate to adjust · press to finish' if self.knob_adjust else 'Press to choose · hold push to exit navigation'
            box(p,QRectF(662,675,875,35),self.theme.active,6)
            text(p,675,675,850,35,label,18,self.theme.activeInk,literal_color=True);p.end()
