"""Preferences dialog — exposes the QSettings-backed knobs that drive
the editor and the rest of the UI.

Kept self-contained: it talks to ``MainWindow`` only via a small
``Preferences`` snapshot dataclass plus a single ``apply()`` callback,
so the dialog can be shown headlessly in tests without touching real
``QSettings`` storage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


@dataclass
class Preferences:
    """A snapshot of every preference the dialog edits."""

    theme: str = "dark"          # "dark" | "light"
    font_size: int = 13
    tab_size: int = 4
    use_spaces: bool = True
    show_line_numbers: bool = True
    show_minimap: bool = True
    ai_enabled: bool = True


class PreferencesDialog(QDialog):
    """Tabbed Preferences panel: Editor / Appearance / AI."""

    def __init__(
        self,
        prefs: Preferences,
        *,
        on_open_ai_settings: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PreferencesDialog")
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.resize(560, 460)

        self._on_open_ai_settings = on_open_ai_settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 14)
        outer.setSpacing(12)

        title = QLabel("Preferences")
        title.setObjectName("DialogTitle")
        outer.addWidget(title)

        sub = QLabel(
            "Tweak the editor, appearance, and AI assistant. "
            "Changes apply immediately and persist across restarts."
        )
        sub.setProperty("role", "muted")
        sub.setWordWrap(True)
        outer.addWidget(sub)

        tabs = QTabWidget()
        tabs.addTab(self._build_editor_tab(prefs), "Editor")
        tabs.addTab(self._build_appearance_tab(prefs), "Appearance")
        tabs.addTab(self._build_ai_tab(prefs), "AI")
        outer.addWidget(tabs, 1)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        outer.addWidget(bb)

    # ---------------- Tabs ----------------

    def _build_editor_tab(self, prefs: Preferences) -> QWidget:
        page = QFrame()
        form = QFormLayout(page)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 32)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.setValue(prefs.font_size)
        form.addRow("Font size", self.font_size_spin)

        self.tab_size_spin = QSpinBox()
        self.tab_size_spin.setRange(1, 8)
        self.tab_size_spin.setValue(prefs.tab_size)
        form.addRow("Tab size", self.tab_size_spin)

        self.indent_combo = QComboBox()
        self.indent_combo.addItems(["Spaces", "Tabs"])
        self.indent_combo.setCurrentIndex(0 if prefs.use_spaces else 1)
        form.addRow("Indent with", self.indent_combo)

        self.line_numbers_cb = QCheckBox("Show line numbers in the gutter")
        self.line_numbers_cb.setChecked(prefs.show_line_numbers)
        form.addRow("", self.line_numbers_cb)

        self.minimap_cb = QCheckBox("Show minimap")
        self.minimap_cb.setChecked(prefs.show_minimap)
        form.addRow("", self.minimap_cb)

        return page

    def _build_appearance_tab(self, prefs: Preferences) -> QWidget:
        page = QFrame()
        form = QFormLayout(page)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Light", "light")
        idx = 0 if prefs.theme == "dark" else 1
        self.theme_combo.setCurrentIndex(idx)
        form.addRow("Theme", self.theme_combo)

        hint = QLabel(
            "Tip: you can also flip the theme any time with "
            "Ctrl+K Ctrl+T or the moon/sun icon in the activity bar."
        )
        hint.setProperty("role", "muted")
        hint.setWordWrap(True)
        form.addRow("", hint)

        return page

    def _build_ai_tab(self, prefs: Preferences) -> QWidget:
        page = QFrame()
        lay = QVBoxLayout(page)
        lay.setSpacing(10)

        self.ai_enabled_cb = QCheckBox("Enable the AI Assistant")
        self.ai_enabled_cb.setChecked(prefs.ai_enabled)
        lay.addWidget(self.ai_enabled_cb)

        body = QLabel(
            "When enabled, the activity bar shows a Lumen AI tab and "
            "you can chat with a model — by default a free local Ollama "
            "instance, or any OpenAI-compatible endpoint you configure."
        )
        body.setProperty("role", "muted")
        body.setWordWrap(True)
        lay.addWidget(body)

        if self._on_open_ai_settings is not None:
            row = QHBoxLayout()
            row.addStretch(1)
            btn = QPushButton("Configure provider…")
            btn.clicked.connect(self._on_open_ai_settings)
            row.addWidget(btn)
            lay.addLayout(row)

        lay.addStretch(1)
        return page

    # ---------------- Result ----------------

    def result_prefs(self) -> Preferences:
        return Preferences(
            theme=self.theme_combo.currentData() or "dark",
            font_size=self.font_size_spin.value(),
            tab_size=self.tab_size_spin.value(),
            use_spaces=self.indent_combo.currentIndex() == 0,
            show_line_numbers=self.line_numbers_cb.isChecked(),
            show_minimap=self.minimap_cb.isChecked(),
            ai_enabled=self.ai_enabled_cb.isChecked(),
        )


__all__ = ["Preferences", "PreferencesDialog"]
