"""v1.7 touch refinements: two-laser table, anchored dropdowns and tooltips."""
import math
import time
from PySide6.QtCore import QRectF, QPointF, Qt, QTimer, QEvent
from PySide6.QtGui import QColor, QPainter, QFont
from .operational import OperationalSettingsWindow, CONTENT
from .window import SettingsWindow
from .drawing import text, box, line
from .controls import slider, slider_geometry, chevron, switch, tooltip
from .preferences import ACCENTS

LIMITS=[('X minimum','x_min'),('X maximum','x_max'),('Main minimum','main_min'),
        ('Main maximum','main_max'),('Error minimum','error_min'),('Error maximum','error_max')]
FUNCTION_ROWS=[
    ('choose','Sampling rate','sampling_rate',[(f'{n} Hz',n) for n in (5,10,20,30,60)]),
    ('action','Calibrate baseline','calibrate',[]),
    ('action','Reset baseline','baseline_reset',[]),
    ('toggle','Auto bandwidth','auto_bandwidth',[]),
    ('choose','Maximum points','max_points',[(str(n),n) for n in (256,512,1001,2001,4001)]),
]+[('number',label,key,[]) for label,key in LIMITS]+[
    ('choose','Main color','main_color',[('Default trace','#C2C5C2')]+list(ACCENTS.items())),
    ('choose','Error color','error_color',[('Default trace','#C2C5C2')]+list(ACCENTS.items())),
    ('choose','Laser color','laser_color',[('Default white','#D9D9D9'),('Default blue','#2362E5')]+list(ACCENTS.items())),
    ('choose','Main width','main_width',[(f'{n:g} px',n) for n in (1.,1.5,1.7,2.,2.5,3.,4.)]),
    ('choose','Error width','error_width',[(f'{n:g} px',n) for n in (1.,1.5,1.7,2.,2.5,3.,4.)]),
    ('choose','Main stroke','main_style',[(k,k) for k in ('Solid','Dashed','Dotted')]),
    ('choose','Error stroke','error_style',[(k,k) for k in ('Solid','Dashed','Dotted')])]


