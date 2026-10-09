"""Letter-only circular touch keyboard, drawn from the user's reference style."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainterPath, QPen
from .drawing import box, line, cross
from .layout import KEYBOARD_RECT


class TouchKeyboard:
    rect = KEYBOARD_RECT

    def __init__(self):
        self.shift = False
        self.pressed = None

    def key_rects(self):
        keys = []
        for i, value in enumerate('qwertyuiop'):
            keys.append((QRectF(332+i*86,368,76,76),value.upper(),value))
        keys.append((QRectF(1192,368,76,76),'backspace','backspace'))
        for i, value in enumerate('asdfghjkl'):
            keys.append((QRectF(375+i*86,454,76,76),value.upper(),value))
        keys.append((QRectF(332,540,76,76),'shift','shift'))
        for i, value in enumerate('zxcvbnm'):
            keys.append((QRectF(418+i*86,540,76,76),value.upper(),value))
        keys.extend([(QRectF(1020,540,76,76),'left','left'),
                     (QRectF(1106,540,76,76),'right','right'),
                     (QRectF(1192,454,76,162),'enter','enter'),
                     (QRectF(500,632,600,48),'space','space'),
                     (QRectF(1216,303,52,52),'close','close')])
        return keys

    def paint(self, p, register, query):
        box(p,self.rect,'#212121',54)
        font=QFont('Roboto')
        font.setPixelSize(30)
        for rect,label,action in self.key_rects():
            active = action == self.pressed or (action=='shift' and self.shift)
            box(p,rect,'#FF8500' if active else '#333333',min(rect.width(),rect.height())/2)
            p.setPen(QPen(QColor('#FFFFFF'),2.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            cx,cy=rect.center().x(),rect.center().y()
            if action=='backspace':
                path=QPainterPath(QPointF(cx-19,cy))
                for x,y in [(cx-9,cy-12),(cx+17,cy-12),(cx+17,cy+12),(cx-9,cy+12)]:path.lineTo(x,y)
                path.closeSubpath();p.drawPath(path)
                cross(p,cx+2,cy,10,'#FFFFFF')
            elif action=='shift':
                path=QPainterPath(QPointF(cx-16,cy))
                for x,y in [(cx,cy-15),(cx+16,cy),(cx+7,cy),(cx+7,cy+14),(cx-7,cy+14),(cx-7,cy),(cx-16,cy)]:path.lineTo(x,y)
                p.drawPath(path)
            elif action in ('left','right'):
                d=-1 if action=='left' else 1
                line(p,cx-14,cy,cx+14,cy,'#FFFFFF',2.2)
                line(p,cx+d*14,cy,cx+d*3,cy-10,'#FFFFFF',2.2)
                line(p,cx+d*14,cy,cx+d*3,cy+10,'#FFFFFF',2.2)
            elif action=='enter':
                line(p,cx+13,cy-14,cx+13,cy+4,'#FFFFFF',2.2)
                line(p,cx+13,cy+4,cx-15,cy+4,'#FFFFFF',2.2)
                line(p,cx-15,cy+4,cx-4,cy-7,'#FFFFFF',2.2)
                line(p,cx-15,cy+4,cx-4,cy+15,'#FFFFFF',2.2)
            elif action=='space':
                line(p,cx-50,cy+4,cx+50,cy+4,'#FFFFFF',2.2)
                line(p,cx-50,cy+4,cx-50,cy-4,'#FFFFFF',2.2)
                line(p,cx+50,cy+4,cx+50,cy-4,'#FFFFFF',2.2)
            elif action=='close':
                cross(p,cx,cy,15,'#FFFFFF')
            else:
                p.setFont(font);p.setPen(QColor('#FFFFFF'))
                p.drawText(rect,Qt.AlignmentFlag.AlignCenter,label)
            register(rect,('key',action))
