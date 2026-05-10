"""Themed palettes (Dark + Light) and Qt Style Sheet generator.

The chrome (UI surfaces, buttons, sidebars) keeps its monochrome
black/white look — but the **code itself** is fully coloured. Every
syntax token gets its own hue so the editor reads at a glance: keywords,
strings, numbers, functions, classes, types, etc. all carry meaning by
colour. Hero buttons use a glossy gradient + a soft outer glow halo
(see ``lumen.shine.ShineButton``) for the FileHub-style polished look.
"""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass
class Palette:
    name: str

    # Backgrounds
    bg_app: str
    bg_sidebar: str
    bg_editor: str
    bg_panel: str
    bg_elevated: str
    bg_hover: str
    bg_active: str
    bg_input: str

    # Borders / dividers
    border: str
    border_strong: str
    divider: str

    # Text
    text: str
    text_muted: str
    text_dim: str
    text_inverse: str

    # Brand / accents
    accent: str            # primary pink-magenta
    accent_hover: str
    accent_pressed: str
    accent_subtle: str
    accent2: str           # purple complement
    accent_grad_a: str     # gradient stops for buttons
    accent_grad_b: str

    # Primary CTA (mint / green)
    cta: str
    cta_hover: str
    cta_pressed: str
    cta_text: str

    # Semantic
    info: str
    success: str
    warning: str
    error: str

    # Editor specifics
    line_number_bg: str
    line_number_fg: str
    line_number_fg_active: str
    current_line_bg: str
    selection_bg: str
    selection_inactive_bg: str
    matching_bracket_bg: str
    indent_guide: str

    # Syntax
    syn_comment: str
    syn_keyword: str
    syn_keyword2: str
    syn_string: str
    syn_number: str
    syn_function: str
    syn_class: str
    syn_decorator: str
    syn_operator: str
    syn_constant: str
    syn_type: str
    syn_tag: str
    syn_attribute: str
    syn_punct: str
    syn_heading: str
    syn_link: str


# ---------------- Dark — true black / monochrome ----------------

DARK = Palette(
    name="dark",

    bg_app="#000000",
    bg_sidebar="#0a0a0a",
    bg_editor="#000000",
    bg_panel="#0f0f0f",
    bg_elevated="#161616",
    bg_hover="#1c1c1c",
    bg_active="#262626",
    bg_input="#0d0d0d",

    border="#1f1f1f",
    border_strong="#2e2e2e",
    divider="#141414",

    text="#f5f5f5",
    text_muted="#a3a3a3",
    text_dim="#6e6e6e",
    text_inverse="#000000",

    # Accent ramp uses pure white for emphasis; tonal stops below it.
    accent="#ffffff",
    accent_hover="#ededed",
    accent_pressed="#cfcfcf",
    accent_subtle="#1a1a1a",
    accent2="#bdbdbd",
    # Graphite gradient — used for the brand button & AI user bubble.
    # Stays dark enough that hard-coded white text remains readable.
    accent_grad_a="#3f3f3f",
    accent_grad_b="#707070",

    # Primary CTA: white pill with black text (inverse).
    cta="#ffffff",
    cta_hover="#ededed",
    cta_pressed="#cfcfcf",
    cta_text="#000000",

    # Semantic: monochrome with one allowance for error red so
    # destructive states stay unambiguous.
    info="#bdbdbd",
    success="#e5e5e5",
    warning="#cfcfcf",
    error="#ef4444",

    line_number_bg="#000000",
    line_number_fg="#3a3a3a",
    line_number_fg_active="#ffffff",
    current_line_bg="#11151f",   # subtle blue-tinted highlight for active line
    selection_bg="#3a3a3a",
    selection_inactive_bg="#222222",
    matching_bracket_bg="#3a2f60",  # purple-tinted to pair with keyword pink
    indent_guide="#161616",

    # Vibrant neon-on-black syntax palette. Each token type owns a hue;
    # the high saturation against the pure black bg makes them appear
    # to glow.
    syn_comment="#7c8298",     # muted blue-gray (italic)
    syn_keyword="#ff5da2",     # hot pink (bold)
    syn_keyword2="#c8a3ff",    # lavender (italic)   — self / cls / this
    syn_string="#4fffa3",      # neon mint
    syn_number="#ffc94a",      # amber
    syn_function="#5be0ff",    # bright cyan (bold)
    syn_class="#ffd84a",       # gold (bold)
    syn_decorator="#ff8ec0",   # rose (italic)
    syn_operator="#ff5da2",    # hot pink
    syn_constant="#b48bff",    # purple (bold)
    syn_type="#92e3ff",        # aqua
    syn_tag="#ff7fb6",         # rose-pink (bold)
    syn_attribute="#d6c0ff",   # light violet
    syn_punct="#cbd5e1",       # silver
    syn_heading="#ffffff",     # bold white
    syn_link="#5be0ff",        # cyan
)


