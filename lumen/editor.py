"""CodeEditor — a QPlainTextEdit with line numbers, current-line highlight,
bracket matching, smart indentation, auto-pairing, code completion popup,
duplicate-line / move-line shortcuts and TODO highlighting."""

from __future__ import annotations

import keyword
import re

from PyQt6.QtCore import QRect, QSize, QStringListModel, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
    QFontMetrics,
)
from PyQt6.QtWidgets import QCompleter, QPlainTextEdit, QTextEdit, QWidget

from .theme import PALETTE


# Common keywords + builtins for the bundled "always available" completion
# list. Per-language keywords are mixed in via ``set_completion_keywords``.
_PY_KEYWORDS = sorted(set(keyword.kwlist) | set(dir(__builtins__) if isinstance(__builtins__, dict) else dir(__builtins__)))
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


_BRACKET_PAIRS = {"(": ")", "[": "]", "{": "}"}
_OPENERS = set(_BRACKET_PAIRS.keys())
_CLOSERS = set(_BRACKET_PAIRS.values())
_AUTO_PAIRS = {**_BRACKET_PAIRS, '"': '"', "'": "'", "`": "`"}


class _LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """A polished plain text editor for code."""

    cursor_position_changed = pyqtSignal(int, int)  # line, col

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._line_area = _LineNumberArea(self)
        self._tab_size = 4
        self._use_spaces = True
        self._show_line_numbers = True

        self._setup_font(13)
        self.setTabChangesFocus(False)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setCursorWidth(2)
        self.setFrameShape(QPlainTextEdit.Shape.NoFrame)
        self.setMouseTracking(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.blockCountChanged.connect(self._update_viewport_margins)
        self.updateRequest.connect(self._on_update_request)
        self.cursorPositionChanged.connect(self._on_cursor_changed)

        # Completion popup — driven by language keywords + the words
        # currently in the document. Triggers automatically once the
        # prefix is at least ``_completion_min_chars`` long.
        self._completer_model = QStringListModel([], self)
        self._completer = QCompleter(self._completer_model, self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setWrapAround(False)
        self._completer.activated[str].connect(self._insert_completion)
        self._completion_keywords: list[str] = list(_PY_KEYWORDS)
        self._completion_min_chars = 2

        # Debounce model rebuilds so we don't re-scan the document on
        # every keystroke. 250ms feels instant but coalesces bursts.
        self._completion_refresh = QTimer(self)
        self._completion_refresh.setSingleShot(True)
        self._completion_refresh.setInterval(250)
        self._completion_refresh.timeout.connect(self._rebuild_completion_model)
        self.textChanged.connect(self._completion_refresh.start)

        self._update_viewport_margins()
        self._highlight_current_line()
        self._emit_cursor_pos()
        self._rebuild_completion_model()

    # ---------------- Font / settings ----------------

    def _setup_font(self, size: int) -> None:
        f = QFont(
            "JetBrains Mono",
            size,
        )
        f.setStyleHint(QFont.StyleHint.Monospace)
        f.setFixedPitch(True)
        for fam in ("JetBrains Mono", "Fira Code", "Cascadia Code", "Source Code Pro",
                    "Ubuntu Mono", "DejaVu Sans Mono", "monospace"):
            f.setFamily(fam)
            if QFontMetrics(f).horizontalAdvance("M") > 0:
                break
        self.setFont(f)
        self.setTabStopDistance(QFontMetrics(f).horizontalAdvance(" ") * self._tab_size)

    def set_font_size(self, size: int) -> None:
        self._setup_font(max(8, min(40, size)))

    def font_size(self) -> int:
        return self.font().pointSize()

    def set_tab_size(self, size: int) -> None:
        self._tab_size = max(1, min(8, size))
        self.setTabStopDistance(
            QFontMetrics(self.font()).horizontalAdvance(" ") * self._tab_size
        )

    def set_use_spaces(self, use_spaces: bool) -> None:
        self._use_spaces = use_spaces

    def set_show_line_numbers(self, show: bool) -> None:
        self._show_line_numbers = show
        self._line_area.setVisible(show)
        self._update_viewport_margins()

    # ---------------- Line numbers ----------------

    def line_number_area_width(self) -> int:
        if not self._show_line_numbers:
            return 0
        digits = max(3, len(str(max(1, self.blockCount()))))
        char_w = QFontMetrics(self.font()).horizontalAdvance("9")
        return 16 + char_w * digits

    def _update_viewport_margins(self) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _on_update_request(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_viewport_margins()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def paint_line_numbers(self, event: QPaintEvent) -> None:
        if not self._show_line_numbers:
            return
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor(PALETTE.line_number_bg))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        offset = self.contentOffset()
        top = self.blockBoundingGeometry(block).translated(offset).top()
        bottom = top + self.blockBoundingRect(block).height()

        current = self.textCursor().blockNumber()
        normal = QColor(PALETTE.line_number_fg)
        active = QColor(PALETTE.line_number_fg_active)
        font = self.font()
        painter.setFont(font)
        line_height = self.fontMetrics().height()
        width = self._line_area.width()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(active if block_number == current else normal)
                painter.drawText(
                    0, int(top), width - 8, line_height,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1
        painter.end()

    # ---------------- Highlights ----------------

    def _highlight_current_line(self) -> None:
        selections: list[QTextEdit.ExtraSelection] = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            line_color = QColor(PALETTE.current_line_bg)
            sel.format.setBackground(line_color)
            sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            selections.append(sel)
        # bracket match
        selections.extend(self._bracket_match_selections())
        self.setExtraSelections(selections)

    def _bracket_match_selections(self) -> list[QTextEdit.ExtraSelection]:
        out: list[QTextEdit.ExtraSelection] = []
        cursor = self.textCursor()
        doc = self.document()
        pos = cursor.position()
        if pos < 0:
            return out

        ch_after = doc.characterAt(pos)
        ch_before = doc.characterAt(pos - 1) if pos > 0 else ""

        target_pos = -1
        target_char = ""
        match_pos = -1

        if ch_after in _OPENERS:
            target_pos = pos
            target_char = ch_after
            match_pos = self._find_match(pos, ch_after, _BRACKET_PAIRS[ch_after], 1)
        elif ch_before in _CLOSERS:
            target_pos = pos - 1
            target_char = ch_before
            opener = next(o for o, c in _BRACKET_PAIRS.items() if c == ch_before)
            match_pos = self._find_match(pos - 1, ch_before, opener, -1)

        if target_pos >= 0 and match_pos >= 0:
            for p in (target_pos, match_pos):
                sel = QTextEdit.ExtraSelection()
                fmt = QTextCharFormat()
                fmt.setBackground(QColor(PALETTE.matching_bracket_bg))
                fmt.setForeground(QColor(PALETTE.accent))
                sel.format = fmt
                c = QTextCursor(doc)
                c.setPosition(p)
                c.movePosition(
                    QTextCursor.MoveOperation.NextCharacter,
                    QTextCursor.MoveMode.KeepAnchor,
                )
                sel.cursor = c
                out.append(sel)
        return out

    def _find_match(self, pos: int, this_ch: str, other_ch: str, direction: int) -> int:
        doc = self.document()
        depth = 1
        i = pos + direction
        end = doc.characterCount()
        while 0 <= i < end:
            c = doc.characterAt(i)
            if c == this_ch:
                depth += 1
            elif c == other_ch:
                depth -= 1
                if depth == 0:
                    return i
            i += direction
        return -1

    # ---------------- Cursor & key handling ----------------

    def _on_cursor_changed(self) -> None:
        self._highlight_current_line()
        self._emit_cursor_pos()

    def _emit_cursor_pos(self) -> None:
        c = self.textCursor()
        line = c.blockNumber() + 1
        col = c.positionInBlock() + 1
        self.cursor_position_changed.emit(line, col)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        text = event.text()
        cursor = self.textCursor()
        mods = event.modifiers()

        # If the completion popup is showing, let it handle navigation /
        # accept keys before any of our editor-level shortcuts run.
        if self._completer.popup().isVisible():
            if key in (
                Qt.Key.Key_Enter,
                Qt.Key.Key_Return,
                Qt.Key.Key_Escape,
                Qt.Key.Key_Tab,
                Qt.Key.Key_Backtab,
            ):
                event.ignore()
                return

        # Ctrl+Space — manually trigger completion popup.
        if key == Qt.Key.Key_Space and (mods & Qt.KeyboardModifier.ControlModifier):
            self._show_completion_popup(force=True)
            return

        # Alt+Shift+Up / Alt+Shift+Down — move line(s) up / down.
        alt_shift = (
            (mods & Qt.KeyboardModifier.AltModifier)
            and (mods & Qt.KeyboardModifier.ShiftModifier)
        )
        if alt_shift and key == Qt.Key.Key_Up:
            self._move_lines(-1)
            return
        if alt_shift and key == Qt.Key.Key_Down:
            self._move_lines(+1)
            return

        # Smart indent on Enter
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not cursor.hasSelection():
                block_text = cursor.block().text()
                indent = ""
                for ch in block_text:
                    if ch in (" ", "\t"):
                        indent += ch
                    else:
                        break
                # Increase indent if line ends with an opener / colon
                stripped = block_text.rstrip()
                extra = ""
                if stripped.endswith((":", "{", "(", "[")) and cursor.positionInBlock() == len(block_text):
                    extra = " " * self._tab_size if self._use_spaces else "\t"
                # Smart "}" / ")" / "]" auto-dedent on Enter between pair
                pos = cursor.position()
                doc = self.document()
                ch_before = doc.characterAt(pos - 1) if pos > 0 else ""
                ch_after = doc.characterAt(pos)
                if ch_before in _OPENERS and ch_after == _BRACKET_PAIRS.get(ch_before, ""):
                    super().keyPressEvent(event)
                    cursor = self.textCursor()
                    cursor.insertText(indent + (" " * self._tab_size if self._use_spaces else "\t"))
                    save = cursor.position()
                    cursor.insertText("\n" + indent)
                    cursor.setPosition(save)
                    self.setTextCursor(cursor)
                    return
                super().keyPressEvent(event)
                self.textCursor().insertText(indent + extra)
                return

        # Tab / Shift+Tab — indent / dedent block
        if key == Qt.Key.Key_Tab and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            if cursor.hasSelection():
                self._indent_selection(cursor, dedent=False)
                return
            if self._use_spaces:
                cursor.insertText(" " * self._tab_size)
                return
        if key == Qt.Key.Key_Backtab:
            self._indent_selection(cursor, dedent=True)
            return

        # Auto-pair brackets/quotes
        if text in _AUTO_PAIRS and not cursor.hasSelection():
            close = _AUTO_PAIRS[text]
            doc = self.document()
            ch_after = doc.characterAt(cursor.position())
            # Skip over closing char if already there
            if text == close and ch_after == close:
                cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
                self.setTextCursor(cursor)
                return
            # Don't auto-pair if next char is alphanumeric
            if not (ch_after.isalnum() or ch_after == "_"):
                cursor.insertText(text + close)
                cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
                self.setTextCursor(cursor)
                return

        # Wrap selection with bracket / quote
        if text in _AUTO_PAIRS and cursor.hasSelection():
            close = _AUTO_PAIRS[text]
            sel = cursor.selectedText()
            cursor.insertText(text + sel + close)
            return

        # Smart Backspace — remove a tab worth of spaces
        if key == Qt.Key.Key_Backspace and not cursor.hasSelection() and self._use_spaces:
            pos_in_block = cursor.positionInBlock()
            block_text = cursor.block().text()
            if pos_in_block > 0 and block_text[:pos_in_block].strip() == "":
                remove = ((pos_in_block - 1) % self._tab_size) + 1
                for _ in range(remove):
                    cursor.deletePreviousChar()
                return

        # Skip-over auto-closer if next char matches typed closer
        if text in _CLOSERS and not cursor.hasSelection():
            doc = self.document()
            if doc.characterAt(cursor.position()) == text:
                cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
                self.setTextCursor(cursor)
                return

        # Ctrl+/ toggle line comment
        if (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
            and key == Qt.Key.Key_Slash
        ):
            self._toggle_line_comment()
            return

        # Ctrl+D — duplicate line / selection
        if (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
            and key == Qt.Key.Key_D
        ):
            self._duplicate_line()
            return

        super().keyPressEvent(event)

        # After regular key processing, refresh the completion popup if
        # the user is mid-word. This is what makes it feel "live" — like
        # PyCharm's auto-popup that appears as you type.
        if (
            text and (text.isalnum() or text == "_")
            and not (mods & Qt.KeyboardModifier.ControlModifier)
        ):
            self._show_completion_popup(force=False)
        elif self._completer.popup().isVisible():
            self._completer.popup().hide()

    # ---------------- Completion ----------------

    def set_completion_keywords(self, words: list[str]) -> None:
        """Replace the language-specific keyword list used by completion."""
        self._completion_keywords = sorted(set(words) | set(_PY_KEYWORDS))
        self._rebuild_completion_model()

    def _word_under_cursor(self) -> tuple[str, int]:
        """Return (prefix, anchor_position) for the word the cursor is in."""
        cursor = self.textCursor()
        pos = cursor.positionInBlock()
        block_text = cursor.block().text()
        i = pos
        while i > 0 and (block_text[i - 1].isalnum() or block_text[i - 1] == "_"):
            i -= 1
        return block_text[i:pos], cursor.block().position() + i

    def _rebuild_completion_model(self) -> None:
        # Pull the unique identifier-like words out of the document and
        # merge with the language keyword list.
        text = self.toPlainText()
        words: set[str] = set(self._completion_keywords)
        for m in _WORD_RE.finditer(text):
            w = m.group(0)
            if len(w) >= 3:
                words.add(w)
        self._completer_model.setStringList(sorted(words))

    def _show_completion_popup(self, *, force: bool) -> None:
        prefix, _ = self._word_under_cursor()
        if not force and len(prefix) < self._completion_min_chars:
            self._completer.popup().hide()
            return
        if force and not prefix:
            # Ctrl+Space with empty prefix → show all
            prefix = ""
        self._completer.setCompletionPrefix(prefix)
        # Hide if there's nothing to suggest other than what's typed.
        if (
            self._completer.completionCount() == 0
            or (
                self._completer.completionCount() == 1
                and self._completer.currentCompletion() == prefix
            )
        ):
            self._completer.popup().hide()
            return
        rect = self.cursorRect()
        rect.setWidth(
            self._completer.popup().sizeHintForColumn(0)
            + self._completer.popup().verticalScrollBar().sizeHint().width()
            + 24
        )
        self._completer.complete(rect)

    def _insert_completion(self, completion: str) -> None:
        if self._completer.widget() is not self:
            return
        prefix, anchor = self._word_under_cursor()
        cursor = self.textCursor()
        cursor.setPosition(anchor)
        cursor.setPosition(
            anchor + len(prefix), QTextCursor.MoveMode.KeepAnchor
        )
        cursor.insertText(completion)
        self.setTextCursor(cursor)

    # ---------------- Helpers ----------------

    def _indent_selection(self, cursor: QTextCursor, *, dedent: bool) -> None:
        doc = self.document()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        start_block = doc.findBlock(start)
        end_block = doc.findBlock(end if end > start else start)
        unit = " " * self._tab_size if self._use_spaces else "\t"

        cursor.beginEditBlock()
        block = start_block
        while True:
            c = QTextCursor(block)
            if dedent:
                text = block.text()
                if self._use_spaces:
                    n = 0
                    while n < self._tab_size and n < len(text) and text[n] == " ":
                        n += 1
                    if n == 0 and text.startswith("\t"):
                        n = 1
                    for _ in range(n):
                        c.deleteChar()
                else:
                    if text.startswith("\t"):
                        c.deleteChar()
                    elif text.startswith(" " * self._tab_size):
                        for _ in range(self._tab_size):
                            c.deleteChar()
            else:
                c.insertText(unit)
            if block == end_block:
                break
            block = block.next()
            if not block.isValid():
                break
        cursor.endEditBlock()

    def _toggle_line_comment(self) -> None:
        prefix = "# "
        # Pick comment marker by simple heuristic from filename hint stored via property
        marker = self.property("comment_marker")
        if isinstance(marker, str) and marker:
            prefix = marker if marker.endswith(" ") else marker + " "

        cursor = self.textCursor()
        doc = self.document()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        if start == end:
            block = cursor.block()
            blocks = [block]
        else:
            start_block = doc.findBlock(start)
            end_block = doc.findBlock(end)
            blocks = []
            b = start_block
            while True:
                blocks.append(b)
                if b == end_block:
                    break
                b = b.next()

        all_commented = all(
            b.text().lstrip().startswith(prefix.rstrip()) or b.text().strip() == ""
            for b in blocks
        ) and any(b.text().strip() != "" for b in blocks)

        cursor.beginEditBlock()
        for b in blocks:
            text = b.text()
            c = QTextCursor(b)
            if all_commented:
                stripped = text.lstrip()
                if stripped.startswith(prefix):
                    pad = len(text) - len(stripped)
                    c.setPosition(b.position() + pad)
                    for _ in range(len(prefix)):
                        c.deleteChar()
                elif stripped.startswith(prefix.rstrip()):
                    pad = len(text) - len(stripped)
                    c.setPosition(b.position() + pad)
                    for _ in range(len(prefix.rstrip())):
                        c.deleteChar()
            else:
                if text.strip() == "":
                    continue
                indent = len(text) - len(text.lstrip())
                c.setPosition(b.position() + indent)
                c.insertText(prefix)
        cursor.endEditBlock()

    def _move_lines(self, direction: int) -> None:
        """Move the selected line(s) up (-1) or down (+1) one row.

        Implementation is a plain swap on the line array — far simpler
        than chasing QTextBlock references through edit operations.
        Selection and the cursor column are restored on the moved lines.
        """
        if direction not in (-1, 1):
            return
        cursor = self.textCursor()
        sel_start = cursor.selectionStart()
        sel_end = cursor.selectionEnd()
        had_selection = cursor.hasSelection()

        doc = self.document()
        first_block_num = doc.findBlock(sel_start).blockNumber()
        last_block_num = doc.findBlock(
            sel_end if sel_end >= sel_start else sel_start
        ).blockNumber()
        # If the selection lands at column 0 of the next block (typical
        # when shift-arrowing down), don't include that empty block.
        last_block = doc.findBlockByNumber(last_block_num)
        if had_selection and last_block.position() == sel_end and last_block_num > first_block_num:
            last_block_num -= 1

        if direction == -1 and first_block_num == 0:
            return
        if direction == +1 and last_block_num >= doc.blockCount() - 1:
            return

        col = cursor.positionInBlock()
        # Split the doc into a list of lines and swap the relevant slice
        # with the neighbour.
        lines = self.toPlainText().split("\n")
        if direction == -1:
            block = lines[first_block_num - 1]
            chunk = lines[first_block_num:last_block_num + 1]
            new_lines = (
                lines[:first_block_num - 1]
                + chunk
                + [block]
                + lines[last_block_num + 1:]
            )
        else:
            block = lines[last_block_num + 1]
            chunk = lines[first_block_num:last_block_num + 1]
            new_lines = (
                lines[:first_block_num]
                + [block]
                + chunk
                + lines[last_block_num + 2:]
            )

        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText("\n".join(new_lines))
        cursor.endEditBlock()

        new_first = first_block_num + direction
        new_last = last_block_num + direction
        new_first_block = doc.findBlockByNumber(max(0, new_first))
        new_last_block = doc.findBlockByNumber(
            min(doc.blockCount() - 1, new_last)
        )
        new_cursor = QTextCursor(doc)
        if had_selection:
            new_cursor.setPosition(new_first_block.position())
            new_cursor.setPosition(
                new_last_block.position() + len(new_last_block.text()),
                QTextCursor.MoveMode.KeepAnchor,
            )
        else:
            new_cursor.setPosition(
                new_first_block.position()
                + min(col, len(new_first_block.text()))
            )
        self.setTextCursor(new_cursor)
        self.centerCursor()

    def goto_line(self, line: int, col: int = 1) -> None:
        """Move the cursor to *line* (1-based) and *col* (1-based), centered."""
        line = max(1, line)
        col = max(1, col)
        doc = self.document()
        block = doc.findBlockByNumber(min(line - 1, doc.blockCount() - 1))
        cursor = QTextCursor(block)
        target_col = min(col - 1, len(block.text()))
        cursor.setPosition(block.position() + target_col)
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()

    def _duplicate_line(self) -> None:
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.insertText(text + text)
            return
        block = cursor.block()
        text = block.text()
        col = cursor.positionInBlock()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        cursor.insertText("\n" + text)
        cursor.endEditBlock()
        # restore column
        new_block = cursor.block()
        cursor.setPosition(new_block.position() + min(col, len(text)))
        self.setTextCursor(cursor)

    # zoom with Ctrl+Wheel
    def wheelEvent(self, event):  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            self.set_font_size(self.font_size() + (1 if delta > 0 else -1))
            event.accept()
            return
        super().wheelEvent(event)
