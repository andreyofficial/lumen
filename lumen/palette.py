"""Command palette — fuzzy-searchable list of actions, like Ctrl+Shift+P."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QAction
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QColor


class CommandPalette(QFrame):
    """A floating, modal-feeling palette for running named commands."""

    triggered = pyqtSignal(QAction)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("CommandPalette")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWindowFlag(Qt.WindowType.SubWindow, True)
        self.hide()

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.setGraphicsEffect(shadow)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Run a command")
        title.setProperty("role", "muted")
        title.setContentsMargins(4, 0, 4, 0)
        header.addWidget(title)
        header.addStretch(1)
        outer.addLayout(header)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a command…  (e.g. open, save, find, theme)")
        self.input.textChanged.connect(self._filter)
        self.input.installEventFilter(self)
        outer.addWidget(self.input)

        self.list = QListWidget()
        self.list.setObjectName("CommandList")
        self.list.itemActivated.connect(self._activate_item)
        outer.addWidget(self.list, 1)

        self._actions: list[QAction] = []

    def set_actions(self, actions: list[QAction]) -> None:
        self._actions = [a for a in actions if a.text()]

    def open(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        w = min(720, parent.width() - 80)
        h = min(420, parent.height() - 120)
        x = (parent.width() - w) // 2
        y = max(80, parent.height() // 6)
        self.setGeometry(x, y, w, h)
        self.input.clear()
        self._filter("")
        self.show()
        self.raise_()
        self.input.setFocus()

    def _filter(self, query: str) -> None:
        self.list.clear()
        q = query.strip().lower()
        scored: list[tuple[int, str, "QAction"]] = []
        for action in self._actions:
            label = action.text().replace("&", "")
            score = self._score(q, label.lower())
            if score < 0:
                continue
            scored.append((score, label, action))
        scored.sort(key=lambda t: (t[0], t[1].lower()))
        for score, label, action in scored:
            shortcut = action.shortcut().toString() if action.shortcut() else ""
            item = QListWidgetItem()
            item.setText(label + (f"\u2003\u2003{shortcut}" if shortcut else ""))
            item.setData(Qt.ItemDataRole.UserRole, action)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    @staticmethod
    def _score(query: str, label: str) -> int:
        if not query:
            return 0
        if query in label:
            return label.index(query)
        # subsequence match
        i = 0
        for ch in label:
            if i < len(query) and ch == query[i]:
                i += 1
        if i == len(query):
            return 1000 + len(label)
        return -1

    def _activate_item(self, item: QListWidgetItem) -> None:
        action = item.data(Qt.ItemDataRole.UserRole)
        self.hide()
        if isinstance(action, QAction):
            action.trigger()
            self.triggered.emit(action)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event: QEvent) -> bool:  # noqa: N802
        if obj is self.input and event.type() == QEvent.Type.KeyPress:
            assert isinstance(event, QKeyEvent)
            if event.key() == Qt.Key.Key_Down:
                row = min(self.list.count() - 1, self.list.currentRow() + 1)
                self.list.setCurrentRow(row)
                return True
            if event.key() == Qt.Key.Key_Up:
                row = max(0, self.list.currentRow() - 1)
                self.list.setCurrentRow(row)
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                item = self.list.currentItem()
                if item:
                    self._activate_item(item)
                return True
            if event.key() == Qt.Key.Key_Escape:
                self.hide()
                return True
        return super().eventFilter(obj, event)
