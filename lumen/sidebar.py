"""File-tree sidebar with PyCharm-style right-click context menu."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Iterable

from PyQt6.QtCore import QDir, QModelIndex, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFileSystemModel, QGuiApplication
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from .icons import icon


class FileTree(QFrame):
    file_open_requested = pyqtSignal(str)
    open_in_terminal_requested = pyqtSignal(str)  # cwd path
    file_created = pyqtSignal(str)  # newly created file path
    file_renamed = pyqtSignal(str, str)  # old_path, new_path
    file_deleted = pyqtSignal(str)  # deleted path

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

        # Quick "+" buttons in the header — same shortcuts as the
        # context menu but always visible without right-clicking.
        new_file_btn = QToolButton()
        new_file_btn.setIcon(icon("new"))
        new_file_btn.setToolTip("New file in project root")
        new_file_btn.clicked.connect(lambda: self._new_file_in(self._root))
        header.addWidget(new_file_btn)

        new_folder_btn = QToolButton()
        new_folder_btn.setIcon(icon("folder"))
        new_folder_btn.setToolTip("New folder in project root")
        new_folder_btn.clicked.connect(lambda: self._new_folder_in(self._root))
        header.addWidget(new_folder_btn)

        open_btn = QToolButton()
        open_btn.setIcon(icon("open"))
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
        # Multi-select: delete / copy / cut multiple files at once.
        self.tree.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        for col in range(1, 4):
            self.tree.setColumnHidden(col, True)
        self.tree.activated.connect(self._on_activated)
        self.tree.doubleClicked.connect(self._on_activated)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.hide()
        outer.addWidget(self.tree, 1)

        self._root: str | None = None
        # Internal "filesystem clipboard" — paths queued by Cut / Copy
        # waiting to be Paste'd. ``mode`` is "cut" or "copy".
        self._fs_clipboard: tuple[str, list[str]] | None = None

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

    # ---------------- Context menu ----------------

    def _selected_paths(self) -> list[str]:
        """Return paths for every selected row (one per row, not per column)."""
        idxs = self.tree.selectionModel().selectedRows() if self.tree.selectionModel() else []
        out: list[str] = []
        for idx in idxs:
            p = self.model.filePath(idx)
            if p:
                out.append(p)
        return out

    def _path_at(self, pos: QPoint) -> str | None:
        idx = self.tree.indexAt(pos)
        return self.model.filePath(idx) if idx.isValid() else None

    def _parent_dir(self, path: str | None) -> str | None:
        """Pick the directory that creating *inside* should target.

        Selecting a folder → that folder. Selecting a file → its parent.
        Right-clicking empty space → the project root.
        """
        if not path:
            return self._root
        if os.path.isdir(path):
            return path
        return os.path.dirname(path)

    def _show_context_menu(self, pos: QPoint) -> None:
        if not self._root:
            return
        clicked_path = self._path_at(pos)
        # Make sure the clicked row is actually selected; otherwise the
        # user's prior selection wins, which is confusing.
        if clicked_path:
            idx = self.tree.indexAt(pos)
            if idx.isValid() and idx not in self.tree.selectionModel().selectedIndexes():
                self.tree.setCurrentIndex(idx)
        selected = self._selected_paths()
        # If they right-clicked a row that wasn't previously selected,
        # operate on just that row rather than whatever was selected.
        if clicked_path and clicked_path not in selected:
            selected = [clicked_path]

        target_dir = self._parent_dir(clicked_path)
        is_dir = bool(clicked_path and os.path.isdir(clicked_path))
        is_file = bool(clicked_path and os.path.isfile(clicked_path))
        on_empty = clicked_path is None

        menu = QMenu(self)

        # ─── Headline: create new file / folder ───
        act_new_file = menu.addAction(icon("new"), "New File…")
        act_new_file.setShortcut("Ctrl+N")
        act_new_file.triggered.connect(lambda: self._new_file_in(target_dir))

        act_new_folder = menu.addAction(icon("folder"), "New Folder…")
        act_new_folder.triggered.connect(lambda: self._new_folder_in(target_dir))

        menu.addSeparator()

        if is_file:
            act_open = menu.addAction("Open")
            act_open.triggered.connect(
                lambda: self.file_open_requested.emit(clicked_path)
            )

        if is_dir:
            act_expand = menu.addAction(
                "Collapse" if self.tree.isExpanded(self.tree.indexAt(pos))
                else "Expand"
            )
            act_expand.triggered.connect(
                lambda: self.tree.setExpanded(
                    self.tree.indexAt(pos),
                    not self.tree.isExpanded(self.tree.indexAt(pos)),
                )
            )

        if not on_empty:
            menu.addSeparator()
            act_cut = menu.addAction("Cut")
            act_cut.setShortcut("Ctrl+X")
            act_cut.triggered.connect(lambda: self._fs_clipboard_set("cut", selected))

            act_copy = menu.addAction("Copy")
            act_copy.setShortcut("Ctrl+C")
            act_copy.triggered.connect(lambda: self._fs_clipboard_set("copy", selected))

        # Paste is offered whenever the clipboard has something.
        if self._fs_clipboard is not None and target_dir:
            act_paste = menu.addAction("Paste")
            act_paste.setShortcut("Ctrl+V")
            act_paste.triggered.connect(lambda: self._paste_into(target_dir))

        if not on_empty:
            menu.addSeparator()
            act_rename = menu.addAction("Rename…")
            act_rename.setShortcut("F2")
            act_rename.triggered.connect(
                lambda: self._rename_path(clicked_path)
            )

            act_delete = menu.addAction("Delete")
            act_delete.setShortcut("Delete")
            act_delete.triggered.connect(lambda: self._delete_paths(selected))

            menu.addSeparator()
            act_copy_path = menu.addAction("Copy Path")
            act_copy_path.triggered.connect(
                lambda: QGuiApplication.clipboard().setText(clicked_path)
            )

            if self._root:
                rel = os.path.relpath(clicked_path, self._root)
                act_copy_rel = menu.addAction(f"Copy Relative Path  ({rel})")
                act_copy_rel.triggered.connect(
                    lambda: QGuiApplication.clipboard().setText(rel)
                )

        menu.addSeparator()
        act_reveal = menu.addAction("Reveal in File Manager")
        reveal_target = clicked_path or self._root
        act_reveal.triggered.connect(
            lambda: self._reveal_in_file_manager(reveal_target)
        )

        act_terminal = menu.addAction("Open in Terminal")
        act_terminal.triggered.connect(
            lambda: self.open_in_terminal_requested.emit(target_dir or self._root)
        )

        menu.addSeparator()
        act_refresh = menu.addAction("Refresh")
        act_refresh.setShortcut("F5")
        act_refresh.triggered.connect(self._refresh_tree)

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    # ---------------- Filesystem operations ----------------

    def _new_file_in(self, parent_dir: str | None) -> None:
        if not parent_dir or not os.path.isdir(parent_dir):
            QMessageBox.information(
                self, "New File", "Open a folder first."
            )
            return
        name, ok = QInputDialog.getText(
            self, "New File", f"File name (in {self._short(parent_dir)}):",
            QLineEdit.EchoMode.Normal,
        )
        if not ok or not name.strip():
            return
        target = os.path.join(parent_dir, name.strip())
        if os.path.exists(target):
            QMessageBox.warning(
                self, "New File",
                f"{name!r} already exists in this folder.",
            )
            return
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "x", encoding="utf-8"):
                pass
        except OSError as exc:
            QMessageBox.warning(self, "New File", f"Could not create file:\n{exc}")
            return
        self._refresh_tree()
        self._select_path(target)
        self.file_created.emit(target)
        self.file_open_requested.emit(target)

    def _new_folder_in(self, parent_dir: str | None) -> None:
        if not parent_dir or not os.path.isdir(parent_dir):
            QMessageBox.information(
                self, "New Folder", "Open a folder first."
            )
            return
        name, ok = QInputDialog.getText(
            self, "New Folder", f"Folder name (in {self._short(parent_dir)}):",
            QLineEdit.EchoMode.Normal,
        )
        if not ok or not name.strip():
            return
        target = os.path.join(parent_dir, name.strip())
        if os.path.exists(target):
            QMessageBox.warning(
                self, "New Folder",
                f"{name!r} already exists in this folder.",
            )
            return
        try:
            os.makedirs(target)
        except OSError as exc:
            QMessageBox.warning(self, "New Folder", f"Could not create folder:\n{exc}")
            return
        self._refresh_tree()
        self._select_path(target)

    def _rename_path(self, path: str) -> None:
        if not path or not os.path.exists(path):
            return
        old_name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(
            self, "Rename", f"Rename {old_name!r} to:",
            QLineEdit.EchoMode.Normal,
            old_name,
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name or new_name == old_name:
            return
        target = os.path.join(os.path.dirname(path), new_name)
        if os.path.exists(target):
            QMessageBox.warning(
                self, "Rename",
                f"{new_name!r} already exists in this folder.",
            )
            return
        try:
            os.rename(path, target)
        except OSError as exc:
            QMessageBox.warning(self, "Rename", f"Could not rename:\n{exc}")
            return
        self._refresh_tree()
        self._select_path(target)
        self.file_renamed.emit(path, target)

    def _delete_paths(self, paths: Iterable[str]) -> None:
        paths = [p for p in paths if p and os.path.exists(p)]
        if not paths:
            return
        if len(paths) == 1:
            msg = f"Delete {os.path.basename(paths[0])!r}?"
        else:
            msg = f"Delete {len(paths)} items?"
        msg += "\n\nThis cannot be undone."
        res = QMessageBox.question(
            self, "Delete",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if res != QMessageBox.StandardButton.Yes:
            return
        for p in paths:
            try:
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
                self.file_deleted.emit(p)
            except OSError as exc:
                QMessageBox.warning(
                    self, "Delete",
                    f"Could not delete {os.path.basename(p)!r}:\n{exc}",
                )
        self._refresh_tree()

    def _fs_clipboard_set(self, mode: str, paths: list[str]) -> None:
        paths = [p for p in paths if p and os.path.exists(p)]
        if not paths:
            return
        self._fs_clipboard = (mode, paths)

    def _paste_into(self, parent_dir: str) -> None:
        if not self._fs_clipboard or not parent_dir:
            return
        mode, paths = self._fs_clipboard
        moved_or_copied: list[str] = []
        for src in paths:
            if not os.path.exists(src):
                continue
            target = self._unique_target(parent_dir, os.path.basename(src))
            try:
                if mode == "cut":
                    shutil.move(src, target)
                elif os.path.isdir(src):
                    shutil.copytree(src, target)
                else:
                    shutil.copy2(src, target)
                moved_or_copied.append(target)
            except (OSError, shutil.Error) as exc:
                QMessageBox.warning(
                    self, "Paste",
                    f"Could not paste {os.path.basename(src)!r}:\n{exc}",
                )
        if mode == "cut":
            self._fs_clipboard = None
        self._refresh_tree()
        if moved_or_copied:
            self._select_path(moved_or_copied[0])

    @staticmethod
    def _unique_target(parent_dir: str, name: str) -> str:
        base, ext = os.path.splitext(name)
        candidate = os.path.join(parent_dir, name)
        n = 1
        while os.path.exists(candidate):
            candidate = os.path.join(parent_dir, f"{base} ({n}){ext}")
            n += 1
        return candidate

    def _refresh_tree(self) -> None:
        if not self._root:
            return
        # Re-rooting forces QFileSystemModel to re-read the directory.
        self.model.setRootPath("")
        idx = self.model.setRootPath(self._root)
        self.tree.setRootIndex(idx)

    def _select_path(self, path: str) -> None:
        idx = self.model.index(path)
        if idx.isValid():
            self.tree.setCurrentIndex(idx)
            self.tree.scrollTo(idx)

    @staticmethod
    def _reveal_in_file_manager(path: str | None) -> None:
        if not path:
            return
        target = path if os.path.isdir(path) else os.path.dirname(path)
        try:
            subprocess.Popen(
                ["xdg-open", target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            pass

    @staticmethod
    def _short(path: str) -> str:
        home = os.path.expanduser("~")
        if path.startswith(home):
            return "~" + path[len(home):]
        return path
