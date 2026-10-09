"""Frame 60 keyboard: actual editable input with alphabet, symbols and shift."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen

from .drawing import box, line, text
from .layout import KEYBOARD_RECT, POPUP_TRANSFORM, REFERENCE_POPUP


class TouchKeyboard:
    rect = KEYBOARD_RECT

    def __init__(self):
        self.shift = False
        self.numeric = False
        self.pressed = None

    def key_rects(self):
        return [
            (POPUP_TRANSFORM.mapRect(rect), label, action)
            for rect, label, action in self._reference_key_rects()
        ]

    def _reference_key_rects(self):
        first = "1234567890" if self.numeric else "qwertyuiop"
        second = "-/:;()$&@" if self.numeric else "asdfghjkl"
        third = [".", ",", "?", "!", "'", '"', "#"] if self.numeric else list("zxcvbnm")
        result = []
        for row, start, y, width, gap in [
            (first, 790, 153, 33, 6),
            (second, 810, 209, 33, 6),
        ]:
            for i, value in enumerate(row):
                label = value.upper() if self.shift else value
                result.append(
                    (QRectF(start + i * (width + gap), y, width, 45), label, value)
                )
        result.append((QRectF(790, 265, 45, 45), "shift", "shift"))
        for i, value in enumerate(third):
            result.append(
                (
                    QRectF(849 + i * 39, 265, 33, 45),
                    value.upper() if self.shift else value,
                    value,
                )
            )
        result.append((QRectF(1129, 265, 45, 45), "backspace", "backspace"))
        result.extend(
            [
                (QRectF(790, 321, 92, 45), "123" if self.numeric else "ABC", "mode"),
                (QRectF(888, 321, 188, 45), "", "space"),
                (QRectF(1082, 321, 92, 45), "enter", "enter"),
            ]
        )
        return result

    def paint(self, p, register, query):
        p.save()
        p.setWorldTransform(POPUP_TRANSFORM, True)
        self._paint_reference(
            p,
            lambda rect, action: register(POPUP_TRANSFORM.mapRect(rect), action),
            query,
        )
        p.restore()

    def _paint_reference(self, p, register, query):
        box(p, REFERENCE_POPUP, "#faa6aaad", 31)
        suggestions = [f"“{query}”" if query else "“The”", "the", "to"]
        for i, label in enumerate(suggestions):
            r = QRectF(790 + i * 131, 103, 131, 44)
            text(
                p,
                r.x(),
                r.y(),
                r.width(),
                r.height(),
                label,
                16,
                "#080b0c",
                align=Qt.AlignmentFlag.AlignCenter,
            )
            register(
                r, ("suggest", query if i == 0 and query else ["The", "the", "to"][i])
            )
        line(p, 915, 116, 915, 142, "#999da0", 0.7)
        line(p, 1049, 116, 1049, 142, "#999da0", 0.7)
        for rect, label, action in self._reference_key_rects():
            active = action == self.pressed or (action == "shift" and self.shift)
            color = (
                "#008aff" if action == "enter" else ("#ffffff" if active else "#eff1f4")
            )
            box(p, rect, color, 9)
            cx, cy = rect.center().x(), rect.center().y()
            if label == "shift":
                points = [
                    (cx - 10, cy),
                    (cx, cy - 9),
                    (cx + 10, cy),
                    (cx + 4, cy),
                    (cx + 4, cy + 9),
                    (cx - 4, cy + 9),
                    (cx - 4, cy),
                    (cx - 10, cy),
                ]
                path = QPainterPath(QPointF(*points[0]))
                for point in points[1:]:
                    path.lineTo(QPointF(*point))
                p.setBrush(QColor("#4b4f52") if self.shift else Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor("#4b4f52"), 2))
                p.drawPath(path)
            elif label == "backspace":
                path = QPainterPath(QPointF(cx - 12, cy))
                for a, b in [
                    (cx - 5, cy - 8),
                    (cx + 10, cy - 8),
                    (cx + 10, cy + 8),
                    (cx - 5, cy + 8),
                ]:
                    path.lineTo(a, b)
                path.closeSubpath()
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor("#4b4f52"), 2))
                p.drawPath(path)
                line(p, cx - 2, cy - 4, cx + 5, cy + 4, "#4b4f52", 1.5)
                line(p, cx - 2, cy + 4, cx + 5, cy - 4, "#4b4f52", 1.5)
            elif label == "enter":
                line(p, cx + 8, cy - 8, cx + 8, cy + 1, "#fff", 1.6)
                line(p, cx + 8, cy + 1, cx - 8, cy + 1, "#fff", 1.6)
                line(p, cx - 8, cy + 1, cx - 2, cy - 5, "#fff", 1.6)
                line(p, cx - 8, cy + 1, cx - 2, cy + 7, "#fff", 1.6)
            else:
                text(
                    p,
                    rect.x(),
                    rect.y(),
                    rect.width(),
                    rect.height(),
                    label,
                    16 if action == "mode" else 26,
                    "#4b4f52",
                    align=Qt.AlignmentFlag.AlignCenter,
                )
            register(rect, ("key", action))
