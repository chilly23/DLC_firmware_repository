"""Shared appearance and persisted graph configuration."""
from copy import deepcopy
from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtGui import QColor

"""Shared visual preferences based on the supplied Tesla reference palette."""
ACCENTS={
    'Red':'#FF453A', 'Orange':'#FF9F0A', 'Yellow':'#FFD60A',
    'Green':'#008622', 'Mint':'#66D4CF', 'Teal':'#6AC4DC',
    'Cyan':'#5AC8F5', 'Blue':'#0A84FF', 'Indigo':'#5E5CE6',
    'Purple':'#BF5AF2', 'Pink':'#FF375F', 'Brown':'#AC8E68',
    'Gray':'#98989D', 'Black':'#000000', 'White':'#FFFFFF',
}
GRAPH_DEFAULTS=dict(x_min=48.2,x_max=68.2,main_min=-1.,main_max=10.,error_min=-2.5,error_max=2.5,
                    auto_bandwidth=False,max_points=1001,line_width=1.7,graph_color='#C2C5C2',
                    baseline_main=0.,baseline_error=0.,main_color='#C2C5C2',error_color='#C2C5C2',
                    main_width=1.7,error_width=1.7,main_style='Solid',error_style='Dashed')
THEMES={
    'Classic':dict(accent='Green',appearance='Dark'),
    'Lab Light':dict(accent='Blue',appearance='Light',light=['#EAF0F6','#FFFFFF','#D7E3EE','#172C42','#526579']),
    'Ion Cyber':dict(accent='Cyan',appearance='Dark',dark=['#0B1420','#15273A','#213C55','#EBFAFF','#9DBDCF'],light=['#E1F3FA','#F4FCFF','#C5E5F1','#0D2B42','#426C83']),
    'Porcelain':dict(accent='Teal',appearance='Light',light=['#ECEEE8','#FAFBF6','#D4DDD3','#253C38','#5D7169']),
    'Orchid':dict(accent='Purple',appearance='Light',light=['#F1EAF4','#FCF7FF','#E2D4E9','#342541','#71617F'],dark=['#1A1222','#2B2036','#41304D','#F5E9FF','#C0ABCC']),
    'Clay':dict(accent='Orange',appearance='Light',light=['#F1EAE1','#FFF9F0','#E3D5C4','#3C3025','#796756'])}
NEW_DEFAULTS=dict(accent='Green',appearance='Dark',font_family='Roboto',font_scale=1.,ui_scale=1.,
                  theme_preset='Classic',corner_number_color='Automatic',corner_detail_color='Automatic',
                  lock_shutdown_seconds=60,shortcut_left='none',shortcut_right='none',notification_actions=True,notification_size='Medium',
                  button_labels=False,language='English',sampling_rate=20,idle_minutes=0,idle_action='sleep',
                  laser1_color='#D9D9D9',laser2_color='#2362E5',graph1=deepcopy(GRAPH_DEFAULTS),graph2=deepcopy(GRAPH_DEFAULTS),
                  alarms1={'enabled':False,'main_high':8.5,'error_high':2.0},
                  alarms2={'enabled':False,'main_high':8.5,'error_high':2.0})


