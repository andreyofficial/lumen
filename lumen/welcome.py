"""Welcome screen shown when no files are open."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .icons import pixmap as svg_pixmap
from .shine import ShineButton
from .theme import PALETTE


class WelcomeScreen(QFrame):
    new_clicked = pyqtSignal()
    open_file_clicked = pyqtSignal()
    open_folder_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Welcome")
        self.setFrameShape(QFrame.Shape.NoFrame)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(64, 64, 64, 64)
        outer.setSpacing(0)
        outer.addStretch(1)

        # Logo
        logo_row = QHBoxLayout()
        logo_row.addStretch(1)
        logo = QLabel()
        logo.setPixmap(svg_pixmap("logo", 84, PALETTE.accent))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_row.addWidget(logo)
        logo_row.addStretch(1)
        outer.addLayout(logo_row)
        outer.addSpacing(20)

        title = QLabel("Lumen")
        title.setObjectName("WelcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(title)

        subtitle = QLabel("A fast, focused code editor for Linux.")
        subtitle.setObjectName("WelcomeSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(subtitle)
        outer.addSpacing(28)

        # Action buttons — hero buttons get the animated ShineButton sweep.
        row = QHBoxLayout()
        row.addStretch(1)
        new_btn = ShineButton("New File")
        new_btn.setMinimumWidth(160)
        new_btn.setMinimumHeight(40)
        new_btn.clicked.connect(self.new_clicked)
        new_btn.setProperty("role", "primary")
        open_btn = ShineButton("Open File…")
        open_btn.setMinimumWidth(160)
        open_btn.setMinimumHeight(40)
        open_btn.clicked.connect(self.open_file_clicked)
        folder_btn = ShineButton("Open Folder…", intense=True)
        folder_btn.setMinimumWidth(160)
        folder_btn.setMinimumHeight(40)
        folder_btn.clicked.connect(self.open_folder_clicked)
        folder_btn.setProperty("role", "brand")
        row.addWidget(new_btn)
        row.addWidget(open_btn)
        row.addWidget(folder_btn)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addSpacing(36)

        # Shortcuts grid
        shortcuts = [
            ("Command Palette", "Ctrl+Shift+P"),
            ("Find in File", "Ctrl+F"),
            ("Replace", "Ctrl+H"),
            ("New File", "Ctrl+N"),
            ("Open File", "Ctrl+O"),
            ("Save", "Ctrl+S"),
            ("Toggle Sidebar", "Ctrl+B"),
            ("Toggle Comment", "Ctrl+/"),
        ]
        grid_wrap = QHBoxLayout()
        grid_wrap.addStretch(1)
        col_a = QVBoxLayout()
        col_a.setSpacing(6)
        col_b = QVBoxLayout()
        col_b.setSpacing(6)
        for i, (label, kbd) in enumerate(shortcuts):
            line = QLabel(f"{label}  ·  ")
            line.setProperty("role", "muted")
            kbd_label = QLabel(kbd)
            kbd_label.setObjectName("WelcomeKbd")
            row_l = QHBoxLayout()
            row_l.addStretch(1)
            row_l.addWidget(line)
            row_l.addWidget(kbd_label)
            row_l.addStretch(1)
            (col_a if i % 2 == 0 else col_b).addLayout(row_l)
        grid_wrap.addLayout(col_a)
        grid_wrap.addSpacing(40)
        grid_wrap.addLayout(col_b)
        grid_wrap.addStretch(1)
        outer.addLayout(grid_wrap)

        outer.addStretch(2)
