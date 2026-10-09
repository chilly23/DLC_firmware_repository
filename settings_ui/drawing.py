"""Scalable Qt painter primitives and reference-derived navigation glyphs."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPen, QPixmap

from .model import ROOT

WHITE = "#f3f4f4"
BG = "#050704"


def text(
    p,
    x,
    y,
    width,
    height,
    value,
    size=22,
    color=WHITE,
    bold=False,
    align=Qt.AlignmentFlag.AlignLeft,
):
    font = QFont("Roboto")
    font.setPixelSize(round(size))
    font.setWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
    p.setFont(font)
    p.setPen(QColor(color))
    p.drawText(
        QRectF(x, y, width, height), align | Qt.AlignmentFlag.AlignVCenter, str(value)
    )


def box(p, rect, color, radius=0, border=None):
    p.setBrush(QColor(color))
    p.setPen(QPen(QColor(border), 1) if border else Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(rect), radius, radius)


def line(p, x1, y1, x2, y2, color="#393e3d", width=1):
    p.setPen(QPen(QColor(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(x1, y1), QPointF(x2, y2))


class Icons:
    def __init__(self):
        self.images = {
            key: QPixmap(str(ROOT / "assets" / (key + ".png")))
            for key in [
                "display",
                "system",
                "function",
                "storage",
                "about",
                "help",
                "upgrade",
                "model",
                "calibration",
                "firmware",
                "serial",
                "help-large",
            ]
        }

    def draw(self, p, key, cx, cy, size):
        image = self.images.get("help-large" if key == "help" and size > 60 else key)
        if image and not image.isNull():
            p.drawPixmap(
                QRectF(cx - size / 2, cy - size / 2, size, size),
                image,
                QRectF(image.rect()),
            )


def search_icon(p, x, y, size=22):
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor("#bdc2c3"), 2.3))
    p.drawEllipse(QRectF(x, y, size * 0.66, size * 0.66))
    line(p, x + size * 0.58, y + size * 0.58, x + size, y + size, "#bdc2c3", 2.3)


def history_icon(p, x, y):
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(WHITE), 2))
    p.drawRoundedRect(QRectF(x, y, 24, 28), 3, 3)
    for d in [7, 14, 21]:
        line(p, x + 7, y + d, x + 18, y + d, WHITE, 1.5)
    for d in [5, 12, 19, 26]:
        line(p, x - 3, y + d, x + 3, y + d, WHITE, 2)


def cross(p, cx, cy, size=18, color=WHITE):
    line(p, cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2, color, 2.5)
    line(p, cx - size / 2, cy + size / 2, cx + size / 2, cy - size / 2, color, 2.5)