class Appearance(QObject):
    changed=Signal()
    tipRequested=Signal(str,str,float,float)
    @Slot(str,str,float,float)
    def showTip(self,title,body,x,y):self.tipRequested.emit(title,body,x,y)
    @Slot(str,result='QVariantMap')
    def tipFor(self,key):
        from .tooltips import TIPS
        title,body=TIPS.get(key,('',''))
        return dict(title=self.trText(title),body=self.trText(body))
    @Slot(float,result=float)
    def fontSize(self,size):
        from .controls import type_size
        return type_size(size)*self.textScale
    def __init__(self,store,parent=None):
        super().__init__(parent);self.store=store
    def get(self,key):return self.store.values[key]
    @Property(str,notify=changed)
    def accent(self):return ACCENTS.get(self.get('accent'),ACCENTS['Green'])
    @Property(str,notify=changed)
    def accentInk(self):
        c=QColor(self.accent)
        linear=lambda v: v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
        luminance=sum(w*linear(v) for w,v in zip((.2126,.7152,.0722),(c.redF(),c.greenF(),c.blueF())))
        return '#111111' if luminance>.179 else '#FFFFFF'
    @Property(str,notify=changed)
    def parameterInk(self):
        chosen=self.get('corner_number_color')
        return chosen if QColor(chosen).isValid() else self.autoParameterInk
    @property
    def autoParameterInk(self):return '#111111' if self.get('accent') in ('Yellow','Mint','Teal','Cyan','White') else '#FFFFFF'
    @Property(str,notify=changed)
    def parameterDetailInk(self):
        chosen=self.get('corner_detail_color')
        return chosen if QColor(chosen).isValid() else self.autoParameterInk
    def palette(self,index,fallback):
        preset=THEMES.get(self.get('theme_preset'),{})
        colors=preset.get('light' if self.light else 'dark')
        return colors[index] if colors else fallback
    @Property(bool,notify=changed)
    def light(self):return self.get('appearance')=='Light'
    @Property(str,notify=changed)
    def background(self):return self.palette(0,'#EDF0E9' if self.light else '#111111')
    @Property(str,notify=changed)
    def foreground(self):return self.palette(3,'#202920' if self.light else '#F0F1EE')
    @Property(str,notify=changed)
    def surface(self):return self.palette(1,'#DAE0D6' if self.light else '#202720')
    @Property(str,notify=changed)
    def raised(self):return self.palette(2,'#C9D1C5' if self.light else '#303A31')
    @Property(str,notify=changed)
    def muted(self):return self.palette(4,'#536052' if self.light else '#AEB8AC')
    @Property(str,notify=changed)
    def active(self):return '#D9D9D9'
    @Property(str,notify=changed)
    def activeInk(self):return '#101610'
    @Property(str,notify=changed)
    def fontFamily(self):return self.get('font_family')
    @Property(str,notify=changed)
    def language(self):return self.get('language')
    @Slot(str,str,result=str)
    def translate(self,language,value):
        from .translations import translate
        return translate(value,language)
    @Property(float,notify=changed)
    def fontScale(self):return float(self.get('font_scale'))
    @Property(float,notify=changed)
    def uiScale(self):return float(self.get('ui_scale'))
    @Property(float,notify=changed)
    def textScale(self):return self.fontScale*self.uiScale
    @Property(bool,notify=changed)
    def buttonLabels(self):return self.get('button_labels')
    @Property(str,notify=changed)
    def notificationSize(self):return self.get('notification_size')
    @Property(str,notify=changed)
    def laser1Color(self):return self.get('laser1_color')
    @Property(str,notify=changed)
    def laser2Color(self):return self.get('laser2_color')
    @Slot(str,result=str)
    def trText(self,value):
        from .translations import translate
        return translate(value,self.get('language'))

    def apply(self,key,value):
        previous=deepcopy(self.store.values.get(key))
        if key=='theme_preset' and value in THEMES:
            self.store.values.update({k:THEMES[value][k] for k in ('accent','appearance')})
            color='#344F69' if THEMES[value]['appearance']=='Light' else '#C2C5C2'
            self.store.values['laser1_color']='#344F69' if THEMES[value]['appearance']=='Light' else '#D9D9D9'
            for graph in ('graph1','graph2'):
                self.store.values[graph].update(graph_color=color,main_color=color,error_color=color)
        self.store.values[key]=value
        saved=self.store.save();self.changed.emit()
        if getattr(self,'journal',None):
            self.journal.record('Setting changed: '+key if saved else 'Setting save failed: '+key,'Passed' if saved else 'Failed','default' if saved else 'critical','Settings',{'before':previous,'after':value,'error':self.store.error})
