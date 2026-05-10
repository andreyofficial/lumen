#!/usr/bin/env bash
set -euo pipefail
rm -f "${HOME}/.local/bin/lumen"
rm -f "${HOME}/.local/share/icons/hicolor/scalable/apps/lumen.svg"
# Remove every per-size PNG copy installed by install.sh.
for sz in 16x16 22x22 24x24 32x32 48x48 64x64 96x96 128x128 192x192 256x256 512x512; do
    rm -f "${HOME}/.local/share/icons/hicolor/${sz}/apps/lumen.png"
done
rm -f "${HOME}/.local/share/applications/lumen.desktop"
command -v update-desktop-database >/dev/null 2>&1 \
    && update-desktop-database "${HOME}/.local/share/applications" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 \
    && gtk-update-icon-cache -t "${HOME}/.local/share/icons/hicolor" || true
echo "Lumen removed from ~/.local."
