#!/usr/bin/env bash
set -euo pipefail
rm -f "${HOME}/.local/bin/lumen"
rm -f "${HOME}/.local/share/icons/hicolor/scalable/apps/lumen.svg"
rm -f "${HOME}/.local/share/applications/lumen.desktop"
command -v update-desktop-database >/dev/null 2>&1 \
    && update-desktop-database "${HOME}/.local/share/applications" || true
echo "Lumen removed from ~/.local."
