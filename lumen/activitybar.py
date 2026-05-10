"""Vertical activity bar — a thin column of icons for switching sidebar views."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class ActivityBar(QFrame):
    view_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ActivityBar")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedWidth(48)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(2)

        self._buttons: dict[str, QToolButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._layout = layout
        layout.addStretch(1)

    def add_view(
        self,
        view_id: str,
        icon: QIcon,
        tooltip: str,
        *,
        bottom: bool = False,
    ) -> QToolButton:
        btn = QToolButton(self)
        btn.setObjectName("ActivityBtn")
        btn.setIcon(icon)
        btn.setIconSize(btn.iconSize() * 1.2)
        btn.setCheckable(not bottom)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(44)
        btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        if not bottom:
            self._group.addButton(btn)
            btn.toggled.connect(
                lambda checked, vid=view_id: checked and self.view_changed.emit(vid)
            )
            # Insert before the stretch (last item)
            self._layout.insertWidget(self._layout.count() - 1, btn)
        else:
            self._layout.addWidget(btn)
        self._buttons[view_id] = btn
        return btn

    def select(self, view_id: str) -> None:
        btn = self._buttons.get(view_id)
        if btn is not None and btn.isCheckable():
            btn.setChecked(True)

    def button(self, view_id: str) -> QToolButton | None:
        return self._buttons.get(view_id)
