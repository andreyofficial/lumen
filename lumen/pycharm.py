"""Small PyCharm-style productivity widgets: Go to Line dialog,
Recent Files switcher, file structure outline, run console.

Kept together here because each of them is small (one widget /
dialog) and they all share the same style language.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable

from PyQt6.QtCore import (
    QFileSystemWatcher,
    QProcess,
    QProcessEnvironment,
    QSize,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QFont, QFontMetrics, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


# --------------------------------------------------------------------------
#  Go to Line
# --------------------------------------------------------------------------

class GotoLineDialog(QDialog):
    """PyCharm-style "Go to Line:Column" dialog.

    Accepts ``42``  →  line 42, col 1
    Or      ``42:8`` → line 42, col 8
    Emits ``accepted`` with the parsed (line, col).
    """

    requested = pyqtSignal(int, int)

    def __init__(self, max_line: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Go to Line")
        self.setObjectName("GotoLineDialog")
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 14)
        lay.setSpacing(10)

        title = QLabel("Go to line:column")
        title.setObjectName("DialogTitle")
        lay.addWidget(title)

        self.input = QLineEdit()
        self.input.setPlaceholderText(f"Line:Column (1–{max_line})")
        self.input.setClearButtonEnabled(True)
        self.input.returnPressed.connect(self.accept)
        lay.addWidget(self.input)

        self._max_line = max_line
        self._hint = QLabel(" ")
        self._hint.setProperty("role", "muted")
        lay.addWidget(self._hint)

        self.input.textChanged.connect(self._validate)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.input.setFocus()

    def _validate(self, text: str) -> None:
        try:
            line, col = self._parse(text)
            self._hint.setText(f"→ line {line}, column {col}")
        except ValueError as e:
            self._hint.setText(str(e))

    def _parse(self, text: str) -> tuple[int, int]:
        s = text.strip()
        if not s:
            raise ValueError("Enter a line number")
        if ":" in s:
            line_s, col_s = s.split(":", 1)
        else:
            line_s, col_s = s, "1"
        try:
            line = int(line_s.strip())
            col = int(col_s.strip()) if col_s.strip() else 1
        except ValueError:
            raise ValueError("Use the format LINE or LINE:COLUMN") from None
        if line < 1:
            raise ValueError("Line must be ≥ 1")
        if line > self._max_line:
            raise ValueError(f"File only has {self._max_line} lines")
        return line, max(1, col)

    def accept(self) -> None:  # noqa: D401
        try:
            line, col = self._parse(self.input.text())
        except ValueError:
            return
        self.requested.emit(line, col)
        super().accept()


# --------------------------------------------------------------------------
#  Recent Files / Locations switcher
# --------------------------------------------------------------------------

@dataclass
class RecentEntry:
    path: str
    line: int = 1
    label: str | None = None  # e.g. "edited 2 minutes ago"


class RecentFilesPopup(QDialog):
    """A floating switcher listing recently visited files (Ctrl+E)."""

    activated = pyqtSignal(str, int)  # path, line

    def __init__(
        self,
        entries: Iterable[RecentEntry],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("RecentFilesPopup")
        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setModal(True)
        self.resize(560, 380)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        title = QLabel("Recent files")
        title.setObjectName("DialogTitle")
        lay.addWidget(title)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Type to filter…")
        self.search.setClearButtonEnabled(True)
        lay.addWidget(self.search)

        self.list = QListWidget()
        self.list.setObjectName("RecentList")
        self.list.setUniformItemSizes(True)
        lay.addWidget(self.list, 1)

        self._all = list(entries)
        self._populate(self._all)

        self.search.textChanged.connect(self._filter)
        self.list.itemActivated.connect(self._on_activate)

        QShortcut(QKeySequence("Escape"), self, self.reject)
        QShortcut(QKeySequence("Return"), self, self._activate_current)
        QShortcut(QKeySequence("Enter"), self, self._activate_current)

    def _populate(self, entries: Iterable[RecentEntry]) -> None:
        self.list.clear()
        for e in entries:
            base = os.path.basename(e.path) or e.path
            folder = os.path.dirname(e.path)
            it = QListWidgetItem(f"{base}    {folder}")
            it.setData(Qt.ItemDataRole.UserRole, e)
            self.list.addItem(it)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _filter(self, text: str) -> None:
        text = text.strip().lower()
        if not text:
            self._populate(self._all)
            return
        filtered = [
            e for e in self._all
            if text in os.path.basename(e.path).lower()
            or text in e.path.lower()
        ]
        self._populate(filtered)

    def _activate_current(self) -> None:
        it = self.list.currentItem()
        if it:
            self._on_activate(it)

    def _on_activate(self, item: QListWidgetItem) -> None:
        e: RecentEntry = item.data(Qt.ItemDataRole.UserRole)
        self.activated.emit(e.path, e.line)
        self.accept()


# --------------------------------------------------------------------------
#  File Structure outline panel
# --------------------------------------------------------------------------

# Patterns matched against each line. We deliberately keep this dumb and
# regex-based: a real AST per language would be massive and brittle. Most
# of the value comes from showing classes / functions / methods at a
# glance, and that survives partial / broken syntax.
_OUTLINE_PATTERNS = {
    "python": [
        (re.compile(r"^(\s*)class\s+([A-Za-z_]\w*)"), "class"),
        (re.compile(r"^(\s*)(?:async\s+)?def\s+([A-Za-z_]\w*)"), "def"),
    ],
    "javascript": [
        (re.compile(r"^(\s*)class\s+([A-Za-z_$][\w$]*)"), "class"),
        (re.compile(r"^(\s*)function\s+([A-Za-z_$][\w$]*)"), "function"),
        (re.compile(r"^(\s*)(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)\s*=>|function)"), "function"),
        (re.compile(r"^(\s*)([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{"), "method"),
    ],
    "typescript": None,  # filled below
    "rust": [
        (re.compile(r"^(\s*)(?:pub\s+)?fn\s+([A-Za-z_]\w*)"), "fn"),
        (re.compile(r"^(\s*)(?:pub\s+)?struct\s+([A-Za-z_]\w*)"), "struct"),
        (re.compile(r"^(\s*)(?:pub\s+)?enum\s+([A-Za-z_]\w*)"), "enum"),
        (re.compile(r"^(\s*)impl(?:\s*<[^>]*>)?\s+([A-Za-z_][\w:<>, ]*)"), "impl"),
    ],
    "go": [
        (re.compile(r"^(\s*)func\s+(?:\([^)]+\)\s+)?([A-Za-z_]\w*)"), "func"),
        (re.compile(r"^(\s*)type\s+([A-Za-z_]\w*)\s+(?:struct|interface)"), "type"),
    ],
    "java": [
        (re.compile(r"^(\s*)(?:public|private|protected)?\s*class\s+([A-Za-z_]\w*)"), "class"),
        (re.compile(r"^(\s*)(?:public|private|protected)?\s*[\w<>\[\]]+\s+([A-Za-z_]\w*)\s*\("), "method"),
    ],
    "cpp": [
        (re.compile(r"^(\s*)class\s+([A-Za-z_]\w*)"), "class"),
        (re.compile(r"^(\s*)struct\s+([A-Za-z_]\w*)"), "struct"),
        (re.compile(r"^(\s*)[\w:<>\*&\s]+\s+([A-Za-z_]\w*)\s*\([^)]*\)\s*\{?"), "fn"),
    ],
}
_OUTLINE_PATTERNS["typescript"] = _OUTLINE_PATTERNS["javascript"]
_OUTLINE_PATTERNS["c"] = _OUTLINE_PATTERNS["cpp"]


@dataclass
class OutlineNode:
    label: str
    kind: str
    line: int
    indent: int


def parse_outline(language: str, source: str) -> list[OutlineNode]:
    pats = _OUTLINE_PATTERNS.get(language)
    if not pats:
        return []
    nodes: list[OutlineNode] = []
    for n, raw in enumerate(source.splitlines(), 1):
        # skip lines that look like comments
        s = raw.lstrip()
        if not s or s.startswith(("#", "//")):
            continue
        for pat, kind in pats:
            m = pat.match(raw)
            if m:
                indent = len(m.group(1))
                name = m.group(2)
                nodes.append(OutlineNode(label=f"{kind} {name}", kind=kind,
                                         line=n, indent=indent))
                break
    return nodes


class OutlinePanel(QFrame):
    """Sidebar panel showing the symbol outline of the active editor."""

    goto_requested = pyqtSignal(int)  # line number

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("OutlinePanel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        header = QLabel("STRUCTURE")
        header.setObjectName("SidebarHeader")
        lay.addWidget(header)

        self._info = QLabel("No file open.")
        self._info.setProperty("role", "muted")
        self._info.setWordWrap(True)
        lay.addWidget(self._info)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setObjectName("OutlineTree")
        self.tree.itemActivated.connect(self._on_activated)
        self.tree.itemClicked.connect(self._on_activated)
        lay.addWidget(self.tree, 1)
        self.tree.hide()

        self._language = ""

    def update_outline(self, language: str, source: str) -> None:
        self._language = language
        self.tree.clear()
        if not language:
            self._info.setText("No file open.")
            self._info.show()
            self.tree.hide()
            return
        nodes = parse_outline(language, source)
        if not nodes:
            self._info.setText(
                f"No symbols extracted from this {language} file."
            )
            self._info.show()
            self.tree.hide()
            return
        self._info.hide()
        self.tree.show()
        # Build a simple two-level tree: classes get nested children
        # (methods). Anything else stays at the root.
        stack: list[tuple[OutlineNode, QTreeWidgetItem]] = []
        for node in nodes:
            item = QTreeWidgetItem([node.label])
            item.setData(0, Qt.ItemDataRole.UserRole, node.line)
            tip = f"line {node.line}"
            item.setToolTip(0, tip)
            # Pop the stack while indent decreases or stays equal at root.
            while stack and stack[-1][0].indent >= node.indent:
                stack.pop()
            if stack:
                stack[-1][1].addChild(item)
            else:
                self.tree.addTopLevelItem(item)
            stack.append((node, item))
        self.tree.expandAll()

    def _on_activated(self, item: QTreeWidgetItem, _col: int = 0) -> None:
        line = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(line, int):
            self.goto_requested.emit(line)


# --------------------------------------------------------------------------
#  Run console panel
# --------------------------------------------------------------------------

# Filenames → run command. The first match wins; ``None`` means "no
# automatic runner; ask the user".
_RUNNERS = [
    (re.compile(r"\.py$"),     [sys.executable, "-u"]),
    (re.compile(r"\.js$"),     ["node"]),
    (re.compile(r"\.ts$"),     ["node", "--loader", "ts-node/esm"]),
    (re.compile(r"\.sh$"),     ["bash"]),
    (re.compile(r"\.rb$"),     ["ruby"]),
    (re.compile(r"\.pl$"),     ["perl"]),
    (re.compile(r"\.go$"),     ["go", "run"]),
    (re.compile(r"\.rs$"),     None),  # cargo only — no single-file runner
]


def runner_for(path: str) -> list[str] | None:
    base = os.path.basename(path)
    for pat, cmd in _RUNNERS:
        if pat.search(base):
            return list(cmd) if cmd else None
    return None


class RunPanel(QFrame):
    """Bottom-dock console showing stdout/stderr of the running file.

    PyCharm-style layout: header showing the command, scrollable output,
    and a Stop button that terminates the running process.
    """

    finished = pyqtSignal(int)  # exit code

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RunPanel")
        self._proc: QProcess | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)

        header = QHBoxLayout()
        self.title = QLabel("Run")
        self.title.setObjectName("RunTitle")
        header.addWidget(self.title)
        header.addStretch(1)
        self.btn_stop = QToolButton()
        self.btn_stop.setText("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop)
        header.addWidget(self.btn_stop)
        self.btn_clear = QToolButton()
        self.btn_clear.setText("Clear")
        self.btn_clear.clicked.connect(self._clear)
        header.addWidget(self.btn_clear)
        lay.addLayout(header)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setObjectName("RunOutput")
        self.output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("JetBrains Mono", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.output.setFont(font)
        lay.addWidget(self.output, 1)

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.state() != QProcess.ProcessState.NotRunning

    def run_file(self, path: str, *, cwd: str | None = None) -> str | None:
        """Start running *path*. Returns ``None`` on success, otherwise an
        error message describing why the file can't be run."""
        cmd = runner_for(path)
        if cmd is None:
            return f"No automatic runner is configured for {os.path.basename(path)}."
        if self.is_running():
            self.stop()
        full = cmd + [path]
        self._clear()
        self.output.appendPlainText(f"$ {' '.join(full)}\n")
        self.title.setText(f"Run · {os.path.basename(path)}")
        self.btn_stop.setEnabled(True)

        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        self._proc.setProcessEnvironment(env)
        if cwd is None:
            cwd = os.path.dirname(path) or os.getcwd()
        self._proc.setWorkingDirectory(cwd)
        self._proc.readyReadStandardOutput.connect(self._read_output)
        self._proc.finished.connect(self._on_finished)
        self._proc.errorOccurred.connect(self._on_error)
        self._proc.start(full[0], full[1:])
        return None

    def stop(self) -> None:
        if self._proc and self._proc.state() != QProcess.ProcessState.NotRunning:
            self._proc.terminate()
            if not self._proc.waitForFinished(800):
                self._proc.kill()

    def _clear(self) -> None:
        self.output.clear()

    def _read_output(self) -> None:
        if self._proc is None:
            return
        data = bytes(self._proc.readAllStandardOutput()).decode(errors="replace")
        if data:
            self.output.moveCursor(self.output.textCursor().MoveOperation.End)
            self.output.insertPlainText(data)
            self.output.moveCursor(self.output.textCursor().MoveOperation.End)

    def _on_finished(self, exit_code: int, _status) -> None:
        self.output.appendPlainText(f"\n[ exited with code {exit_code} ]")
        self.btn_stop.setEnabled(False)
        self.finished.emit(exit_code)

    def _on_error(self, err) -> None:
        self.output.appendPlainText(f"\n[ process error: {err} ]")
        self.btn_stop.setEnabled(False)


__all__ = [
    "GotoLineDialog",
    "RecentEntry",
    "RecentFilesPopup",
    "OutlineNode",
    "OutlinePanel",
    "RunPanel",
    "parse_outline",
    "runner_for",
]
