"""Shared search geometry in the 1600 × 720 design coordinate space."""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QTransform

SEARCH_RECT = QRectF((1600-(321*1.5+60))/2, 25, 321 * 1.5, 48)
HISTORY_RECT = QRectF(SEARCH_RECT.right() + 12, 25, 48, 48)
SEARCH_GROUP = SEARCH_RECT.united(HISTORY_RECT)
INPUT_RECT = QRectF(SEARCH_RECT.left() + 46, 26, SEARCH_RECT.width() - 82, 46)
SEARCH_FILL = "#b3202020"  # The wheel's #202020, at 70% opacity.
REFERENCE_POPUP = QRectF(781, 93, 402, 297)
POPUP_SCALE = SEARCH_RECT.width() / REFERENCE_POPUP.width()
POPUP_TRANSFORM = QTransform()
POPUP_TRANSFORM.translate(SEARCH_RECT.left(), REFERENCE_POPUP.top())
POPUP_TRANSFORM.scale(POPUP_SCALE, POPUP_SCALE)
POPUP_TRANSFORM.translate(-REFERENCE_POPUP.left(), -REFERENCE_POPUP.top())
KEYBOARD_RECT = QRectF(280, 228, 1040, 456)  # Taller, with 36 px bottom clearance.
KEYBOARD_INPUT_RECT = QRectF(332, 244, 856, 48)
