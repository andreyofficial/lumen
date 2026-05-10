"""Minimap — a small overview of the document on the right of the editor.

Renders each line as a thin horizontal bar whose width is proportional to
the line's content length. The visible viewport is overlaid as a translucent
rectangle, and the user can click/drag anywhere on the minimap to scroll.
"""

from __future__ import annotations

from PyQt6.QtCore import QRect, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QResizeEvent
from PyQt6.QtWidgets import QPlainTextEdit, QWidget

from . import theme


class Minimap(QWidget):
    LINE_HEIGHT = 2     # pixels per line
    LEFT_PAD = 4
    RIGHT_PAD = 4
    MAX_CHARS = 90      # treat anything beyond this as "full-width"

    def __init__(self, editor: QPlainTextEdit, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Minimap")
        self._editor = editor
        self._dragging = False
        self.setMouseTracking(True)
        self.setFixedWidth(110)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Repaint on any change
        editor.document().contentsChanged.connect(self._schedule_update)
        editor.verticalScrollBar().valueChanged.connect(self.update)
        editor.cursorPositionChanged.connect(self.update)

        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(40)
        self._update_timer.timeout.connect(self.update)

    def _schedule_update(self) -> None:
        self._update_timer.start()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(110, 200)

    # ---------------- mapping ----------------

    def _line_count(self) -> int:
        return max(1, self._editor.document().blockCount())

    def _scale(self) -> float:
        usable_h = max(1, self.height())
        needed = self._line_count() * self.LINE_HEIGHT
        if needed <= usable_h:
            return 1.0
        return usable_h / needed

    def _line_at_y(self, y: int) -> int:
        scale = self._scale()
        line = int(y / (self.LINE_HEIGHT * scale))
        return max(0, min(self._line_count() - 1, line))

    # ---------------- painting ----------------

    def paintEvent(self, _ev: QPaintEvent) -> None:  # noqa: N802
        p = theme.PALETTE
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(p.bg_editor))

        scale = self._scale()
        h = self.LINE_HEIGHT * scale
        usable_w = self.width() - self.LEFT_PAD - self.RIGHT_PAD

        block = self._editor.document().firstBlock()
        idx = 0
        line_color = QColor(p.text_muted)
        line_color.setAlpha(120)
        accent_color = QColor(p.accent)
        accent_color.setAlpha(220)
        cursor_block = self._editor.textCursor().blockNumber()

        while block.isValid():
            text = block.text()
            stripped_len = len(text.rstrip())
            indent = len(text) - len(text.lstrip(" \t"))
            if stripped_len > 0:
                length_ratio = min(1.0, (stripped_len - indent) / self.MAX_CHARS)
                indent_ratio = min(1.0, indent / self.MAX_CHARS)
                bar_x = self.LEFT_PAD + int(indent_ratio * usable_w)
                bar_w = max(1, int(length_ratio * usable_w))
                y = int(idx * h)
                bh = max(1, int(h))
                color = accent_color if idx == cursor_block else line_color
                painter.fillRect(QRect(bar_x, y, bar_w, bh), color)
            idx += 1
            block = block.next()

        # Visible viewport overlay
        sb = self._editor.verticalScrollBar()
        first_visible = sb.value()
        # Approximate visible-line count using viewport / line height
        line_h_px = max(1, self._editor.fontMetrics().height())
        visible_lines = max(1, self._editor.viewport().height() // line_h_px)
        view_y = int(first_visible * h)
        view_h = max(8, int(visible_lines * h))
        overlay_color = QColor(p.text)
        overlay_color.setAlpha(28)
        painter.fillRect(QRect(0, view_y, self.width(), view_h), overlay_color)
        # Border
        border_color = QColor(p.border_strong)
        border_color.setAlpha(200)
        painter.setPen(border_color)
        painter.drawRect(QRect(0, view_y, self.width() - 1, view_h - 1))
        painter.end()

    # ---------------- mouse ----------------

    def mousePressEvent(self, ev: QMouseEvent) -> None:  # noqa: N802
        if ev.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._scroll_to(int(ev.position().y()))

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:  # noqa: N802
        if self._dragging:
            self._scroll_to(int(ev.position().y()))

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:  # noqa: N802
        if ev.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def wheelEvent(self, ev) -> None:  # noqa: N802
        # Pass through to editor for natural scrolling
        self._editor.verticalScrollBar().wheelEvent(ev)

    def resizeEvent(self, ev: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(ev)
        self.update()

    def _scroll_to(self, y: int) -> None:
        line = self._line_at_y(y)
        sb = self._editor.verticalScrollBar()
        # Center the clicked line in the viewport
        line_h_px = max(1, self._editor.fontMetrics().height())
        visible_lines = max(1, self._editor.viewport().height() // line_h_px)
        target = max(sb.minimum(), min(sb.maximum(), line - visible_lines // 2))
        sb.setValue(target)
        self.update()
