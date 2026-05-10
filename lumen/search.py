"""Project-wide search panel.

Walks the project root, scans text files for a query (literal or regex),
and shows results grouped by file. Clicking a result opens the file in the
editor at the matching line.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from PyQt6.QtCore import (
    QObject,
    QRunnable,
    QThreadPool,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import theme

# Skip these directories to keep searches fast
_IGNORED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".tox", ".idea", ".vscode", "dist",
    "build", "target", ".next", ".cache",
}
_BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".so", ".dll", ".dylib", ".class", ".jar", ".exe", ".bin",
    ".mp3", ".mp4", ".mov", ".avi", ".wav",
    ".pyc", ".pyo",
}
_MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
_MAX_RESULTS = 1000


@dataclass
class _Match:
    path: str
    line: int
    column: int
    text: str


class _SearchSignals(QObject):
    match = pyqtSignal(object)         # _Match
    file_done = pyqtSignal(str, int)   # path, n_matches
    finished = pyqtSignal(int, int)    # files_with_matches, total_matches
    error = pyqtSignal(str)


class _SearchTask(QRunnable):
    def __init__(self, root: str, query: str, *, regex: bool, case: bool, whole: bool) -> None:
        super().__init__()
        self.root = root
        self.query = query
        self.regex = regex
        self.case = case
        self.whole = whole
        self.signals = _SearchSignals()
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def _build_pattern(self) -> re.Pattern[str] | None:
        flags = 0 if self.case else re.IGNORECASE
        try:
            if self.regex:
                pat = self.query
            else:
                pat = re.escape(self.query)
            if self.whole:
                pat = r"\b" + pat + r"\b"
            return re.compile(pat, flags)
        except re.error as exc:
            self.signals.error.emit(f"Invalid pattern: {exc}")
            return None

    @pyqtSlot()
    def run(self) -> None:
        pattern = self._build_pattern()
        if pattern is None:
            self.signals.finished.emit(0, 0)
            return
        files_with = 0
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.root, followlinks=False):
                if self._cancelled:
                    break
                dirnames[:] = [d for d in dirnames if d not in _IGNORED_DIRS and not d.startswith(".")]
                for fn in filenames:
                    if self._cancelled:
                        break
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in _BINARY_EXTS:
                        continue
                    if fn.startswith("."):
                        continue
                    full = os.path.join(dirpath, fn)
                    try:
                        if os.path.getsize(full) > _MAX_FILE_SIZE:
                            continue
                    except OSError:
                        continue
                    file_matches = 0
                    try:
                        with open(full, "r", encoding="utf-8", errors="replace") as f:
                            for i, line in enumerate(f, start=1):
                                if self._cancelled:
                                    break
                                if "\x00" in line:
                                    file_matches = 0
                                    break
                                m = pattern.search(line)
                                if m:
                                    self.signals.match.emit(_Match(
                                        path=full,
                                        line=i,
                                        column=m.start() + 1,
                                        text=line.rstrip("\n")[:400],
                                    ))
                                    file_matches += 1
                                    total += 1
                                    if total >= _MAX_RESULTS:
                                        break
                    except OSError:
                        continue
                    if file_matches:
                        files_with += 1
                        self.signals.file_done.emit(full, file_matches)
                    if total >= _MAX_RESULTS:
                        break
                if total >= _MAX_RESULTS:
                    break
        finally:
            self.signals.finished.emit(files_with, total)


class SearchPanel(QFrame):
    """A panel that runs ripgrep-style searches across the active folder."""

    file_open_requested = pyqtSignal(str, int)  # path, line

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SearchPanel")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._root: str | None = None
        self._task: _SearchTask | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        title = QLabel("SEARCH")
        title.setProperty("role", "sidebar-title")
        outer.addWidget(title)

        controls = QVBoxLayout()
        controls.setContentsMargins(12, 0, 12, 8)
        controls.setSpacing(6)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Search in folder…")
        self.input.returnPressed.connect(self.start_search)
        self.input.textChanged.connect(self._on_text_changed)
        controls.addWidget(self.input)

        flags_row = QHBoxLayout()
        flags_row.setSpacing(8)
        self.case_cb = QCheckBox("Aa")
        self.case_cb.setToolTip("Match case")
        self.word_cb = QCheckBox("W")
        self.word_cb.setToolTip("Whole word")
        self.regex_cb = QCheckBox(".*")
        self.regex_cb.setToolTip("Regular expression")
        for cb in (self.case_cb, self.word_cb, self.regex_cb):
            cb.toggled.connect(self._defer_search)
            flags_row.addWidget(cb)
        flags_row.addStretch(1)
        controls.addLayout(flags_row)
        outer.addLayout(controls)

        self.summary = QLabel("Type to search the project")
        self.summary.setStyleSheet(f"color:{theme.PALETTE.text_dim}; padding: 4px 14px;")
        outer.addWidget(self.summary)

        self.results = QTreeWidget()
        self.results.setHeaderHidden(True)
        self.results.setUniformRowHeights(True)
        self.results.setIndentation(14)
        self.results.itemActivated.connect(self._on_activate)
        self.results.itemDoubleClicked.connect(self._on_activate)
        # Slightly smaller monospace for matches
        f = QFont("JetBrains Mono")
        f.setStyleHint(QFont.StyleHint.Monospace)
        f.setPointSize(11)
        self.results.setFont(f)
        outer.addWidget(self.results, 1)

        self._timer = None
        from PyQt6.QtCore import QTimer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(280)
        self._timer.timeout.connect(self.start_search)

    # ---------------- API ----------------

    def set_root(self, path: str | None) -> None:
        self._root = path
        if path:
            self.summary.setText(f"Searching in {os.path.basename(path)}")
        else:
            self.summary.setText("Open a folder to enable project search")

    def focus_input(self) -> None:
        self.input.setFocus()
        self.input.selectAll()

    def set_query(self, query: str) -> None:
        self.input.setText(query)

    # ---------------- internals ----------------

    def _on_text_changed(self, _t: str) -> None:
        self._defer_search()

    def _defer_search(self) -> None:
        self._timer.start()

    def _cancel_running(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    def start_search(self) -> None:
        self._cancel_running()
        self.results.clear()
        query = self.input.text().strip()
        if not self._root or not query:
            self.summary.setText(
                "Open a folder to enable project search"
                if not self._root else
                f"Searching in {os.path.basename(self._root)}"
            )
            return

        task = _SearchTask(
            self._root, query,
            regex=self.regex_cb.isChecked(),
            case=self.case_cb.isChecked(),
            whole=self.word_cb.isChecked(),
        )
        task.signals.match.connect(self._on_match)
        task.signals.finished.connect(self._on_finished)
        task.signals.error.connect(lambda msg: self.summary.setText(msg))
        self._task = task
        self.summary.setText("Searching…")
        QThreadPool.globalInstance().start(task)

    def _file_item(self, path: str) -> QTreeWidgetItem:
        # Top-level item per file
        rel = os.path.relpath(path, self._root) if self._root else path
        # Find existing
        for i in range(self.results.topLevelItemCount()):
            it = self.results.topLevelItem(i)
            if it.data(0, Qt.ItemDataRole.UserRole) == path:
                return it
        from PyQt6.QtGui import QBrush, QColor
        item = QTreeWidgetItem([rel])
        item.setData(0, Qt.ItemDataRole.UserRole, path)
        f = item.font(0)
        f.setBold(True)
        item.setFont(0, f)
        item.setForeground(0, QBrush(QColor(theme.PALETTE.accent)))
        self.results.addTopLevelItem(item)
        item.setExpanded(True)
        return item

    def _on_match(self, m: _Match) -> None:
        parent = self._file_item(m.path)
        text = m.text.lstrip()
        # Trim middle if very long
        max_len = 180
        if len(text) > max_len:
            text = text[:max_len - 1] + "…"
        label = f"  {m.line:>4}:  {text}"
        child = QTreeWidgetItem([label])
        child.setData(0, Qt.ItemDataRole.UserRole, (m.path, m.line))
        parent.addChild(child)

    def _on_finished(self, files: int, total: int) -> None:
        if total == 0:
            self.summary.setText("No matches")
        else:
            limit = " (truncated)" if total >= _MAX_RESULTS else ""
            self.summary.setText(f"{total} match" + ("es" if total != 1 else "")
                                 + f" in {files} file" + ("s" if files != 1 else "") + limit)
            # Update each top-level header to include count
            for i in range(self.results.topLevelItemCount()):
                it = self.results.topLevelItem(i)
                count = it.childCount()
                base = it.text(0).rsplit("  ·  ", 1)[0]
                it.setText(0, f"{base}  ·  {count}")
        self._task = None

    def _on_activate(self, item: QTreeWidgetItem, _col: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, tuple):
            path, line = data
            self.file_open_requested.emit(path, int(line))
        elif isinstance(data, str):
            self.file_open_requested.emit(data, 1)
