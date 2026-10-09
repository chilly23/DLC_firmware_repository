"""Touch settings pages; wheel navigation and search are inherited from v1.6.

The right panel owns its navigation stack and kinetic document/list scrolling.
Native host work is delegated to SettingsCoordinator.
"""
from copy import deepcopy
import datetime
import html
import math
import platform
import shutil
import time
from pathlib import Path
from PySide6.QtCore import QPointF,QRectF,Qt,QVariantAnimation,QEasingCurve,QEvent
from PySide6.QtGui import QColor,QFont,QFontDatabase,QPainter,QPen,QTextDocument
from PySide6.QtWidgets import QLineEdit
from .window import SettingsWindow
from .drawing import text,box,line,cross,search_icon,history_icon
from . import drawing
from .layout import SEARCH_RECT,HISTORY_RECT,INPUT_RECT,KEYBOARD_INPUT_RECT,KEYBOARD_RECT
from .model import LABELS
from .preferences import ACCENTS
from .help_content import TOPICS

CONTENT=QRectF(650,185,914,487)
SWATCHES=['#C2C5C2','#2362E5','#F17DAD','#EF9338','#E7C748','#AD8EE6','#DA5555','#50BB89']


class OperationalSettingsWindow(SettingsWindow):
    def __init__(self,theme,system):
        self.theme,self.system=theme,system
        self.route='';self.route_stack=[];self.scroll=0.;self.velocity=0.;self.content_height=0
        self.content_pressed=False;self.content_moved=False;self.pointer_last=None;self.scroll_time=0
        self.transition=0.;self.last_content='about';self.laser_index=0;self.pick=None;self.editor_spec=None;self.confirm=None
        self.display_preview={};self.slider_action=None;self.live_info={};self.page_document=None
        self.dropdown=None;self.dropdown_anchor=None;self._slider_value=None
        self.slide=QVariantAnimation();self.slide.setDuration(280);self.slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide.valueChanged.connect(self.slide_frame)
        super().__init__(58,theme.store)
        self.selected=self.order.index('about');self.motion.position=float(self.selected);self.content='about';self.last_index=self.selected
        self.editor=QLineEdit(self);self.editor.setObjectName('settingsValueEditor');self.editor.hide();self.editor.returnPressed.connect(self.commit_editor)
        theme.changed.connect(self.appearance_changed);system.changed.connect(self.update);system.message.connect(self.notify)
        self.appearance_changed()

    def appearance_changed(self):
        drawing.STYLE=self.theme
        self.setFont(QFont(self.theme.fontFamily))
        self.search.setPlaceholderText(self.theme.trText('Search'))
        self.search.setStyleSheet(f'QLineEdit {{background:transparent;color:{self.theme.foreground};border:0;selection-background-color:{self.theme.accent};padding:0;}}')
        self.layout_search();self.layout_editor();self.update()

    def layout_search(self):
        super().layout_search()
        f=QFont(self.theme.fontFamily);f.setPixelSize(round((27 if self.overlay=='keyboard' else 19)*self.scale*self.theme.fontScale));self.search.setFont(f)

    def open_search(self):
        if hasattr(self,'editor'):self.editor.hide()
        super().open_search()

    def close_overlay(self):
        super().close_overlay()
        if self.editor_spec:self.editor.show()

    def layout_editor(self):
        if not hasattr(self,'editor'):return
        rect=QRectF(758,208,650,60)
        self.editor.setGeometry(round(self.offset.x()+rect.x()*self.scale),round(self.offset.y()+rect.y()*self.scale),round(rect.width()*self.scale),round(rect.height()*self.scale))
        font=QFont(self.theme.fontFamily);font.setPixelSize(round(30*self.scale*self.theme.fontScale));self.editor.setFont(font)
        self.editor.setStyleSheet(f'QLineEdit {{background:{self.theme.surface};color:{self.theme.foreground};border:0;border-radius:8px;padding:8px;}}')

    def resizeEvent(self,event):super().resizeEvent(event);self.layout_editor()

    def slide_frame(self,value):self.transition=float(value);self.update()

    def navigate(self,route):
        self.dropdown=None;self.route_stack.append((self.route,self.scroll));self.route=route;self.scroll=0;self.velocity=0
        self.slide.stop();self.slide.setStartValue(914);self.slide.setEndValue(0);self.slide.start();self.update()

    def back(self):
        self.pick=None;self.confirm=None;self.editor_spec=None;self.dropdown=None;self.editor.hide()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.route,self.scroll=self.route_stack.pop() if self.route_stack else ('',0.)
        self.slide.stop();self.slide.setStartValue(-300);self.slide.setEndValue(0);self.slide.start();self.update()

    def select(self,index,absolute=None):
        self.route='';self.route_stack=[];self.scroll=0;self.pick=None;self.confirm=None;self.dropdown=None;self.velocity=0
        if hasattr(self,'editor'):self.editor.hide();self.editor_spec=None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        super().select(index,absolute)

    def tick(self):
        now=time.monotonic();dt=min(.05,max(0,now-self.last_tick))
        super().tick()
        if abs(self.velocity)>1 and not self.content_pressed:
            self.scroll=self.clamp_scroll(self.scroll+self.velocity*dt);self.velocity*=math.exp(-6*dt);self.update()
        if self.content=='system' and self.route in ('clock','info'):self.update()

    def clamp_scroll(self,value):return max(0,min(max(0,self.content_height-CONTENT.height()),value))

    def paintEvent(self,event):
        drawing.STYLE=self.theme
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(),QColor(self.theme.background));p.translate(self.offset);p.scale(self.scale,self.scale);p.setClipRect(QRectF(0,0,1600,720))
        self.hits=[];self.menu_hits=[]
        self.draw_menu(p);self.draw_content(p)
        text(p,1170,18,319,48,'Settings',26,bold=True,align=Qt.AlignmentFlag.AlignRight)
        rect=QRectF(1501,12,86,82);box(p,rect,'#A92621')
        p.setPen(QPen(QColor('#FFFFFF'),2.5));c=rect.center();p.drawLine(c+QPointF(-12,-12),c+QPointF(12,12));p.drawLine(c+QPointF(-12,12),c+QPointF(12,-12));self.register(rect,('close',))
        self.draw_search(p)
        if self.overlay=='keyboard':
            box(p,QRectF(0,0,1600,720),'#B8000000');self.hits=[];self.keyboard.paint(p,self.register,self.search.text())
        elif self.overlay in ('history','results'):self.draw_popup(p)
        if self.system.modeSeconds:
            box(p,QRectF(655,99,900,77),self.theme.raised,12)
            text(p,675,104,475,64,f'Keep this display mode? {self.system.modeSeconds}s',22)
            self.action_button(p,QRectF(1160,110,150,54),'Keep',('keep_mode',));self.action_button(p,QRectF(1322,110,210,54),'Revert',('revert_mode',))
        if self.toast and self.overlay!='keyboard' and self.system.tourIndex<0:
            box(p,QRectF(655,676,900,38),self.theme.surface,8);text(p,669,678,870,33,self.toast,16)
        if self.system.tourIndex>=0 and self.system.tour.get("section"):self.draw_guide(p)
        if self.system.powerSeconds:
            box(p,QRectF(460,280,900,160),self.theme.surface,20)
            text(p,490,298,840,50,f'{self.theme.trText(self.store.values["idle_action"])} in {self.system.powerSeconds}s',28)
            self.action_button(p,QRectF(740,367,340,54),'Cancel',('cancel_power',))
        p.end()

    def draw_search(self,p):
        box(p,SEARCH_RECT,self.theme.surface,24);box(p,HISTORY_RECT,self.theme.surface,24)
        search_icon(p,SEARCH_RECT.left()+18,SEARCH_RECT.top()+14,21)
        history_icon(p,HISTORY_RECT.left()+13,HISTORY_RECT.top()+10)
        self.register(SEARCH_RECT,('search',));self.register(HISTORY_RECT,('history',))
        if self.search.text():
            cross(p,SEARCH_RECT.right()-21,SEARCH_RECT.center().y(),14,self.theme.foreground)
            self.register(QRectF(SEARCH_RECT.right()-36,SEARCH_RECT.y(),36,48),('clear',))

    def rows(self):
        v=self.store.values;g=v['graph'+str(self.laser_index+1)];route=self.route
        if route.startswith('help:'):return []
        if route=='pick':return [('pick',str(label),value) for label,value in self.pick['items']]
        if route in ('edit','confirm','info','clock'):return []
        if self.content=='display':
            mode=self.system.caps.get('current');modes=self.system.caps.get('modes',[])
            sizes=sorted(set((m[0],m[1]) for m in modes))
            rates=sorted(set(m[2] for m in modes if mode and m[:2]==mode[:2]))
            return [('hardware','Brightness','brightness'),('hardware','Contrast','contrast'),
                    ('choose','Accent color','accent',[(k,k) for k in ACCENTS]),('choose','Appearance','appearance',[(k,k) for k in ['Dark','Light']]),
                    ('choose','Resolution','resolution',[(f'{w} × {h}',[w,h]) for w,h in sizes]),
                    ('choose','Refresh rate','refresh',[(f'{r:g} Hz',r) for r in rates]),
                    ('choose','UI scale','ui_scale',[(f'{s}%',s/100) for s in (90,100,110,120)])]
        if self.content=='function':
            common=[('choose','Laser','laser', [('Laser 1',0),('Laser 2',1)])]
            if route=='limits':return common+[( 'number',label,key) for label,key in [('X minimum','x_min'),('X maximum','x_max'),('Main minimum','main_min'),('Main maximum','main_max'),('Error minimum','error_min'),('Error maximum','error_max')]]
            if route=='processing':return common+[('action','Calibrate baseline','calibrate'),('action','Reset baseline','baseline_reset'),('toggle','Auto bandwidth','auto_bandwidth'),('choose','Maximum points','max_points',[(str(n),n) for n in (256,512,1001,2001,4001)])]
            if route=='style':return common+[('choose','Graph color','graph_color',[(c,c) for c in SWATCHES]),('choose','Laser color','laser_color',[(c,c) for c in ['#D9D9D9']+SWATCHES[1:]]),('choose','Line width','line_width',[(f'{x:g} px',x) for x in (1.,1.5,1.7,2.,2.5,3.,4.)])]
            return common+[('choose','Sampling rate','sampling_rate',[(f'{n} Hz',n) for n in (5,10,20,30,60)]),('nav','X / Y limits','limits'),('nav','Signal processing','processing'),('nav','Graph appearance','style')]
        if self.content=='system':
            if route=='power':return [('choose','Idle action','idle_action',[(k,k) for k in ('sleep','shutdown')]),('choose','Idle timeout','idle_minutes',[('Never',0)]+[(f'{n} min',n) for n in (1,5,15,30,60)])]
            fonts=sorted(QFontDatabase.families())
            return [('nav','Date and time','clock'),('choose','Language','language',[(s,s) for s in ('English','Français','Deutsch','Español','Italiano','Português')]),
                    ('choose','Font family','font_family',[(s,s) for s in fonts]),('choose','Text size','font_scale',[(f'{n}%',n/100) for n in (90,100,110,120)]),
                    ('choose','Side buttons','button_labels',[('Icons only',False),('Icon + name',True)]),('nav','Automatic power','power'),('nav','System information','info'),
                    ('action','Restore defaults','restore'),('action','Factory reset','factory'),('action','Take a tour','tour')]
        if self.content=='storage':return [('action','Export settings','export_settings'),('action','Capture graph frame','export_frame'),('action','Clear search history','clear_history')]
        if self.content=='help':return [('nav',key,'help:'+key) for key in TOPICS]
        return []

    def value_label(self,key):
        if key=='laser':return 'Laser '+str(self.laser_index+1)
        if key=='resolution':
            m=self.system.caps.get('current');return f'{m[0]} × {m[1]}' if m else 'Unavailable'
        if key=='refresh':
            m=self.system.caps.get('current');return f'{m[2]:g} Hz' if m else 'Unavailable'
        if key=='laser_color':return self.store.values['laser'+str(self.laser_index+1)+'_color']
        g=self.store.values['graph'+str(self.laser_index+1)]
        value=g.get(key,self.store.values.get(key,''))
        if key in ('font_scale','ui_scale'):return f'{round(value*100)}%'
        if key=='button_labels':return 'Icon + name' if value else 'Icons only'
        if key=='idle_minutes':return f'{value} min' if value else 'Never'
        if isinstance(value,float):return f'{value:g}'
        return str(value)

    def draw_content(self,p):
        if self.content!=self.last_content:
            self.route='';self.route_stack=[];self.scroll=0;self.pick=None;self.editor_spec=None;self.editor.hide();self.last_content=self.content
        title=self.route.split(':',1)[1] if self.route.startswith('help:') else {'limits':'X / Y limits','processing':'Signal processing','style':'Graph appearance','info':'System information','clock':'Date and time','power':'Automatic power'}.get(self.route,LABELS[self.content])
        if self.route=='pick':title=self.pick['label']
        if self.route=='edit':title=self.editor_spec['label']
        if self.route=='confirm':title=self.confirm['label']
        if self.route:
            self.action_button(p,QRectF(655,113,154,54),'Back',('page_back',));tx=830
        else:tx=680
        text(p,tx,108,775 if not self.route else 710,60,title,31,bold=True)
        p.save();p.setClipRect(CONTENT);p.translate(self.transition,0)
        if self.content=='about' and not self.route:self.draw_about(p)
        elif self.route.startswith('help:'):self.draw_document(p,TOPICS[self.route.split(':',1)[1]])
        elif self.route=='edit':self.draw_editor(p)
        elif self.route=='confirm':self.draw_confirmation(p)
        elif self.route=='info':self.draw_info(p)
        elif self.route=='clock':self.draw_clock(p)
        elif self.content in ('control','upgrade') and not self.route:self.draw_placeholder(p)
        else:
            top=CONTENT.y()
            if self.content=='storage' and not self.route:
                usage=shutil.disk_usage(self.store.path.parent);used=usage.used/2**30;total=usage.total/2**30
                text(p,680,190,850,40,f'{used:.1f} GB used / {total:.1f} GB',23)
                box(p,QRectF(680,243,842,10),self.theme.surface,5);box(p,QRectF(680,243,842*usage.used/usage.total,10),self.theme.active,5)
                top=282
            self.dropdown_anchor=None
            rows=self.rows();height=86*self.theme.uiScale
            self.content_height=(top-CONTENT.y())+len(rows)*height
            for i,row in enumerate(rows):
                y=top+i*height-self.scroll
                if y+height<CONTENT.y() or y>CONTENT.bottom():continue
                self.draw_row(p,row,y,height)
            if self.dropdown and self.dropdown_anchor:
                self.draw_dropdown(p)
        p.restore()
        if self.content_height>CONTENT.height() and self.route not in ('edit','confirm'):
            h=max(45,CONTENT.height()**2/self.content_height);y=CONTENT.y()+self.scroll/max(1,self.content_height-CONTENT.height())*(CONTENT.height()-h)
            box(p,QRectF(1555,y,5,h),self.theme.muted,2)

    def draw_row(self,p,row,y,height):
        kind,label,key,*extra=row;rect=QRectF(676,y+5,865,height-10)
        clipped=rect.intersected(CONTENT)
        if clipped.height()<20:return
        line(p,680,y+height-1,1535,y+height-1,self.theme.raised,.8)
        swatch=ACCENTS.get(str(key)) if kind=='pick' and self.pick and self.pick['key']=='accent' else key if kind=='pick' and isinstance(key,str) and key.startswith('#') else None
        if swatch:box(p,QRectF(688,y+height/2-17,34,34),swatch,17)
        text(p,742 if swatch else 685,y+14,750 if kind=='pick' else 425,height-22,label,23)
        if kind=='hardware':
            current=self.display_preview.get(key,self.system.caps.get(key))
            if current is None:
                text(p,1110,y+8,423,height-10,'Unavailable',20,self.theme.muted);self.register(clipped,('hardware_reason',key));return
            text(p,1060,y+15,95,height-22,f'{current}%',21)
            # A wide touch track with a stable, rounded thumb prevents visual
            # jitter while the host value is only committed on release.
            box(p,QRectF(1160,y+height/2-25,370,50),self.theme.surface,10)
            box(p,QRectF(1180,y+height/2-4,326,8),self.theme.raised,4)
            box(p,QRectF(1180,y+height/2-4,3.26*current,8),self.theme.active,4)
            box(p,QRectF(1163+3.26*current,y+height/2-17,34,34),self.theme.active,17,self.theme.surface)
            if not self.system.busy:self.register(QRectF(1156,y+4,381,height-8).intersected(CONTENT),('hardware_slider',key))
        elif kind=='toggle':
            on=self.store.values['graph'+str(self.laser_index+1)][key]
            box(p,QRectF(1430,y+height/2-22,84,44),self.theme.active if on else self.theme.raised,22)
            box(p,QRectF(1472 if on else 1434,y+height/2-18,36,36),self.theme.activeInk if on else self.theme.muted,18)
            self.register(clipped,('graph_toggle',key))
        elif kind in ('choose','number'):
            value=self.value_label(key);r=QRectF(1115,y+10,417,height-20)
            box(p,r,self.theme.surface,10)
            if value.startswith('#'):box(p,QRectF(1132,y+height/2-16,32,32),value,16)
            text(p,1168 if value.startswith('#') else 1130,y+14,382 if not value.startswith('#') else 348,height-28,value,22,align=Qt.AlignmentFlag.AlignCenter)
            if kind=='choose':
                self.register(r.intersected(CONTENT),('choose_setting',label,key,extra[0]))
                if self.dropdown and self.dropdown['key']==key:
                    self.dropdown_anchor=QRectF(r)
            else:
                self.register(r.intersected(CONTENT),('edit_setting',label,key))
        else:
            text(p,1490,y+14,40,height-22,'›',34)
            self.register(clipped,('pick_value',key) if kind=='pick' else ('page_nav',key) if kind=='nav' else ('settings_action',key))

    def action_button(self,p,rect,label,action):
        box(p,rect,self.theme.surface,10);text(p,rect.x()+10,rect.y(),rect.width()-20,rect.height(),label,21,align=Qt.AlignmentFlag.AlignCenter)
        self.register(rect,action)

    def draw_dropdown(self,p):
        """Touch dropdown: choices stay on this page instead of navigating away."""
        anchor=self.dropdown_anchor;items=self.dropdown['items']
        row_h=48;visible=min(6,len(items));height=visible*row_h+12
        below=anchor.bottom()+6
        y=below if below+height<=CONTENT.bottom() else max(CONTENT.y()+4,anchor.top()-height-6)
        rect=QRectF(anchor.left(),y,anchor.width(),height)
        box(p,rect,self.theme.surface,10,self.theme.active)
        for i,(label,value) in enumerate(items[:visible]):
            item=QRectF(rect.left()+6,rect.top()+6+i*row_h,rect.width()-12,row_h-2)
            selected=str(value)==str(self.value_label(self.dropdown['key']))
            if selected:box(p,item,self.theme.active,7)
            text(p,item.left()+14,item.top(),item.width()-28,item.height(),str(label),20,
                 self.theme.activeInk if selected else self.theme.foreground,
                 align=Qt.AlignmentFlag.AlignVCenter,literal_color=True)
            self.register(item,('dropdown_value',value))

    def draw_about(self,p):
        self.content_height=0
        rows=[('Model','Nexatom-DLC-Pro-2000'),('Firmware','V1.6.0'),('Organization','Nexatom Research & Instruments'),('Serial Number','NA-202609-01')]
        for i,(label,value) in enumerate(rows):
            y=210+i*108;text(p,685,y,610,28,label,18,self.theme.muted);text(p,685,y+31,620,48,value,25)
            if i<3:line(p,685,y+94,1295,y+94,self.theme.raised,1)
        rect=QRectF(1316,258,224,224);p.drawPixmap(rect,self.qr,QRectF(self.qr.rect()))

    def draw_document(self,p,paragraphs):
        doc=QTextDocument();doc.setDefaultFont(QFont(self.theme.fontFamily));doc.setTextWidth(850)
        scale=self.theme.textScale
        doc.setDefaultStyleSheet(f'body {{color:{self.theme.foreground}; font-size:{22*scale}px;}} h3 {{font-size:{25*scale}px; margin-top:22px;margin-bottom:10px;}} p {{line-height:145%;margin-bottom:22px;}}')
        markup='<body>'+''.join(f'<p style="font-size:{25*scale}px;font-weight:600;margin-top:22px;margin-bottom:10px;">'+html.escape(self.theme.trText(a))+'</p><p>'+html.escape(self.theme.trText(b))+'</p>' for a,b in paragraphs)+'</body>'
        doc.setHtml(markup);self.content_height=doc.size().height()+24
        p.save();p.translate(680,CONTENT.y()-self.scroll);doc.drawContents(p);p.restore()

    def draw_info(self,p):
        import PySide6
        rows=[('Application version','1.11.0'),('Firmware','V1.6.0'),('Operating system',platform.platform()),('Architecture',platform.machine()),('Python',platform.python_version()),('Qt / PySide6',PySide6.__version__),('Data location',str(self.store.path.parent)),('Display',self.system.caps.get('target','Detecting…'))]
        self.draw_document(p,rows)

    def draw_clock(self,p):
        self.content_height=0
        text(p,680,222,850,65,datetime.datetime.now().strftime('%Y-%m-%d   %H:%M:%S'),34)
        text(p,680,305,850,45,'Host local time',22,self.theme.muted)
        self.action_button(p,QRectF(680,391,440,66),'Set date and time',('edit_clock',))
        text(p,680,481,855,90,'YYYY-MM-DD HH:MM:SS · OS permission is required.',20,self.theme.muted)

    def draw_placeholder(self,p):
        self.content_height=0
        if self.content=='control':
            self.draw_document(p,[('Preview','External control routing will be configured in the next version.'),('Reserved controls','Front-panel buttons · encoder behavior · remote/local ownership.')])
        else:
            text(p,680,229,850,50,'Firmware V1.6.0',30)
            text(p,680,307,850,65,'No firmware will be installed.',23,self.theme.muted)
            self.action_button(p,QRectF(680,414,435,64),'Check for updates',('upgrade',))
            if self.upgrade_progress>=0:
                box(p,QRectF(680,520,840,12),self.theme.raised,6);box(p,QRectF(680,520,8.4*self.upgrade_progress,12),self.theme.active,6)
                text(p,680,553,850,55,'Preview complete · no update source configured' if self.upgrade_progress>=100 else 'Checking preview…',22)

    def begin_editor(self,label,key,current):
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.editor_spec=dict(label=label,key=key);self.navigate('edit');self.editor.setText(str(current));self.editor.selectAll();self.editor.show();self.editor.setFocus();self.layout_editor()

    def draw_editor(self,p):
        self.content_height=0
        keys=['7','8','9','backspace','4','5','6','-','1','2','3',':','0','.',' ','Apply']
        for i,key in enumerate(keys):
            rect=QRectF(758+(i%4)*166,290+(i//4)*85,152,72)
            self.action_button(p,rect,'⌫' if key=='backspace' else 'Space' if key==' ' else key,('edit_key',key))

    def commit_editor(self):
        raw=self.editor.text().strip();key=self.editor_spec['key']
        if key=='clock':
            try:datetime.datetime.fromisoformat(raw)
            except ValueError:self.notify('Use YYYY-MM-DD HH:MM:SS.');return
            self.system.change_time(raw);self.back();return
        try:value=float(raw)
        except ValueError:self.notify('Enter a number.');return
        if not math.isfinite(value) or not -1000<=value<=1000:self.notify('Range: -1000 to 1000 V');return
        if self.system.set_graph(self.laser_index,key,value):self.back()

    def draw_confirmation(self,p):
        self.content_height=0
        self.draw_document(p,[('Confirm',self.confirm['body'])])
        self.action_button(p,QRectF(690,440,380,70),'Cancel',('page_back',))
        self.action_button(p,QRectF(1100,440,420,70),'Confirm',('confirm_action',))

    def apply_choice(self,key,value):
        if key=='laser':self.laser_index=value
        elif key=='resolution':
            old=self.system.caps.get('current');modes=[m for m in self.system.caps['modes'] if m[:2]==value]
            chosen=min(modes,key=lambda m:abs(m[2]-(old[2] if old else 60)));self.system.change_mode(chosen)
        elif key=='refresh':self.system.change_mode(self.system.caps['current'][:2]+[value])
        elif key=='laser_color':self.theme.apply('laser'+str(self.laser_index+1)+'_color',value)
        elif key in ('max_points','graph_color','line_width'):self.system.set_graph(self.laser_index,key,value)
        else:self.theme.apply(key,value)

    def activate(self,action):
        kind=action[0]
        if kind=='page_nav':self.navigate(action[1])
        elif kind=='page_back':self.back()
        elif kind=='choose_setting':
            label,key,options=action[1:]
            if not options:self.notify(self.system.caps.get('reasons',{}).get('mode','No options available.'));return
            self.dropdown=None if self.dropdown and self.dropdown['key']==key else dict(label=label,key=key,items=options)
        elif kind=='dropdown_value':
            key=self.dropdown['key'];self.dropdown=None;self.apply_choice(key,action[1])
        elif kind=='pick_value':
            key=self.pick['key'];value=action[1];self.back();self.apply_choice(key,value)
        elif kind=='edit_setting':self.begin_editor(action[1],action[2],self.store.values['graph'+str(self.laser_index+1)][action[2]])
        elif kind=='edit_clock':self.begin_editor('Date and time','clock',datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        elif kind=='edit_key':
            key=action[1]
            if key=='Apply':self.commit_editor()
            elif key=='backspace':self.editor.backspace()
            else:self.editor.insert(key)
        elif kind=='graph_toggle':
            key=action[1];self.system.set_graph(self.laser_index,key,not self.store.values['graph'+str(self.laser_index+1)][key])
        elif kind=='hardware_reason':self.notify(self.system.caps.get('reasons',{}).get(action[1],'Detecting hardware controls…'))
        elif kind=='settings_action':
            key=action[1]
            if key in ('restore','factory'):
                self.confirm=dict(label='Factory reset' if key=='factory' else 'Restore defaults',action=key,body='Reset application preferences and graph settings'+(' and clear history and laser session.' if key=='factory' else ', keeping search history.')+' This does not reflash the device or change OS display settings.');self.navigate('confirm')
            elif key=='tour':self.system.startTour()
            elif key=='calibrate':self.system.calibrate(self.laser_index)
            elif key=='baseline_reset':self.system.calibrate(self.laser_index,True)
            elif key in ('export_frame','export_settings'):self.system.export(key=='export_frame')
            elif key=='clear_history':super().activate(('clear_history',));self.notify('Search history cleared.')
        elif kind=='confirm_action':
            factory=self.confirm['action']=='factory';self.back();self.system.restore(factory)
        elif kind=='keep_mode':self.system.keep_mode()
        elif kind=='revert_mode':self.system.revert_mode()
        elif kind=='cancel_power':self.system.cancel_power()
        elif kind=='tour_next':self.system.tourNext()
        elif kind=='tour_back':self.system.tourPrevious()
        elif kind=='tour_skip':self.system.stopTour()
        elif kind=='tour_pause':self.system.tourPause()
        else:super().activate(action)
        self.update()

    def pointer_down(self,pt):
        if self.system.tourIndex>=0 and self.system.tour.get("section"):
            self.pending=next(((r,a) for r,a in reversed(self.hits) if a[0].startswith('tour_') and r.contains(pt)),None);return
        super().pointer_down(pt)
        self.content_pressed=not self.overlay and CONTENT.contains(pt) and self.route not in ('edit','confirm')
        self.content_moved=False;self.pointer_last=pt;self.scroll_time=time.monotonic();self.velocity=0
        if self.pending:
            a=self.pending[1]
            if a[0]=='hardware_slider':self.slider_action=a[1];self.move_hardware_slider(pt)
            if a==('edit_key','backspace'):self.backspace_hold.start()

    def move_hardware_slider(self,pt):
        value=round(max(1,min(100,(pt.x()-1180)/326*100)))
        # Do not redraw the native preview for sub-pixel pointer noise.
        if self.display_preview.get(self.slider_action)!=value:
            self.display_preview[self.slider_action]=value
            self.update()

    def pointer_move(self,pt):
        if self.slider_action:self.move_hardware_slider(pt);return
        if self.content_pressed:
            delta=pt.y()-self.pointer_last.y();now=time.monotonic()
            if abs(delta)>3 or self.content_moved:
                self.content_moved=True;self.pending=None;self.scroll=self.clamp_scroll(self.scroll-delta)
                self.velocity=max(-1800,min(1800,-delta/max(.005,now-self.scroll_time)));self.update()
            self.pointer_last=pt;self.scroll_time=now;return
        if self.pending and self.pending[1]==('edit_key','backspace') and not self.pending[0].contains(pt):self.backspace_hold.stop()
        super().pointer_move(pt)

    def pointer_up(self,pt):
        if self.slider_action:
            key=self.slider_action;self.system.set_level(key,self.display_preview.pop(key));self.slider_action=None;self.pending=None
        if self.content_moved:self.pending=None
        self.content_pressed=False
        super().pointer_up(pt)

    def clear_held_input(self):
        if self.pending and self.pending[1]==('edit_key','backspace'):
            self.editor.clear();self.pending=None;self.update()
        else:super().clear_held_input()

    def wheelEvent(self,event):
        if CONTENT.contains(self.point(event.position())) and not self.overlay:
            self.scroll=self.clamp_scroll(self.scroll-event.angleDelta().y()/2);self.update();event.accept()
        else:super().wheelEvent(event)

    def draw_guide(self,p):
        info=self.system.tour
        box(p,QRectF(0,0,1600,105),'#B8000000');box(p,QRectF(0,105,630,615),'#B8000000')
        box(p,QRectF(665,464,880,202),self.theme.surface,18)
        text(p,690,477,820,42,f'{self.system.tourIndex+1}/{info["count"]}  '+info['title'],26,bold=True)
        doc=QTextDocument();doc.setDefaultFont(QFont(self.theme.fontFamily,14));doc.setTextWidth(820)
        doc.setHtml('<div style="color:'+self.theme.foreground+'">'+html.escape(info['body'])+'</div>')
        p.save();p.translate(690,525);doc.drawContents(p);p.restore()
        for x,w,label,act in [(690,170,'Skip guide','tour_skip'),(872,125,'Pause' if self.system.tourPlaying else 'Play','tour_pause'),(1009,180,'Previous','tour_back'),(1201,312,'Finish' if self.system.tourIndex==info['count']-1 else 'Next','tour_next')]:
            rect=QRectF(x,600,w,50)
            box(p,rect,self.theme.active if act=='tour_next' else self.theme.raised,10)
            text(p,x+10,600,w-20,50,label,21,self.theme.activeInk if act=='tour_next' else self.theme.foreground,align=Qt.AlignmentFlag.AlignCenter,literal_color=True)
            self.register(rect,(act,))