# ---------------- Light — pure white / monochrome ----------------

LIGHT = Palette(
    name="light",

    bg_app="#ffffff",
    bg_sidebar="#fafafa",
    bg_editor="#ffffff",
    bg_panel="#ffffff",
    bg_elevated="#ffffff",
    bg_hover="#f0f0f0",
    bg_active="#e5e5e5",
    bg_input="#fafafa",

    border="#e5e5e5",
    border_strong="#cfcfcf",
    divider="#f0f0f0",

    text="#000000",
    text_muted="#525252",
    text_dim="#888888",
    text_inverse="#ffffff",

    accent="#000000",
    accent_hover="#1f1f1f",
    accent_pressed="#2e2e2e",
    accent_subtle="#f0f0f0",
    accent2="#3a3a3a",
    accent_grad_a="#3f3f3f",
    accent_grad_b="#707070",

    cta="#000000",
    cta_hover="#1f1f1f",
    cta_pressed="#2e2e2e",
    cta_text="#ffffff",

    info="#525252",
    success="#2e2e2e",
    warning="#525252",
    error="#cc0000",

    line_number_bg="#ffffff",
    line_number_fg="#cfcfcf",
    line_number_fg_active="#000000",
    current_line_bg="#f5f5f5",
    selection_bg="#cfcfcf",
    selection_inactive_bg="#e5e5e5",
    matching_bracket_bg="#d4d4d4",
    indent_guide="#f0f0f0",

    # Saturated-but-readable syntax palette for white background. Same
    # semantic mapping as the dark theme, just darker hues so they pass
    # contrast on white.
    syn_comment="#6c6f93",
    syn_keyword="#c026d3",     # bold magenta
    syn_keyword2="#7c3aed",    # violet (italic) — self / cls / this
    syn_string="#15803d",      # forest green
    syn_number="#b45309",      # burnt amber
    syn_function="#0e7490",    # deep teal (bold)
    syn_class="#92400e",       # dark gold (bold)
    syn_decorator="#be185d",   # deep rose (italic)
    syn_operator="#c026d3",
    syn_constant="#6d28d9",    # deep violet (bold)
    syn_type="#0d9488",        # teal
    syn_tag="#be185d",
    syn_attribute="#4f46e5",   # indigo
    syn_punct="#475569",       # slate
    syn_heading="#000000",
    syn_link="#0891b2",        # cyan-700
)


PALETTES: dict[str, Palette] = {"dark": DARK, "light": LIGHT}

# Live, mutable singleton. Theme switching mutates this instance in place
# so that `from .theme import PALETTE` references stay valid.
def _clone(src: Palette) -> Palette:
    return Palette(**{f.name: getattr(src, f.name) for f in fields(src)})


PALETTE: Palette = _clone(DARK)


def set_active(name: str) -> Palette:
    """Switch the live palette to *name* by copying fields in place."""
    src = PALETTES.get(name, DARK)
    for f in fields(src):
        setattr(PALETTE, f.name, getattr(src, f.name))
    return PALETTE


