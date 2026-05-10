"""Find / Replace bar that slides in below the active editor."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QTextDocument
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .editor import CodeEditor
from .icons import icon


class FindBar(QFrame):
    """Slim find/replace bar embedded above the status bar."""

    closed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FindBar")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._editor: CodeEditor | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(6)

        # Find row
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        find_label = QLabel("Find")
        find_label.setObjectName("FindLabel")
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find in current file…")
        self.find_input.textChanged.connect(self._update_count)
        self.find_input.returnPressed.connect(self.find_next)

        self.case_cb = QCheckBox("Aa")
        self.case_cb.setToolTip("Match case")
        self.word_cb = QCheckBox("W")
        self.word_cb.setToolTip("Whole word")
        self.regex_cb = QCheckBox(".*")
        self.regex_cb.setToolTip("Regular expression")

        prev_btn = QToolButton()
        prev_btn.setText("‹")
        prev_btn.setToolTip("Previous match (Shift+F3)")
        prev_btn.clicked.connect(self.find_previous)

        next_btn = QToolButton()
        next_btn.setText("›")
        next_btn.setToolTip("Next match (F3)")
        next_btn.clicked.connect(self.find_next)

        self.count_label = QLabel("")
        self.count_label.setProperty("role", "dim")

        close_btn = QToolButton()
        close_btn.setIcon(icon("close"))
        close_btn.setToolTip("Close (Esc)")
        close_btn.clicked.connect(self.close_bar)

        row1.addWidget(find_label)
        row1.addWidget(self.find_input, 1)
        row1.addWidget(self.case_cb)
        row1.addWidget(self.word_cb)
        row1.addWidget(self.regex_cb)
        row1.addWidget(prev_btn)
        row1.addWidget(next_btn)
        row1.addWidget(self.count_label)
        row1.addStretch(0)
        row1.addWidget(close_btn)
        outer.addLayout(row1)

        # Replace row
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        replace_label = QLabel("Replace")
        replace_label.setObjectName("FindLabel")
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with…")

        replace_btn = QPushButton("Replace")
        replace_btn.clicked.connect(self.replace_one)
        replace_all_btn = QPushButton("All")
        replace_all_btn.setDefault(True)
        replace_all_btn.clicked.connect(self.replace_all)

        row2.addWidget(replace_label)
        row2.addWidget(self.replace_input, 1)
        row2.addWidget(replace_btn)
        row2.addWidget(replace_all_btn)
        outer.addLayout(row2)

        self.hide()

    # ---------- public API ----------

    def attach_editor(self, editor: CodeEditor | None) -> None:
        self._editor = editor
        self._update_count()

    def show_for(self, editor: CodeEditor, *, with_replace: bool = False) -> None:
        self.attach_editor(editor)
        sel = editor.textCursor().selectedText()
        if sel and "\u2029" not in sel:  # not a multi-line selection
            self.find_input.setText(sel)
        self.show()
        self.find_input.setFocus()
        self.find_input.selectAll()

    def close_bar(self) -> None:
        self.hide()
        self.closed.emit()
        if self._editor:
            self._editor.setFocus()

    # ---------- search ----------

    def _flags(self) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if self.case_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.word_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        return flags

    def _do_find(self, *, backward: bool = False) -> bool:
        if not self._editor:
            return False
        needle = self.find_input.text()
        if not needle:
            return False
        flags = self._flags()
        if backward:
            flags |= QTextDocument.FindFlag.FindBackward

        if self.regex_cb.isChecked():
            from PyQt6.QtCore import QRegularExpression
            opts = QRegularExpression.PatternOption.NoPatternOption
            if not self.case_cb.isChecked():
                opts |= QRegularExpression.PatternOption.CaseInsensitiveOption
            rx = QRegularExpression(needle, opts)
            ok = self._editor.find(rx, flags)
        else:
            ok = self._editor.find(needle, flags)

        if not ok:
            # Wrap around
            cursor = self._editor.textCursor()
            cursor.movePosition(
                cursor.MoveOperation.End if backward else cursor.MoveOperation.Start
            )
            self._editor.setTextCursor(cursor)
            if self.regex_cb.isChecked():
                from PyQt6.QtCore import QRegularExpression
                opts = QRegularExpression.PatternOption.NoPatternOption
                if not self.case_cb.isChecked():
                    opts |= QRegularExpression.PatternOption.CaseInsensitiveOption
                rx = QRegularExpression(needle, opts)
                ok = self._editor.find(rx, flags)
            else:
                ok = self._editor.find(needle, flags)
        return ok

    def find_next(self) -> None:
        self._do_find(backward=False)
        self._update_count()

    def find_previous(self) -> None:
        self._do_find(backward=True)
        self._update_count()

    def replace_one(self) -> None:
        if not self._editor:
            return
        needle = self.find_input.text()
        if not needle:
            return
        cursor = self._editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == needle:
            cursor.insertText(self.replace_input.text())
        self.find_next()

    def replace_all(self) -> None:
        if not self._editor:
            return
        needle = self.find_input.text()
        if not needle:
            return
        replacement = self.replace_input.text()
        text = self._editor.toPlainText()
        count = 0
        if self.regex_cb.isChecked():
            import re
            flags = 0 if self.case_cb.isChecked() else re.IGNORECASE
            try:
                pattern = re.compile(needle, flags)
            except re.error:
                return
            new_text, count = pattern.subn(replacement, text)
        else:
            if self.case_cb.isChecked():
                count = text.count(needle)
                new_text = text.replace(needle, replacement)
            else:
                # Case-insensitive plain replace
                import re
                pattern = re.compile(re.escape(needle), re.IGNORECASE)
                new_text, count = pattern.subn(replacement, text)
        if count:
            cursor = self._editor.textCursor()
            cursor.beginEditBlock()
            cursor.select(cursor.SelectionType.Document)
            cursor.insertText(new_text)
            cursor.endEditBlock()
        self.count_label.setText(f"{count} replaced")

    # ---------- helpers ----------

    def _update_count(self) -> None:
        if not self._editor:
            self.count_label.setText("")
            return
        needle = self.find_input.text()
        if not needle:
            self.count_label.setText("")
            return
        text = self._editor.toPlainText()
        if self.regex_cb.isChecked():
            import re
            flags = 0 if self.case_cb.isChecked() else re.IGNORECASE
            try:
                count = len(re.findall(needle, text, flags))
            except re.error:
                count = 0
        else:
            if self.case_cb.isChecked():
                count = text.count(needle)
            else:
                count = text.lower().count(needle.lower())
        self.count_label.setText(f"{count} match" + ("es" if count != 1 else ""))

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.close_bar()
            return
        super().keyPressEvent(event)
