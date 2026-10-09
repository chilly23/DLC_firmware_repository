"""Native PySide6 touch UI, rendered in the references' 1600 x 720 space."""

import math
import time
from collections import deque

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QLineEdit, QWidget

from .drawing import BG, WHITE, Icons, box, cross, line, text
from .keyboard import TouchKeyboard
from .layout import (
    HISTORY_RECT,
    INPUT_RECT,
    POPUP_TRANSFORM,
    SEARCH_FILL,
    SEARCH_GROUP,
    SEARCH_RECT,
    KEYBOARD_INPUT_RECT,
)
from .model import LABELS, ORDERS, ROOT, SettingsStore
from .motion import WheelMotion


class SettingsWindow(QWidget):
    def __init__(self, variant=32, store=None):
        super().__init__()
        self.variant = variant
        self.store = store or SettingsStore()
        self.order = ORDERS[variant]
        self.selected = self.order.index("help")
        self.content = "about"  # Reference opening state, intentionally Help + About.
        self.motion = WheelMotion(self.selected)
        self.icons = Icons()
        self.qr = QPixmap(str(ROOT / "assets" / "qr.png"))
        self.keyboard = TouchKeyboard()
        self.overlay = None
        self.hits = []
        self.menu_hits = []
        self.pending = None
        self.query_dirty = False
        self.backspace_hold = QTimer(self)
        self.backspace_hold.setSingleShot(True)
        self.backspace_hold.setInterval(650)
        self.backspace_hold.timeout.connect(self.clear_held_input)
        self._touch_id = None
        self._touch_active = False
        self._last_touch = -float('inf')
        self.gesture = None
        self.dragged = False
        self.samples = deque(maxlen=30)
        self.toast = ""
        self.toast_until = 0
        self.upgrade_progress = -1
        self.scale = 1.0
        self.offset = QPointF()
        self.last_tick = time.monotonic()
        self.last_index = self.selected
        self.setWindowTitle(
            f"Nexatom · Frame {variant} · "
            + {32: "Classic settings", 58: "Vertical wheel", 59: "Circular wheel"}[
                variant
            ]
        )
        self.resize(1600, 720)
        self.setMinimumSize(800, 360)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search")
        self.search.setFrame(False)
        palette = self.search.palette()
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#c4c7c5"))
        self.search.setPalette(palette)
        self.search.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, False)
        self.search.setStyleSheet(
            "QLineEdit {background:transparent; color:#f3f4f4; border:0; selection-background-color:#008aff; selection-color:white; padding:0;}"
        )
        self.search.textChanged.connect(self.search_changed)
        self.search.returnPressed.connect(self.submit_search)
        self.search.installEventFilter(self)
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.resizeEvent(None)

    def resizeEvent(self, event):
        self.scale = min(self.width() / 1600, self.height() / 720)
        self.offset = QPointF(
            (self.width() - 1600 * self.scale) / 2,
            (self.height() - 720 * self.scale) / 2,
        )
        self.layout_search()

    def layout_search(self):
        rect = KEYBOARD_INPUT_RECT if self.overlay == 'keyboard' else INPUT_RECT
        self.search.setGeometry(
            round(self.offset.x() + rect.x() * self.scale),
            round(self.offset.y() + rect.y() * self.scale),
            round(rect.width() * self.scale),
            round(rect.height() * self.scale),
        )
        f = QFont('Roboto')
        f.setPixelSize(max(10, round((27 if self.overlay=='keyboard' else 17) * self.scale)))
        self.search.setFont(f)

    def point(self, local):
        return (local - self.offset) / self.scale

    def tick(self):
        now = time.monotonic()
        dt = now - self.last_tick
        self.last_tick = now
        changed = self.motion.tick(dt) if self.variant != 32 else False
        idx = round(self.motion.position) % len(self.order)
        if self.variant != 32 and idx != self.last_index:
            self.last_index = self.selected = idx
            self.content = self.order[idx]
            changed = True
        if self.upgrade_progress >= 0 and self.upgrade_progress < 100:
            self.upgrade_progress = min(100, self.upgrade_progress + dt * 38)
            if self.upgrade_progress == 100:
                self.notify("Demo check complete · Firmware v1.2.3 is up to date")
            changed = True
        if self.toast and now > self.toast_until:
            self.toast = ""
            changed = True
        if changed:
            self.update()

    def notify(self, message):
        self.toast = message
        self.toast_until = time.monotonic() + 3.5
        self.update()

    def register(self, rect, action):
        self.hits.append((QRectF(rect), action))

    def select(self, index, absolute=None):
        index %= len(self.order)
        self.content = self.order[index]
        self.selected = index
        if self.variant == 32:
            self.motion.position = index
        else:
            target = (
                absolute
                if absolute is not None
                else self.motion.nearest(index, len(self.order))
            )
            if self.store.values["animations"]:
                self.motion.move_to(target)
            else:
                self.motion.position = target
                self.motion.target = None
                self.motion.velocity = 0
            self.last_index = round(self.motion.position) % len(self.order)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor(BG))
        p.translate(self.offset)
        p.scale(self.scale, self.scale)
        p.setClipRect(QRectF(0, 0, 1600, 720))
        self.hits = []
        self.menu_hits = []
        self.draw_menu(p)
        self.draw_content(p)
        text(p,1344,25,145,48,'Settings',26,bold=True)
        close_rect = QRectF(1501,12,86,82)
        box(p, close_rect, "#a92621")
        cross(p, close_rect.center().x(), close_rect.center().y(), 19)
        self.register(close_rect, ("close",))
        self.draw_search(p)
        if self.overlay == "keyboard":
            box(p,QRectF(0,0,1600,720),'#B8000000')
            self.hits = []
            self.keyboard.paint(p, self.register, self.search.text())
        elif self.overlay in ("history", "results"):
            self.draw_popup(p)
        if self.toast:
            box(p, QRectF(667, 649, 898, 53), "#ee252a28", 14, "#555b56")
            text(p, 687, 654, 858, 43, self.toast, 19)
        p.end()

    def draw_menu(self, p):
        p.save()
        if self.variant == 32:
            p.setClipRect(QRectF(1, 100, 632, 620))
            line(p, 633, 100, 633, 720, "#262725", 3)
            ys = [153, 226, 300, 375, 449, 526, 599]
            for i, (key, y) in enumerate(zip(self.order, ys)):
                rect = QRectF(5, y - 35, 623, 70)
                if self.selected == i:
                    box(p, rect, "#202020", 4)
                self.icons.draw(
                    p,
                    key,
                    58.5,
                    [157.5, 226.5, 297.5, 370.5, 447.5, 525.5, 598.5][i],
                    51,
                )
                text(p, 100, y - 25, 492, 50, LABELS[key], 25)
                self.menu_hits.append((rect, i))
        else:
            p.setClipRect(QRectF(0, 0, 600, 720))
            if self.variant == 59:
                path = QPainterPath()
                path.addEllipse(QRectF(-558, -206, 1120, 1120))
                path.addEllipse(QRectF(-297, 105, 500, 500))
                path.setFillRule(Qt.FillRule.OddEvenFill)
                p.setBrush(QColor("#202020"))
                p.setPen(QPen(QColor("#e1e2e2"), 1))
                p.drawPath(path)
                line(p, 196, 309, 561, 308, "#959797", 0.8)
                line(p, 195, 420, 561, 420, "#959797", 0.8)
            else:
                line(p, 1, 306, 591, 306, "#999b9b", 0.8)
                line(p, 1, 414, 591, 414, "#999b9b", 0.8)
                p.setClipRect(QRectF(0, 0, 600, 720))
            low = math.floor(self.motion.position) - 5
            for absolute in range(low, low + 12):
                d = absolute - self.motion.position
                if abs(d) > 4.4:
                    continue
                size = 20 + 20 * max(0, 1 - abs(d)) ** 1.6
                icon_size = 40 + 25 * max(0, 1 - abs(d)) ** 1.6
                idx = absolute % len(self.order)
                key = self.order[idx]
                if self.variant == 58:
                    cy = self.interpolate(
                        d,
                        [-4, -3, -2, -1, 0, 1, 2, 3, 4],
                        [-40, 48, 142, 246, 360, 474, 578, 672, 760],
                    )
                    cx = 54 + 33 * max(0, 1 - abs(d))
                    tx = 100 + 43 * max(0, 1 - abs(d))
                    if cy < -40 or cy > 760:
                        continue
                    rect = QRectF(15, cy - 30, 572, 60 if abs(d) > 0.5 else 82)
                else:
                    # Reference anchors lie along the annulus; interpolate between them continuously.
                    cy = self.interpolate(
                        d,
                        [-4, -3, -2, -1, 0, 1, 2, 3, 4],
                        [-30, 64, 139, 239, 365, 493, 587, 674, 760],
                    )
                    cx = self.interpolate(
                        d,
                        [-4, -3, -2, -1, 0, 1, 2, 3, 4],
                        [-15, 112, 232, 315, 342, 307, 244, 145, 20],
                    )
                    tx = cx + 42 + 14 * max(0, 1 - abs(d))
                    icon_size = 51 + 14 * max(0, 1 - abs(d))
                    rect = QRectF(cx - 32, cy - 32, 340, 64)
                    if cy < -30 or cy > 750:
                        continue
                # Frame 58's reference swaps these two glyphs; retain its artwork.
                icon_key = (
                    {"upgrade": "about", "about": "upgrade"}.get(key, key)
                    if self.variant == 58
                    else key
                )
                self.icons.draw(p, icon_key, cx, cy, icon_size)
                text(p, tx, cy - 30, 400, 60, self.menu_label(key), size)
                self.menu_hits.append((rect, absolute))
        p.restore()

    def menu_label(self, key):
        label = LABELS[key]
        return label.removesuffix(" Settings") if self.variant == 59 else label

    @staticmethod
    def interpolate(value, xs, ys):
        for i in range(len(xs) - 1):
            if value <= xs[i + 1]:
                a = (value - xs[i]) / (xs[i + 1] - xs[i])
                y0 = ys[max(0, i - 1)]
                y1 = ys[i]
                y2 = ys[i + 1]
                y3 = ys[min(len(ys) - 1, i + 2)]
                return 0.5 * (
                    (2 * y1)
                    + (-y0 + y2) * a
                    + (2 * y0 - 5 * y1 + 4 * y2 - y3) * a * a
                    + (-y0 + 3 * y1 - 3 * y2 + y3) * a * a * a
                )
        return ys[-1]

    def draw_content(self, p):
        x = 685 if self.variant == 32 else 680
        title_y = 145 if self.variant == 32 else 155
        key = self.content
        text(
            p,
            x,
            title_y,
            740,
            52,
            LABELS[key] if key != "about" else "About",
            32,
            bold=True,
        )
        if key == "about":
            base = 264 if self.variant == 32 else 274
            left = x + 77
            rows = [
                ("model", "Model", "NEXATOM NA-2000"),
                ("calibration", "Calibration Time", "15 - JUL - 2026"),
                ("firmware", "Firmware Version", "v1.2.3"),
                ("serial", "Serial Number", "NA2000-26A7-8E3B-1001"),
            ]
            for i, (icon, label, value) in enumerate(rows):
                y = base + 92 * i
                self.icons.draw(p, icon, x + 25, y, 44)
                text(p, left, y - 23, 251, 46, label, 20)
                text(
                    p,
                    x + 308,
                    y - 23,
                    252,
                    46,
                    value,
                    20,
                    align=Qt.AlignmentFlag.AlignRight,
                )
                if i < 3:
                    line(p, x + 5, y + 45, x + 571, y + 45)
            p.drawPixmap(
                QRectF(
                    1348 if self.variant == 32 else 1343,
                    254 if self.variant == 32 else 264,
                    184,
                    222,
                ),
                self.qr,
                QRectF(self.qr.rect()),
            )
            return
        if key == "display":
            self.slider(p, "Brightness", "brightness", 249)
            self.toggle(p, "Interface animations", "animations", 341)
            self.choice(
                p,
                "Screen timeout",
                "timeout",
                ["1 minute", "5 minutes", "15 minutes", "Never"],
                433,
            )
        elif key == "system":
            self.choice(
                p, "Language", "language", ["English", "Deutsch", "Français"], 249
            )
            self.toggle(p, "Touch feedback sound", "sound", 341)
            self.choice(p, "Measurement units", "units", ["SI", "Engineering"], 433)
        elif key == "function":
            self.toggle(p, "Laser 1 emission", "laser1", 249)
            self.toggle(p, "Laser 2 emission", "laser2", 331)
            self.toggle(p, "Stabilise both lasers", "stabilisation", 413)
            self.choice(
                p,
                "Graph refresh rate",
                "scan_rate",
                ["5 Hz", "10 Hz", "20 Hz", "30 Hz"],
                495,
            )
        elif key == "storage":
            text(p, x, 221, 800, 40, "Local storage", 23)
            box(p, QRectF(x, 274, 800, 14), "#292e2a", 7)
            box(p, QRectF(x, 274, 208, 14), "#d9d9d9", 7)
            text(
                p, x, 299, 800, 36, "Example data · 8.3 GB of 32 GB used", 20, "#bcc1bc"
            )
            self.toggle(p, "Save session logs", "logging", 381)
            self.choice(
                p, "Log retention", "retention", ["7 days", "30 days", "90 days"], 473
            )
            self.button(p, QRectF(x, 571, 280, 60), "Export settings", ("export",))
        elif key == "help":
            rows = [
                ("Navigate", "Tap any option to bring it into focus."),
                ("Scroll", "Swipe up or down. A fast swipe keeps the wheel moving."),
                ("Search", "Tap Search. Enter a term and press the blue return key."),
                ("History", "Tap the notepad to view or clear recent searches."),
            ]
            for i, (a, b) in enumerate(rows):
                y = 227 + i * 102
                text(p, x, y, 810, 32, a, 23, bold=True)
                text(p, x, y + 35, 870, 34, b, 20, "#bdc2bd")
                if i < 3:
                    line(p, x, y + 85, 1535, y + 85)
        elif key == "upgrade":
            text(p, x, 237, 550, 48, "Installed firmware", 23)
            text(p, 1290, 237, 244, 48, "v1.2.3", 23, align=Qt.AlignmentFlag.AlignRight)
            line(p, x, 310, 1535, 310)
            text(
                p,
                x,
                337,
                850,
                50,
                "Preview mode · No device firmware is modified.",
                21,
                "#bdc2bd",
            )
            self.button(p, QRectF(x, 422, 300, 64), "Check for updates", ("upgrade",))
            if self.upgrade_progress >= 0:
                box(p, QRectF(x, 528, 800, 12), "#2c312d", 6)
                box(p, QRectF(x, 528, 8 * self.upgrade_progress, 12), "#d9d9d9", 6)
                text(
                    p,
                    x,
                    557,
                    850,
                    40,
                    "Up to date" if self.upgrade_progress >= 100 else "Checking…",
                    22,
                )

    def row_label(self, p, label, y):
        text(p, 685, y - 29, 430, 58, label, 24)
        line(p, 685, y + 45, 1535, y + 45)

    def toggle(self, p, label, key, y):
        self.row_label(p, label, y)
        on = self.store.values[key]
        rect = QRectF(1433, y - 22, 84, 44)
        box(p, rect, "#d9d9d9" if on else "#343935", 22)
        box(
            p,
            QRectF(1475 if on else 1437, y - 18, 36, 36),
            "#131714" if on else "#b8bcb9",
            18,
        )
        self.register(QRectF(1150, y - 35, 385, 70), ("toggle", key))

    def choice(self, p, label, key, choices, y):
        self.row_label(p, label, y)
        rect = QRectF(1190, y - 28, 345, 56)
        box(p, rect, "#1f2420", 8)
        text(
            p,
            1204,
            y - 25,
            287,
            50,
            self.store.values[key],
            23,
            align=Qt.AlignmentFlag.AlignCenter,
        )
        line(p, 1501, y - 3, 1508, y + 4, WHITE, 2)
        line(p, 1508, y + 4, 1515, y - 3, WHITE, 2)
        self.register(rect, ("choice", key, choices))

    def slider(self, p, label, key, y):
        self.row_label(p, label, y)
        value = self.store.values[key]
        text(
            p, 1050, y - 24, 97, 48, f"{value}%", 23, align=Qt.AlignmentFlag.AlignRight
        )
        box(p, QRectF(1190, y - 4, 326, 8), "#333833", 4)
        box(p, QRectF(1190, y - 4, 3.26 * value, 8), "#d9d9d9", 4)
        box(p, QRectF(1174 + 3.26 * value, y - 16, 32, 32), "#f4f4f4", 16)
        self.register(QRectF(1168, y - 35, 370, 70), ("slider", key))

    def button(self, p, rect, label, action):
        box(p, rect, "#292f2b", 10, "#555c56")
        text(
            p,
            rect.x() + 12,
            rect.y(),
            rect.width() - 24,
            rect.height(),
            label,
            22,
            align=Qt.AlignmentFlag.AlignCenter,
        )
        self.register(rect, action)

    def draw_search(self, p):
        box(p, SEARCH_RECT, SEARCH_FILL, 24)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(WHITE), 1.8))
        p.drawEllipse(QRectF(814, 50, 12, 12))
        line(p, 824, 60, 829, 65, WHITE, 1.8)
        self.register(SEARCH_RECT, ("search",))
        box(p, HISTORY_RECT, SEARCH_FILL, 24)
        p.save()
        p.translate(HISTORY_RECT.x() - 1126, 0)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(WHITE), 1.8))
        path = QPainterPath(QPointF(1159, 56))
        path.lineTo(1159, 63)
        path.quadTo(1159, 66, 1156, 66)
        path.lineTo(1144, 66)
        path.quadTo(1141, 66, 1141, 63)
        path.lineTo(1141, 51)
        path.quadTo(1141, 48, 1144, 48)
        path.lineTo(1151, 48)
        p.drawPath(path)
        line(p, 1148, 59, 1160, 47, WHITE, 2)
        line(p, 1159, 46, 1161, 48, WHITE, 2)
        p.restore()
        self.register(HISTORY_RECT, ("history",))
        if self.search.text():
            cross(p, SEARCH_RECT.right() - 21, 57, 11, WHITE)
            self.register(QRectF(SEARCH_RECT.right() - 35, 33, 35, 48), ("clear",))

    def draw_popup(self, p):
        p.save()
        p.setWorldTransform(POPUP_TRANSFORM, True)
        self._draw_popup_reference(p)
        p.restore()

    def register_popup(self, rect, action):
        self.register(POPUP_TRANSFORM.mapRect(rect), action)

    def _draw_popup_reference(self, p):
        if self.overlay == "history":
            entries = [("history_item", s) for s in self.store.history]
            title = "Recent searches"
        else:
            entries = [("result", i) for i in self.store.search(self.search.text())]
            title = "Search results"
        count = min(8, len(entries))
        height = 76 + max(1, count) * 53
        rect = QRectF(781, 93, 402, height)
        box(p, rect, "#f0a5aaad", 28)
        text(p, 804, 108, 275, 42, title, 21, "#111617", bold=True)
        if self.overlay == "history":
            text(
                p,
                1080,
                108,
                82,
                42,
                "Clear",
                17,
                "#075dae",
                align=Qt.AlignmentFlag.AlignRight,
            )
            self.register_popup(QRectF(1078, 104, 90, 46), ("clear_history",))
        if not entries:
            text(
                p,
                804,
                169,
                356,
                44,
                "No recent searches"
                if self.overlay == "history"
                else "No matching settings",
                20,
                "#343a3d",
            )
        for i, (action, data) in enumerate(entries[:8]):
            y = 161 + i * 53
            if i:
                line(p, 804, y - 4, 1160, y - 4, "#858c90", 0.7)
            label = data if action == "history_item" else data[1]
            text(p, 804, y, 350, 43, label, 21, "#111617")
            if self.overlay != "history":
                self.register_popup(QRectF(795, y - 3, 376, 51), (action, data))

    def popup_rect(self):
        if self.overlay == "keyboard":
            return self.keyboard.rect
        n = (
            len(self.store.history)
            if self.overlay == "history"
            else len(self.store.search(self.search.text()))
        )
        return POPUP_TRANSFORM.mapRect(
            QRectF(781, 93, 402, 76 + max(1, min(8, n)) * 53)
        )

    def open_search(self):
        self.overlay = "keyboard"
        self.layout_search()
        self.search.setFocus()
        self.update()

    def close_overlay(self):
        self.backspace_hold.stop()
        if self.overlay == 'keyboard':
            self.remember_query()
        self.overlay = None
        self.layout_search()
        self.keyboard.pressed = None
        self.search.clearFocus()
        self.setFocus()
        self.update()

    def search_changed(self):
        self.query_dirty = True
        if self.overlay is None:
            self.overlay = "keyboard"
            self.layout_search()
        self.update()

    def submit_search(self):
        query = self.search.text().strip()
        self.store.remember(query)
        self.query_dirty = False
        matches = self.store.search(query)
        if query and len(matches) == 1:
            self.select(self.order.index(matches[0][0]))
            self.close_overlay()
        else:
            self.overlay = "results"
            self.layout_search()
            self.search.clearFocus()
            self.update()

    def activate(self, action):
        kind = action[0]
        if kind == "close":
            self.close()
        elif kind == "search":
            self.open_search()
        elif kind == "history":
            if self.overlay == 'keyboard':self.remember_query()
            self.overlay = None if self.overlay == "history" else "history"
            self.layout_search()
            self.search.clearFocus()
        elif kind == "clear":
            self.search.clear()
            self.open_search()
        elif kind == "clear_history":
            self.store.history = []
            self.query_dirty = False
            self.persist()
        elif kind == "history_item":
            return  # History is a read-only viewer; only Clear changes it.
        elif kind == "result":
            self.store.remember(self.search.text())
            self.select(self.order.index(action[1][0]))
            self.close_overlay()
        elif kind == "suggest":
            cursor = self.search.cursorPosition()
            content = self.search.text()
            start = cursor
            while start > 0 and content[start-1].isalnum():
                start -= 1
            end = cursor
            while end < len(content) and content[end].isalnum():
                end += 1
            self.search.setSelection(start, end-start)
            self.search.insert(action[1] + " ")
        elif kind == "key":
            key = action[1]
            if key == "shift":
                self.keyboard.shift = not self.keyboard.shift
            elif key == "close":
                self.close_overlay()
            elif key == "left":
                self.search.setCursorPosition(max(0,self.search.cursorPosition()-1))
            elif key == "right":
                self.search.setCursorPosition(min(len(self.search.text()),self.search.cursorPosition()+1))
            elif key == "backspace":
                self.search.backspace()
            elif key == "space":
                self.search.insert(" ")
            elif key == "enter":
                self.submit_search()
            else:
                self.search.insert(key.upper() if self.keyboard.shift else key)
                self.keyboard.shift = False
        elif kind == "toggle":
            key = action[1]
            self.store.values[key] = not self.store.values[key]
            self.persist()
        elif kind == "choice":
            key, choices = action[1:]
            current = self.store.values[key]
            self.store.values[key] = (
                choices[(choices.index(current) + 1) % len(choices)]
                if current in choices
                else choices[0]
            )
            self.persist()
        elif kind == "upgrade":
            self.upgrade_progress = 0
        elif kind == "export":
            import json

            try:
                out = ROOT / "exports"
                out.mkdir(exist_ok=True)
                (out / "nexatom-settings.json").write_text(
                    json.dumps(self.store.values, indent=2), encoding="utf8"
                )
                self.notify("Saved exports/nexatom-settings.json")
            except OSError:
                self.notify("Export failed: the application folder is not writable")
        self.update()

    def persist(self):
        if not self.store.save():
            self.notify(self.store.error)

    def remember_query(self):
        if self.query_dirty:
            self.store.remember(self.search.text())
            self.query_dirty = False
            if self.store.error:self.notify(self.store.error)

    def clear_held_input(self):
        if self.overlay == 'keyboard' and self.pending and self.pending[1] == ('key','backspace'):
            self.search.clear()
            self.pending = None  # Release must not delete a second time.
            self.keyboard.pressed = None
            self.update()

    def eventFilter(self, obj, event):
        if obj is self.search:
            if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.TouchBegin):
                self.open_search()
            if (
                event.type() == QEvent.Type.KeyPress
                and event.key() == Qt.Key.Key_Escape
            ):
                self.close_overlay()
                return True
        return super().eventFilter(obj, event)

    def pointer_down(self, pt):
        self.backspace_hold.stop()
        self.pending = None
        self.gesture = None
        self.dragged = False
        if (
            self.overlay
            and not self.popup_rect().contains(pt)
            and (self.overlay=='keyboard' or not SEARCH_GROUP.contains(pt))
        ):
            self.close_overlay()
            return
        for rect, action in reversed(self.hits):
            if rect.contains(pt):
                self.pending = (rect, action)
                if action[0] == "key":
                    self.keyboard.pressed = action[1]
                    if action[1] == 'backspace':self.backspace_hold.start()
                    self.update()
                if action[0] == "slider":
                    self.gesture = "slider"
                    self.slider_key = action[1]
                    self.change_slider(pt)
                return
        if self.overlay == 'keyboard':
            return  # Empty spaces between keys must not scroll the settings wheel.
        if pt.x() < 633 and (self.variant != 32 or pt.y() >= 100):
            self.gesture = "menu"
            self.start = pt
            self.previous = pt
            self.samples.clear()
            self.samples.append((time.monotonic(), self.motion.position))
            self.tapped_index = None
            for rect, idx in self.menu_hits:
                if rect.contains(pt):
                    self.tapped_index = idx
                    break
            if self.variant != 32:
                self.motion.begin()

    def change_slider(self, pt):
        self.store.values[self.slider_key] = round(
            max(0, min(100, (pt.x() - 1190) / 3.26))
        )
        self.update()

    def pointer_move(self, pt):
        if self.pending and self.pending[1] == ('key','backspace') and not self.pending[0].contains(pt):
            self.backspace_hold.stop()
        if self.gesture == "slider":
            self.change_slider(pt)
            return
        if self.gesture != "menu" or self.variant == 32:
            return
        if (pt - self.start).manhattanLength() > 7:
            self.dragged = True
        if self.dragged:
            if self.variant == 59:
                a = math.atan2(self.previous.y() - 354, self.previous.x() + 50)
                b = math.atan2(pt.y() - 354, pt.x() + 50)
                delta = -math.atan2(math.sin(b - a), math.cos(b - a)) / 0.32
            else:
                delta = -(pt.y() - self.previous.y()) / 104
            self.motion.drag(delta)
            self.samples.append((time.monotonic(), self.motion.position))
            self.update()
        self.previous = pt

    def pointer_up(self, pt):
        self.backspace_hold.stop()
        if self.gesture == "slider":
            self.persist()
        elif self.gesture == "menu":
            if not self.dragged:
                self.motion.dragging = False
                if self.tapped_index is not None:
                    self.select(self.tapped_index % len(self.order), self.tapped_index)
                elif self.variant != 32:
                    self.motion.release(0)
            elif self.variant != 32:
                now = time.monotonic()
                self.samples.append((now, self.motion.position))
                recent = [s for s in self.samples if now - s[0] <= 0.14]
                velocity = 0
                if len(recent) > 1 and recent[-1][0] - recent[0][0] > 0.005:
                    velocity = (recent[-1][1] - recent[0][1]) / (
                        recent[-1][0] - recent[0][0]
                    )
                self.motion.release(velocity)
        elif self.pending and self.pending[0].contains(pt):
            self.activate(self.pending[1])
        self.pending = None
        self.gesture = None
        self.keyboard.pressed = None
        self.update()

    def mousePressEvent(self, event):
        if self.ignore_compatibility_mouse(event):
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.pointer_down(self.point(event.position()))
            event.accept()

    def mouseMoveEvent(self, event):
        if self.ignore_compatibility_mouse(event):
            event.accept()
            return
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.pointer_move(self.point(event.position()))
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.ignore_compatibility_mouse(event):
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.pointer_up(self.point(event.position()))
            event.accept()

    def ignore_compatibility_mouse(self, event):
        return self._touch_active or (
            event.source() != Qt.MouseEventSource.MouseEventNotSynthesized
            and time.monotonic() - self._last_touch < 0.8
        )

    def event(self, event):
        if event.type() in (
            QEvent.Type.TouchBegin,
            QEvent.Type.TouchUpdate,
            QEvent.Type.TouchEnd,
        ):
            self._last_touch = time.monotonic()
            if event.type() == QEvent.Type.TouchBegin and event.points():
                self._touch_id = event.points()[0].id()
                self._touch_active = True
                self.pointer_down(self.point(event.points()[0].position()))
            elif self._touch_active:
                point = next((p for p in event.points() if p.id() == self._touch_id), None)
                if point is not None:
                    pt = self.point(point.position())
                    if event.type() == QEvent.Type.TouchEnd or point.state() == point.State.Released:
                        self._touch_active = False
                        self._touch_id = None
                        self.pointer_up(pt)
                    else:
                        self.pointer_move(pt)
            event.accept()
            return True
        if event.type() == QEvent.Type.TouchCancel:
            self.backspace_hold.stop()
            self._touch_active = False
            self._touch_id = None
            self._last_touch = time.monotonic()
            self.motion.release(0)
            self.gesture = None
            self.pending = None
            self.keyboard.pressed = None
            self.update()
            event.accept()
            return True
        return super().event(event)

    def wheelEvent(self, event):
        pt = self.point(event.position())
        if pt.x() < 633 and self.variant != 32 and not self.overlay:
            delta = (
                event.pixelDelta().y() / 104
                if not event.pixelDelta().isNull()
                else event.angleDelta().y() / 120
            )
            self.motion.move_to(
                (
                    self.motion.target
                    if self.motion.target is not None
                    else self.motion.position
                )
                - delta
            )
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.overlay:
                self.close_overlay()
            elif self.isFullScreen():
                self.showNormal()
            else:
                self.close()
        elif event.key() == Qt.Key.Key_F11:
            self.showNormal() if self.isFullScreen() else self.showFullScreen()
        elif event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            d = 1 if event.key() == Qt.Key.Key_Down else -1
            target = (
                round(
                    self.motion.target
                    if self.motion.target is not None
                    else self.motion.position
                )
                + d
            )
            self.select(target % len(self.order), target)
        else:
            super().keyPressEvent(event)
