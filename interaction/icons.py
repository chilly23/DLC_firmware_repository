"""Shared 24-unit outline icons, used by Qt Quick and QWidget Settings."""
from PySide6.QtCore import QByteArray,QSize,QRectF
from PySide6.QtGui import QImage,QPainter,QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtQuick import QQuickImageProvider

PATHS={
 'control':'<path d="M4 3v6m0 4v8m8-18v12m0 4v2m8-18v2m0 4v12"/><circle cx="4" cy="11" r="2"/><circle cx="12" cy="17" r="2"/><circle cx="20" cy="7" r="2"/>',
 'alarm':'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4M12 1v1"/>',
 'knob':'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 4v2M3 12H1m22 0h-2M12 23v-2M12 1v1"/>',
 'calibrate':'<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 1v5m0 12v5M1 12h5m12 0h5"/>',
 'screencheck':'<rect x="2" y="3" width="20" height="14" rx="2"/><path d="m7 10 3 3 7-7M12 17v4m-4 0h8"/>',
 'diagnostics':'<path d="M2 12h5l3-9 4 18 3-9h5"/>',
}

def svg(name,color):
    color=QColor(color).name()
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{PATHS.get(name,PATHS["control"])}</svg>'.encode()

def paint_icon(p,name,rect,color):
    QSvgRenderer(QByteArray(svg(name,color))).render(p,QRectF(rect))

class IconProvider(QQuickImageProvider):
    def __init__(self):super().__init__(QQuickImageProvider.ImageType.Image)
    def requestImage(self,identifier,size,requestedSize):
        name,_,color=identifier.partition('/')
        side=max(32,min(256,requestedSize.width() if requestedSize.width()>0 else 96))
        image=QImage(side,side,QImage.Format.Format_ARGB32_Premultiplied);image.fill(0)
        p=QPainter(image);paint_icon(p,name,QRectF(0,0,side,side),'#'+color if color else '#D9D9D9');p.end()
        size.setWidth(side);size.setHeight(side)
        return image
