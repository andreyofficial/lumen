"""Linux desktop integration helpers — taskbar / dock icon registration.

When Lumen first runs, this module copies the bundled hicolor PNG icons
into the user's ``~/.local/share/icons/hicolor/`` tree (creating the
size buckets as needed) and refreshes the GTK icon cache. This makes
the Lumen icon appear in the taskbar / dock / Alt-Tab switcher
*without* the user having to run ``install.sh``.

It's a no-op on non-Linux platforms and silently skips any size whose
target file already exists with the same byte length (idempotent and
cheap on every subsequent launch).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _bundled_icons_root() -> Path | None:
    """Return the directory holding ``<size>x<size>/lumen.png`` PNGs.

    Resolves to the right place whether we're running from source, from
    a PyInstaller one-folder bundle, or from a one-file bundle (whose
    extraction dir is exposed via ``sys._MEIPASS``).
    """
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "assets" / "icons")
    # Source layout: <repo>/assets/icons.
    here = Path(__file__).resolve().parent
    candidates.append(here.parent / "assets" / "icons")
    # PyInstaller one-folder layout: <dist>/lumen/_internal/assets/icons.
    candidates.append(here.parent.parent / "_internal" / "assets" / "icons")
    for c in candidates:
        if c.is_dir():
            return c
    return None


def _user_hicolor_root() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return Path(base) / "icons" / "hicolor"


def _files_match(src: Path, dst: Path) -> bool:
    try:
        return src.stat().st_size == dst.stat().st_size
    except OSError:
        return False


def ensure_taskbar_icon_installed() -> bool:
    """Copy the bundled hicolor PNGs into the user icon theme directory.

    Returns ``True`` when at least one new file was written (so the
    caller can decide to refresh the icon cache). Failures are
    swallowed — this function is best-effort.
    """
    if sys.platform != "linux":
        return False

    src_root = _bundled_icons_root()
    if src_root is None:
        return False

    dst_root = _user_hicolor_root()
    written = False
    for size_dir in sorted(src_root.iterdir()):
        png = size_dir / "lumen.png"
        if not png.is_file():
            continue
        target_dir = dst_root / size_dir.name / "apps"
        target = target_dir / "lumen.png"
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        if target.exists() and _files_match(png, target):
            continue
        try:
            shutil.copyfile(png, target)
            written = True
        except OSError:
            continue

    # Drop the scalable SVG too if missing — same logic.
    bundled_svg = (src_root.parent / "lumen.svg")
    if bundled_svg.is_file():
        scalable_target = dst_root / "scalable" / "apps" / "lumen.svg"
        try:
            scalable_target.parent.mkdir(parents=True, exist_ok=True)
            if (
                not scalable_target.exists()
                or not _files_match(bundled_svg, scalable_target)
            ):
                shutil.copyfile(bundled_svg, scalable_target)
                written = True
        except OSError:
            pass

    if written:
        # Refresh the icon cache so the taskbar / dock notice the new
        # files immediately. Both calls are best-effort.
        try:
            subprocess.run(
                ["gtk-update-icon-cache", "-tq", str(dst_root)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=4,
            )
        except (OSError, subprocess.SubprocessError):
            pass

    return written


__all__ = ["ensure_taskbar_icon_installed"]