class RefinedSettingsWindow(OperationalSettingsWindow):
    def __init__(self,theme,system):
        self.drop_scroll=0.;self.drop_velocity=0.;self.drop_rect=QRectF()
        self.drop_drag=False;self.drop_start=QPointF();self.drop_last=QPointF()
        self.tip=None;self.tip_target=None;self.tip_consumed=False
        self.number_drop=False;self.numeric_error=''
        self.slider_rect=QRectF();self.slider_grab=0.;self.slider_held=False
        super().__init__(theme,system)
        self.tip_timer=QTimer(self);self.tip_timer.setSingleShot(True);self.tip_timer.setInterval(850)
        self.tip_timer.timeout.connect(self.show_tip)
        system.levelFinished.connect(self.level_finished)

    def level_finished(self,key):
        self.display_preview.pop(key,None);self.update()

    def select(self,index,absolute=None):
        self.tip=None;self.number_drop=False
        super().select(index,absolute)

    def draw_content(self,p):
        if self.content!='function':
            super().draw_content(p);return
        if self.last_content!=self.content:
            self.route='';self.route_stack=[];self.scroll=0;self.dropdown=None
            self.editor_spec=None;self.editor.hide();self.last_content=self.content
        # All per-laser controls stay in this table; there is no laser picker.
        text(p,680,106,850,60,'Function Settings',36,bold=True)
        self.dropdown_anchor=None
        p.save();p.setClipRect(CONTENT)
        h=76*self.theme.uiScale
        self.content_height=60+len(FUNCTION_ROWS)*h
        for i,(kind,label,key,options) in enumerate(FUNCTION_ROWS):
            y=CONTENT.top()+60+i*h-self.scroll
            if y+h<CONTENT.top()+60 or y>CONTENT.bottom():continue
            p.save();p.setClipRect(QRectF(650,245,914,427),Qt.ClipOperation.IntersectClip)
            text(p,680,y+6,305,h-12,label,24)
            line(p,680,y+h-1,1535,y+h-1,self.theme.raised,.8)
            for index,x in enumerate((1000,1270)):
                rect=QRectF(x,y+8,254,h-16);clipped=rect.intersected(QRectF(650,245,914,427))
                if clipped.height()<35:continue
                action=('table',index,kind,label,key,options)
                if kind=='toggle':
                    on=self.store.values[f'graph{index+1}'][key]
                    switch(p,QRectF(x+158,y+(h-44)/2,82,44),on,self.theme)
                    text(p,x+10,y+5,125,h-10,'On' if on else 'Off',24)
                else:
                    box(p,rect,self.theme.surface,8)
                    value='Apply' if kind=='action' else self.table_value(index,key,options)
                    text(p,x+12,y+6,206,h-12,value,24)
                    if kind in ('choose','number'):chevron(p,rect,self.theme)
                self.register(clipped,action)
                if self.dropdown and self.dropdown.get('index')==index and self.dropdown['key']==key:
                    self.dropdown_anchor=rect
            p.restore()
        # Sticky headers remain readable while swiping the table.
        box(p,QRectF(650,185,914,60),self.theme.background)
        text(p,680,187,300,50,'Parameter',24,bold=True)
        for x,index in ((1000,0),(1270,1)):
            text(p,x,187,254,50,f'Laser {index+1}',28,bold=True)
        if self.dropdown and self.dropdown_anchor:self.draw_dropdown(p)
        p.restore()
        if self.content_height>487:
            h=max(35,487**2/self.content_height)
            box(p,QRectF(1555,185+self.scroll/(self.content_height-487)*(487-h),5,h),self.theme.muted,2)

    def table_value(self,index,key,options=()):
        if key=='laser_color':value=self.store.values[f'laser{index+1}_color']
        elif key=='sampling_rate':value=self.store.values[key]
        else:value=self.store.values[f'graph{index+1}'][key]
        for label,v in options:
            if value==v:return label
        return f'{value:g}' if isinstance(value,float) else str(value)

    def draw_row(self,p,row,y,height):
        if row[0]!='hardware':
            super().draw_row(p,row,y,height)
            if row[0]=='choose':chevron(p,QRectF(1115,y+10,417,height-20),self.theme)
            return
        _,label,key=row
        text(p,685,y+10,365,height-20,label,24)
        line(p,680,y+height-1,1535,y+height-1,self.theme.raised,.8)
        value=self.display_preview.get(key,self.system.caps.get(key))
        rect=QRectF(1090,y+(height-56)/2,438,56)
        if value is None:
            text(p,1100,y+10,428,height-20,'Unavailable',24,self.theme.muted)
            self.register(rect.intersected(CONTENT),('hardware_reason',key));return
        slider(p,rect,value,self.theme)
        if not self.system.busy:
            self.register(rect.intersected(CONTENT),('hardware_slider',key,rect))

    def open_dropdown(self,label,key,options,index=None,numeric=False):
        if self.dropdown and self.dropdown['key']==key and self.dropdown.get('index')==index:
            self.close_dropdown();return
        self.velocity=0;self.drop_scroll=0;self.drop_velocity=0
        self.dropdown=dict(label=label,key=key,items=options,index=index)
        self.number_drop=numeric;self.numeric_error=''
        if numeric:
            self.editor.setText(self.table_value(index,key));self.editor.selectAll()
            QTimer.singleShot(0,self.editor.setFocus)
        self.update()

    def close_dropdown(self):
        self.dropdown=None;self.drop_velocity=0;self.number_drop=False;self.drop_rect=QRectF()
        self.editor.hide();self.editor_spec=None;self.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.update()

    def draw_dropdown(self,p):
        if not self.dropdown_anchor:return
        anchor=self.dropdown_anchor;numeric=self.number_drop
        h=374 if numeric else min(330,52*len(self.dropdown['items'])+12)
        w=max(anchor.width(),400 if numeric else 315)
        x=min(1540-w,max(655,anchor.x()))
        y=anchor.bottom()+5
        if y+h>CONTENT.bottom():y=max(190,anchor.top()-h-5)
        rect=QRectF(x,y,w,h);self.drop_rect=rect
        box(p,rect.adjusted(3,5,3,5),'#44000000',9)
        box(p,rect,self.theme.surface,9,self.theme.muted)
        if numeric:
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            edit_rect=QRectF(x+12,y+10,w-24,48)
            self.editor.setGeometry(round(self.offset.x()+edit_rect.x()*self.scale),round(self.offset.y()+edit_rect.y()*self.scale),round(edit_rect.width()*self.scale),round(edit_rect.height()*self.scale))
            self.editor.show()
            keys=['7','8','9','backspace','4','5','6','-','1','2','3','Cancel','0','.','left','Apply']
            for i,key in enumerate(keys):
                r=QRectF(x+10+i%4*(w-20)/4,y+65+i//4*65,(w-20)/4-6,58)
                box(p,r,'#A92621' if key=='Cancel' else self.theme.background if key.isdigit() else self.theme.raised,5)
                label={'backspace':'⌫','left':'←','-':'−'}.get(key,key)
                text(p,r.x()+3,r.y(),r.width()-6,r.height(),label,24,'#FFFFFF' if key=='Cancel' else self.theme.foreground,align=Qt.AlignmentFlag.AlignCenter,literal_color=True)
                self.register(r,('inline_key',key))
            text(p,x+12,y+h-40,w-24,35,self.numeric_error,16,'#FF8A80')
            return
        items=self.dropdown['items'];self.drop_scroll=max(0,min(self.drop_scroll,max(0,len(items)*52-(h-12))))
        p.save();p.setClipRect(rect.adjusted(6,6,-6,-6),Qt.ClipOperation.IntersectClip)
        for i,(label,value) in enumerate(items):
            r=QRectF(x+6,y+6+i*52-self.drop_scroll,w-12,50)
            if not r.intersects(rect):continue
            selected=self.current_choice()==value
            if selected:box(p,r,self.theme.active,6)
            color=ACCENTS.get(value) if self.dropdown['key']=='accent' else value if isinstance(value,str) and value.startswith('#') else None
            if color:box(p,QRectF(x+18,r.y()+13,24,24),color,12,self.theme.muted)
            text(p,x+(55 if color else 18),r.y(),w-(72 if color else 40),50,str(label),24,
                 self.theme.activeInk if selected else self.theme.foreground,literal_color=True)
            hit=r.intersected(rect.adjusted(6,6,-6,-6))
            if hit.height()>30:self.register(hit,('dropdown_value',value))
        p.restore()
        if len(items)*52>h-12:
            sh=max(24,(h-12)**2/(len(items)*52))
            sy=y+6+self.drop_scroll/(len(items)*52-h+12)*(h-12-sh)
            box(p,QRectF(rect.right()-5,sy,3,sh),self.theme.muted,1)

    def current_choice(self):
        key=self.dropdown['key'];idx=self.dropdown.get('index')
        if idx is not None:
            if key=='laser_color':return self.store.values[f'laser{idx+1}_color']
            if key!='sampling_rate':return self.store.values[f'graph{idx+1}'][key]
        if key=='resolution':return (self.system.caps.get('current') or [])[:2]
        if key=='refresh':return (self.system.caps.get('current') or [0,0,0])[2]
        return self.store.values.get(key)

    def activate(self,action):
        kind=action[0]
        if kind=='table':
            _,idx,typ,label,key,options=action;self.laser_index=idx
            if typ in ('choose','number'):self.open_dropdown(label,key,options,idx,typ=='number')
            elif typ=='toggle':self.system.set_graph(idx,key,not self.store.values[f'graph{idx+1}'][key])
            elif typ=='action':self.system.calibrate(idx,key=='baseline_reset')
            self.update();return
        if kind=='choose_setting':
            _,label,key,options=action
            if options:self.open_dropdown(label,key,options)
            else:self.notify(self.system.caps.get('reasons',{}).get('mode','No options available.'))
            return
        if kind=='dropdown_value':
            idx=self.dropdown.get('index');key=self.dropdown['key']
            if idx is not None:self.laser_index=idx
            self.close_dropdown();self.apply_choice(key,action[1]);self.update();return
        if kind=='inline_key':
            key=action[1]
            if key=='Cancel':self.close_dropdown()
            elif key=='Apply':self.commit_editor()
            elif key=='backspace':self.editor.backspace()
            elif key=='left':self.editor.setCursorPosition(max(0,self.editor.cursorPosition()-1))
            elif key=='-':
                v=self.editor.text();self.editor.setText(v[1:] if v.startswith('-') else '-'+v)
            elif key=='.' and '.' in self.editor.text() and not self.editor.hasSelectedText():pass
            else:self.editor.insert(key)
            self.update();return
        super().activate(action)

    def commit_editor(self):
        if not self.number_drop:return super().commit_editor()
        try:v=float(self.editor.text())
        except ValueError:self.numeric_error='Enter a number';self.update();return
        if not math.isfinite(v) or not -1000<=v<=1000:self.numeric_error='Range: −1000 to 1000 V';self.update();return
        d=self.dropdown
        if self.system.set_graph(d['index'],d['key'],v):self.close_dropdown()
        else:self.numeric_error=self.system.status;self.update()

    def pointer_down(self,pt):
        self.tip=None;self.tip_consumed=False
        if self.system.tourIndex>=0 and self.system.tour.get('section'):
            self.pending=next(((r,a) for r,a in reversed(self.hits) if a[0].startswith('tour_') and r.contains(pt)),None)
            self.content_pressed=False;return
        if self.dropdown:
            if not self.drop_rect.contains(pt):self.close_dropdown();self.pending=None;return
            self.pending=next(((r,a) for r,a in reversed(self.hits) if a[0] in ('dropdown_value','inline_key') and r.contains(pt)),None)
            self.drop_start=self.drop_last=pt;self.drop_drag=True;self.content_moved=False;self.content_pressed=False;self.drop_velocity=0
            if self.pending and self.pending[1]==('inline_key','backspace'):self.backspace_hold.start()
            self.update();return
        super().pointer_down(pt)
        if self.slider_action:
            self.content_pressed=False;self.slider_held=True;self.velocity=0
            self.slider_rect=self.pending[1][2] if len(self.pending[1])>2 else QRectF(1090,200,438,56)
            current=self.system.caps.get(self.slider_action,50);thumb=slider_geometry(self.slider_rect,current)
            self.slider_grab=pt.x()-thumb.left() if thumb.contains(pt) else thumb.width()/2
            self.move_hardware_slider(pt)
        elif self.pending and self.pending[1][0] not in ('key','edit_key'):
            self.tip_target=self.pending;self.tip_timer.start()

    def move_hardware_slider(self,pt):
        if not self.slider_held:return
        rect=self.slider_rect;tw=min(100.,rect.width()*.265)
        v=round(1+99*max(0,min(1,(pt.x()-rect.x()-4-self.slider_grab)/(rect.width()-tw-8))))
        if self.display_preview.get(self.slider_action)!=v:self.display_preview[self.slider_action]=v;self.update()

    def pointer_move(self,pt):
        if self.drop_drag:
            if (pt-self.drop_start).manhattanLength()>8:self.content_moved=True;self.pending=None;self.backspace_hold.stop()
            if not self.number_drop:
                delta=pt.y()-self.drop_last.y();self.drop_scroll-=delta;self.drop_velocity=-delta*25
                self.drop_last=pt;self.update()
            return
        if self.tip_target and not self.tip_target[0].contains(pt):self.tip_timer.stop()
        super().pointer_move(pt)
        if self.content_moved:self.tip_timer.stop()

    def pointer_up(self,pt):
        self.tip_timer.stop()
        if self.tip_consumed:self.pending=None;self.content_pressed=False;self.tip_consumed=False;return
        if self.drop_drag:
            self.drop_drag=False;self.backspace_hold.stop()
            if self.pending and self.pending[0].contains(pt) and not self.content_moved:self.activate(self.pending[1])
            self.pending=None;self.update();return
        if self.slider_action:
            key=self.slider_action;self.move_hardware_slider(pt)
            v=self.display_preview.get(key,self.system.caps[key])
            self.slider_action=None;self.slider_held=False;self.pending=None;self.content_pressed=False
            self.system.set_level(key,v);self.update();return
        super().pointer_up(pt)

    def wheelEvent(self,event):
        pt=self.point(event.position())
        if self.dropdown and self.drop_rect.contains(pt):
            if not self.number_drop:self.drop_scroll-=event.angleDelta().y()/2;self.update()
            event.accept();return
        super().wheelEvent(event)

    def tick(self):
        super().tick()
        if self.dropdown and not self.drop_drag and not self.number_drop and abs(self.drop_velocity)>2:
            self.drop_scroll+=self.drop_velocity*.016;self.drop_velocity*=.88;self.update()

    def clear_held_input(self):
        if self.number_drop and self.pending and self.pending[1]==('inline_key','backspace'):
            self.editor.clear();self.pending=None;self.update()
        else:super().clear_held_input()

    def event(self,event):
        if event.type()==QEvent.Type.TouchCancel:
            self.slider_action=None;self.slider_held=False;self.content_pressed=False;self.drop_drag=False
            self.display_preview.clear()
        return super().event(event)

    def show_tip(self):
        if not self.tip_target:return
        rect,action=self.tip_target
        label=str(action[3] if action[0]=='table' else action[1] if len(action)>1 else action[0]).replace('_',' ').title()
        descriptions={'history':'Tap a recent search to fill the search bar and search again. Clear removes the saved list.',
                      'search':'Search settings. Tap outside the keyboard to dismiss it.',
                      'calibrate':'Use the current live frame as the zero reference.',
                      'brightness':'Change the actual display brightness. Release to apply.',
                      'contrast':'Change the actual monitor contrast when supported.'}
        body=next((v for k,v in descriptions.items() if k in str(action).lower()),'Tap to adjust this option. Changes apply to the selected control immediately.')
        self.tip=(rect,label,body);self.tip_consumed=True;self.pending=None;self.update()

    def paintEvent(self,event):
        super().paintEvent(event)
        if self.tip and self.system.tourIndex<0:
            p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.translate(self.offset);p.scale(self.scale,self.scale)
            tooltip(p,*self.tip,self.theme);p.end()

    def prepare_tour(self,info):
        self.search.setEnabled(True)
        index=self.order.index(info['section']);self.select(index)
        self.motion.position=float(index);self.motion.target=None;self.motion.velocity=0
        self.selected=self.last_index=index;self.content=self.last_content=info['section']
        self.route=info.get('route','');self.slide.stop();self.transition=0
        row=info.get('row');self.scroll=0
        if row is not None:
            h=(76 if self.content=='function' else 86)*self.theme.uiScale
            top=245 if self.content=='function' else 282 if self.content=='storage' else 185
            count=len(FUNCTION_ROWS) if self.content=='function' else len(self.rows())
            self.scroll=min(max(0,row*h-180),max(0,top-185+count*h-487))
            self.guide_focus=QRectF(672,top+row*h-self.scroll,868,h)
        else:self.guide_focus=QRectF(*info['rect'])
        if info.get('action')=='keyboard':self.open_search();self.search.setEnabled(False)
        elif info.get('action')=='history':self.activate(('history',))
        self.repaint()

    def draw_guide(self,p):
        from PySide6.QtGui import QTextDocument
        import html
        info=self.system.tour;r=getattr(self,'guide_focus',QRectF(*info['rect']))
        for mask in [QRectF(0,0,1600,r.top()),QRectF(0,r.bottom(),1600,720-r.bottom()),
                     QRectF(0,r.top(),r.left(),r.height()),QRectF(r.right(),r.top(),1600-r.right(),r.height())]:
            box(p,mask,'#73000000')
        p.setBrush(Qt.BrushStyle.NoBrush)
        from PySide6.QtGui import QPen
        p.setPen(QPen(QColor(self.theme.accent),2));p.drawRoundedRect(r,8,8)
        # Keep the guide on the wheel side; the highlighted setting stays uncovered.
        if info.get('action')=='keyboard':
            box(p,QRectF(280,8,1040,202),self.theme.surface,14)
            text(p,300,16,1000,46,f'{self.system.tourIndex+1}/{info["count"]}  '+info['title'],24,bold=True)
            doc=QTextDocument();f=QFont(self.theme.fontFamily);f.setPixelSize(18);doc.setDefaultFont(f);doc.setTextWidth(990)
            doc.setHtml('<div style="color:'+self.theme.foreground+'">'+html.escape(info['body'])+'</div>')
            p.save();p.translate(300,64);doc.drawContents(p);p.restore()
            for x,label,act in [(300,'Skip guide','tour_skip'),(540,'Pause' if self.system.tourPlaying else 'Play','tour_pause'),(780,'Previous','tour_back'),(1020,'Next','tour_next')]:
                self.action_button(p,QRectF(x,148,220,50),label,(act,))
            return
        y=233
        rect=QRectF(22,y,600,298);box(p,rect,self.theme.surface,14)
        text(p,42,y+12,560,48,f'{self.system.tourIndex+1}/{info["count"]}  '+info['title'],24,bold=True)
        doc=QTextDocument();f=QFont(self.theme.fontFamily);f.setPixelSize(18);doc.setDefaultFont(f);doc.setTextWidth(555)
        doc.setHtml('<div style="color:'+self.theme.foreground+'">'+html.escape(info['body'])+'</div>')
        p.save();p.translate(43,y+70);doc.drawContents(p);p.restore()
        for x,w,label,act in [(42,132,'Skip guide','tour_skip'),(182,110,'Pause' if self.system.tourPlaying else 'Play','tour_pause'),(300,144,'Previous','tour_back'),(452,148,'Finish' if self.system.tourIndex==info['count']-1 else 'Next','tour_next')]:
            b=QRectF(x,y+226,w,54)
            box(p,b,self.theme.accent if act=='tour_next' else self.theme.raised,8)
            text(p,x+6,y+226,w-12,54,label,18,self.theme.accentInk if act=='tour_next' else self.theme.foreground,align=Qt.AlignmentFlag.AlignCenter,literal_color=True)
            self.register(b,(act,))
