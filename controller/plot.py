"""QPainter plot: bounded geometry, native Qt text, no chart-package dependency."""
from math import ceil, isfinite
from PySide6.QtCore import Property, Signal, Slot, QRectF, QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtQuick import QQuickPaintedItem


def axis_label(value):
    """Fixed notation, at most two decimals, and no negative zero."""
    if abs(value) < .005:
        value = 0.
    return f'{value:.2f}'.rstrip('0').rstrip('.')


class SpectrumPlot(QQuickPaintedItem):
    changed = Signal()
    controller = None  # Injected once by the launcher before QML instantiation.

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAntialiasing(True)
        self._channel = 0
        self._error = False
        self._large = False
        self._combined = False
        self._bottom_axis = False
        self._minimum, self._maximum = 48.2, 68.2
        self._yshift, self._yscale = 0.0, 1.0
        if self.controller:
            self.controller.frame.connect(self.refresh)
            self.controller.changed.connect(self.state_changed)

    def state_changed(self):
        if self.controller and hasattr(self.controller,'preferences'):
            config=self.controller.preferences['graph'+str(self._channel+1)]
            bounds=(config['x_min'],config['x_max'])
            if getattr(self,'_configured_x',None)!=bounds:
                self._configured_x=bounds;self._minimum,self._maximum=bounds
        self.changed.emit()
        self.refresh()

    @Property(bool, notify=changed)
    def interactionLocked(self):
        return self.controller.instrument.lasers[self._channel].locked

    @Property(bool, notify=changed)
    def showXAxis(self):
        return self._bottom_axis

    @Property(bool, notify=changed)
    def bottomAxis(self):
        return self._bottom_axis

    @bottomAxis.setter
    def bottomAxis(self, value):
        self._bottom_axis = value
        self.state_changed()

    @Property(bool, notify=changed)
    def combined(self):
        return self._combined

    @combined.setter
    def combined(self, value):
        self._combined = value
        self.state_changed()

    def refresh(self):
        if self.isVisible() and not self.controller.presentation_busy:
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
        if not (isfinite(lo) and isfinite(hi)) or hi - lo < .399999 or hi - lo > 80.000001:
            return
        # Keep the acquired domain in view, with a small amount of overscroll.
        width = hi-lo
        domain=self.controller.instrument.lasers[self._channel].signal.x_values
        start,end=domain[0],domain[-1]
        if width <= end-start:
            lower, upper = start-.1*width, end-.9*width
        else:
            middle=(start+end)/2
            lower, upper = middle-.6*width, middle-.4*width
        lo = max(lower, min(upper, lo))
        hi = lo+width
        if self._minimum == lo and self._maximum == hi:
            return
        self._minimum, self._maximum = lo, hi
        self.changed.emit()
        self.update()

    def area(self):
        chart = self.controller.instrument.lasers[self._channel].chart
        # Wider gutters are only needed when an edited axis has long labels.
        values = chart.bounds(False)+chart.bounds(True)
        left = max(43, min(90, max(len(axis_label(n)) for n in values)*8+9))
        right = 72 if self._combined and chart.main_visible and chart.error_visible else 16
        return QRectF(left, 10, max(1,self.width()-left-right),
                      max(1,self.height()-((55 if self._large else 40) if self._bottom_axis else 20)))

    @Slot(float, float)
    def pan(self, dx, dy):
        if self.interactionLocked or not (isfinite(dx) and isfinite(dy)):
            return
        a = self.area()
        delta = -dx / a.width() * (self._maximum - self._minimum)
        self.setRange(self._minimum + delta, self._maximum + delta)
        chart = self.controller.instrument.lasers[self._channel].chart
        sample = self.controller.instrument.lasers[self._channel].signal.sample
        domain=self.controller.instrument.lasers[self._channel].signal.x_values
        visible_lo, visible_hi = max(domain[0],self._minimum), min(domain[-1],self._maximum)
        samples = [sample(visible_lo+(visible_hi-visible_lo)*i/256) for i in range(257)]
        signals = [False, True] if self._combined else [self._error]
        for error in signals:
            prefix = 'error' if error else 'main'
            scale = chart.axes[prefix+'_scale']
            shift = chart.axes[prefix+'_position']+dy/a.height()*4*scale
            values = [pair[1 if error else 0] for pair in samples]
            # Retain some trace inside a 10% inset of the viewport, even after
            # a very large swipe. Explicit axis edits remain unrestricted.
            low, high = min(values)-1.6*scale, max(values)+1.6*scale
            chart.axes[prefix+'_position'] = round(max(low,min(high,shift)),3)
        self.controller.changed.emit()
        self.update()

    @Slot(float, float)
    def zoom(self, factor, px):
        if self.interactionLocked or factor <= 0:
            return
        a = self.area()
        ratio = max(0., min(1., (px - a.left()) / a.width()))
        width = self._maximum - self._minimum
        new = max(.4, min(80., width / factor))
        anchor = self._minimum + ratio * width
        self.setRange(anchor - ratio * new, anchor + (1 - ratio) * new)

    @Slot()
    def resetView(self):
        if self.interactionLocked:
            return
        self._yscale, self._yshift = 1., 0.
        from .charts import AXIS_DEFAULTS
        chart = self.controller.instrument.lasers[self._channel].chart
        for error in ([False,True] if self._combined else [self._error]):
            prefix = 'error' if error else 'main'
            for key in (prefix+'_scale',prefix+'_position'):
                chart.axes[key] = AXIS_DEFAULTS[key]
        self.controller.changed.emit()
        domain=self.controller.instrument.lasers[self._channel].signal.x_values
        self.setRange(domain[0], domain[-1])
        self.update()

    @Slot(float)
    def pick(self, px):
        if self.interactionLocked:
            return
        if self._combined and not self.controller.instrument.lasers[self._channel].chart.main_visible:
            return
        a = self.area()
        value = self._minimum + (px - a.left()) / a.width() * (self._maximum - self._minimum)
        laser = self.controller.instrument.lasers[self._channel]
        centers = [laser.signal.center(c) for c,_,_ in laser.signal.peaks]
        index = min(range(len(centers)), key=lambda i: abs(centers[i] - value))
        if laser.signal.level > 0 and abs(centers[index] - value) / (self._maximum - self._minimum) * a.width() < 36:
            self.controller.selectTarget(self._channel, index)

    def paint(self, painter: QPainter):
        if not self.controller:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        a = self.area()
        laser = self.controller.instrument.lasers[self._channel]
        chart = laser.chart
        primary = self._error or (self._combined and not chart.main_visible)
        lo,hi = chart.bounds(primary)
        minimum,maximum = self._minimum,self._maximum
        left,x_scale = a.left(),a.width()/(maximum-minimum)
        x = lambda value: left+(value-minimum)*x_scale
        appearance=self.controller.theme
        config=self.controller.preferences['graph'+str(self._channel+1)]
        color = QColor(config['graph_color'])
        if appearance.light and color.lightnessF()>.55:color=color.darker(190)
        font = QFont(appearance.fontFamily)
        font.setPixelSize(round(14*appearance.textScale))
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
            painter.setPen(QColor(appearance.foreground))
            value = lo + (hi - lo) * ratio
            if a.height()>145 or i % 2 == 0:
                painter.drawText(QRectF(0, yy - 12, a.left() - 9, 24), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, axis_label(value))
                if self._combined and chart.main_visible and chart.error_visible:
                    elo,ehi = chart.bounds(True)
                    painter.drawText(QRectF(a.right()+7,yy-12,62,24),Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,axis_label(elo+(ehi-elo)*ratio))
            label_x = min(self.width() - 66, max(0, xx - 32))
            if self._bottom_axis:
                painter.drawText(QRectF(label_x, a.bottom() + 5, 64, 25), Qt.AlignmentFlag.AlignHCenter, axis_label(self._minimum + ratio * (self._maximum - self._minimum)))
        painter.setPen(QPen(QColor('#A0A59E'), 1.3))
        painter.drawLine(a.bottomLeft(), a.topLeft())
        painter.drawLine(a.bottomLeft(), a.bottomRight())
        signals = ([False] if chart.main_visible else []) + ([True] if chart.error_visible else []) if self._combined else [self._error]
        for error in signals:
            self.paint_trace(painter,a,laser,error,color,x)

    def paint_trace(self,painter,a,laser,error,color,x):
        lo,hi = laser.chart.bounds(error)
        bottom,y_scale = a.bottom(),a.height()/(hi-lo)
        y = lambda value: bottom-(value-lo)*y_scale
        painter.save()
        painter.setClipRect(a.adjusted(1, 1, -1, -1))
        path = QPainterPath()
        # At most one sample per pixel, with a minimum for narrow peaks.
        count = min(1600, max(720, ceil(a.width())))
        minimum,step = self._minimum,(self._maximum-self._minimum)/count
        sample = laser.signal.sample
        for i in range(count + 1):
            value = minimum+step*i
            pair = sample(value)
            point = QPointF(x(value), y(pair[1 if error else 0]))
            if i == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        width=self.controller.preferences['graph'+str(self._channel+1)]['line_width']
        pen = QPen(color, width)
        if error:
            pen.setDashPattern([2.4, 2.4])
        painter.setPen(pen)
        painter.drawPath(path)
        if not error and laser.signal.level > 0.01:
            painter.setOpacity(laser.signal.level)
            for index, (center, _, _) in enumerate(laser.signal.peaks):
                center = laser.signal.center(center)
                xx = x(center)
                yy = y(laser.sample(center, self.controller.elapsed)[0])
                selected = laser.selected == index
                selected_color = QColor(self.controller.theme.foreground)
                painter.setPen(QPen(selected_color if selected else color, 2 if selected else 1.2))
                painter.setBrush(selected_color if selected else Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(xx, yy - 24), 5, 5)
                painter.drawLine(QPointF(xx, yy - 19), QPointF(xx, yy + 2))
                painter.drawPolygon(QPolygonF([QPointF(xx, yy - 2), QPointF(xx - 5, yy + 11), QPointF(xx + 5, yy + 11)]))
        painter.restore()
