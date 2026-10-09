"""QPainter plot: bounded geometry, native Qt text, no chart-package dependency."""
from math import ceil
from PySide6.QtCore import Property, Signal, Slot, QRectF, QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtQuick import QQuickPaintedItem
from .model import PEAKS


class SpectrumPlot(QQuickPaintedItem):
    changed = Signal()
    controller = None  # Injected once by the launcher before QML instantiation.

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAntialiasing(True)
        self._channel = 0
        self._error = False
        self._large = False
        self._minimum, self._maximum = 48.2, 68.2
        self._yshift, self._yscale = 0.0, 1.0
        if self.controller:
            self.controller.frame.connect(self.refresh)
            self.controller.changed.connect(self.refresh)

    def refresh(self):
        if self.isVisible():
            self.update()

    @Property(int, notify=changed)
    def channelIndex(self):
        return self._channel

    @channelIndex.setter
    def channelIndex(self, value):
        if value != self._channel:
            self._channel = value
            self.changed.emit()
            self.update()

    @Property(bool, notify=changed)
    def errorPlot(self):
        return self._error

    @errorPlot.setter
    def errorPlot(self, value):
        self._error = value
        self.changed.emit()
        self.update()

    @Property(bool, notify=changed)
    def large(self):
        return self._large

    @large.setter
    def large(self, value):
        self._large = value
        self.changed.emit()
        self.update()

    @Property(float, notify=changed)
    def xMinimum(self):
        return self._minimum

    @Property(float, notify=changed)
    def xMaximum(self):
        return self._maximum

    @Slot(float, float)
    def setRange(self, lo, hi):
        if hi - lo < .4 or hi - lo > 80:
            return
        if self._minimum == lo and self._maximum == hi:
            return
        self._minimum, self._maximum = lo, hi
        self.changed.emit()
        self.update()

    def area(self):
        return QRectF(55 if self._large else 43, 10,
                      max(1, self.width() - (71 if self._large else 59)),
                      max(1, self.height() - (55 if self._large else 40)))

    @Slot(float, float)
    def pan(self, dx, dy):
        a = self.area()
        delta = -dx / a.width() * (self._maximum - self._minimum)
        self.setRange(self._minimum + delta, self._maximum + delta)
        self._yshift += dy / a.height() * (5 if self._error else 11) * self._yscale
        self.update()

    @Slot(float, float)
    def zoom(self, factor, px):
        if factor <= 0:
            return
        a = self.area()
        ratio = max(0., min(1., (px - a.left()) / a.width()))
        width = self._maximum - self._minimum
        new = max(.4, min(80., width / factor))
        anchor = self._minimum + ratio * width
        self.setRange(anchor - ratio * new, anchor + (1 - ratio) * new)

    @Slot()
    def resetView(self):
        self._yscale, self._yshift = 1., 0.
        self.setRange(48.2, 68.2)
        self.update()

    @Slot(float)
    def pick(self, px):
        a = self.area()
        value = self._minimum + (px - a.left()) / a.width() * (self._maximum - self._minimum)
        laser = self.controller.instrument.lasers[self._channel]
        drift = laser.drift(self.controller.elapsed)
        index = min(range(len(PEAKS)), key=lambda i: abs(PEAKS[i][0] + drift - value))
        if abs(PEAKS[index][0] + drift - value) / (self._maximum - self._minimum) * a.width() < 36:
            self.controller.selectTarget(self._channel, index)

    def paint(self, painter: QPainter):
        if not self.controller:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        a = self.area()
        lo, hi = ((-2.5, 2.5) if self._error else (-1, 10))
        lo = lo * self._yscale + self._yshift
        hi = hi * self._yscale + self._yshift
        x = lambda value: a.left() + (value - self._minimum) / (self._maximum - self._minimum) * a.width()
        y = lambda value: a.bottom() - (value - lo) / (hi - lo) * a.height()
        color = QColor('#C2C5C2')
        font = QFont('Roboto')
        font.setPixelSize(20 if self._large else 14)
        painter.setFont(font)
        painter.setPen(QPen(QColor('#535953'), .7))
        painter.drawRect(a)
        for i in range(5):
            ratio = i / 4
            yy = a.bottom() - ratio * a.height()
            xx = a.left() + ratio * a.width()
            painter.setPen(QPen(QColor('#535953'), .7))
            painter.drawLine(QPointF(a.left(), yy), QPointF(a.right(), yy))
            painter.drawLine(QPointF(xx, a.top()), QPointF(xx, a.bottom()))
            painter.setPen(color)
            value = lo + (hi - lo) * ratio
            if not self._error or self._large or i % 2 == 0:
                painter.drawText(QRectF(0, yy - 12, a.left() - 9, 24), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f'{value:g}')
            label_x = min(self.width() - 66, max(0, xx - 32))
            painter.drawText(QRectF(label_x, a.bottom() + 5, 64, 25), Qt.AlignmentFlag.AlignHCenter, f'{self._minimum + ratio * (self._maximum - self._minimum):.1f}')
        painter.setPen(QPen(QColor('#A0A59E'), 1.3))
        painter.drawLine(a.bottomLeft(), a.topLeft())
        painter.drawLine(a.bottomLeft(), a.bottomRight())
        laser = self.controller.instrument.lasers[self._channel]
        if self._error and not laser.show_error:
            return
        painter.save()
        painter.setClipRect(a.adjusted(1, 1, -1, -1))
        path = QPainterPath()
        # At most one sample per pixel, with a minimum for narrow peaks.
        count = min(1600, max(720, ceil(a.width())))
        for i in range(count + 1):
            value = self._minimum + (self._maximum - self._minimum) * i / count
            pair = laser.sample(value, self.controller.elapsed)
            point = QPointF(x(value), y(pair[1 if self._error else 0]))
            if i == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        pen = QPen(color, 1.5 if self._error else 1.7)
        if self._error:
            pen.setDashPattern([2.4, 2.4])
        painter.setPen(pen)
        painter.drawPath(path)
        if not self._error:
            drift = laser.drift(self.controller.elapsed)
            for index, (center, _, _) in enumerate(PEAKS):
                xx = x(center + drift)
                yy = y(laser.sample(center + drift, self.controller.elapsed)[0])
                selected = laser.selected == index
                painter.setPen(QPen(QColor('#FFFFFF') if selected else color, 2 if selected else 1.2))
                painter.setBrush(QColor('#D9D9D9') if selected else Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(xx, yy - 24), 5, 5)
                painter.drawLine(QPointF(xx, yy - 19), QPointF(xx, yy + 2))
                painter.drawPolygon(QPolygonF([QPointF(xx, yy - 2), QPointF(xx - 5, yy + 11), QPointF(xx + 5, yy + 11)]))
        painter.restore()
