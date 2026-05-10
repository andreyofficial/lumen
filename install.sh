#!/usr/bin/env bash
# Install Lumen into the current user's desktop environment.
# Creates a launcher in ~/.local/bin, installs the icon, and registers a .desktop entry.
#
# If a PyInstaller build exists at dist/lumen/lumen, that binary is used as the
# launcher target (no Python install required to run). Otherwise the run.sh
# wrapper is used (which sets up a venv on first launch).
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
ROOT="$(pwd)"

BIN_DIR="${HOME}/.local/bin"
ICON_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
APP_DIR="${HOME}/.local/share/applications"

mkdir -p "$BIN_DIR" "$ICON_DIR" "$APP_DIR"

if [[ -x "$ROOT/dist/lumen/lumen" ]]; then
    LAUNCH_TARGET="$ROOT/dist/lumen/lumen"
    echo "Using prebuilt binary at $LAUNCH_TARGET"
else
    chmod +x "$ROOT/run.sh"
    LAUNCH_TARGET="$ROOT/run.sh"
    echo "No prebuilt binary found — falling back to $LAUNCH_TARGET"
    echo "Tip: run ./build.sh to produce a standalone executable first."
fi

cat > "$BIN_DIR/lumen" <<EOF
#!/usr/bin/env bash
exec "$LAUNCH_TARGET" "\$@"
EOF
chmod +x "$BIN_DIR/lumen"

# Install icon
cp "$ROOT/assets/lumen.svg" "$ICON_DIR/lumen.svg"

# Install desktop entry (substitute paths)
sed \
    -e "s|__EXEC__|$BIN_DIR/lumen %F|g" \
    -e "s|__ICON__|lumen|g" \
    "$ROOT/lumen.desktop" > "$APP_DIR/lumen.desktop"
chmod 644 "$APP_DIR/lumen.desktop"

# Refresh desktop / icon caches when available
command -v update-desktop-database >/dev/null 2>&1 \
    && update-desktop-database "$APP_DIR" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 \
    && gtk-update-icon-cache -t "${HOME}/.local/share/icons/hicolor" || true

cat <<EOF

Lumen installed.

  Launch:        lumen          (ensure ~/.local/bin is in PATH)
  Desktop entry: $APP_DIR/lumen.desktop
  Icon:          $ICON_DIR/lumen.svg

Run \`run.sh\` directly from this folder if you don't want a system-wide install.
EOF
