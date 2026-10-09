"""One software-compatible card renderer for Qt Quick and native Settings.

Blurred exit frames are cached; no shader/GPU effect dependency on the Pi.
"""
from collections import OrderedDict
from PySide6.QtCore import QRectF,QPointF,Qt
from PySide6.QtGui import QImage,QPixmap,QPainter,QColor,QFont,QPen,QPolygonF
from PySide6.QtWidgets import QGraphicsScene,QGraphicsPixmapItem,QGraphicsBlurEffect
from PySide6.QtQuick import QQuickImageProvider

def buttons(width,height,decision):
    result=[(QRectF(width-66,10,56,height-20),'close')]
    if decision:result.insert(0,(QRectF(width-219,10,130,height-20),'accept'))
    return result

def metrics(size,native=False):
    return {'Small':(720 if native else 600,64,18),'Medium':(860 if native else 724,78,20),'Large':(880 if native else 740,98,24)}.get(size,(724,78,20))

class NotificationArt:
    def __init__(self,notices,theme):
        self.notices=notices;self.theme=theme;self.cache=OrderedDict();self.generation=0
        theme.changed.connect(self.invalidate)
    def invalidate(self):self.cache.clear();self.generation+=1
    def discard(self,identifier):
        for key in list(self.cache):
            if key[0]==identifier:self.cache.pop(key)
    def image(self,entry,width=724,height=78,focus=''):
        key=(entry['id'],entry['revision'],width,height,entry['blurStep'],focus,self.generation)
        if key in self.cache:self.cache.move_to_end(key);return self.cache[key]
        image=QImage(width,height,QImage.Format.Format_ARGB32_Premultiplied);image.fill(0)
        p=QPainter(image);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        outline=QColor(self.theme.foreground);outline.setAlpha(55)
        p.setPen(QPen(outline,1));p.setBrush(QColor(self.theme.surface));p.drawRoundedRect(QRectF(.5,.5,width-1,height-1),12,12)
        severity={'normal':self.theme.foreground,'warning':'#FFD60A','critical':'#FF453A'}[entry['level']]
        p.setBrush(QColor(severity));p.drawRoundedRect(QRectF(0,11,4,height-22),2,2)
        p.setBrush(Qt.BrushStyle.NoBrush);p.setPen(QPen(QColor(severity),2))
        cx,cy=30,height/2
        if entry['level']=='warning':p.drawPolygon(QPolygonF([QPointF(cx,cy-14),QPointF(cx+14,cy+14),QPointF(cx-14,cy+14)]))
        else:p.drawEllipse(QRectF(cx-13,cy-13,26,26))
        if entry['level']=='normal':p.drawPoint(QPointF(cx,cy-7));p.drawLine(QPointF(cx,cy-2),QPointF(cx,cy+7))
        else:p.drawLine(QPointF(cx,cy-6),QPointF(cx,cy+3));p.drawPoint(QPointF(cx,cy+8))
        font=QFont(self.theme.fontFamily);font.setPixelSize(round(metrics(self.theme.notificationSize)[2]*self.theme.fontScale));p.setFont(font);p.setPen(QColor(self.theme.foreground))
        right=width-(230 if entry['decision'] else 76)
        p.drawText(QRectF(56,8,right-56,height-16),Qt.AlignmentFlag.AlignVCenter|Qt.TextFlag.TextWordWrap,entry['text'])
        for rect,action in buttons(width,height,entry['decision']):
            selected=focus==action;ink=self.theme.activeInk if selected else self.theme.foreground
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(self.theme.active if selected else self.theme.raised));p.drawRoundedRect(rect,8,8)
            p.setPen(QPen(QColor(ink),2))
            if action=='accept':p.drawText(rect,Qt.AlignmentFlag.AlignCenter,self.theme.trText('Confirm'))
            else:
                c=rect.center();p.drawLine(c+QPointF(-6,-6),c+QPointF(6,6));p.drawLine(c+QPointF(-6,6),c+QPointF(6,-6))
        p.end()
        if entry['blurStep']:
            scene=QGraphicsScene();item=QGraphicsPixmapItem(QPixmap.fromImage(image));effect=QGraphicsBlurEffect()
            effect.setBlurRadius(entry['blurStep']*1.6);item.setGraphicsEffect(effect);scene.addItem(item);scene.setSceneRect(QRectF(image.rect()))
            blurred=QImage(image.size(),image.format());blurred.fill(0);p=QPainter(blurred);scene.render(p);p.end();image=blurred
        self.cache[key]=image
        while len(self.cache)>128:self.cache.popitem(last=False)
        return image

class NotificationImageProvider(QQuickImageProvider):
    def __init__(self,art):super().__init__(QQuickImageProvider.ImageType.Image);self.art=art
    def requestImage(self,identifier,size,requestedSize):
        parts=identifier.split('/');entry=self.art.notices.find(int(parts[0]))
        width,height=metrics(self.art.theme.notificationSize)[:2]
        image=self.art.image(entry,width,height) if entry else QImage(width,height,QImage.Format.Format_ARGB32_Premultiplied)
        if not entry:image.fill(0)
        size.setWidth(image.width());size.setHeight(image.height());return image
