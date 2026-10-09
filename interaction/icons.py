"""Shared 24-unit outline icons, used by Qt Quick and QWidget Settings."""
from pathlib import Path
from PySide6.QtCore import QByteArray,QSize,QRectF
from PySide6.QtGui import QImage,QPainter,QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtQuick import QQuickImageProvider

PATHS={
 'placeholder':'<path d="M8 3H3v5m13-5h5v5M3 16v5h5m8 0h5v-5M8 12h8m-4-4v8"/>',
 'reorder':'<path d="M5 6h14M5 12h14M5 18h14"/>',
 'lobby':'<rect x="2" y="2" width="9" height="12" rx="2"/><rect x="14" y="2" width="8" height="6" rx="2"/><rect x="14" y="11" width="8" height="11" rx="2"/><rect x="2" y="17" width="9" height="5" rx="2"/>',
 'buttons':'<rect x="3" y="2" width="18" height="20" rx="2"/><path d="M8 7h8M8 12h8M8 17h8"/><circle cx="5.5" cy="7" r=".2"/><circle cx="5.5" cy="12" r=".2"/><circle cx="5.5" cy="17" r=".2"/>',
 'cube':'<path d="m12 2 9 5v10l-9 5-9-5V7Zm-9 5 9 5 9-5M12 12v10M7.5 4.5l9 5"/>',
 'graphsize':'<path d="M3 3v18h18M6 15l4-5 4 3 6-7M16 3h5v5"/>',
 'camera':'<path d="M3 6h4l2-3h6l2 3h4v15H3Z"/><circle cx="12" cy="13" r="4"/>',
 'folder':'<path d="M2 5h8l2 3h10v12H2Z"/>',
 'monitor':'<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M12 17v4m-4 0h8M5 11h3l2-5 4 8 2-3h3"/>',
 'sliders':'<path d="M4 3v18M12 3v18M20 3v18M1 8h6M9 16h6M17 10h6"/>',
 'home':'<path d="m2 11 10-9 10 9M5 9v13h14V9M9 22v-8h6v8"/>',
 'legal':'<path d="M12 2v19M4 21h16M3 7h18M5 7l-4 7h8Zm14 0-4 7h8Z"/>',
 'book':'<path d="M12 5C9 2 4 2 2 3v17c4-1 7 0 10 2 3-2 6-3 10-2V3c-2-1-7-1-10 2Zm0 0v17"/>',
 'info':'<circle cx="12" cy="12" r="10"/><path d="M12 11v7M12 6v1"/>',
 'logs':'<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 7h8M8 12h8M8 17h5"/>',
 'retry':'<path d="M20 8a8 8 0 1 0 0 8M20 2v6h-6"/>',
 'control':'<path d="M4 3v6m0 4v8m8-18v12m0 4v2m8-18v2m0 4v12"/><circle cx="4" cy="11" r="2"/><circle cx="12" cy="17" r="2"/><circle cx="20" cy="7" r="2"/>',
 'alarm':'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4M12 1v1"/>',
 'knob':'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 4v2M3 12H1m22 0h-2M12 23v-2M12 1v1"/>',
 'calibrate':'<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 1v5m0 12v5M1 12h5m12 0h5"/>',
 'screencheck':'<rect x="2" y="3" width="20" height="14" rx="2"/><path d="m7 10 3 3 7-7M12 17v4m-4 0h8"/>',
 'diagnostics':'<path d="M2 12h5l3-9 4 18 3-9h5"/>',
 'notifications':'<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M7 8h10M7 12h10M7 16h6"/>',
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
        ink='#'+color if color else '#D9D9D9'
        p=QPainter(image)
        if name=='drag':
            original=QImage(str(Path(__file__).resolve().parents[1]/'assets/dragndrop-white.png'))
            p.drawImage(image.rect(),original)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn);p.fillRect(image.rect(),QColor(ink))
        else:paint_icon(p,name,QRectF(0,0,side,side),ink)
        p.end()
        size.setWidth(side);size.setHeight(side)
        return image
