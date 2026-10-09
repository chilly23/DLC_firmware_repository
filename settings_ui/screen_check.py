"""Touch diagnostic surface: corners, continuous tracing, drag targets and solid colors."""
import math
from PySide6.QtCore import Qt,QPointF,QRectF,QEvent,Signal
from PySide6.QtGui import QPainter,QPen,QColor,QFont,QPainterPath
from PySide6.QtWidgets import QWidget

class ScreenCheck(QWidget):
    finished=Signal(object)
    def __init__(self,parent=None):
        super().__init__(parent,Qt.WindowType.Window|Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        self.stage=0;self.hits=set();self.traces=[];self.path=None;self.dragging=False
        self.trace_index=0;self.drag_targets=set();self.puck=QPointF(800,390);self.color_index=0
        self.checks=dict(corners=False,trace=False,drag=False);self.nav_index=0;self.active_touch=None;self.suppress_mouse=False
        self.resize(1600,720)
    def open(self,host):
        self.setGeometry(host.geometry())
        self.showFullScreen() if host.isFullScreen() else self.show()
        self.raise_();self.activateWindow()
    def point(self,p):
        scale=min(self.width()/1600,self.height()/720)
        return QPointF((p.x()-(self.width()-1600*scale)/2)/scale,(p.y()-(self.height()-720*scale)/2)/scale)
    @property
    def targets(self):return [QPointF(85,155),QPointF(1515,155),QPointF(1515,630),QPointF(85,630)]
    @property
    def trace_points(self):return [QPointF(240,240),QPointF(1360,240),QPointF(1360,570),QPointF(240,570),QPointF(240,240)]
    def label(self,p,r,value,size=24,color='#F0F0F0'):
        f=QFont(self.font().family());f.setPixelSize(size);p.setFont(f);p.setPen(QColor(color))
        p.drawText(QRectF(*r),Qt.AlignmentFlag.AlignVCenter|Qt.TextFlag.TextWordWrap,value)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors=['#FFFFFF','#FF0000','#00FF00','#0000FF','#000000']
        p.fillRect(self.rect(),QColor(colors[self.color_index] if self.stage==3 else '#111111'))
        scale=min(self.width()/1600,self.height()/720);p.translate((self.width()-1600*scale)/2,(self.height()-720*scale)/2);p.scale(scale,scale)
        p.fillRect(QRectF(0,0,1600,108),QColor('#202020'))
        names=['Corner targets','Continuous trace','Drag targets','Display colors','Results']
        self.label(p,(28,16,620,43),f'Screen check · {names[self.stage]}',28)
        captions=['Touch each of the four dots.','Follow the outline in one continuous drag, starting at the bright dot.',
                  'Drag the centre disc onto each corner target.','Tap the screen to cycle white, red, green, blue and black.',
                  'This checks touch response and visible pixels; it cannot detect a physical crack automatically.']
        self.label(p,(28,57,1130,42),captions[self.stage],18,'#CCCCCC')
        for i,(x,w,title) in enumerate(((1190,170,'Next' if self.stage<4 else 'Restart'),(1390,180,'Close'))):
            r=QRectF(x,22,w,64);p.setPen(QPen(QColor('#FFFFFF'),3 if self.nav_index==i else 1));p.setBrush(QColor('#343434'));p.drawRoundedRect(r,10,10)
            self.label(p,(x+22,22,w-32,64),title,24)
        if self.stage==0:
            for i,c in enumerate(self.targets):
                p.setBrush(QColor('#32D74B' if i in self.hits else '#D9D9D9'));p.setPen(QPen(QColor('#D9D9D9'),2));p.drawEllipse(c,44,44)
                self.label(p,(c.x()-10,c.y()-25,30,50),'✓' if i in self.hits else str(i+1),28,'#111111')
            self.label(p,(580,310,440,100),f'{len(self.hits)} / 4 targets touched',36)
        elif self.stage==1:
            path=QPainterPath(self.trace_points[0])
            for point in self.trace_points[1:]:path.lineTo(point)
            p.setPen(QPen(QColor('#707070'),14,Qt.PenStyle.DashLine));p.setBrush(Qt.BrushStyle.NoBrush);p.drawPath(path)
            p.setPen(QPen(QColor('#32D74B'),5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
            for trace in self.traces:p.drawPath(trace)
            if self.trace_index<5:
                p.setBrush(QColor('#FFFFFF'));p.setPen(Qt.PenStyle.NoPen);p.drawEllipse(self.trace_points[self.trace_index],24,24)
            self.label(p,(550,338,550,65),'Trace complete' if self.checks['trace'] else 'Keep your finger on the screen',28)
        elif self.stage==2:
            for i,c in enumerate(self.targets):
                p.setBrush(QColor('#1B6830' if i in self.drag_targets else '#2B2B2B'));p.setPen(QPen(QColor('#D9D9D9'),2));p.drawEllipse(c,50,50)
            p.setBrush(QColor('#D9D9D9'));p.setPen(QPen(QColor('#FFFFFF'),3));p.drawEllipse(self.puck,38,38)
            self.label(p,(555,125,500,60),f'{len(self.drag_targets)} / 4 drag targets',28)
        elif self.stage==4:
            for i,(key,title) in enumerate((('corners','Four corner touches'),('trace','Continuous trace'),('drag','Drag coverage'))):
                self.label(p,(320,205+i*100,760,65),title,28)
                self.label(p,(1100,205+i*100,340,65),'Passed' if self.checks[key] else 'Not completed',28,'#32D74B' if self.checks[key] else '#FFD60A')
        p.end()
    def advance(self):
        if self.stage==4:
            self.stage=0;self.hits.clear();self.traces=[];self.trace_index=0;self.drag_targets.clear();self.puck=QPointF(800,390);self.checks=dict(corners=False,trace=False,drag=False)
        else:self.stage+=1
        self.update()
    def down(self,p):
        if QRectF(1390,22,180,64).contains(p):self.close();return
        if QRectF(1190,22,170,64).contains(p):self.advance();return
        if p.y()<110:return
        if self.stage==0:
            for i,c in enumerate(self.targets):
                if math.hypot(p.x()-c.x(),p.y()-c.y())<55:self.hits.add(i)
            self.checks['corners']=len(self.hits)==4
        elif self.stage==1:
            if not self.checks['trace']:
                self.trace_index=0;self.traces=[];self.path=QPainterPath(p);self.traces.append(self.path);self.dragging=True;self.move(p)
        elif self.stage==2:self.dragging=math.hypot(p.x()-self.puck.x(),p.y()-self.puck.y())<65
        elif self.stage==3:self.color_index=(self.color_index+1)%5
        self.update()
    def move(self,p):
        if not self.dragging:return
        if self.stage==1:
            self.path.lineTo(p)
            if self.trace_index<5:
                c=self.trace_points[self.trace_index]
                if math.hypot(p.x()-c.x(),p.y()-c.y())<50:self.trace_index+=1
            self.checks['trace']=self.trace_index==5
        elif self.stage==2:
            self.puck=QPointF(max(40,min(1560,p.x())),max(150,min(680,p.y())))
            for i,c in enumerate(self.targets):
                if math.hypot(p.x()-c.x(),p.y()-c.y())<55:self.drag_targets.add(i)
            self.checks['drag']=len(self.drag_targets)==4
        self.update()
    def up(self,p):self.move(p);self.dragging=False
    def mousePressEvent(self,e):
        if e.source()==Qt.MouseEventSource.MouseEventNotSynthesized:self.down(self.point(e.position()))
    def mouseMoveEvent(self,e):
        if e.source()==Qt.MouseEventSource.MouseEventNotSynthesized:self.move(self.point(e.position()))
    def mouseReleaseEvent(self,e):
        if e.source()==Qt.MouseEventSource.MouseEventNotSynthesized:self.up(self.point(e.position()))
    def event(self,e):
        typ=e.type()
        if typ in (QEvent.Type.TouchBegin,QEvent.Type.TouchUpdate,QEvent.Type.TouchEnd):
            points=e.points()
            if points:
                point=next((p for p in points if p.id()==self.active_touch),points[0]);p=self.point(point.position())
                if typ==QEvent.Type.TouchBegin:self.active_touch=point.id();self.down(p)
                elif typ==QEvent.Type.TouchEnd:self.up(p);self.active_touch=None
                else:self.move(p)
            e.accept();return True
        if typ==QEvent.Type.TouchCancel:self.dragging=False;self.active_touch=None;e.accept();return True
        return super().event(e)
    def navigate(self,delta):self.nav_index=(self.nav_index+delta)%2;self.update()
    def activate(self):self.advance() if self.nav_index==0 else self.close()
    def closeEvent(self,event):self.finished.emit(dict(self.checks));event.accept()
