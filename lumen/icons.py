"""Inline SVG icons rendered to QIcon — keeps the app self-contained."""

from __future__ import annotations

from PyQt6.QtCore import QByteArray, QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

from .theme import PALETTE

_SVGS: dict[str, str] = {
    "logo": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'>
          <rect x='2' y='2' width='20' height='20' rx='6' fill='#000000'/>
          <rect x='2.5' y='2.5' width='19' height='19' rx='5.5' fill='none'
                stroke='#ffffff' stroke-opacity='0.18' stroke-width='1'/>
          <path fill='#ffffff'
                d='M7 7h2v8h4v2H7V7Zm6 0h4l3 5-3 5h-4V7Zm2 2v6h1.4l1.6-3-1.6-3H15Z'/>
        </svg>
    """,
    "new": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z'/>
          <path d='M14 3v5h5'/>
          <path d='M12 12v6M9 15h6'/>
        </svg>
    """,
    "open": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z'/>
        </svg>
    """,
    "save": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M5 3h11l3 3v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z'/>
          <path d='M7 3v6h9V3'/>
          <path d='M7 14h10v6H7z'/>
        </svg>
    """,
    "folder": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z'/>
        </svg>
    """,
    "file": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z'/>
          <path d='M14 3v5h5'/>
        </svg>
    """,
    "find": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <circle cx='11' cy='11' r='7'/>
          <path d='m20 20-3.5-3.5'/>
        </svg>
    """,
    "undo": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M9 14 4 9l5-5'/>
          <path d='M4 9h10a6 6 0 0 1 0 12h-3'/>
        </svg>
    """,
    "redo": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='m15 14 5-5-5-5'/>
          <path d='M20 9H10a6 6 0 0 0 0 12h3'/>
        </svg>
    """,
    "settings": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <circle cx='12' cy='12' r='3'/>
          <path d='M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3h.1a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z'/>
        </svg>
    """,
    "close": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M18 6 6 18M6 6l12 12'/>
        </svg>
    """,
    "palette": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M4 6h16M4 12h10M4 18h16'/>
        </svg>
    """,
    "play": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='{c}'>
          <path d='M8 5v14l11-7z'/>
        </svg>
    """,
    "search": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <circle cx='11' cy='11' r='7'/>
          <path d='m20 20-3.5-3.5'/>
        </svg>
    """,
    "terminal": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <rect x='3' y='4' width='18' height='16' rx='2'/>
          <path d='m7 9 3 3-3 3'/>
          <path d='M13 15h4'/>
        </svg>
    """,
    "sun": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <circle cx='12' cy='12' r='4'/>
          <path d='M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41'/>
        </svg>
    """,
    "moon": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z'/>
        </svg>
    """,
    "explorer": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M3 6h6l2 2h10v10a2 2 0 0 1-2 2H3z'/>
        </svg>
    """,
    "trash": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2'/>
          <path d='M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6'/>
          <path d='M10 11v6M14 11v6'/>
        </svg>
    """,
    "chevron-down": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
          <path d='m6 9 6 6 6-6'/>
        </svg>
    """,
    "chevron-right": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
          <path d='m9 6 6 6-6 6'/>
        </svg>
    """,
    "sparkles": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1'/>
          <path d='M12 8.5 13.4 11l2.6.7L14 13.5l.4 2.7L12 14.9l-2.4 1.3.4-2.7-2-1.8 2.6-.7Z' fill='{c}' stroke='none'/>
        </svg>
    """,
    "send": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='{c}'>
          <path d='M3.4 2.5a1 1 0 0 0-1.3 1.3l3 7.2L13 12l-7.9 1L2.1 20.2a1 1 0 0 0 1.4 1.2l18-9a1 1 0 0 0 0-1.8Z'/>
        </svg>
    """,
    "stop": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='{c}'>
          <rect x='5' y='5' width='14' height='14' rx='3'/>
        </svg>
    """,
    "copy": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <rect x='9' y='9' width='12' height='12' rx='2'/>
          <path d='M5 15V5a2 2 0 0 1 2-2h10'/>
        </svg>
    """,
    "refresh": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M3 12a9 9 0 0 1 15.5-6.3L21 8'/>
          <path d='M21 3v5h-5'/>
          <path d='M21 12a9 9 0 0 1-15.5 6.3L3 16'/>
          <path d='M3 21v-5h5'/>
        </svg>
    """,
    "history": """
        <svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' fill='none'
             stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M3 12a9 9 0 1 0 3-6.7L3 8'/>
          <path d='M3 3v5h5'/>
          <path d='M12 7v5l3 2'/>
        </svg>
    """,
}


def _render(svg: str, size: int, color: str) -> QPixmap:
    data = QByteArray(svg.replace("{c}", color).encode("utf-8"))
    renderer = QSvgRenderer(data)
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter)
    painter.end()
    return pix


def icon(name: str, color: str | None = None, size: int = 18) -> QIcon:
    """Return a QIcon for the given name. Pass color to override default."""
    svg = _SVGS.get(name)
    if svg is None:
        return QIcon()
    c = color or PALETTE.text_muted
    qicon = QIcon()
    for s in (size, size * 2):
        qicon.addPixmap(_render(svg, s, c))
    # Active/selected state — accent color
    for s in (size, size * 2):
        qicon.addPixmap(_render(svg, s, PALETTE.accent), QIcon.Mode.Active)
        qicon.addPixmap(_render(svg, s, PALETTE.accent), QIcon.Mode.Selected)
    return qicon


def app_icon(size: int = 128) -> QIcon:
    """Render the gradient logo (color arg is ignored — gradient is baked in)."""
    qicon = QIcon()
    for s in (32, 64, 128, 256):
        qicon.addPixmap(_render(_SVGS["logo"], s, PALETTE.accent))
    return qicon


def logo_pixmap(size: int = 64) -> QPixmap:
    """Plain gradient logo pixmap for use inline (welcome screen, etc.)."""
    return _render(_SVGS["logo"], size, PALETTE.accent)


def pixmap(name: str, size: int = 18, color: str | None = None) -> QPixmap:
    svg = _SVGS.get(name, "")
    return _render(svg, size, color or PALETTE.text_muted)


__all__ = ["icon", "app_icon", "pixmap"]
