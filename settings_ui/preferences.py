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
                    baseline_main=0.,baseline_error=0.)
NEW_DEFAULTS=dict(accent='Green',appearance='Dark',font_family='Roboto',font_scale=1.,ui_scale=1.,
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
        return '#111111' if self.get('accent') in ('Yellow','Mint','Teal','Cyan','White') else '#FFFFFF'
    @Property(bool,notify=changed)
    def light(self):return self.get('appearance')=='Light'
    @Property(str,notify=changed)
    def background(self):return '#EDF0E9' if self.light else '#111111'
    @Property(str,notify=changed)
    def foreground(self):return '#202920' if self.light else '#F0F1EE'
    @Property(str,notify=changed)
    def surface(self):return '#DAE0D6' if self.light else '#202720'
    @Property(str,notify=changed)
    def raised(self):return '#C9D1C5' if self.light else '#303A31'
    @Property(str,notify=changed)
    def muted(self):return '#536052' if self.light else '#AEB8AC'
    @Property(str,notify=changed)
    def active(self):return '#394D3C' if self.light else '#D9D9D9'
    @Property(str,notify=changed)
    def activeInk(self):return '#FFFFFF' if self.light else '#101610'
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
    def laser1Color(self):return self.get('laser1_color')
    @Property(str,notify=changed)
    def laser2Color(self):return self.get('laser2_color')
    @Slot(str,result=str)
    def trText(self,value):
        from .translations import translate
        return translate(value,self.get('language'))

    def apply(self,key,value):
        self.store.values[key]=value
        self.store.save();self.changed.emit()
