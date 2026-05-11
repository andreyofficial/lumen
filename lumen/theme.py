"""Themed palettes (Dark + Light) and Qt Style Sheet generator.

The chrome (UI surfaces, buttons, sidebars) keeps its monochrome
black/white look — but the **code itself** is fully coloured. Every
syntax token gets its own hue so the editor reads at a glance: keywords,
strings, numbers, functions, classes, types, etc. all carry meaning by
colour. Hero buttons use a glossy gradient + a soft outer glow halo
(see ``lumen.shine.ShineButton``) for the FileHub-style polished look.

The palettes are intentionally **eye-friendly**: the dark theme uses a
warm dark grey (never pure ``#000000``) with off-white text to avoid
halation on modern displays, and the light theme uses a warm off-white
cream rather than pure white. Syntax colours are pastel-leaning so
they stay legible without "glowing" at the reader.
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
    # PyCharm-style Run accent — a single small allowance for green
    # so the play button stays recognisable on a monochrome toolbar.
    run_action: str
    run_action_hover: str
    run_action_pressed: str

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


# ---------------- Dark — warm dark grey, eye-friendly ----------------

DARK = Palette(
    name="dark",

    # Warm dark grey instead of pure #000 to avoid halation on OLED /
    # high-contrast displays. The whole surface ramp keeps a tiny blue
    # tint so it reads as "dark" rather than "muddy brown".
    bg_app="#1a1a1d",
    bg_sidebar="#1f1f23",
    bg_editor="#1d1d20",
    bg_panel="#212126",
    bg_elevated="#27272d",
    bg_hover="#2d2d34",
    bg_active="#33333a",
    bg_input="#1f1f23",

    border="#2a2a30",
    border_strong="#393944",
    divider="#252529",

    # Off-white text (not pure #fff) drops the contrast ratio from
    # ~21:1 to a still-comfortably-AAA ~12:1 — way easier on the eyes
    # over long sessions.
    text="#d4d4d4",
    text_muted="#909096",
    text_dim="#6a6a72",
    text_inverse="#1a1a1d",

    # Accent ramp is soft off-white so highlights don't punch.
    accent="#e8e8ec",
    accent_hover="#d4d4d8",
    accent_pressed="#bcbcc4",
    accent_subtle="#2a2a30",
    accent2="#a8a8b0",
    # Graphite gradient — used for the brand button & AI user bubble.
    accent_grad_a="#3a3a42",
    accent_grad_b="#5c5c66",

    # Primary CTA: soft white pill with dark text (inverse).
    cta="#e8e8ec",
    cta_hover="#d4d4d8",
    cta_pressed="#bcbcc4",
    cta_text="#1a1a1d",

    # Semantic — neutral grays with a desaturated red for danger so
    # destructive states stay unambiguous without screaming.
    info="#a8a8b0",
    success="#cfcfd6",
    warning="#bcbcc4",
    error="#d9685c",
    # PyCharm-style soft sage green for the Run pill — same family as
    # the string-literal syntax colour so it doesn't fight the palette.
    run_action="#7eb56c",
    run_action_hover="#94c280",
    run_action_pressed="#629158",

    line_number_bg="#1a1a1d",
    line_number_fg="#4a4a52",
    line_number_fg_active="#d4d4d4",
    current_line_bg="#26262c",
    selection_bg="#3d3d46",
    selection_inactive_bg="#28282e",
    matching_bracket_bg="#3d3645",
    indent_guide="#2a2a30",

    # Pastel-leaning syntax palette. Each token type still owns a hue
    # (keyword vs string vs function) but the saturation is tuned so
    # the editor reads like a printed page, not a neon sign.
    syn_comment="#6a737d",     # muted slate (italic)
    syn_keyword="#c586c0",     # soft magenta (bold)
    syn_keyword2="#9b8ed8",    # muted lavender (italic) — self / cls
    syn_string="#a9c97b",      # sage green
    syn_number="#d4a574",      # warm amber
    syn_function="#7eb8d6",    # steel blue (bold)
    syn_class="#dcbe6f",       # warm gold (bold)
    syn_decorator="#c98aaf",   # muted rose (italic)
    syn_operator="#c586c0",    # soft magenta
    syn_constant="#a18cd1",    # soft purple (bold)
    syn_type="#7fc8c0",        # sea teal
    syn_tag="#c98aaf",         # rose (bold)
    syn_attribute="#bdb1d8",   # dusty violet
    syn_punct="#a9b2c0",       # slate
    syn_heading="#e0e0e0",     # bold soft white
    syn_link="#7eb8d6",        # steel blue
)


# ---------------- Light — warm cream off-white, eye-friendly ----------------

LIGHT = Palette(
    name="light",

    # Warm cream off-white instead of pure #fff to avoid the "snow
    # blindness" effect of staring into a max-luminance screen.
    bg_app="#fbfbf8",
    bg_sidebar="#f4f4f0",
    bg_editor="#fbfbf8",
    bg_panel="#ffffff",
    bg_elevated="#f9f9f5",
    bg_hover="#eeeee8",
    bg_active="#e3e3dc",
    bg_input="#f4f4f0",

    border="#e0e0d8",
    border_strong="#c8c8c0",
    divider="#ededec",

    # Soft "ink" instead of pure black for the body text.
    text="#2c2c30",
    text_muted="#5c5c66",
    text_dim="#8a8a92",
    text_inverse="#fbfbf8",

    accent="#2c2c30",
    accent_hover="#1a1a1d",
    accent_pressed="#0d0d10",
    accent_subtle="#ededec",
    accent2="#5c5c66",
    accent_grad_a="#3a3a42",
    accent_grad_b="#5c5c66",

    cta="#2c2c30",
    cta_hover="#1a1a1d",
    cta_pressed="#0d0d10",
    cta_text="#fbfbf8",

    info="#5c5c66",
    success="#3a3a42",
    warning="#5c5c66",
    error="#b85a52",
    # Forest green — same family as the string-literal colour in the
    # light theme. Pops on cream without screaming.
    run_action="#3f7d2a",
    run_action_hover="#326322",
    run_action_pressed="#28501b",

    line_number_bg="#fbfbf8",
    line_number_fg="#c8c8c0",
    line_number_fg_active="#2c2c30",
    current_line_bg="#f3f3ee",
    selection_bg="#d4d4cc",
    selection_inactive_bg="#e3e3dc",
    matching_bracket_bg="#d4d0e0",
    indent_guide="#ededec",

    # Desaturated syntax palette for the cream background. Same
    # semantic mapping as the dark theme — every hue is tuned for
    # legibility rather than punch.
    syn_comment="#7d808d",     # soft slate (italic)
    syn_keyword="#a32b9e",     # softer magenta (bold)
    syn_keyword2="#6b3aac",    # muted violet (italic) — self / cls
    syn_string="#3f7d2a",      # forest green
    syn_number="#9d5408",      # warm amber
    syn_function="#1e6b8a",    # deep steel teal (bold)
    syn_class="#7d3a08",       # dark gold (bold)
    syn_decorator="#9c2d5a",   # deep rose (italic)
    syn_operator="#a32b9e",    # softer magenta
    syn_constant="#5d2eb5",    # soft violet (bold)
    syn_type="#0d7d70",        # deep teal
    syn_tag="#9c2d5a",         # deep rose (bold)
    syn_attribute="#3f3aaf",   # softer indigo
    syn_punct="#475569",       # slate
    syn_heading="#1a1a1d",     # bold soft black
    syn_link="#0e6d8a",        # deep cyan
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

    /* ================ PyCharm-style Run pill (right side of toolbar) ================
       A grouped "Run: <current file> [▶] [■]" widget. The file label
       sits inside a soft chip; the play button is the one place we
       allow a green accent so the run target is unmistakable. */
    QFrame#RunPill {{
        background: {p.bg_input};
        border: 1px solid {p.border};
        border-radius: 10px;
        padding: 2px 4px 2px 10px;
    }}
    QLabel#RunPillLabel {{
        color: {p.text_muted};
        background: transparent;
        font-weight: 600;
        font-size: 12px;
        padding: 0 6px;
    }}
    QLabel#RunPillLabel[role="empty"] {{
        color: {p.text_dim};
        font-style: italic;
        font-weight: 400;
    }}
    QToolButton#RunPillPlay {{
        background: transparent;
        color: {p.run_action};
        border: none;
        padding: 4px 6px;
        border-radius: 8px;
    }}
    QToolButton#RunPillPlay:hover {{
        background: {p.bg_hover};
        color: {p.run_action_hover};
    }}
    QToolButton#RunPillPlay:pressed {{
        background: {p.bg_active};
        color: {p.run_action_pressed};
    }}
    QToolButton#RunPillStop {{
        background: transparent;
        color: {p.error};
        border: none;
        padding: 4px 6px;
        border-radius: 8px;
    }}
    QToolButton#RunPillStop:hover {{
        background: {p.bg_hover};
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

    /* Debug- and Scan-mode toggles — sit flush-left on the composer row.
       Lit-up when on so the user always sees the active mode. */
    QPushButton#AIDebugToggle, QPushButton#AIScanToggle {{
        background: {p.bg_input};
        color: {p.text_muted};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 4px 10px 4px 8px;
        font-size: 11px;
        font-weight: 600;
    }}
    QPushButton#AIDebugToggle:hover, QPushButton#AIScanToggle:hover {{
        border-color: {p.accent};
        color: {p.text};
    }}
    QPushButton#AIDebugToggle:checked, QPushButton#AIScanToggle:checked {{
        background: {p.accent_subtle};
        color: {p.accent};
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
