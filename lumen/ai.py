"""Built-in AI assistant panel.

Lumen ships with a chat panel that talks to any OpenAI-compatible
``/v1/chat/completions`` endpoint. Out of the box it points at a local
Ollama instance (``http://localhost:11434/v1``) so no signup or paid API
key is required — install Ollama, ``ollama pull llama3.2`` and you can
chat with the model from inside the editor.

The same panel works with OpenAI, OpenRouter, Groq, LocalAI, vLLM, and
anything else that speaks the OpenAI chat-completions protocol.

Implementation notes
--------------------
* Streaming uses ``QNetworkAccessManager`` so we don't add any extra
  Python dependencies (no ``requests``, no ``httpx``) — the PyQt6
  bundle already ships ``QtNetwork``.
* Server-Sent Events are parsed line-by-line on each ``readyRead``
  signal: each ``data: {...}`` line is decoded as JSON and the delta
  ``choices[0].delta.content`` is appended to the current bubble.
* Persistence: backend URL, model, API key, system prompt, temperature
  and "include current file" toggle are all saved to ``QSettings`` so
  they survive restarts.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from PyQt6.QtCore import (
    QByteArray,
    QSettings,
    QSize,
    Qt,
    QUrl,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QKeyEvent, QPalette, QTextCursor
from PyQt6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
)
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .chats import ChatStore, StoredChat
from .icons import icon
from .shine import ShineButton
from .theme import PALETTE


# --------------------------- Data classes ---------------------------

@dataclass
class AIConfig:
    """User-tunable settings for the AI client."""

    enabled: bool = True
    base_url: str = "http://localhost:11434/v1"
    api_key: str = ""
    model: str = "llama3.2"
    system_prompt: str = (
        "You are Lumen, a helpful AI coding assistant embedded in a code "
        "editor. Be concise, prefer short focused answers, and always "
        "format code with markdown fenced blocks. When the user shares "
        "a file, refer to it by its filename."
    )
    temperature: float = 0.4
    include_current_file: bool = False
    max_history: int = 16  # how many past messages to send to the API
    debug_mode: bool = False  # extra "code-review / find bugs / optimise" pass

    @classmethod
    def load(cls, settings: QSettings) -> "AIConfig":
        cfg = cls()
        cfg.enabled = bool(settings.value("ai/enabled", cfg.enabled, type=bool))
        cfg.base_url = str(settings.value("ai/base_url", cfg.base_url))
        cfg.api_key = str(settings.value("ai/api_key", cfg.api_key))
        cfg.model = str(settings.value("ai/model", cfg.model))
        cfg.system_prompt = str(settings.value("ai/system_prompt", cfg.system_prompt))
        try:
            cfg.temperature = float(settings.value("ai/temperature", cfg.temperature))
        except (TypeError, ValueError):
            pass
        cfg.include_current_file = bool(
            settings.value("ai/include_current_file", cfg.include_current_file, type=bool)
        )
        try:
            cfg.max_history = int(settings.value("ai/max_history", cfg.max_history))
        except (TypeError, ValueError):
            pass
        cfg.debug_mode = bool(
            settings.value("ai/debug_mode", cfg.debug_mode, type=bool)
        )
        return cfg

    def save(self, settings: QSettings) -> None:
        settings.setValue("ai/enabled", bool(self.enabled))
        settings.setValue("ai/base_url", self.base_url)
        settings.setValue("ai/api_key", self.api_key)
        settings.setValue("ai/model", self.model)
        settings.setValue("ai/system_prompt", self.system_prompt)
        settings.setValue("ai/temperature", float(self.temperature))
        settings.setValue("ai/include_current_file", bool(self.include_current_file))
        settings.setValue("ai/max_history", int(self.max_history))
        settings.setValue("ai/debug_mode", bool(self.debug_mode))


# The system prompt that turns the AI into a debug + optimisation engineer.
# We append this *in addition to* the user's normal system prompt so the
# Lumen persona stays intact.
DEBUG_SYSTEM_PROMPT = (
    "You are now operating in DEBUG MODE. The user's current file is "
    "attached above. Mentally simulate every reachable code path of "
    "that file — branches, edge cases, exception paths, empty inputs, "
    "boundary values, concurrency, IO failures, type confusions, and "
    "off-by-one errors. Then produce a single response with these "
    "sections, in this order, using markdown headings:\n"
    "  ## Crashes & bugs\n"
    "    - For each, state: where (line / function), what triggers it, "
    "and a one-line root cause.\n"
    "  ## Edge cases\n"
    "    - Inputs / states the code does not handle gracefully.\n"
    "  ## Performance / optimisations\n"
    "    - Hot paths, redundant work, complexity wins, and cleaner "
    "idioms — only suggest changes that are clearly worth the churn.\n"
    "  ## Patched version\n"
    "    - A single fenced code block of the **whole file** with all "
    "fixes and optimisations applied. Preserve the original public API "
    "and behaviour. Add brief inline `# ...` comments only where the "
    "change is non-obvious.\n"
    "If the file looks correct, say so explicitly under each heading "
    "and emit an unchanged 'Patched version' so the user can still "
    "diff it against their copy. Never invent code outside the file."
)


@dataclass
class _Message:
    role: str       # "user" | "assistant"
    content: str = ""
    bubble: "_Bubble | None" = field(default=None, repr=False)


# --------------------------- Bubbles ---------------------------

class _Bubble(QFrame):
    """One chat message bubble. Streaming-friendly via ``append_text``."""

    def __init__(self, role: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.role = role
        self.setObjectName("BubbleUser" if role == "user" else "BubbleAssistant")
        self._buffer = ""
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(4)

        if role == "assistant":
            header = QHBoxLayout()
            header.setSpacing(6)
            label = QLabel("LUMEN AI")
            label.setObjectName("BubbleRole")
            header.addWidget(label)
            header.addStretch(1)
            self.copy_btn = QPushButton("Copy")
            self.copy_btn.setObjectName("BubbleAction")
            self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.copy_btn.clicked.connect(self._copy_to_clipboard)
            header.addWidget(self.copy_btn)
            outer.addLayout(header)

        self.body = QTextBrowser(self)
        self.body.setOpenExternalLinks(True)
        self.body.setFrameShape(QFrame.Shape.NoFrame)
        self.body.setStyleSheet("background: transparent;")
        self.body.setReadOnly(True)
        self.body.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body.document().setDocumentMargin(0)
        outer.addWidget(self.body)

    # -- streaming helpers --
    def set_text(self, text: str) -> None:
        self._buffer = text
        self._render()

    def append_text(self, chunk: str) -> None:
        self._buffer += chunk
        self._render()

    def text(self) -> str:
        return self._buffer

    def _render(self) -> None:
        self.body.setMarkdown(self._buffer or " ")
        self._adjust_height()

    def _adjust_height(self) -> None:
        doc = self.body.document()
        doc.setTextWidth(max(120, self.width() - 28))
        h = int(doc.size().height()) + 6
        self.body.setFixedHeight(max(20, h))

    def resizeEvent(self, ev) -> None:  # noqa: N802
        super().resizeEvent(ev)
        self._adjust_height()

    def _copy_to_clipboard(self) -> None:
        from PyQt6.QtWidgets import QApplication
        cb = QApplication.clipboard()
        if cb is not None:
            cb.setText(self._buffer)
            self.copy_btn.setText("Copied")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1200, lambda: self.copy_btn.setText("Copy"))


class _BubbleRow(QWidget):
    """Wraps a bubble in a row that aligns it left/right and constrains width."""

    def __init__(self, bubble: _Bubble, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)
        if bubble.role == "user":
            layout.addStretch(1)
            layout.addWidget(bubble, 4)  # max ~80% width
        else:
            layout.addWidget(bubble, 1)
            layout.addStretch(0)


# --------------------------- Settings dialog ---------------------------

_PRESETS: dict[str, dict[str, str]] = {
    "Ollama (local, free)": {
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "model": "llama3.2",
    },
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
    },
    "Groq (free tier)": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": "",
        "model": "llama-3.1-8b-instant",
    },
    "OpenRouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "",
        "model": "openrouter/auto",
    },
    "LocalAI / vLLM (custom)": {
        "base_url": "http://localhost:8080/v1",
        "api_key": "",
        "model": "local-model",
    },
    "Custom…": {},
}


class AISettingsDialog(QDialog):
    """Configure the AI client (provider, model, key, prompt)."""

    def __init__(self, cfg: AIConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI Assistant — Settings")
        self.setMinimumWidth(560)
        self._cfg = cfg

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        intro = QLabel(
            "Lumen uses any OpenAI-compatible chat-completions endpoint. "
            "Out of the box it points at a local Ollama install — completely free, "
            "runs entirely on your machine. Pick a preset or enter your own."
        )
        intro.setProperty("role", "muted")
        intro.setWordWrap(True)
        root.addWidget(intro)

        # Master enable/disable toggle. When unchecked, every AI-related UI
        # element in the editor (activity bar entry, menu, toolbar button,
        # shortcuts) is hidden until the user re-enables it.
        self.enabled = QCheckBox("Enable AI assistant features")
        self.enabled.setChecked(cfg.enabled)
        self.enabled.setToolTip(
            "Turn off to remove the sidebar panel, menu, toolbar button and "
            "keyboard shortcuts for the AI assistant."
        )
        root.addWidget(self.enabled)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.preset = QComboBox()
        for name in _PRESETS:
            self.preset.addItem(name)
        self.preset.currentTextChanged.connect(self._apply_preset)

        self.base_url = QLineEdit(cfg.base_url)
        self.base_url.setPlaceholderText("http://localhost:11434/v1")

        self.api_key = QLineEdit(cfg.api_key)
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("(leave empty for local Ollama)")

        self.model = QLineEdit(cfg.model)
        self.model.setPlaceholderText("e.g. llama3.2, gpt-4o-mini, gemma2:2b…")

        self.temperature = QSpinBox()
        self.temperature.setRange(0, 100)
        self.temperature.setSuffix(" / 100")
        self.temperature.setValue(int(round(cfg.temperature * 100)))

        self.max_history = QSpinBox()
        self.max_history.setRange(2, 64)
        self.max_history.setValue(cfg.max_history)

        self.system_prompt = QPlainTextEdit(cfg.system_prompt)
        self.system_prompt.setMinimumHeight(100)

        form.addRow("Preset", self.preset)
        form.addRow("Base URL", self.base_url)
        form.addRow("API key", self.api_key)
        form.addRow("Model", self.model)
        form.addRow("Temperature", self.temperature)
        form.addRow("Max history msgs", self.max_history)
        form.addRow("System prompt", self.system_prompt)
        root.addLayout(form)

        hint = QLabel(
            "<b>Quick start with Ollama</b><br>"
            "1. Install Ollama: <code>curl -fsSL https://ollama.com/install.sh | sh</code><br>"
            "2. Pull a model: <code>ollama pull llama3.2</code><br>"
            "3. Make sure <code>ollama serve</code> is running, then click OK."
        )
        hint.setWordWrap(True)
        hint.setProperty("role", "dim")
        hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _apply_preset(self, name: str) -> None:
        preset = _PRESETS.get(name) or {}
        if not preset:
            return
        self.base_url.setText(preset.get("base_url", ""))
        if preset.get("api_key") is not None:
            self.api_key.setText(preset.get("api_key", ""))
        self.model.setText(preset.get("model", ""))

    def result_config(self) -> AIConfig:
        return AIConfig(
            enabled=self.enabled.isChecked(),
            base_url=self.base_url.text().strip().rstrip("/") or self._cfg.base_url,
            api_key=self.api_key.text().strip(),
            model=self.model.text().strip() or self._cfg.model,
            system_prompt=self.system_prompt.toPlainText().strip() or self._cfg.system_prompt,
            temperature=max(0.0, min(2.0, self.temperature.value() / 100.0)),
            include_current_file=self._cfg.include_current_file,
            max_history=int(self.max_history.value()),
        )


# --------------------------- Composer (input) ---------------------------

class _Composer(QPlainTextEdit):
    """Multi-line input that sends on Enter and inserts newline on Shift+Enter."""

    submit = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AIInput")
        self.setPlaceholderText("Ask Lumen anything…  (Enter to send, Shift+Enter for newline)")
        self.setTabChangesFocus(True)
        self.setMinimumHeight(40)
        self.setMaximumHeight(160)
        self.document().contentsChanged.connect(self._auto_grow)

    def keyPressEvent(self, e: QKeyEvent) -> None:  # noqa: N802
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            mods = e.modifiers()
            if mods & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier):
                super().keyPressEvent(e)
            else:
                self.submit.emit()
            return
        super().keyPressEvent(e)

    def _auto_grow(self) -> None:
        doc_h = int(self.document().size().height())
        h = max(40, min(160, doc_h + 18))
        self.setFixedHeight(h)


# --------------------------- The panel ---------------------------

class AIPanel(QFrame):
    """Side-panel chat interface (lives inside the sidebar stack)."""

    file_open_requested = pyqtSignal(str)
    enabled_changed = pyqtSignal(bool)

    def __init__(
        self,
        settings: QSettings,
        parent: QWidget | None = None,
        *,
        store: ChatStore | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("AIPanel")
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._settings = settings
        self._cfg = AIConfig.load(settings)
        self._messages: list[_Message] = []
        self._current_assistant: _Message | None = None
        self._sse_buffer = b""
        self._reply: QNetworkReply | None = None
        self._busy = False

        # Persistent chat history. Either injected (handy for tests) or
        # built from the default JSON file under the app config dir.
        self._store = store if store is not None else ChatStore(parent=self)
        self._active_chat_id: str | None = None
        # While we restore a chat from disk we must not re-write the same
        # messages back into the store via our normal hooks.
        self._restoring = False

        # External "context provider" hooks set by the main window.
        self._context_provider = None  # callable -> (filename, language, code) | None

        self._net = QNetworkAccessManager(self)

        # ---- Header ----
        title = QLabel("AI Assistant")
        title.setObjectName("AITitle")
        subtitle = QLabel("Powered by your model — Ollama, OpenAI, Groq, OpenRouter, …")
        subtitle.setObjectName("AISubtitle")
        subtitle.setWordWrap(True)

        toolbar = QFrame()
        toolbar.setObjectName("AIToolbar")
        tlay = QHBoxLayout(toolbar)
        tlay.setContentsMargins(10, 6, 10, 6)
        tlay.setSpacing(6)

        self.context_chip = QPushButton("Include current file")
        self.context_chip.setObjectName("AIContextChip")
        self.context_chip.setCheckable(True)
        self.context_chip.setChecked(self._cfg.include_current_file)
        self.context_chip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.context_chip.toggled.connect(self._on_context_toggled)
        tlay.addWidget(self.context_chip)

        tlay.addStretch(1)

        self.btn_history = QToolButton()
        self.btn_history.setIcon(icon("history"))
        self.btn_history.setIconSize(QSize(16, 16))
        self.btn_history.setToolTip("Chat history")
        self.btn_history.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_history.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._history_menu = QMenu(self.btn_history)
        self._history_menu.aboutToShow.connect(self._populate_history_menu)
        self.btn_history.setMenu(self._history_menu)
        tlay.addWidget(self.btn_history)

        self.btn_clear = QToolButton()
        self.btn_clear.setIcon(icon("refresh"))
        self.btn_clear.setIconSize(QSize(16, 16))
        self.btn_clear.setToolTip("New chat")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self.new_chat)
        tlay.addWidget(self.btn_clear)

        self.btn_settings = QToolButton()
        self.btn_settings.setIcon(icon("settings"))
        self.btn_settings.setIconSize(QSize(16, 16))
        self.btn_settings.setToolTip("AI settings")
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(self.open_settings)
        tlay.addWidget(self.btn_settings)

        # ---- Chat scroll area ----
        self.scroll = QScrollArea()
        self.scroll.setObjectName("AIChat")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.chat_host = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_host)
        self.chat_layout.setContentsMargins(4, 4, 4, 4)
        self.chat_layout.setSpacing(2)
        self.chat_layout.addStretch(1)
        self.scroll.setWidget(self.chat_host)

        # Empty state card
        self.empty = self._build_empty_state()
        self.chat_layout.insertWidget(0, self.empty)

        # ---- Status / model line ----
        self.status_label = QLabel("")
        self.status_label.setObjectName("AIStatus")
        self.status_label.setWordWrap(True)
        self._refresh_status()

        # ---- Composer row ----
        input_row = QFrame()
        input_row.setObjectName("AIInputRow")
        ilay = QVBoxLayout(input_row)
        ilay.setContentsMargins(10, 8, 10, 10)
        ilay.setSpacing(6)

        self.input = _Composer()
        self.input.submit.connect(self.send_message)
        ilay.addWidget(self.input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        # Debug-mode toggle. Lives flush-left so it stays put while the
        # Send button on the right swaps with the red Stop button.
        self.btn_debug = QPushButton("  Debug")
        self.btn_debug.setObjectName("AIDebugToggle")
        self.btn_debug.setIcon(icon("bug"))
        self.btn_debug.setIconSize(QSize(14, 14))
        self.btn_debug.setCheckable(True)
        self.btn_debug.setChecked(self._cfg.debug_mode)
        self.btn_debug.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_debug.setToolTip(
            "Debug Mode\n"
            "When on, every message is followed by a deep-scan of the\n"
            "current file: crashes, edge cases, optimisations, and a\n"
            "patched version. Press Send with an empty prompt to run a\n"
            "full file audit."
        )
        self.btn_debug.toggled.connect(self._on_debug_toggled)
        btn_row.addWidget(self.btn_debug)

        btn_row.addStretch(1)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("AIStop")
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.clicked.connect(self.cancel_request)
        self.btn_stop.hide()
        btn_row.addWidget(self.btn_stop)

        self.btn_send = ShineButton("Send  ⏎", intense=True)
        self.btn_send.setObjectName("AISend")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self.send_message)
        btn_row.addWidget(self.btn_send)

        ilay.addLayout(btn_row)

        # ---- Compose layout ----
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(toolbar)
        root.addWidget(self.scroll, 1)
        root.addWidget(self.status_label)
        root.addWidget(input_row)

        # Restore the most-recent chat (if any) from the on-disk store.
        self._restore_active_chat()

    # ---- Empty state ----

    def _build_empty_state(self) -> QFrame:
        card = QFrame()
        card.setObjectName("AIEmpty")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        title = QLabel("Hi! I'm Lumen AI.")
        title.setObjectName("AIEmptyTitle")
        title.setWordWrap(True)
        lay.addWidget(title)

        body = QLabel(
            "I'm a chat assistant built into the editor. Ask me to explain code, "
            "fix a bug, write a regex, generate a snippet — anything you'd ask "
            "ChatGPT.<br><br>"
            "<b>By default I'm wired to a local Ollama model</b>, so I cost "
            "nothing to run. To get started:<br>"
            "&nbsp;&nbsp;1. Install "
            "<a href='https://ollama.com'>Ollama</a> on your machine.<br>"
            "&nbsp;&nbsp;2. Run <code>ollama pull llama3.2</code> in a terminal.<br>"
            "&nbsp;&nbsp;3. Type a question below and press Enter.<br><br>"
            "Want to use OpenAI, Groq, OpenRouter, or your own server? Click the "
            "gear icon above to switch."
        )
        body.setObjectName("AIEmptyBody")
        body.setWordWrap(True)
        body.setOpenExternalLinks(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        # Qt renders <a> using QPalette.Link, ignoring inline `color:inherit`.
        # Pin it to the syntax-cyan so the link reads on every theme.
        link_pal = body.palette()
        link_pal.setColor(QPalette.ColorRole.Link, QColor(PALETTE.syn_link))
        body.setPalette(link_pal)
        lay.addWidget(body)

        wrap = QFrame()
        wrap_lay = QHBoxLayout(wrap)
        wrap_lay.setContentsMargins(8, 12, 8, 8)
        wrap_lay.addWidget(card, 1)
        return wrap

    # ---- Public API ----

    def set_context_provider(self, fn) -> None:
        """Register a callable returning (filename, language, code) or None."""
        self._context_provider = fn

    def focus_input(self) -> None:
        self.input.setFocus()

    def open_settings(self) -> None:
        dlg = AISettingsDialog(self._cfg, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            old_enabled = self._cfg.enabled
            self._cfg = dlg.result_config()
            self._cfg.include_current_file = self.context_chip.isChecked()
            self._cfg.save(self._settings)
            self._refresh_status()
            if self._cfg.enabled != old_enabled:
                self.enabled_changed.emit(self._cfg.enabled)

    def is_enabled(self) -> bool:
        return self._cfg.enabled

    def set_enabled(self, enabled: bool) -> None:
        """Update the persisted enabled state (called from MainWindow)."""
        if self._cfg.enabled == enabled:
            return
        self._cfg.enabled = enabled
        self._cfg.save(self._settings)
        if not enabled:
            self.cancel_request()

    def new_chat(self) -> None:
        """Start a fresh conversation. The previous one is preserved on disk."""
        self.cancel_request()
        self._clear_bubbles()
        # Only spawn a brand-new chat in the store if the current chat
        # actually has content; otherwise reuse the empty one.
        active = self._store.active()
        if active is None or active.messages:
            chat = self._store.new_chat()
        else:
            chat = active
        self._active_chat_id = chat.id
        if self.empty is not None:
            self.empty.show()

    def _clear_bubbles(self) -> None:
        for msg in list(self._messages):
            if msg.bubble is not None:
                row = msg.bubble.parentWidget()
                if isinstance(row, _BubbleRow):
                    row.deleteLater()
        self._messages.clear()
        self._current_assistant = None

    # ---- Chat history persistence ----

    def chat_store(self) -> ChatStore:
        return self._store

    def _restore_active_chat(self) -> None:
        """On startup, repopulate the panel from the most-recent chat."""
        chat = self._store.active()
        if chat is None:
            chat = self._store.new_chat()
        self._load_chat(chat)

    def _load_chat(self, chat: StoredChat) -> None:
        self.cancel_request()
        self._clear_bubbles()
        self._active_chat_id = chat.id
        # Avoid re-saving every restored bubble back through our hooks.
        self._restoring = True
        try:
            for stored in chat.messages:
                if stored.role == "user":
                    bubble = _Bubble("user", self.chat_host)
                    bubble.set_text(stored.content)
                    self._add_bubble_row(bubble)
                    self._messages.append(_Message("user", stored.content, bubble))
                else:
                    bubble = _Bubble("assistant", self.chat_host)
                    bubble.set_text(stored.content or " ")
                    self._add_bubble_row(bubble)
                    self._messages.append(
                        _Message("assistant", stored.content, bubble)
                    )
        finally:
            self._restoring = False
        if self.empty is not None:
            self.empty.setVisible(not chat.messages)

    def switch_to_chat(self, chat_id: str) -> None:
        chat = self._store.get(chat_id)
        if chat is None:
            return
        self._store.set_active(chat.id)
        self._load_chat(chat)

    def _populate_history_menu(self) -> None:
        menu = self._history_menu
        menu.clear()

        chats = self._store.chats()
        if not chats:
            empty_action = QAction("(no past chats)", menu)
            empty_action.setEnabled(False)
            menu.addAction(empty_action)
        else:
            for chat in chats:
                title = chat.title or "Untitled"
                if len(title) > 50:
                    title = title[:50] + "…"
                marker = "•  " if chat.id == self._active_chat_id else "    "
                action = QAction(f"{marker}{title}", menu)
                action.setData(chat.id)
                if chat.id == self._active_chat_id:
                    f = action.font()
                    f.setBold(True)
                    action.setFont(f)
                action.triggered.connect(
                    lambda _checked=False, cid=chat.id: self.switch_to_chat(cid)
                )
                menu.addAction(action)

        menu.addSeparator()

        new_action = QAction("New chat", menu)
        new_action.triggered.connect(self.new_chat)
        menu.addAction(new_action)

        if self._active_chat_id is not None:
            rename_action = QAction("Rename current chat…", menu)
            rename_action.triggered.connect(self._rename_current_chat)
            menu.addAction(rename_action)

            delete_action = QAction("Delete current chat", menu)
            delete_action.triggered.connect(self._delete_current_chat)
            menu.addAction(delete_action)

    def _rename_current_chat(self) -> None:
        if self._active_chat_id is None:
            return
        chat = self._store.get(self._active_chat_id)
        if chat is None:
            return
        new_title, ok = QInputDialog.getText(
            self, "Rename chat", "Title:", text=chat.title
        )
        if ok:
            self._store.rename(chat.id, new_title)

    def _delete_current_chat(self) -> None:
        if self._active_chat_id is None:
            return
        chat = self._store.get(self._active_chat_id)
        if chat is None:
            return
        ans = QMessageBox.question(
            self,
            "Delete chat",
            f"Delete the chat “{chat.title}”? This cannot be undone.",
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._store.delete(chat.id)
        next_chat = self._store.active() or self._store.new_chat()
        self._load_chat(next_chat)

    # ---- Sending ----

    def send_message(self) -> None:
        text = self.input.toPlainText().strip()
        if self._busy:
            return
        # Debug-mode lets the user fire a full file audit by hitting Send
        # with an empty prompt — saves them typing the same thing twice.
        if not text:
            if self._cfg.debug_mode:
                text = (
                    "Run a full debug pass on the current file. Find every "
                    "crash path, edge case, and optimisation opportunity, "
                    "then return a patched version."
                )
            else:
                return
        self.input.clear()
        self._append_user_bubble(text)
        if self.empty is not None:
            self.empty.hide()
        self._start_request()

    def cancel_request(self) -> None:
        if self._reply is not None:
            try:
                self._reply.abort()
            except Exception:
                pass
        self._busy = False
        self._reply = None
        self._set_busy(False)
        if self._current_assistant and not self._current_assistant.content:
            self._current_assistant.content = "_(stopped)_"
            if self._current_assistant.bubble is not None:
                self._current_assistant.bubble.set_text("_(stopped)_")
            self._persist_update_last(self._current_assistant.content)
        elif self._current_assistant is not None:
            self._persist_update_last(self._current_assistant.content)
        self._current_assistant = None
        self._store.flush_now()

    # ---- Internal ----

    def _on_context_toggled(self, checked: bool) -> None:
        self._cfg.include_current_file = checked
        self._cfg.save(self._settings)
        self._refresh_status()

    def _on_debug_toggled(self, checked: bool) -> None:
        """Persist the Debug Mode flag and refresh the placeholder text."""
        self._cfg.debug_mode = bool(checked)
        self._cfg.save(self._settings)
        # File context is required for a meaningful debug pass — switch
        # it on automatically when the user enables Debug Mode (but never
        # silently off — they may want to re-disable it later).
        if checked and not self._cfg.include_current_file:
            self.context_chip.setChecked(True)
        self._set_busy(self._busy)  # refresh placeholder
        self._refresh_status()

    def _refresh_status(self) -> None:
        ctx_label = "with current file context" if self._cfg.include_current_file else "no file context"
        try:
            host = QUrl(self._cfg.base_url).host() or self._cfg.base_url
        except Exception:
            host = self._cfg.base_url
        debug_label = "  ·  debug mode" if self._cfg.debug_mode else ""
        self.status_label.setText(
            f"{self._cfg.model}  ·  {host}  ·  {ctx_label}{debug_label}"
        )

    def _append_user_bubble(self, text: str) -> None:
        bubble = _Bubble("user", self.chat_host)
        bubble.set_text(text)
        self._add_bubble_row(bubble)
        self._messages.append(_Message("user", text, bubble))
        if self.empty is not None:
            self.empty.hide()
        self._persist_append("user", text)

    def _start_assistant_bubble(self) -> _Bubble:
        bubble = _Bubble("assistant", self.chat_host)
        bubble.set_text("…")
        self._add_bubble_row(bubble)
        msg = _Message("assistant", "", bubble)
        self._messages.append(msg)
        self._current_assistant = msg
        if self.empty is not None:
            self.empty.hide()
        self._persist_append("assistant", "")
        return bubble

    # ---- Helpers that bridge UI state into the on-disk store ----

    def _ensure_active_chat_id(self) -> str | None:
        if self._restoring:
            return None
        if self._active_chat_id is None:
            chat = self._store.active() or self._store.new_chat()
            self._active_chat_id = chat.id
        return self._active_chat_id

    def _persist_append(self, role: str, content: str) -> None:
        chat_id = self._ensure_active_chat_id()
        if chat_id is None:
            return
        self._store.append_message(chat_id, role, content)

    def _persist_update_last(self, content: str) -> None:
        chat_id = self._ensure_active_chat_id()
        if chat_id is None:
            return
        self._store.update_last_message(chat_id, content)

    def _add_bubble_row(self, bubble: _Bubble) -> None:
        row = _BubbleRow(bubble, self.chat_host)
        # insert before the trailing stretch
        last_idx = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(max(0, last_idx), row)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        from PyQt6.QtCore import QTimer

        def _go() -> None:
            sb = self.scroll.verticalScrollBar()
            if sb is not None:
                sb.setValue(sb.maximum())

        QTimer.singleShot(0, _go)

    def _build_payload(self) -> dict:
        """Build the JSON body for /v1/chat/completions."""
        msgs: list[dict] = []
        if self._cfg.system_prompt:
            msgs.append({"role": "system", "content": self._cfg.system_prompt})

        # Optional file context. Debug Mode forces this on so the model
        # actually has the code in front of it to audit.
        wants_context = self._cfg.include_current_file or self._cfg.debug_mode
        if wants_context and self._context_provider is not None:
            try:
                ctx = self._context_provider()
            except Exception:
                ctx = None
            if ctx:
                filename, language, code = ctx
                if code and len(code) <= 60_000:
                    msgs.append({
                        "role": "system",
                        "content": (
                            f"The user is currently editing `{filename or 'untitled'}` "
                            f"({language}). The full file contents are:\n\n"
                            f"```{language}\n{code}\n```"
                        ),
                    })

        # Debug Mode persona — appended *after* the file context so the
        # model has both the user's persona AND the file in scope when
        # the debug instructions arrive.
        if self._cfg.debug_mode:
            msgs.append({"role": "system", "content": DEBUG_SYSTEM_PROMPT})

        # Conversation history (cap to max_history excluding the just-appended user message)
        history = [m for m in self._messages if m.content]
        cap = max(2, int(self._cfg.max_history))
        if len(history) > cap:
            history = history[-cap:]
        for m in history:
            msgs.append({"role": m.role, "content": m.content})

        return {
            "model": self._cfg.model,
            "messages": msgs,
            "stream": True,
            "temperature": float(self._cfg.temperature),
        }

    def _start_request(self) -> None:
        url = QUrl(self._cfg.base_url.rstrip("/") + "/chat/completions")
        if not url.isValid() or not url.host():
            self._show_error(
                "The configured base URL looks invalid.\n\n"
                f"`{self._cfg.base_url}`\n\n"
                "Click the gear icon to fix it."
            )
            return

        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        request.setRawHeader(b"Accept", b"text/event-stream")
        if self._cfg.api_key:
            request.setRawHeader(b"Authorization", f"Bearer {self._cfg.api_key}".encode())

        try:
            payload = json.dumps(self._build_payload()).encode("utf-8")
        except (TypeError, ValueError) as exc:
            self._show_error(f"Failed to encode request: {exc}")
            return

        self._sse_buffer = b""
        self._set_busy(True)
        self._start_assistant_bubble()

        reply = self._net.post(request, QByteArray(payload))
        self._reply = reply
        reply.readyRead.connect(self._on_ready_read)
        reply.finished.connect(self._on_finished)
        reply.errorOccurred.connect(self._on_error)

    # ---- Streaming SSE handler ----

    def _on_ready_read(self) -> None:
        if self._reply is None:
            return
        chunk = bytes(self._reply.readAll())
        self._sse_buffer += chunk

        # Split on newlines (handle both \r\n and \n) and process complete lines.
        # SSE events are separated by blank lines, but each "data:" line is also
        # individually parseable for OpenAI-style streams.
        while b"\n" in self._sse_buffer:
            line, _, rest = self._sse_buffer.partition(b"\n")
            self._sse_buffer = rest
            self._handle_sse_line(line.rstrip(b"\r"))

    def _handle_sse_line(self, line: bytes) -> None:
        if not line:
            return
        # OpenAI returns lines like:  data: {...}
        # Ollama's /v1 also conforms.
        if line.startswith(b":"):  # comment
            return
        if not line.startswith(b"data:"):
            # Some non-streaming errors come back as plain JSON
            try:
                obj = json.loads(line.decode("utf-8"))
                self._handle_error_object(obj)
            except (ValueError, UnicodeDecodeError):
                pass
            return
        payload = line[5:].strip()
        if payload == b"[DONE]":
            return
        try:
            obj = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return
        if "error" in obj:
            self._handle_error_object(obj)
            return

        # OpenAI: choices[0].delta.content
        try:
            choice = obj["choices"][0]
        except (KeyError, IndexError, TypeError):
            return
        delta = choice.get("delta") or choice.get("message") or {}
        text = delta.get("content")
        if text:
            self._append_assistant_chunk(text)

    def _handle_error_object(self, obj: dict) -> None:
        err = obj.get("error")
        if isinstance(err, dict):
            msg = err.get("message") or json.dumps(err)
        else:
            msg = str(err) if err else json.dumps(obj)
        self._show_error(f"Server error: {msg}")

    def _append_assistant_chunk(self, text: str) -> None:
        if self._current_assistant is None:
            return
        if not self._current_assistant.content:
            # First chunk: replace the placeholder dot
            self._current_assistant.content = text
        else:
            self._current_assistant.content += text
        if self._current_assistant.bubble is not None:
            self._current_assistant.bubble.set_text(self._current_assistant.content)
        # Stream into the store too — the debounced flush coalesces these.
        self._persist_update_last(self._current_assistant.content)
        self._scroll_to_bottom()

    def _on_finished(self) -> None:
        # Drain anything left in the buffer one more time
        if self._sse_buffer:
            for line in self._sse_buffer.split(b"\n"):
                self._handle_sse_line(line.rstrip(b"\r"))
            self._sse_buffer = b""

        if self._current_assistant is not None and not self._current_assistant.content:
            # Likely a non-streaming response — read the entire body as JSON
            if self._reply is not None:
                body = bytes(self._reply.readAll())
                try:
                    obj = json.loads(body.decode("utf-8"))
                    text = obj["choices"][0]["message"]["content"]
                    self._append_assistant_chunk(text)
                except Exception:
                    pass

        if self._current_assistant is not None and not self._current_assistant.content:
            self._current_assistant.content = "_(no response)_"
            if self._current_assistant.bubble is not None:
                self._current_assistant.bubble.set_text(self._current_assistant.content)
            self._persist_update_last(self._current_assistant.content)
        elif self._current_assistant is not None:
            # Final flush for the streamed content — guarantees the
            # finished message is on disk even if the debounce is
            # still pending.
            self._persist_update_last(self._current_assistant.content)
            self._store.flush_now()

        self._current_assistant = None
        self._reply = None
        self._set_busy(False)

    def _on_error(self, code: QNetworkReply.NetworkError) -> None:
        if self._reply is None:
            return
        msg = self._reply.errorString() or f"Network error ({code})"
        # Drop the placeholder bubble if no content arrived
        if self._current_assistant is not None and not self._current_assistant.content:
            hint = ""
            if "localhost" in self._cfg.base_url and "11434" in self._cfg.base_url:
                hint = (
                    "\n\nIs Ollama running? Try in a terminal:\n"
                    "    `ollama serve`\n"
                    "If you don't have Ollama yet:\n"
                    "    `curl -fsSL https://ollama.com/install.sh | sh`\n"
                    f"    `ollama pull {self._cfg.model}`"
                )
            self._current_assistant.content = f"**Connection failed.**\n\n`{msg}`{hint}"
            if self._current_assistant.bubble is not None:
                self._current_assistant.bubble.set_text(self._current_assistant.content)
            self._persist_update_last(self._current_assistant.content)

    # ---- Misc ----

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.btn_send.setEnabled(not busy)
        self.btn_send.setVisible(not busy)
        self.btn_stop.setVisible(busy)
        # Debug toggle stays enabled even while a request is streaming so
        # the user can flip the mode for the next message.
        self.input.setEnabled(not busy)
        if busy:
            self.input.setPlaceholderText(
                "Debugging…" if self._cfg.debug_mode else "Generating…"
            )
        elif self._cfg.debug_mode:
            self.input.setPlaceholderText(
                "Debug Mode — describe what to debug, or press Enter to scan the current file."
            )
        else:
            self.input.setPlaceholderText(
                "Ask Lumen anything…  (Enter to send, Shift+Enter for newline)"
            )

    def _show_error(self, message: str) -> None:
        if self._current_assistant is not None:
            self._current_assistant.content = message
            if self._current_assistant.bubble is not None:
                self._current_assistant.bubble.set_text(message)
            self._persist_update_last(message)
        else:
            bubble = self._start_assistant_bubble()
            bubble.set_text(message)
            self._persist_update_last(message)
        self._set_busy(False)
        self._reply = None
        self._current_assistant = None
        self._store.flush_now()

    # ---- External slash-command-style helpers ----

    def ask_about(self, prompt: str, *, code: str | None = None, filename: str | None = None,
                  language: str = "text") -> None:
        """Pre-populate the composer and optionally bundle a code snippet."""
        if code:
            block = f"```{language}\n{code}\n```"
            tag = f" from `{filename}`" if filename else ""
            self.input.setPlainText(f"{prompt}{tag}\n\n{block}")
        else:
            self.input.setPlainText(prompt)
        self.input.setFocus()
        cursor = self.input.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.input.setTextCursor(cursor)


__all__ = ["AIPanel", "AIConfig", "AISettingsDialog"]
