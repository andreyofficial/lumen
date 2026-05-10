"""Standalone entry point for Lumen — used by PyInstaller and `python main.py`."""

from __future__ import annotations

import sys


def _main() -> int:
    from lumen.app import run
    return run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(_main())
