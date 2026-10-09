"""Shared painter controls and the reference typography scale."""
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen
from .drawing import box, text, line

TYPE_SIZES = (14, 16, 18, 24, 28, 36, 46)

def type_size(size):
    # Preserve large instrument readouts; all ordinary UI uses the reference scale.
    return size if size > 46 else min(TYPE_SIZES, key=lambda n: abs(n-size))

def slider_geometry(rect, value, minimum=1, maximum=100):
    thumb_width = min(100., rect.width()*.265)
    travel = rect.width()-thumb_width-8
    fraction = max(0., min(1., (value-minimum)/(maximum-minimum)))
    return QRectF(rect.x()+4+travel*fraction, rect.y()+3, thumb_width, rect.height()-6)

def slider(p, rect, value, theme, label=None):
    """Reference slider: rectangular track, broad value tile and sun endpoints."""
    box(p, rect, theme.raised, 7, theme.muted)
    for x in (rect.x()+25, rect.right()-25):
        p.setBrush(Qt.BrushStyle.NoBrush);p.setPen(QPen(QColor(theme.muted),1.6))
        p.drawEllipse(QPointF(x,rect.center().y()),5,5)
        for dx,dy in ((-12,0),(12,0),(0,-12),(0,12),(-9,-9),(9,9),(-9,9),(9,-9)):
            line(p,x+dx*.72,rect.center().y()+dy*.72,x+dx,rect.center().y()+dy,theme.muted,1.4)
    thumb=slider_geometry(rect,value)
    box(p,thumb,theme.active,6,theme.muted)
    for dx in (8,12,16):line(p,thumb.x()+dx,thumb.center().y()-8,thumb.x()+dx,thumb.center().y()+8,'#697069',1.2)
    text(p,thumb.x()+17,thumb.y(),thumb.width()-20,thumb.height(),label or f'{round(value)}%',20,theme.activeInk,
         align=Qt.AlignmentFlag.AlignCenter,literal_color=True)

def chevron(p, rect, theme):
    x,y=rect.right()-22,rect.center().y()
    line(p,x-5,y-3,x,y+2,theme.foreground,1.8)
    line(p,x,y+2,x+5,y-3,theme.foreground,1.8)

def switch(p, rect, checked, theme):
    box(p,rect,theme.accent if checked else theme.raised,rect.height()/2,theme.muted if not checked else None)
    d=rect.height()-8
    box(p,QRectF(rect.right()-d-4 if checked else rect.left()+4,rect.top()+4,d,d),'#FFFFFF',d/2)

def tooltip(p, anchor, title, body, theme):
    width,height=360,138
    x=max(12,min(1228,anchor.center().x()-width/2))
    y=anchor.top()-height-14 if anchor.top()>height+30 else anchor.bottom()+14
    y=max(12,min(570,y))
    color='#FFFFFF' if theme.light else '#111827'
    ink='#111827' if theme.light else '#FFFFFF'
    box(p,QRectF(x+3,y+7,width,height),'#28000000',12)
    box(p,QRectF(x,y,width,height),color,10)
    # Small triangular pointer, matching Tooltip.png.
    ax=max(x+18,min(x+width-18,anchor.center().x()))
    path=QPainterPath(QPointF(ax-8,y+height if y<anchor.top() else y))
    path.lineTo(ax,y+height+8 if y<anchor.top() else y-8)
    path.lineTo(ax+8,y+height if y<anchor.top() else y);path.closeSubpath()
    p.fillPath(path,QColor(color))
    text(p,x+16,y+10,width-32,30,title,18,ink,bold=True,literal_color=True)
    from PySide6.QtGui import QFont
    font=QFont(theme.fontFamily);font.setPixelSize(18);p.setFont(font);p.setPen(QColor(ink))
    p.drawText(QRectF(x+16,y+47,width-32,80),Qt.TextFlag.TextWordWrap,theme.trText(body))
