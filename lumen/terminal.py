"""Integrated terminal panel.

Runs commands in the active project's working directory. Keeps a per-session
history (Up/Down to navigate). Output is appended to a read-only view above
the input. Supports `cd` natively to keep the working directory in sync.

This is a pragmatic, non-PTY console — most build / test / git workflows
work great. For full TTY apps (vim, top), launch your system terminal.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess

from PyQt6.QtCore import (
    QObject,
    QProcess,
    Qt,
    pyqtSignal,
    QEvent,
)
from PyQt6.QtGui import QKeyEvent, QTextCharFormat, QTextCursor, QColor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .icons import icon

# Strip ANSI escape sequences before display
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


class TerminalPanel(QFrame):
    visibility_changed = pyqtSignal(bool)
    # Fires whenever a backgrounded shell process ends (normally or
    # killed). Carries the exit code (-1 for kill / error).
    process_finished = pyqtSignal(int)
    # Fires whenever a process is freshly started in the terminal.
    process_started = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Terminal")
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._cwd = os.path.expanduser("~")
        self._history: list[str] = []
        self._history_idx: int = 0
        self._proc: QProcess | None = None
        self._closed_recent_output = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- header ----
        header = QHBoxLayout()
        header.setContentsMargins(12, 6, 6, 6)
        header.setSpacing(8)
        title = QLabel("TERMINAL")
        title.setProperty("role", "sidebar-title")
        title.setStyleSheet(
            f"color:{theme.PALETTE.text_dim}; font-weight:700; "
            f"letter-spacing:1.5px; padding:0;"
        )
        self._cwd_label = QLabel(self._cwd)
        self._cwd_label.setObjectName("TerminalCwd")
        header.addWidget(title)
        header.addSpacing(8)
        header.addWidget(self._cwd_label, 1)

        clear_btn = QToolButton()
        clear_btn.setIcon(icon("trash"))
        clear_btn.setToolTip("Clear")
        clear_btn.clicked.connect(self.clear)
        header.addWidget(clear_btn)

        kill_btn = QToolButton()
        kill_btn.setIcon(icon("close"))
        kill_btn.setToolTip("Kill running command")
        kill_btn.clicked.connect(self.kill_process)
        header.addWidget(kill_btn)

        header_widget = QWidget()
        header_widget.setLayout(header)
        outer.addWidget(header_widget)

        # ---- output ----
        self._view = QPlainTextEdit()
        self._view.setObjectName("TerminalView")
        self._view.setReadOnly(True)
        self._view.setUndoRedoEnabled(False)
        self._view.setMaximumBlockCount(5000)
        outer.addWidget(self._view, 1)

        # ---- input row ----
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self._prompt = QLabel("›")
        self._prompt.setObjectName("TerminalPrompt")
        row.addWidget(self._prompt)
        self._input = QLineEdit()
        self._input.setObjectName("TerminalInput")
        self._input.setPlaceholderText("Run a command…   (Ctrl+C to interrupt, ↑/↓ for history)")
        self._input.installEventFilter(self)
        self._input.returnPressed.connect(self._on_enter)
        row.addWidget(self._input, 1)
        row_widget = QWidget()
        row_widget.setLayout(row)
        outer.addWidget(row_widget)

        self._intro()

    # ---------------- API ----------------

    def set_cwd(self, path: str | None) -> None:
        if path and os.path.isdir(path):
            self._cwd = os.path.abspath(path)
            self._cwd_label.setText(self._compact_cwd(self._cwd))

    def cwd(self) -> str:
        return self._cwd

    def focus_input(self) -> None:
        self._input.setFocus()

    def clear(self) -> None:
        self._view.clear()
        self._intro()

    def kill_process(self) -> None:
        if self._proc and self._proc.state() != QProcess.ProcessState.NotRunning:
            self._proc.kill()
            self._append("\n^C process killed\n", color=theme.PALETTE.warning)

    def run_command(self, cmd: str) -> bool:
        """Inject *cmd* into the terminal as if the user had typed it.

        Echoes the prompt + command into the view, adds it to history so
        Up-arrow recalls it, then dispatches through the same path as a
        manual Enter (so built-ins like ``cd`` still work).

        Returns ``False`` if another command is already running, in which
        case nothing happens. The caller can decide whether to surface a
        message to the user.
        """
        if not cmd or not cmd.strip():
            return False
        if self._proc and self._proc.state() != QProcess.ProcessState.NotRunning:
            self._append(
                "A command is already running in the terminal — "
                "press the close (✕) button or Ctrl+C to kill it first.\n",
                color=theme.PALETTE.warning,
            )
            return False
        self._history.append(cmd)
        del self._history[-200:-100]
        self._history_idx = len(self._history)
        self._print_command(cmd)
        stripped = cmd.strip()
        if stripped == "clear":
            self.clear()
        elif stripped in ("exit", "quit"):
            self._append("(close the terminal panel with Ctrl+`)\n",
                         color=theme.PALETTE.text_dim)
        elif stripped.startswith("cd"):
            self._builtin_cd(stripped)
        else:
            self._run(cmd)
        return True

    def setVisible(self, visible: bool) -> None:  # noqa: N802
        super().setVisible(visible)
        self.visibility_changed.emit(visible)

    # ---------------- internals ----------------

    @staticmethod
    def _compact_cwd(path: str) -> str:
        home = os.path.expanduser("~")
        if path == home:
            return "~"
        if path.startswith(home + os.sep):
            return "~" + path[len(home):]
        return path

    def _intro(self) -> None:
        self._append(
            "Lumen Terminal — runs commands one at a time in the project folder.\n"
            "Built-in: cd, clear, exit. ↑/↓ navigates history, Ctrl+L clears.\n",
            color=theme.PALETTE.text_dim,
        )

    def _append(self, text: str, *, color: str | None = None) -> None:
        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if color:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            cursor.insertText(text, fmt)
        else:
            cursor.insertText(text)
        self._view.setTextCursor(cursor)
        self._view.ensureCursorVisible()

    def _print_command(self, cmd: str) -> None:
        prompt_color = theme.PALETTE.cta
        self._append("\n", color=None)
        self._append("›", color=prompt_color)
        self._append(f" {self._compact_cwd(self._cwd)}", color=theme.PALETTE.text_muted)
        self._append(f"  {cmd}\n", color=theme.PALETTE.text)

    # ---------------- history ----------------

    def eventFilter(self, obj, event: QEvent) -> bool:  # noqa: N802
        if obj is self._input and event.type() == QEvent.Type.KeyPress:
            assert isinstance(event, QKeyEvent)
            key = event.key()
            mods = event.modifiers()
            if key == Qt.Key.Key_Up:
                self._history_back()
                return True
            if key == Qt.Key.Key_Down:
                self._history_forward()
                return True
            if key == Qt.Key.Key_L and mods & Qt.KeyboardModifier.ControlModifier:
                self.clear()
                return True
            if key == Qt.Key.Key_C and mods & Qt.KeyboardModifier.ControlModifier:
                if self._proc and self._proc.state() != QProcess.ProcessState.NotRunning:
                    self.kill_process()
                    return True
        return super().eventFilter(obj, event)

    def _history_back(self) -> None:
        if not self._history:
            return
        self._history_idx = max(0, self._history_idx - 1)
        self._input.setText(self._history[self._history_idx])

    def _history_forward(self) -> None:
        if not self._history:
            return
        self._history_idx += 1
        if self._history_idx >= len(self._history):
            self._history_idx = len(self._history)
            self._input.clear()
        else:
            self._input.setText(self._history[self._history_idx])

    # ---------------- run ----------------

    def _on_enter(self) -> None:
        cmd = self._input.text()
        self._input.clear()
        if not cmd.strip():
            return
        self._history.append(cmd)
        del self._history[-200:-100]  # cap history at ~100
        self._history_idx = len(self._history)

        self._print_command(cmd)

        # Built-ins
        stripped = cmd.strip()
        if stripped == "clear":
            self.clear()
            return
        if stripped in ("exit", "quit"):
            self._append("(close the terminal panel with Ctrl+`)\n", color=theme.PALETTE.text_dim)
            return
        if stripped.startswith("cd"):
            self._builtin_cd(stripped)
            return

        # Anything else — run via /bin/sh -c so pipes/quotes work
        self._run(cmd)

    def _builtin_cd(self, cmd: str) -> None:
        try:
            parts = shlex.split(cmd)
        except ValueError as exc:
            self._append(f"cd: {exc}\n", color=theme.PALETTE.error)
            return
        target = os.path.expanduser(parts[1]) if len(parts) > 1 else os.path.expanduser("~")
        if not os.path.isabs(target):
            target = os.path.join(self._cwd, target)
        target = os.path.normpath(target)
        if os.path.isdir(target):
            self._cwd = target
            self._cwd_label.setText(self._compact_cwd(target))
        else:
            self._append(f"cd: no such directory: {target}\n", color=theme.PALETTE.error)

    def _run(self, cmd: str) -> None:
        if self._proc and self._proc.state() != QProcess.ProcessState.NotRunning:
            self._append("A command is already running. Press the close button to kill it.\n",
                         color=theme.PALETTE.warning)
            return
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.setWorkingDirectory(self._cwd)
        proc.readyReadStandardOutput.connect(self._on_stdout)
        proc.finished.connect(self._on_finished)
        proc.errorOccurred.connect(self._on_error)
        # Disable colors / paginators where we can
        env = proc.processEnvironment()
        if env.isEmpty():
            from PyQt6.QtCore import QProcessEnvironment
            env = QProcessEnvironment.systemEnvironment()
        env.insert("PAGER", "cat")
        env.insert("CLICOLOR", "0")
        env.insert("TERM", "dumb")
        proc.setProcessEnvironment(env)
        self._proc = proc
        proc.start("/bin/sh", ["-c", cmd])
        self.process_started.emit()

    def _on_stdout(self) -> None:
        if not self._proc:
            return
        data = bytes(self._proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._append(_strip_ansi(data))

    def _on_finished(self, exit_code: int, _status) -> None:
        if exit_code == 0:
            self._append(f"\n[exit 0]\n", color=theme.PALETTE.success)
        else:
            self._append(f"\n[exit {exit_code}]\n", color=theme.PALETTE.error)
        self._proc = None
        self.process_finished.emit(exit_code)

    def _on_error(self, _err) -> None:
        # Both errorOccurred and finished can fire for a single command
        # (e.g. Crashed). Make sure process_finished is only emitted
        # once — first signal in wins.
        if self._proc is None:
            return
        self._append(f"\n[error: {self._proc.errorString()}]\n", color=theme.PALETTE.error)
        self._proc = None
        self.process_finished.emit(-1)
