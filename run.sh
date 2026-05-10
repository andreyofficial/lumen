#!/usr/bin/env bash
# Lumen launcher — sets up a venv on first run, installs deps, and starts the app.
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

VENV_DIR=".venv"
PYTHON=${PYTHON:-python3}

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment in $VENV_DIR …"
    "$PYTHON" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if ! python -c "import PyQt6" >/dev/null 2>&1; then
    echo "Installing dependencies …"
    pip install --upgrade pip >/dev/null
    pip install -r requirements.txt
fi

exec python -m lumen "$@"
