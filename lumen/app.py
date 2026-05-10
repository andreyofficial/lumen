"""Lumen main window — wires every widget into a polished editor."""

from __future__ import annotations

import os
from dataclasses import dataclass

from PyQt6.QtCore import QSettings, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QFont,
    QKeySequence,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from . import __app_name__, __version__, theme
from .activitybar import ActivityBar
from .ai import AIPanel
from .editor import CodeEditor
from .findbar import FindBar
from .highlighter import CodeHighlighter, comment_marker_for, detect_language
from .icons import app_icon, icon
from .minimap import Minimap
from .palette import CommandPalette
from .pycharm import (
    GotoLineDialog,
    OutlinePanel,
    RecentEntry,
    RecentFilesPopup,
    RunPanel,
    runner_for,
)
from .search import SearchPanel
from .sidebar import FileTree
from .terminal import TerminalPanel
from .welcome import WelcomeScreen


# ----------------------------- Tab document -----------------------------

@dataclass
class TabState:
    path: str | None = None
    language: str = "text"
    saved_text: str = ""


class _TabContainer(QWidget):
    """Holds one CodeEditor + minimap side-by-side, with highlighter + state."""

    title_changed = pyqtSignal()
    cursor_changed = pyqtSignal(int, int)
    language_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.editor = CodeEditor(self)
        layout.addWidget(self.editor, 1)
        self.minimap = Minimap(self.editor, self)
        layout.addWidget(self.minimap)
        self.state = TabState()
        self.highlighter = CodeHighlighter(self.editor.document(), "text")
        self.editor.cursor_position_changed.connect(self.cursor_changed)
        self.editor.document().modificationChanged.connect(
            lambda _m: self.title_changed.emit()
        )

    # -- title --
    def display_name(self) -> str:
        return os.path.basename(self.state.path) if self.state.path else "Untitled"

    def is_modified(self) -> bool:
        return self.editor.document().isModified()

    # -- file io --
    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        self.editor.setPlainText(text)
        self.state.path = path
        self.state.saved_text = text
        self.set_language(detect_language(path, text))
        self.editor.document().setModified(False)
        self.title_changed.emit()

    def save(self, path: str | None = None) -> bool:
        target = path or self.state.path
        if not target:
            return False
        try:
            with open(target, "w", encoding="utf-8", newline="\n") as f:
                f.write(self.editor.toPlainText())
        except OSError:
            return False
        self.state.path = target
        self.state.saved_text = self.editor.toPlainText()
        self.set_language(detect_language(target, self.state.saved_text))
        self.editor.document().setModified(False)
        self.title_changed.emit()
        return True

    def set_language(self, language: str) -> None:
        self.state.language = language
        self.highlighter.set_language(language)
        self.editor.setProperty("comment_marker", comment_marker_for(language))
        self.language_changed.emit(language)

    def goto_line(self, line: int) -> None:
        line = max(1, line)
        block = self.editor.document().findBlockByNumber(line - 1)
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        self.editor.setTextCursor(cursor)
        self.editor.centerCursor()
        self.editor.setFocus()

    def show_minimap(self, visible: bool) -> None:
        self.minimap.setVisible(visible)


