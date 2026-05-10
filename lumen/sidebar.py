"""File-tree sidebar."""

from __future__ import annotations

import os

from PyQt6.QtCore import QDir, QModelIndex, Qt, pyqtSignal
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from .icons import icon


class FileTree(QFrame):
    file_open_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 8, 4)
        header.setSpacing(6)
        self.title = QLabel("EXPLORER")
        self.title.setProperty("role", "sidebar-title")
        header.addWidget(self.title, 1)

        open_btn = QToolButton()
        open_btn.setIcon(icon("folder"))
        open_btn.setToolTip("Open folder…")
        open_btn.clicked.connect(self.choose_folder)
        header.addWidget(open_btn)
        outer.addLayout(header)

        self.empty_label = QLabel(
            "No folder opened.\n\nOpen a folder to start exploring your project."
        )
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setProperty("role", "dim")
        self.empty_label.setContentsMargins(24, 24, 24, 24)

        self.empty_btn = QPushButton("Open Folder")
        self.empty_btn.clicked.connect(self.choose_folder)
        self.empty_btn.setProperty("role", "primary")

        empty_wrap = QFrame()
        empty_layout = QVBoxLayout(empty_wrap)
        empty_layout.setContentsMargins(16, 0, 16, 16)
        empty_layout.addStretch(1)
        empty_layout.addWidget(self.empty_label)
        empty_layout.addSpacing(6)
        wrap_btn = QHBoxLayout()
        wrap_btn.addStretch(1)
        wrap_btn.addWidget(self.empty_btn)
        wrap_btn.addStretch(1)
        empty_layout.addLayout(wrap_btn)
        empty_layout.addStretch(2)
        self.empty_wrap = empty_wrap
        outer.addWidget(empty_wrap, 1)

        self.model = QFileSystemModel(self)
        self.model.setFilter(
            QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot
        )
        self.model.setNameFilterDisables(False)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(14)
        self.tree.setUniformRowHeights(True)
        self.tree.setSortingEnabled(False)
        self.tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        for col in range(1, 4):
            self.tree.setColumnHidden(col, True)
        self.tree.activated.connect(self._on_activated)
        self.tree.doubleClicked.connect(self._on_activated)
        self.tree.hide()
        outer.addWidget(self.tree, 1)

        self._root: str | None = None

    # ---------------- API ----------------

    def root_path(self) -> str | None:
        return self._root

    def set_root(self, path: str) -> None:
        if not path or not os.path.isdir(path):
            return
        self._root = path
        idx = self.model.setRootPath(path)
        self.tree.setRootIndex(idx)
        self.title.setText(os.path.basename(path).upper() or "/")
        self.empty_wrap.hide()
        self.tree.show()

    def choose_folder(self) -> None:
        start = self._root or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, "Open Folder", start)
        if path:
            self.set_root(path)

    def _on_activated(self, index: QModelIndex) -> None:
        info = self.model.fileInfo(index)
        if info.isDir():
            self.tree.setExpanded(index, not self.tree.isExpanded(index))
            return
        self.file_open_requested.emit(info.filePath())