def active_name() -> str:
    return PALETTE.name


def stylesheet(p: Palette) -> str:
    """Build the full QSS for the given palette."""
    return f"""
    /* ================ Global ================ */
    QWidget {{
        background-color: {p.bg_app};
        color: {p.text};
        font-family: "Inter", "Segoe UI", "Cantarell", "Ubuntu", "Noto Sans", sans-serif;
        font-size: 13px;
        selection-background-color: {p.selection_bg};
        selection-color: {p.text};
    }}
    QMainWindow, QDialog {{
        background-color: {p.bg_app};
    }}
    QToolTip {{
        background-color: {p.bg_elevated};
        color: {p.text};
        border: 1px solid {p.border_strong};
        padding: 6px 10px;
        border-radius: 6px;
    }}

    /* ================ Menu bar ================ */
    QMenuBar {{
        background-color: {p.bg_app};
        color: {p.text_muted};
        border-bottom: 1px solid {p.border};
        padding: 3px 8px;
        spacing: 2px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 6px 10px;
        border-radius: 6px;
    }}
    QMenuBar::item:selected {{ background: {p.bg_hover}; color: {p.text}; }}
    QMenuBar::item:pressed {{ background: {p.bg_active}; color: {p.text}; }}

    QMenu {{
        background-color: {p.bg_elevated};
        color: {p.text};
        border: 1px solid {p.border_strong};
        padding: 6px;
        border-radius: 10px;
    }}
    QMenu::item {{
        padding: 7px 24px 7px 24px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background-color: {p.accent_subtle};
        color: {p.text};
    }}
    QMenu::separator {{ height: 1px; background: {p.border}; margin: 6px 8px; }}
    QMenu::icon {{ padding-left: 8px; }}

    /* ================ Tool bar ================ */
    QToolBar {{
        background-color: {p.bg_sidebar};
        border: none;
        border-bottom: 1px solid {p.border};
        padding: 6px 8px;
        spacing: 2px;
    }}
    QToolBar::separator {{
        background: {p.border}; width: 1px; margin: 6px 6px;
    }}
    QToolButton {{
        background: transparent;
        color: {p.text_muted};
        border: 1px solid transparent;
        padding: 6px 8px;
        border-radius: 8px;
    }}
    QToolButton:hover {{
        background: {p.bg_hover};
        color: {p.text};
    }}
    QToolButton:pressed, QToolButton:checked {{
        background: {p.bg_active};
        color: {p.accent};
        border-color: {p.border_strong};
    }}

    /* ================ Activity bar (left rail) ================ */
    QFrame#ActivityBar {{
        background: {p.bg_sidebar};
        border-right: 1px solid {p.border};
    }}
    QToolButton#ActivityBtn {{
        background: transparent;
        color: {p.text_dim};
        border: none;
        padding: 12px 8px;
        border-left: 2px solid transparent;
        border-radius: 0;
    }}
    QToolButton#ActivityBtn:hover {{ color: {p.text}; }}
    QToolButton#ActivityBtn:checked {{
        color: {p.accent};
        border-left: 2px solid {p.accent};
    }}

    /* ================ Status bar ================ */
    QStatusBar {{
        background-color: {p.bg_sidebar};
        color: {p.text_muted};
        border-top: 1px solid {p.border};
        padding: 2px 6px;
    }}
    QStatusBar::item {{ border: none; }}
    QStatusBar QLabel {{
        background: transparent;
        color: {p.text_muted};
        padding: 2px 8px;
        border-radius: 6px;
    }}
    QStatusBar QLabel[role="accent"] {{
        color: {p.accent};
        font-weight: 600;
    }}

    /* ================ Splitter ================ */
    QSplitter::handle {{ background: {p.bg_app}; }}
    QSplitter::handle:horizontal {{ width: 1px; background: {p.border}; }}
    QSplitter::handle:vertical {{ height: 1px; background: {p.border}; }}

    /* ================ Sidebar / tree ================ */
    QFrame#Sidebar {{
        background: {p.bg_sidebar};
        border-right: 1px solid {p.border};
    }}
    QTreeView, QListView {{
        background-color: transparent;
        color: {p.text};
        border: none;
        outline: 0;
        padding: 4px 0;
        show-decoration-selected: 1;
        alternate-background-color: {p.bg_sidebar};
    }}
    QTreeView::item, QListView::item {{
        padding: 4px 6px;
        border-radius: 6px;
        margin: 1px 8px;
    }}
    QTreeView::item:hover, QListView::item:hover {{ background-color: {p.bg_hover}; }}
    QTreeView::item:selected, QListView::item:selected {{
        background-color: {p.accent_subtle};
        color: {p.text};
    }}
    QTreeView::branch {{ background: transparent; }}

    /* ================ Tab widget ================ */
    QTabWidget::pane {{
        border: none;
        background: {p.bg_editor};
        top: 0px;
    }}
    QTabBar {{
        background: {p.bg_app};
        qproperty-drawBase: 0;
        border-bottom: 1px solid {p.border};
    }}
    QTabBar::tab {{
        background: {p.bg_app};
        color: {p.text_muted};
        border: none;
        border-right: 1px solid {p.border};
        padding: 8px 16px;
        min-width: 60px;
    }}
    QTabBar::tab:hover {{ background: {p.bg_hover}; color: {p.text}; }}
    QTabBar::tab:selected {{
        background: {p.bg_editor};
        color: {p.text};
        border-bottom: 2px solid {p.accent};
        padding-bottom: 6px;
    }}
    QTabBar::close-button {{
        image: none; subcontrol-position: right; margin: 2px; padding: 2px;
        border-radius: 4px;
    }}
    QTabBar::close-button:hover {{ background: {p.bg_active}; }}

    /* ================ Plain text edit (editor) ================ */
    QPlainTextEdit, QTextEdit {{
        background-color: {p.bg_editor};
        color: {p.text};
        border: none;
        selection-background-color: {p.selection_bg};
        selection-color: {p.text};
        font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Source Code Pro", "Ubuntu Mono", "DejaVu Sans Mono", monospace;
        font-size: 13px;
    }}

    /* ================ Inputs ================ */
    QLineEdit, QComboBox, QSpinBox {{
        background-color: {p.bg_input};
        color: {p.text};
        border: 1px solid {p.border_strong};
        border-radius: 8px;
        padding: 7px 12px;
        selection-background-color: {p.selection_bg};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border: 1px solid {p.accent};
    }}
    QComboBox::drop-down {{ border: none; width: 18px; }}
    QComboBox QAbstractItemView {{
        background: {p.bg_elevated};
        color: {p.text};
        border: 1px solid {p.border_strong};
        selection-background-color: {p.accent_subtle};
        outline: 0; padding: 4px; border-radius: 8px;
    }}

    /* ================ Buttons ================ */
    /* Default secondary button — vertical glossy gradient. The 0.5/0.51
       stop pair creates a faint horizontal "ridge" half-way down which
       gives the button its chrome / glassy feel. */
    QPushButton {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 {p.bg_elevated},
            stop:0.5 {p.bg_panel},
            stop:0.51 {p.bg_input},
            stop:1 {p.bg_app}
        );
        color: {p.text};
        border: 1px solid {p.border_strong};
        border-top: 1px solid {p.text_dim};
        border-radius: 8px;
        padding: 8px 16px;
    }}
    QPushButton:hover {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 {p.bg_hover},
            stop:0.5 {p.bg_elevated},
            stop:0.51 {p.bg_panel},
            stop:1 {p.bg_input}
        );
        border-top-color: {p.accent};
    }}
    QPushButton:pressed {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 {p.bg_active},
            stop:1 {p.bg_active}
        );
        border-top: 1px solid {p.border_strong};
    }}

    /* Default / primary button — high-contrast CTA pill with a glossy
       top highlight so it always looks freshly polished. */
    QPushButton:default,
    QPushButton[role="primary"] {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #ffffff,
            stop:0.5 {p.cta},
            stop:0.51 {p.cta},
            stop:1 {p.cta_pressed}
        );
        color: {p.cta_text};
        border: 1px solid {p.cta_pressed};
        border-top: 1px solid #ffffff;
        border-radius: 10px;
        padding: 9px 18px;
        font-weight: 800;
    }}
    QPushButton:default:hover,
    QPushButton[role="primary"]:hover {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #ffffff,
            stop:0.4 {p.cta_hover},
            stop:0.41 {p.cta},
            stop:1 {p.cta_pressed}
        );
    }}
    QPushButton:default:pressed,
    QPushButton[role="primary"]:pressed {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 {p.cta_pressed},
            stop:1 {p.cta}
        );
    }}

    /* Brand button — graphite gradient with a bright top highlight. */
    QPushButton[role="brand"] {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #b8b8b8,
            stop:0.5 {p.accent_grad_a},
            stop:0.51 {p.accent_grad_b},
            stop:1 #1a1a1a
        );
        color: #ffffff;
        border: 1px solid #1a1a1a;
        border-top: 1px solid #f0f0f0;
        border-radius: 10px;
        padding: 9px 18px;
        font-weight: 800;
    }}
    QPushButton[role="brand"]:hover {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #d4d4d4,
            stop:0.5 #5a5a5a,
            stop:0.51 #4a4a4a,
            stop:1 #262626
        );
    }}
    QPushButton[role="brand"]:pressed {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 {p.accent_grad_b},
            stop:1 {p.accent_grad_a}
        );
        border-top: 1px solid {p.accent_grad_a};
    }}

    QPushButton:disabled {{
        color: {p.text_dim};
        background: {p.bg_panel};
        border-color: {p.border};
        border-top-color: {p.border};
    }}

    /* ================ Checkboxes ================ */
    QCheckBox {{ spacing: 8px; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border-radius: 4px;
        border: 1px solid {p.border_strong};
        background: {p.bg_input};
    }}
    QCheckBox::indicator:hover {{ border-color: {p.accent}; }}
    QCheckBox::indicator:checked {{ background: {p.accent}; border-color: {p.accent}; }}

    /* ================ Scrollbars ================ */
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
    QScrollBar::handle:vertical {{
        background: {p.border_strong};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {p.text_dim}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        background: none; border: none; height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
    QScrollBar::handle:horizontal {{
        background: {p.border_strong};
        border-radius: 5px;
        min-width: 24px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {p.text_dim}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        background: none; border: none; width: 0;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

    /* ================ Card / panel ================ */
    QFrame#Card {{
        background: {p.bg_panel};
        border: 1px solid {p.border};
        border-radius: 14px;
    }}

    /* ================ Find bar ================ */
    QFrame#FindBar {{
        background: {p.bg_panel};
        border-top: 1px solid {p.border};
        border-bottom: 1px solid {p.border};
    }}
    QLabel#FindLabel {{ color: {p.text_muted}; padding: 0 4px; }}

    /* ================ Sidebar header ================ */
    QLabel[role="sidebar-title"] {{
        color: {p.text_dim};
        padding: 12px 14px 8px 14px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.5px;
    }}

    /* Generic semantic label colors */
    QLabel[role="muted"] {{ color: {p.text_muted}; }}
    QLabel[role="dim"]   {{ color: {p.text_dim}; }}
    QLabel[role="accent"] {{ color: {p.accent}; font-weight: 600; }}
    QLabel[role="success"] {{ color: {p.success}; font-weight: 600; }}
    QLabel[role="warning"] {{ color: {p.warning}; font-weight: 600; }}
    QLabel[role="error"]   {{ color: {p.error};   font-weight: 600; }}

    /* ================ Welcome ================ */
    QFrame#Welcome {{ background: {p.bg_editor}; }}
    QLabel#WelcomeTitle {{
        color: {p.text};
        font-size: 32px;
        font-weight: 700;
        letter-spacing: -0.5px;
    }}
    QLabel#WelcomeSubtitle {{
        color: {p.text_muted};
        font-size: 14px;
    }}
    QLabel#WelcomeKbd {{
        color: {p.accent};
        font-family: "JetBrains Mono", monospace;
        font-weight: 600;
    }}

    /* ================ Command palette ================ */
    QFrame#CommandPalette {{
        background: {p.bg_elevated};
        border: 1px solid {p.border_strong};
        border-radius: 12px;
    }}
    QListWidget#CommandList {{
        background: {p.bg_elevated};
        border: none;
        padding: 4px;
    }}
    QListWidget#CommandList::item {{
        padding: 9px 12px;
        border-radius: 8px;
    }}
    QListWidget#CommandList::item:selected {{
        background: {p.accent_subtle};
        color: {p.text};
    }}

    /* ================ Search panel ================ */
    QFrame#SearchPanel QLabel[role="match-file"] {{
        color: {p.accent};
        font-weight: 600;
    }}
    QFrame#SearchPanel QLabel[role="match-count"] {{
        color: {p.text_dim};
    }}

    /* ================ Terminal ================ */
    QFrame#Terminal {{
        background: {p.bg_panel};
        border-top: 1px solid {p.border};
    }}
    QPlainTextEdit#TerminalView {{
        background: {p.bg_panel};
        color: {p.text};
        border: none;
        font-family: "JetBrains Mono", "Fira Code", "Source Code Pro", "Ubuntu Mono", monospace;
        font-size: 12.5px;
        padding: 8px 12px;
    }}
    QLineEdit#TerminalInput {{
        background: {p.bg_panel};
        border: none;
        border-top: 1px solid {p.border};
        border-radius: 0;
        padding: 8px 12px;
        font-family: "JetBrains Mono", "Fira Code", "Source Code Pro", "Ubuntu Mono", monospace;
    }}
    QLineEdit#TerminalInput:focus {{
        border: none;
        border-top: 1px solid {p.accent};
    }}
    QLabel#TerminalPrompt {{
        color: {p.cta};
        font-family: "JetBrains Mono", monospace;
        font-weight: 700;
        padding: 0 6px 0 12px;
    }}
    QLabel#TerminalCwd {{
        color: {p.text_muted};
        font-family: "JetBrains Mono", monospace;
    }}

    /* ================ Minimap ================ */
    QWidget#Minimap {{
        background: {p.bg_editor};
        border-left: 1px solid {p.border};
    }}

    /* ================ AI panel ================ */
    QFrame#AIPanel {{
        background: {p.bg_sidebar};
        border-right: 1px solid {p.border};
    }}
    QFrame#AIPanel QLabel#AITitle {{
        color: {p.text};
        font-weight: 700;
        font-size: 13px;
        padding: 12px 14px 4px 14px;
        letter-spacing: 0.5px;
    }}
    QFrame#AIPanel QLabel#AISubtitle {{
        color: {p.text_dim};
        padding: 0 14px 8px 14px;
        font-size: 11px;
    }}
    QFrame#AIPanel QFrame#AIToolbar {{
        background: {p.bg_sidebar};
        border-bottom: 1px solid {p.border};
    }}
    QFrame#AIPanel QFrame#AIInputRow {{
        background: {p.bg_sidebar};
        border-top: 1px solid {p.border};
    }}
    QFrame#AIPanel QScrollArea#AIChat {{
        background: {p.bg_sidebar};
        border: none;
    }}
    QFrame#AIPanel QScrollArea#AIChat > QWidget > QWidget {{
        background: {p.bg_sidebar};
    }}

    /* Empty-state card (shown when chat is empty) */
    QFrame#AIEmpty {{
        background: {p.bg_panel};
        border: 1px solid {p.border};
        border-radius: 14px;
    }}
    QFrame#AIEmpty QLabel#AIEmptyTitle {{
        color: {p.text};
        font-size: 15px;
        font-weight: 700;
    }}
    QFrame#AIEmpty QLabel#AIEmptyBody {{
        color: {p.text_muted};
        font-size: 12px;
    }}

    /* User bubble — right-aligned, accent gradient */
    QFrame#BubbleUser {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {p.accent_grad_a}, stop:1 {p.accent_grad_b}
        );
        border-radius: 12px;
    }}
    QFrame#BubbleUser QTextBrowser, QFrame#BubbleUser QLabel {{
        background: transparent;
        color: white;
        border: none;
        font-size: 13px;
    }}

    /* Assistant bubble — left-aligned, panel background */
    QFrame#BubbleAssistant {{
        background: {p.bg_panel};
        border: 1px solid {p.border};
        border-radius: 12px;
    }}
    QFrame#BubbleAssistant QTextBrowser, QFrame#BubbleAssistant QLabel {{
        background: transparent;
        color: {p.text};
        border: none;
        font-size: 13px;
    }}
    QFrame#BubbleAssistant QLabel#BubbleRole {{
        color: {p.accent};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    QFrame#BubbleAssistant QPushButton#BubbleAction {{
        background: transparent;
        color: {p.text_dim};
        border: none;
        padding: 2px 6px;
        border-radius: 6px;
    }}
    QFrame#BubbleAssistant QPushButton#BubbleAction:hover {{
        background: {p.bg_hover};
        color: {p.text};
    }}

    /* Composer (input area) */
    QPlainTextEdit#AIInput {{
        background: {p.bg_input};
        color: {p.text};
        border: 1px solid {p.border_strong};
        border-radius: 10px;
        padding: 8px 10px;
        font-family: "Inter", "Segoe UI", "Cantarell", sans-serif;
        font-size: 13px;
    }}
    QPlainTextEdit#AIInput:focus {{ border: 1px solid {p.accent}; }}

    /* Send button — glossy graphite pill */
    QPushButton#AISend {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #d4d4d4,
            stop:0.5 #5a5a5a,
            stop:0.51 #424242,
            stop:1 #1a1a1a
        );
        color: #ffffff;
        border: 1px solid #1a1a1a;
        border-top: 1px solid #f5f5f5;
        border-radius: 10px;
        padding: 8px 14px;
        font-weight: 800;
    }}
    QPushButton#AISend:hover {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #ffffff,
            stop:0.5 #707070,
            stop:0.51 #525252,
            stop:1 #262626
        );
    }}
    QPushButton#AISend:pressed {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #2a2a2a, stop:1 #525252
        );
    }}
    QPushButton#AISend:disabled {{
        background: {p.bg_panel};
        color: {p.text_dim};
        border-top: 1px solid {p.border};
    }}
    QPushButton#AIStop {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #ffd5d5,
            stop:0.5 {p.bg_panel},
            stop:0.51 {p.bg_panel},
            stop:1 {p.bg_app}
        );
        color: {p.error};
        border: 1px solid {p.error};
        border-top: 1px solid #ffb0b0;
        border-radius: 10px;
        padding: 8px 14px;
        font-weight: 800;
    }}
    QPushButton#AIStop:hover {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #ff8080, stop:0.5 {p.error}, stop:1 #aa0000
        );
        color: white;
    }}

    /* Context chip (shows whether current file is included) */
    QPushButton#AIContextChip {{
        background: {p.bg_input};
        color: {p.text_muted};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 4px 10px;
        font-size: 11px;
        font-weight: 600;
    }}
    QPushButton#AIContextChip:checked {{
        background: {p.accent_subtle};
        color: {p.accent};
        border-color: {p.accent};
    }}
    QPushButton#AIContextChip:hover {{
        border-color: {p.accent};
    }}

    QLabel#AIStatus {{
        color: {p.text_dim};
        font-size: 11px;
        padding: 0 14px 8px 14px;
    }}
    """


__all__ = [
    "Palette", "DARK", "LIGHT", "PALETTES", "PALETTE",
    "stylesheet", "set_active", "active_name",
]