# ----------------------------- Main window -----------------------------

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._settings = QSettings("Lumen", "Lumen")
        self.setWindowTitle(__app_name__)
        self.setWindowIcon(app_icon())
        self.resize(1320, 820)
        self.setMinimumSize(960, 620)

        self._build_ui()
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()
        self._wire_command_palette()
        self._restore_state()

        if self.tabs.count() == 0:
            self.center_stack.setCurrentWidget(self.welcome)

    # ================ UI ================

    def _build_ui(self) -> None:
        # Activity bar (left rail)
        self.activity = ActivityBar()
        self.activity.add_view("explorer", icon("explorer"), "Explorer (Ctrl+Shift+E)")
        self.activity.add_view("search", icon("search"), "Search (Ctrl+Shift+F)")
        self.activity.add_view("structure", icon("file"), "Structure (Ctrl+F12)")
        self.activity.add_view("ai", icon("sparkles"), "AI Assistant (Ctrl+Shift+A)")
        self.activity.view_changed.connect(self._on_activity_changed)

        # Theme toggle button at the bottom of the activity bar
        self._activity_theme_btn = self.activity.add_view(
            "theme", icon("moon"), "Toggle Theme", bottom=True,
        )
        self._activity_theme_btn.clicked.connect(lambda _c=False: self.toggle_theme())

        # Sidebar stack
        self.sidebar_explorer = FileTree()
        self.sidebar_explorer.setObjectName("Sidebar")
        self.sidebar_explorer.file_open_requested.connect(self.open_path)

        self.sidebar_search = SearchPanel()
        self.sidebar_search.setObjectName("Sidebar")
        self.sidebar_search.file_open_requested.connect(self._open_at_line)

        self.sidebar_outline = OutlinePanel()
        self.sidebar_outline.setObjectName("Sidebar")
        self.sidebar_outline.goto_requested.connect(self._goto_line_in_current)

        self.sidebar_ai = AIPanel(self._settings)
        self.sidebar_ai.setObjectName("Sidebar")
        self.sidebar_ai.set_context_provider(self._collect_ai_context)
        self.sidebar_ai.enabled_changed.connect(self.set_ai_enabled)

        self.sidebar_stack = QStackedWidget()
        self.sidebar_stack.addWidget(self.sidebar_explorer)
        self.sidebar_stack.addWidget(self.sidebar_search)
        self.sidebar_stack.addWidget(self.sidebar_outline)
        self.sidebar_stack.addWidget(self.sidebar_ai)
        self.sidebar_stack.setMinimumWidth(260)

        # Center: tabs + welcome + findbar
        self.editor_area = QWidget()
        ea_layout = QVBoxLayout(self.editor_area)
        ea_layout.setContentsMargins(0, 0, 0, 0)
        ea_layout.setSpacing(0)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        ea_layout.addWidget(self.tabs, 1)
        self.findbar = FindBar()
        ea_layout.addWidget(self.findbar)

        self.welcome = WelcomeScreen()
        self.welcome.new_clicked.connect(self.new_file)
        self.welcome.open_file_clicked.connect(self.open_file_dialog)
        self.welcome.open_folder_clicked.connect(self.sidebar_explorer.choose_folder)

        self.center_stack = QStackedWidget()
        self.center_stack.addWidget(self.welcome)
        self.center_stack.addWidget(self.editor_area)

        # Vertical splitter: editor area | bottom dock (terminal + run panel,
        # tab-switched). PyCharm-style — Run shares the same horizontal
        # band as the terminal, so the editor doesn't lose more vertical
        # real estate when both are available.
        self.terminal = TerminalPanel()
        self.run_panel = RunPanel()
        self.bottom_dock = QTabWidget()
        self.bottom_dock.setDocumentMode(True)
        self.bottom_dock.setTabPosition(QTabWidget.TabPosition.North)
        self.bottom_dock.addTab(self.terminal, icon("terminal"), "Terminal")
        self.bottom_dock.addTab(self.run_panel, icon("file"), "Run")
        self.bottom_dock.hide()
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.setChildrenCollapsible(False)
        self.v_splitter.setHandleWidth(1)
        self.v_splitter.addWidget(self.center_stack)
        self.v_splitter.addWidget(self.bottom_dock)
        self.v_splitter.setStretchFactor(0, 1)
        self.v_splitter.setStretchFactor(1, 0)
        self.v_splitter.setSizes([620, 220])

        # Horizontal splitter: [activity bar] [sidebar] [vertical splitter]
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.h_splitter.setChildrenCollapsible(False)
        self.h_splitter.setHandleWidth(1)
        # The activity bar lives outside the splitter so its width is locked
        outer = QWidget()
        outer_layout = QHBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addWidget(self.activity)
        self.h_splitter.addWidget(self.sidebar_stack)
        self.h_splitter.addWidget(self.v_splitter)
        self.h_splitter.setStretchFactor(0, 0)
        self.h_splitter.setStretchFactor(1, 1)
        self.h_splitter.setSizes([260, 1020])
        outer_layout.addWidget(self.h_splitter, 1)
        self.setCentralWidget(outer)

        # Initial activity selection (signals blocked so _on_activity_changed
        # doesn't run before _build_actions populates self.act_*).
        explorer_btn = self.activity.button("explorer")
        if explorer_btn is not None:
            explorer_btn.blockSignals(True)
            explorer_btn.setChecked(True)
            explorer_btn.blockSignals(False)
        self.sidebar_stack.setCurrentWidget(self.sidebar_explorer)

        # Command palette overlay
        self.command_palette = CommandPalette(self)

    # ================ Actions ================

    def _build_actions(self) -> None:
        # File
        self.act_new = QAction(icon("new"), "New File", self)
        self.act_new.setShortcut(QKeySequence.StandardKey.New)
        self.act_new.triggered.connect(self.new_file)

        self.act_open = QAction(icon("open"), "Open File…", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self.open_file_dialog)

        self.act_open_folder = QAction(icon("folder"), "Open Folder…", self)
        self.act_open_folder.setShortcut("Ctrl+K Ctrl+O")
        self.act_open_folder.triggered.connect(self.sidebar_explorer.choose_folder)

        self.act_save = QAction(icon("save"), "Save", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self.save_file)

        self.act_save_as = QAction("Save As…", self)
        self.act_save_as.setShortcut("Ctrl+Shift+S")
        self.act_save_as.triggered.connect(self.save_as)

        self.act_close_tab = QAction("Close Tab", self)
        self.act_close_tab.setShortcut("Ctrl+W")
        self.act_close_tab.triggered.connect(self._close_current_tab)

        self.act_quit = QAction("Quit", self)
        self.act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_quit.triggered.connect(self.close)

        # Edit
        self.act_undo = QAction(icon("undo"), "Undo", self)
        self.act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.act_undo.triggered.connect(lambda: self._with_editor(lambda e: e.undo()))

        self.act_redo = QAction(icon("redo"), "Redo", self)
        self.act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.act_redo.triggered.connect(lambda: self._with_editor(lambda e: e.redo()))

        self.act_cut = QAction("Cut", self)
        self.act_cut.setShortcut(QKeySequence.StandardKey.Cut)
        self.act_cut.triggered.connect(lambda: self._with_editor(lambda e: e.cut()))

        self.act_copy = QAction("Copy", self)
        self.act_copy.setShortcut(QKeySequence.StandardKey.Copy)
        self.act_copy.triggered.connect(lambda: self._with_editor(lambda e: e.copy()))

        self.act_paste = QAction("Paste", self)
        self.act_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.act_paste.triggered.connect(lambda: self._with_editor(lambda e: e.paste()))

        self.act_select_all = QAction("Select All", self)
        self.act_select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        self.act_select_all.triggered.connect(lambda: self._with_editor(lambda e: e.selectAll()))

        self.act_find = QAction(icon("find"), "Find…", self)
        self.act_find.setShortcut(QKeySequence.StandardKey.Find)
        self.act_find.triggered.connect(self.show_find)

        self.act_replace = QAction("Replace…", self)
        self.act_replace.setShortcut("Ctrl+H")
        self.act_replace.triggered.connect(self.show_find)

        self.act_find_next = QAction("Find Next", self)
        self.act_find_next.setShortcut("F3")
        self.act_find_next.triggered.connect(lambda: self.findbar.find_next())

        self.act_find_prev = QAction("Find Previous", self)
        self.act_find_prev.setShortcut("Shift+F3")
        self.act_find_prev.triggered.connect(lambda: self.findbar.find_previous())

        self.act_search_in_folder = QAction(icon("search"), "Search in Folder…", self)
        self.act_search_in_folder.setShortcut("Ctrl+Shift+F")
        self.act_search_in_folder.triggered.connect(self.show_search_panel)

        # AI
        self.act_toggle_ai = QAction("Enable AI Assistant", self)
        self.act_toggle_ai.setCheckable(True)
        self.act_toggle_ai.setChecked(self.sidebar_ai.is_enabled())
        self.act_toggle_ai.setStatusTip(
            "Show or hide all AI assistant features (panel, menu, shortcuts)."
        )
        self.act_toggle_ai.triggered.connect(self.set_ai_enabled)

        self.act_show_ai = QAction(icon("sparkles"), "AI Assistant", self)
        self.act_show_ai.setShortcut("Ctrl+Shift+A")
        self.act_show_ai.triggered.connect(self.show_ai_panel)

        self.act_ask_ai = QAction(icon("sparkles"), "Ask AI About Selection", self)
        self.act_ask_ai.setShortcut("Ctrl+L")
        self.act_ask_ai.triggered.connect(self.ask_ai_about_selection)

        self.act_ai_settings = QAction(icon("settings"), "AI Settings…", self)
        self.act_ai_settings.triggered.connect(lambda: self.sidebar_ai.open_settings())

        # View
        self.act_toggle_sidebar = QAction("Toggle Sidebar", self)
        self.act_toggle_sidebar.setShortcut("Ctrl+B")
        self.act_toggle_sidebar.setCheckable(True)
        self.act_toggle_sidebar.setChecked(True)
        self.act_toggle_sidebar.triggered.connect(self._toggle_sidebar)

        self.act_show_explorer = QAction("Show Explorer", self)
        self.act_show_explorer.setShortcut("Ctrl+Shift+E")
        self.act_show_explorer.triggered.connect(lambda: self._switch_sidebar("explorer"))

        self.act_toggle_terminal = QAction(icon("terminal"), "Toggle Terminal", self)
        self.act_toggle_terminal.setShortcut("Ctrl+`")
        self.act_toggle_terminal.setCheckable(True)
        self.act_toggle_terminal.triggered.connect(self._toggle_terminal)

        self.act_toggle_minimap = QAction("Toggle Minimap", self)
        self.act_toggle_minimap.setCheckable(True)
        self.act_toggle_minimap.setChecked(True)
        self.act_toggle_minimap.triggered.connect(self._toggle_minimap)

        self.act_toggle_lineno = QAction("Show Line Numbers", self)
        self.act_toggle_lineno.setCheckable(True)
        self.act_toggle_lineno.setChecked(True)
        self.act_toggle_lineno.triggered.connect(self._toggle_line_numbers)

        self.act_zoom_in = QAction("Zoom In", self)
        self.act_zoom_in.setShortcut(QKeySequence("Ctrl+="))
        self.act_zoom_in.triggered.connect(lambda: self._zoom(+1))

        self.act_zoom_out = QAction("Zoom Out", self)
        self.act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        self.act_zoom_out.triggered.connect(lambda: self._zoom(-1))

        self.act_zoom_reset = QAction("Reset Zoom", self)
        self.act_zoom_reset.setShortcut("Ctrl+0")
        self.act_zoom_reset.triggered.connect(lambda: self._zoom(0, reset=True))

        self.act_toggle_theme = QAction(icon("sun"), "Toggle Theme", self)
        self.act_toggle_theme.setShortcut("Ctrl+K Ctrl+T")
        self.act_toggle_theme.triggered.connect(self.toggle_theme)

        # Command palette
        self.act_palette = QAction(icon("palette"), "Command Palette", self)
        self.act_palette.setShortcut("Ctrl+Shift+P")
        self.act_palette.triggered.connect(self._show_palette)

        # ---------- PyCharm-style productivity actions ----------
        self.act_goto_line = QAction("Go to Line…", self)
        self.act_goto_line.setShortcut("Ctrl+G")
        self.act_goto_line.triggered.connect(self.show_goto_line)

        self.act_recent_files = QAction("Recent Files…", self)
        self.act_recent_files.setShortcut("Ctrl+E")
        self.act_recent_files.triggered.connect(self.show_recent_files)

        self.act_show_structure = QAction("File Structure", self)
        self.act_show_structure.setShortcut("Ctrl+F12")
        self.act_show_structure.triggered.connect(
            lambda: self._switch_sidebar("structure")
        )

        self.act_run_file = QAction(icon("file"), "Run Current File", self)
        self.act_run_file.setShortcut("Shift+F10")
        self.act_run_file.triggered.connect(self.run_current_file)

        self.act_stop_run = QAction("Stop Running Process", self)
        self.act_stop_run.setShortcut("Ctrl+F2")
        self.act_stop_run.triggered.connect(lambda: self.run_panel.stop())

        self.act_duplicate_line = QAction("Duplicate Line", self)
        self.act_duplicate_line.setShortcut("Ctrl+D")
        self.act_duplicate_line.triggered.connect(
            lambda: self._with_editor(lambda e: e._duplicate_line())
        )

        self.act_move_line_up = QAction("Move Line Up", self)
        self.act_move_line_up.setShortcut("Alt+Shift+Up")
        self.act_move_line_up.triggered.connect(
            lambda: self._with_editor(lambda e: e._move_lines(-1))
        )

        self.act_move_line_down = QAction("Move Line Down", self)
        self.act_move_line_down.setShortcut("Alt+Shift+Down")
        self.act_move_line_down.triggered.connect(
            lambda: self._with_editor(lambda e: e._move_lines(+1))
        )

        self.act_toggle_comment = QAction("Toggle Comment", self)
        self.act_toggle_comment.setShortcut("Ctrl+/")
        self.act_toggle_comment.triggered.connect(
            lambda: self._with_editor(lambda e: e._toggle_line_comment())
        )

        self.act_complete = QAction("Trigger Completion", self)
        self.act_complete.setShortcut("Ctrl+Space")
        self.act_complete.triggered.connect(
            lambda: self._with_editor(lambda e: e._show_completion_popup(force=True))
        )

        self.act_about = QAction("About Lumen", self)
        self.act_about.triggered.connect(self._show_about)

        # Language picker actions
        self._language_actions: dict[str, QAction] = {}
        self._language_group = QActionGroup(self)
        self._language_group.setExclusive(True)
        for lang in ["text", "python", "javascript", "typescript", "json", "html",
                     "css", "markdown", "c", "cpp", "go", "rust", "shell", "yaml",
                     "toml", "ini"]:
            a = QAction(lang.title() if lang != "cpp" else "C++", self)
            a.setCheckable(True)
            a.setData(lang)
            a.triggered.connect(lambda _checked, lng=lang: self._set_current_language(lng))
            self._language_group.addAction(a)
            self._language_actions[lang] = a

    def _build_menus(self) -> None:
        mb = self.menuBar()

        file_menu: QMenu = mb.addMenu("&File")
        file_menu.addAction(self.act_new)
        file_menu.addAction(self.act_open)
        file_menu.addAction(self.act_open_folder)
        self.recent_menu = file_menu.addMenu("Open Recent")
        file_menu.addSeparator()
        file_menu.addAction(self.act_save)
        file_menu.addAction(self.act_save_as)
        file_menu.addSeparator()
        file_menu.addAction(self.act_close_tab)
        file_menu.addAction(self.act_quit)

        edit_menu: QMenu = mb.addMenu("&Edit")
        edit_menu.addAction(self.act_undo)
        edit_menu.addAction(self.act_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_cut)
        edit_menu.addAction(self.act_copy)
        edit_menu.addAction(self.act_paste)
        edit_menu.addAction(self.act_select_all)
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_find)
        edit_menu.addAction(self.act_replace)
        edit_menu.addAction(self.act_find_next)
        edit_menu.addAction(self.act_find_prev)
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_search_in_folder)
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_duplicate_line)
        edit_menu.addAction(self.act_move_line_up)
        edit_menu.addAction(self.act_move_line_down)
        edit_menu.addAction(self.act_toggle_comment)
        edit_menu.addAction(self.act_complete)

        nav_menu: QMenu = mb.addMenu("&Navigate")
        nav_menu.addAction(self.act_goto_line)
        nav_menu.addAction(self.act_recent_files)
        nav_menu.addAction(self.act_show_structure)
        nav_menu.addSeparator()
        nav_menu.addAction(self.act_palette)

        run_menu: QMenu = mb.addMenu("&Run")
        run_menu.addAction(self.act_run_file)
        run_menu.addAction(self.act_stop_run)

        view_menu: QMenu = mb.addMenu("&View")
        view_menu.addAction(self.act_palette)
        view_menu.addAction(self.act_toggle_sidebar)
        view_menu.addAction(self.act_show_explorer)
        view_menu.addAction(self.act_search_in_folder)
        view_menu.addAction(self.act_show_ai)
        view_menu.addAction(self.act_toggle_terminal)
        view_menu.addSeparator()
        view_menu.addAction(self.act_toggle_minimap)
        view_menu.addAction(self.act_toggle_lineno)
        view_menu.addSeparator()
        view_menu.addAction(self.act_toggle_theme)
        view_menu.addSeparator()
        view_menu.addAction(self.act_zoom_in)
        view_menu.addAction(self.act_zoom_out)
        view_menu.addAction(self.act_zoom_reset)

        ai_menu: QMenu = mb.addMenu("&AI")
        ai_menu.addAction(self.act_toggle_ai)
        ai_menu.addSeparator()
        ai_menu.addAction(self.act_show_ai)
        ai_menu.addAction(self.act_ask_ai)
        ai_menu.addSeparator()
        ai_menu.addAction(self.act_ai_settings)
        self._ai_menu = ai_menu

        lang_menu: QMenu = mb.addMenu("&Language")
        for a in self._language_group.actions():
            lang_menu.addAction(a)

        help_menu: QMenu = mb.addMenu("&Help")
        help_menu.addAction(self.act_about)

        self._update_recent_menu()

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main")
        tb.setObjectName("MainToolBar")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        tb.addAction(self.act_new)
        tb.addAction(self.act_open)
        tb.addAction(self.act_save)
        tb.addSeparator()
        tb.addAction(self.act_undo)
        tb.addAction(self.act_redo)
        tb.addSeparator()
        tb.addAction(self.act_find)
        tb.addAction(self.act_search_in_folder)
        tb.addAction(self.act_palette)
        tb.addAction(self.act_run_file)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)
        tb.addAction(self.act_show_ai)
        tb.addAction(self.act_toggle_terminal)
        tb.addAction(self.act_toggle_theme)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)
        self._toolbar = tb

    def _build_statusbar(self) -> None:
        sb = QStatusBar()
        sb.setSizeGripEnabled(False)
        self.setStatusBar(sb)

        self.status_path = QLabel("")
        self.status_pos = QLabel("Ln 1, Col 1")
        self.status_lang = QLabel("Plain Text")
        self.status_lang.setProperty("role", "accent")
        self.status_indent = QLabel("Spaces: 4")
        self.status_encoding = QLabel("UTF-8")
        self.status_theme = QLabel("Dark")

        sb.addWidget(self.status_path, 1)
        sb.addPermanentWidget(self._sep())
        sb.addPermanentWidget(self.status_pos)
        sb.addPermanentWidget(self._sep())
        sb.addPermanentWidget(self.status_indent)
        sb.addPermanentWidget(self._sep())
        sb.addPermanentWidget(self.status_encoding)
        sb.addPermanentWidget(self._sep())
        sb.addPermanentWidget(self.status_theme)
        sb.addPermanentWidget(self._sep())
        sb.addPermanentWidget(self.status_lang)

        self.status_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_lang.mousePressEvent = lambda _e: self._show_language_menu()
        self.status_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_theme.mousePressEvent = lambda _e: self.toggle_theme()

    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.VLine)
        f.setStyleSheet(f"color:{theme.PALETTE.border};")
        f.setFixedHeight(14)
        return f

    # ================ Command palette wiring ================

    def _wire_command_palette(self) -> None:
        actions = [
            self.act_new, self.act_open, self.act_open_folder,
            self.act_save, self.act_save_as, self.act_close_tab,
            self.act_undo, self.act_redo,
            self.act_find, self.act_replace,
            self.act_search_in_folder,
            self.act_goto_line, self.act_recent_files,
            self.act_show_structure,
            self.act_run_file, self.act_stop_run,
            self.act_duplicate_line, self.act_move_line_up,
            self.act_move_line_down, self.act_toggle_comment,
            self.act_complete,
            self.act_toggle_sidebar, self.act_show_explorer,
            self.act_toggle_terminal,
            self.act_toggle_minimap, self.act_toggle_lineno,
            self.act_toggle_theme,
            self.act_zoom_in, self.act_zoom_out, self.act_zoom_reset,
            self.act_about, self.act_quit,
        ]
        # AI actions only appear in the palette when the feature is enabled.
        if self.sidebar_ai.is_enabled():
            actions.extend([self.act_show_ai, self.act_ask_ai, self.act_ai_settings])
        # The enable/disable toggle itself is always available.
        actions.append(self.act_toggle_ai)
        for a in self._language_group.actions():
            wrap = QAction(f"Set Language: {a.text()}", self)
            lang = a.data()
            wrap.triggered.connect(lambda _c, lng=lang: self._set_current_language(lng))
            actions.append(wrap)
        self.command_palette.set_actions(actions)

    # ================ Tabs ================

    def _current_tab(self) -> _TabContainer | None:
        w = self.tabs.currentWidget()
        return w if isinstance(w, _TabContainer) else None

    def _current_editor(self) -> CodeEditor | None:
        t = self._current_tab()
        return t.editor if t else None

    def _with_editor(self, fn) -> None:
        ed = self._current_editor()
        if ed:
            fn(ed)

    def _add_tab(self, tab: _TabContainer) -> int:
        idx = self.tabs.addTab(tab, tab.display_name())
        tab.title_changed.connect(lambda t=tab: self._refresh_tab_title(t))
        tab.cursor_changed.connect(self._on_cursor_changed)
        tab.language_changed.connect(self._on_language_changed)
        # Keep the file structure outline in lock-step with the active tab.
        tab.editor.textChanged.connect(
            lambda t=tab: self._maybe_refresh_outline(t)
        )
        tab.language_changed.connect(
            lambda _l, t=tab: self._maybe_refresh_outline(t)
        )
        # Seed completion keywords from the language dictionary.
        tab.language_changed.connect(self._update_completion_keywords)
        size = getattr(self, "_initial_font_size", 13)
        tab.editor.set_font_size(size)
        tab.editor.set_show_line_numbers(self.act_toggle_lineno.isChecked())
        tab.show_minimap(self.act_toggle_minimap.isChecked())
        self.tabs.setCurrentIndex(idx)
        self.center_stack.setCurrentWidget(self.editor_area)
        tab.editor.setFocus()
        self._update_completion_keywords(tab.state.language)
        return idx

    def _maybe_refresh_outline(self, tab: _TabContainer) -> None:
        """Update the outline only when it's the visible sidebar."""
        if (
            hasattr(self, "sidebar_outline")
            and self.sidebar_stack.currentWidget() is self.sidebar_outline
            and tab is self._current_tab()
        ):
            self._refresh_outline()

    def _update_completion_keywords(self, language: str | None = None) -> None:
        """Push the active language's keyword set into every editor's completer."""
        from .highlighter import LANG_KEYWORDS  # lazy import to avoid cycles
        words = list(LANG_KEYWORDS.get(language or "", ()))
        for i in range(self.tabs.count()):
            t = self.tabs.widget(i)
            if isinstance(t, _TabContainer):
                t.editor.set_completion_keywords(words)

    def _refresh_tab_title(self, tab: _TabContainer) -> None:
        idx = self.tabs.indexOf(tab)
        if idx < 0:
            return
        title = tab.display_name() + (" •" if tab.is_modified() else "")
        self.tabs.setTabText(idx, title)
        if tab.state.path:
            self.tabs.setTabToolTip(idx, tab.state.path)
        if tab is self._current_tab():
            self._update_window_title()
            self.status_path.setText(tab.state.path or "Untitled")

    def _update_window_title(self) -> None:
        tab = self._current_tab()
        if not tab:
            self.setWindowTitle(__app_name__)
            return
        name = tab.display_name() + (" •" if tab.is_modified() else "")
        self.setWindowTitle(f"{name}  —  {__app_name__}")

    def _close_tab(self, index: int) -> None:
        tab = self.tabs.widget(index)
        if not isinstance(tab, _TabContainer):
            return
        if tab.is_modified():
            res = QMessageBox.question(
                self, "Save changes?",
                f"Save changes to {tab.display_name()} before closing?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if res == QMessageBox.StandardButton.Cancel:
                return
            if res == QMessageBox.StandardButton.Save:
                if not self._save_tab(tab):
                    return
        self.tabs.removeTab(index)
        tab.deleteLater()
        if self.tabs.count() == 0:
            self.center_stack.setCurrentWidget(self.welcome)
            self.findbar.hide()
            self._update_window_title()
            self.status_path.setText("")
            self.status_pos.setText("")
            self.status_lang.setText("Plain Text")

    def _close_current_tab(self) -> None:
        idx = self.tabs.currentIndex()
        if idx >= 0:
            self._close_tab(idx)

    def _on_tab_changed(self, _idx: int) -> None:
        tab = self._current_tab()
        if tab is None:
            return
        self._update_window_title()
        self.status_path.setText(tab.state.path or "Untitled")
        c = tab.editor.textCursor()
        self.status_pos.setText(f"Ln {c.blockNumber()+1}, Col {c.positionInBlock()+1}")
        self._on_language_changed(tab.state.language)
        self.findbar.attach_editor(tab.editor)
        if (
            hasattr(self, "sidebar_outline")
            and self.sidebar_stack.currentWidget() is self.sidebar_outline
        ):
            self._refresh_outline()

    def _on_cursor_changed(self, line: int, col: int) -> None:
        if self.sender() is None or self.sender() is self._current_tab():
            self.status_pos.setText(f"Ln {line}, Col {col}")

    def _on_language_changed(self, language: str) -> None:
        label = {
            "text": "Plain Text", "cpp": "C++", "css": "CSS", "html": "HTML",
            "ini": "INI", "json": "JSON", "toml": "TOML", "yaml": "YAML",
        }.get(language, language.title())
        self.status_lang.setText(label)
        if language in self._language_actions:
            self._language_actions[language].setChecked(True)

    def _set_current_language(self, language: str) -> None:
        tab = self._current_tab()
        if tab:
            tab.set_language(language)

    def _show_language_menu(self) -> None:
        menu = QMenu(self)
        for a in self._language_group.actions():
            menu.addAction(a)
        menu.exec(self.status_lang.mapToGlobal(self.status_lang.rect().bottomLeft()))

    # ================ File operations ================

    def new_file(self) -> _TabContainer:
        tab = _TabContainer()
        tab.set_language("text")
        self._add_tab(tab)
        return tab

    def open_file_dialog(self) -> None:
        start = self._project_root() or os.path.expanduser("~")
        paths, _ = QFileDialog.getOpenFileNames(self, "Open File", start)
        for p in paths:
            self.open_path(p)

    def open_path(self, path: str) -> None:
        path = os.path.abspath(path)
        for i in range(self.tabs.count()):
            t = self.tabs.widget(i)
            if isinstance(t, _TabContainer) and t.state.path == path:
                self.tabs.setCurrentIndex(i)
                return
        try:
            tab = _TabContainer()
            tab.load(path)
        except OSError as exc:
            QMessageBox.warning(self, "Open File", f"Could not open file:\n{exc}")
            return
        self._add_tab(tab)
        self._add_recent(path)

    def _open_at_line(self, path: str, line: int) -> None:
        self.open_path(path)
        tab = self._current_tab()
        if tab:
            tab.goto_line(line)

    def save_file(self) -> None:
        tab = self._current_tab()
        if not tab:
            return
        if tab.state.path is None:
            self.save_as()
        else:
            tab.save()

    def save_as(self) -> None:
        tab = self._current_tab()
        if not tab:
            return
        start = tab.state.path or (
            os.path.join(self._project_root() or os.path.expanduser("~"), "untitled.txt")
        )
        path, _ = QFileDialog.getSaveFileName(self, "Save As", start)
        if not path:
            return
        if tab.save(path):
            self._add_recent(path)

    def _save_tab(self, tab: _TabContainer) -> bool:
        if tab.state.path:
            return tab.save()
        start = os.path.join(self._project_root() or os.path.expanduser("~"), tab.display_name())
        path, _ = QFileDialog.getSaveFileName(self, "Save As", start)
        if not path:
            return False
        return tab.save(path)

    def _project_root(self) -> str | None:
        return self.sidebar_explorer.root_path()

    # ================ Recent files ================

    def _recent(self) -> list[str]:
        v = self._settings.value("recent", [])
        if isinstance(v, str):
            v = [v]
        return [p for p in (v or []) if isinstance(p, str)]

    def _add_recent(self, path: str) -> None:
        recent = [p for p in self._recent() if p != path]
        recent.insert(0, path)
        del recent[10:]
        self._settings.setValue("recent", recent)
        self._update_recent_menu()

    def _update_recent_menu(self) -> None:
        self.recent_menu.clear()
        recent = self._recent()
        if not recent:
            placeholder = self.recent_menu.addAction("No Recent Files")
            placeholder.setEnabled(False)
            return
        for p in recent:
            a = self.recent_menu.addAction(p)
            a.triggered.connect(lambda _c, x=p: self.open_path(x))
        self.recent_menu.addSeparator()
        clear = self.recent_menu.addAction("Clear Recent")
        clear.triggered.connect(self._clear_recent)

    def _clear_recent(self) -> None:
        self._settings.setValue("recent", [])
        self._update_recent_menu()

    # ================ Sidebar / activity bar ================

    def _on_activity_changed(self, view_id: str) -> None:
        if view_id == "explorer":
            self.sidebar_stack.setCurrentWidget(self.sidebar_explorer)
        elif view_id == "search":
            self.sidebar_stack.setCurrentWidget(self.sidebar_search)
            self.sidebar_search.set_root(self._project_root())
            self.sidebar_search.focus_input()
        elif view_id == "structure":
            self.sidebar_stack.setCurrentWidget(self.sidebar_outline)
            self._refresh_outline()
        elif view_id == "ai":
            self.sidebar_stack.setCurrentWidget(self.sidebar_ai)
            self.sidebar_ai.focus_input()

        target_w = 360 if view_id == "ai" else 260
        if not self.sidebar_stack.isVisible():
            self.sidebar_stack.show()
            act = getattr(self, "act_toggle_sidebar", None)
            if act is not None:
                act.setChecked(True)
            self.h_splitter.setSizes(
                [target_w, max(700, self.width() - target_w - 48)]
            )
        else:
            sizes = self.h_splitter.sizes()
            if sizes and sizes[0] < target_w:
                total = sum(sizes) or self.width()
                self.h_splitter.setSizes([target_w, max(600, total - target_w)])

    def _switch_sidebar(self, view_id: str) -> None:
        self.activity.select(view_id)

    def show_search_panel(self) -> None:
        sel = ""
        ed = self._current_editor()
        if ed:
            sel = ed.textCursor().selectedText()
        self._switch_sidebar("search")
        if sel and "\u2029" not in sel:
            self.sidebar_search.set_query(sel)

    def show_ai_panel(self) -> None:
        if not self.sidebar_ai.is_enabled():
            return
        self._switch_sidebar("ai")
        self.sidebar_ai.focus_input()

    def ask_ai_about_selection(self) -> None:
        """Send the current selection (or whole file) into the AI composer."""
        if not self.sidebar_ai.is_enabled():
            return
        tab = self._current_tab()
        if tab is None:
            self.show_ai_panel()
            return
        ed = tab.editor
        cursor = ed.textCursor()
        sel = cursor.selectedText().replace("\u2029", "\n")
        filename = os.path.basename(tab.state.path) if tab.state.path else "untitled"
        language = tab.state.language or "text"
        if sel.strip():
            prompt = "Explain this code"
            code = sel
        else:
            prompt = "Explain this file"
            code = ed.toPlainText()
        self.show_ai_panel()
        self.sidebar_ai.ask_about(prompt, code=code, filename=filename, language=language)

    def _collect_ai_context(self):
        """Provider for AIPanel — returns (filename, language, code) or None."""
        tab = self._current_tab()
        if tab is None:
            return None
        filename = os.path.basename(tab.state.path) if tab.state.path else "untitled"
        return (filename, tab.state.language or "text", tab.editor.toPlainText())

    def set_ai_enabled(self, enabled: bool) -> None:
        """Show or hide every AI-related UI element.

        Disabling hides the activity bar entry, the AI menu's command items,
        the toolbar AI button, the sidebar panel itself, and disables the
        keyboard shortcuts. Enabling restores them.
        """
        enabled = bool(enabled)
        # Persist on the panel's config (panel may also have called this
        # from its own settings-dialog flow).
        self.sidebar_ai.set_enabled(enabled)

        # Keep the checkable action in sync (even when set_ai_enabled is
        # called programmatically rather than from the action itself).
        if hasattr(self, "act_toggle_ai") and self.act_toggle_ai.isChecked() != enabled:
            self.act_toggle_ai.blockSignals(True)
            self.act_toggle_ai.setChecked(enabled)
            self.act_toggle_ai.blockSignals(False)

        # Activity bar button
        ai_btn = self.activity.button("ai")
        if ai_btn is not None:
            ai_btn.setVisible(enabled)
            if not enabled and ai_btn.isChecked():
                # Switch to explorer if the AI activity was selected
                self._switch_sidebar("explorer")

        # Sidebar stack page (hide it when disabled so a cached current
        # widget can't get re-shown by some other path).
        if not enabled and self.sidebar_stack.currentWidget() is self.sidebar_ai:
            self.sidebar_stack.setCurrentWidget(self.sidebar_explorer)

        # Menu items + their shortcuts. setVisible(False) also disables
        # the shortcut from triggering.
        for act in (self.act_show_ai, self.act_ask_ai, self.act_ai_settings):
            act.setVisible(enabled)
            act.setEnabled(enabled)

        # Toolbar action
        if hasattr(self, "_toolbar"):
            self.act_show_ai.setVisible(enabled)

        # Refresh command palette so disabled actions don't show up
        if hasattr(self, "command_palette"):
            self._wire_command_palette()

        # Persist at the MainWindow level too (matches what AIPanel does)
        self._settings.setValue("ai/enabled", enabled)

    def _toggle_sidebar(self, checked: bool) -> None:
        sizes = self.h_splitter.sizes()
        if checked:
            self.sidebar_stack.show()
            if sizes[0] == 0:
                total = sum(sizes) or self.width()
                self.h_splitter.setSizes([260, max(600, total - 260)])
        else:
            self.sidebar_stack.hide()
        self._settings.setValue("sidebar_visible", checked)

    # ================ Terminal ================

    def _toggle_terminal(self, checked: bool | None = None) -> None:
        if checked is None:
            checked = not self.bottom_dock.isVisible()
        self.act_toggle_terminal.setChecked(bool(checked))
        if checked:
            self.terminal.set_cwd(self._project_root() or os.path.expanduser("~"))
            self.bottom_dock.show()
            self.bottom_dock.setCurrentWidget(self.terminal)
            sizes = self.v_splitter.sizes()
            total = sum(sizes) or 800
            if sizes[1] < 80:
                self.v_splitter.setSizes([max(300, total - 220), 220])
            self.terminal.focus_input()
        else:
            self.bottom_dock.hide()
        self._settings.setValue("terminal_visible", bool(checked))

    def _show_run_panel(self) -> None:
        """Reveal the bottom dock and switch to the Run tab."""
        self.bottom_dock.show()
        self.bottom_dock.setCurrentWidget(self.run_panel)
        self.act_toggle_terminal.setChecked(True)
        sizes = self.v_splitter.sizes()
        total = sum(sizes) or 800
        if sizes[1] < 120:
            self.v_splitter.setSizes([max(300, total - 260), 260])

    # ================ PyCharm-style productivity actions ================

    def show_goto_line(self) -> None:
        ed = self._current_editor()
        if not ed:
            return
        max_line = ed.document().blockCount()
        dlg = GotoLineDialog(max_line, self)
        dlg.requested.connect(lambda ln, col: ed.goto_line(ln, col))
        dlg.exec()

    def show_recent_files(self) -> None:
        recent = self._recent()
        if not recent:
            QMessageBox.information(
                self, "Recent Files",
                "No files in your recent list yet — open something first.",
            )
            return
        entries = [RecentEntry(path=p) for p in recent]
        popup = RecentFilesPopup(entries, self)
        popup.activated.connect(lambda p, _ln: self.open_path(p))
        popup.move(
            self.geometry().center().x() - popup.width() // 2,
            self.geometry().top() + 120,
        )
        popup.exec()

    def run_current_file(self) -> None:
        tab = self._current_tab()
        if not tab:
            QMessageBox.information(
                self, "Run", "Open a file first."
            )
            return
        if not tab.state.path:
            res = QMessageBox.question(
                self, "Run",
                "Save this file before running?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Cancel,
            )
            if res != QMessageBox.StandardButton.Save:
                return
            if not self._save_tab(tab):
                return
        if tab.is_modified() and tab.state.path:
            tab.save()
        if runner_for(tab.state.path or "") is None:
            QMessageBox.information(
                self, "Run",
                f"No runner is configured for "
                f"{os.path.basename(tab.state.path or '')}.",
            )
            return
        self._show_run_panel()
        err = self.run_panel.run_file(
            tab.state.path,
            cwd=self._project_root() or os.path.dirname(tab.state.path),
        )
        if err:
            QMessageBox.warning(self, "Run", err)

    def _goto_line_in_current(self, line: int) -> None:
        ed = self._current_editor()
        if ed:
            ed.goto_line(line)

    def _refresh_outline(self) -> None:
        tab = self._current_tab()
        if tab:
            self.sidebar_outline.update_outline(
                tab.state.language, tab.editor.toPlainText()
            )
        else:
            self.sidebar_outline.update_outline("", "")

    # ================ Minimap / line numbers ================

    def _toggle_minimap(self, checked: bool) -> None:
        for i in range(self.tabs.count()):
            t = self.tabs.widget(i)
            if isinstance(t, _TabContainer):
                t.show_minimap(checked)
        self._settings.setValue("minimap", checked)

    def _toggle_line_numbers(self, checked: bool) -> None:
        for i in range(self.tabs.count()):
            t = self.tabs.widget(i)
            if isinstance(t, _TabContainer):
                t.editor.set_show_line_numbers(checked)
        self._settings.setValue("line_numbers", checked)

    # ================ Theme ================

    def toggle_theme(self) -> None:
        self.set_theme("light" if theme.active_name() == "dark" else "dark")

    def set_theme(self, name: str) -> None:
        if name not in theme.PALETTES:
            return
        theme.set_active(name)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(theme.stylesheet(theme.PALETTE))
        # Rebuild syntax highlighter rules so colors update
        for i in range(self.tabs.count()):
            t = self.tabs.widget(i)
            if isinstance(t, _TabContainer):
                t.highlighter.set_language(t.state.language)
                t.editor._highlight_current_line()
                t.editor.viewport().update()
                t.minimap.update()
        # Refresh the activity bar's theme button icon
        self._activity_theme_btn.setIcon(
            icon("sun" if name == "dark" else "moon")
        )
        self.act_toggle_theme.setIcon(
            icon("sun" if name == "dark" else "moon")
        )
        self.status_theme.setText("Dark" if name == "dark" else "Light")
        self._settings.setValue("theme", name)

    # ================ Misc ================

    def _zoom(self, delta: int, *, reset: bool = False) -> None:
        ed = self._current_editor()
        if not ed:
            return
        size = 13 if reset else max(8, min(32, ed.font_size() + delta))
        for i in range(self.tabs.count()):
            t = self.tabs.widget(i)
            if isinstance(t, _TabContainer):
                t.editor.set_font_size(size)
        self._settings.setValue("font_size", size)

    def show_find(self) -> None:
        ed = self._current_editor()
        if not ed:
            return
        self.findbar.show_for(ed)

    def _show_palette(self) -> None:
        self._wire_command_palette()
        self.command_palette.open()

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {__app_name__}",
            f"<h3>{__app_name__} {__version__}</h3>"
            "<p>A fast, focused code editor for Linux.</p>"
            "<p>Built with PyQt6.</p>",
        )

    # ================ Persistence ================

    def _restore_state(self) -> None:
        geom = self._settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        state = self._settings.value("window_state")
        if state:
            self.restoreState(state)

        theme_name = self._settings.value("theme", "dark")
        if isinstance(theme_name, str):
            self.set_theme(theme_name)

        sb_visible = self._settings.value("sidebar_visible", True, type=bool)
        self.act_toggle_sidebar.setChecked(bool(sb_visible))
        self._toggle_sidebar(bool(sb_visible))

        term_visible = self._settings.value("terminal_visible", False, type=bool)
        self._toggle_terminal(bool(term_visible))

        minimap_on = self._settings.value("minimap", True, type=bool)
        self.act_toggle_minimap.setChecked(bool(minimap_on))

        ln = self._settings.value("line_numbers", True, type=bool)
        self.act_toggle_lineno.setChecked(bool(ln))

        root = self._settings.value("last_folder")
        if isinstance(root, str) and os.path.isdir(root):
            self.sidebar_explorer.set_root(root)
            self.sidebar_search.set_root(root)
            self.terminal.set_cwd(root)

        font_size = self._settings.value("font_size", 13, type=int)
        self._initial_font_size = max(8, min(32, int(font_size)))

        # Apply the persisted AI-enabled state so the UI matches on startup.
        ai_enabled = self._settings.value("ai/enabled", True, type=bool)
        self.set_ai_enabled(bool(ai_enabled))

    def _persist_state(self) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("window_state", self.saveState())
        if self._project_root():
            self._settings.setValue("last_folder", self._project_root())

    # ================ Close handling ================

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        for i in range(self.tabs.count()):
            t = self.tabs.widget(i)
            if isinstance(t, _TabContainer) and t.is_modified():
                self.tabs.setCurrentIndex(i)
                res = QMessageBox.question(
                    self, "Save changes?",
                    f"Save changes to {t.display_name()} before quitting?",
                    QMessageBox.StandardButton.Save
                    | QMessageBox.StandardButton.Discard
                    | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Save,
                )
                if res == QMessageBox.StandardButton.Cancel:
                    event.ignore()
                    return
                if res == QMessageBox.StandardButton.Save:
                    if not self._save_tab(t):
                        event.ignore()
                        return
        self._persist_state()
        super().closeEvent(event)


# ============================== Entry point ==============================

def run(argv: list[str] | None = None) -> int:
    import sys
    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    app.setOrganizationName("Lumen")
    app.setStyle("Fusion")
    app.setStyleSheet(theme.stylesheet(theme.PALETTE))
    base_font = QFont("Inter")
    base_font.setStyleHint(QFont.StyleHint.SansSerif)
    base_font.setPointSize(10)
    app.setFont(base_font)
    app.setWindowIcon(app_icon())

    w = MainWindow()
    w.show()

    cli_files = [a for a in argv[1:] if not a.startswith("-")]
    for p in cli_files:
        if os.path.isdir(p):
            w.sidebar_explorer.set_root(p)
            w.sidebar_search.set_root(p)
            w.terminal.set_cwd(p)
        elif os.path.isfile(p):
            w.open_path(p)

    return app.exec()
