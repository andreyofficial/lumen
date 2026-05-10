#!/usr/bin/env python3
"""Generate hicolor PNG rasters for the Lumen taskbar icon.

Reads ``assets/lumen.svg`` and writes a PNG into ``assets/icons/{N}x{N}/lumen.png``
for every standard XDG hicolor size. Re-run this whenever the SVG
changes; ``install.sh`` copies the resulting tree into
``~/.local/share/icons/hicolor/`` so the WM has a crisp pixmap at every
size it might ask for (taskbar, dock, Alt-Tab, tray, notifications…).

Usage:
    .buildvenv/bin/python gen_icons.py
"""

from __future__ import annotations

import os
import sys

# Standard hicolor sizes used by Linux desktops.
SIZES = (16, 22, 24, 32, 48, 64, 96, 128, 192, 256, 512)


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "assets", "lumen.svg")
    out_root = os.path.join(here, "assets", "icons")
    if not os.path.isfile(src):
        print(f"missing source: {src}", file=sys.stderr)
        return 2

    # Use Qt's SVG renderer so we never depend on rsvg / inkscape being
    # installed on the host.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtCore import QByteArray, Qt
    from PyQt6.QtGui import QPainter, QPixmap
    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    with open(src, "rb") as f:
        svg_bytes = f.read()
    renderer = QSvgRenderer(QByteArray(svg_bytes))
    if not renderer.isValid():
        print("invalid SVG source", file=sys.stderr)
        return 3

    for size in SIZES:
        out_dir = os.path.join(out_root, f"{size}x{size}")
        os.makedirs(out_dir, exist_ok=True)
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        renderer.render(painter)
        painter.end()
        out_path = os.path.join(out_dir, "lumen.png")
        if not pix.save(out_path, "PNG"):
            print(f"failed to write {out_path}", file=sys.stderr)
            return 4
        print(f"wrote {out_path}")

    print(f"\n{len(SIZES)} hicolor sizes generated under {out_root}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
