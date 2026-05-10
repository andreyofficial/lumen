#!/usr/bin/env bash
# Build a standalone Linux executable for Lumen using PyInstaller.
#
# Usage:
#   ./build.sh                # one-folder build at  dist/lumen/  (faster startup)
#   ./build.sh --onefile      # single binary at     dist/lumen   (one file, slower startup)
#   ./build.sh --clean        # remove previous build/ and dist/ first
#
# The result is a self-contained app — users do NOT need Python or PyQt6 installed.
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
ROOT="$(pwd)"

ONEFILE=0
CLEAN=0
for arg in "$@"; do
    case "$arg" in
        --onefile) ONEFILE=1 ;;
        --onedir)  ONEFILE=0 ;;
        --clean)   CLEAN=1 ;;
        -h|--help)
            sed -n '2,12p' "$0" | sed 's/^# *//'
            exit 0
            ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

VENV_DIR=".buildvenv"
PYTHON=${PYTHON:-python3}

if [[ ! -d "$VENV_DIR" ]]; then
    echo "==> Creating build virtualenv in $VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Installing build dependencies"
pip install --upgrade pip >/dev/null
pip install -q -r requirements.txt
pip install -q "pyinstaller>=6.4"

if [[ "$CLEAN" == "1" ]]; then
    echo "==> Cleaning previous build/ and dist/"
    rm -rf build dist
fi

export LUMEN_SPECPATH="$ROOT"
if [[ "$ONEFILE" == "1" ]]; then
    export LUMEN_ONEFILE=1
    echo "==> Building one-file executable (this can take a few minutes)"
else
    unset LUMEN_ONEFILE
    echo "==> Building one-folder app bundle (this can take a few minutes)"
fi

pyinstaller --noconfirm --clean lumen.spec

echo
if [[ "$ONEFILE" == "1" ]]; then
    BIN="$ROOT/dist/lumen"
    echo "Built single binary:  $BIN"
    file "$BIN" || true
    du -h "$BIN" | awk '{print "Size:                 " $1}'
    echo
    echo "Run it with:          $BIN"
else
    BIN="$ROOT/dist/lumen/lumen"
    echo "Built application folder: $ROOT/dist/lumen"
    echo "Launcher binary:          $BIN"
    du -sh "$ROOT/dist/lumen" | awk '{print "Total size:               " $1}'
    echo
    echo "Run it with:              $BIN"
    echo "Distribute:               tar czf lumen-linux.tar.gz -C dist lumen"
fi
