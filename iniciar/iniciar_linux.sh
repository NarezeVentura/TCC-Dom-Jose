#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    if command -v python3 >/dev/null 2>&1; then
        python3 -m venv "$PROJECT_DIR/.venv"
    elif command -v python >/dev/null 2>&1; then
        python -m venv "$PROJECT_DIR/.venv"
    else
        echo "Python 3 nao foi encontrado. Instale Python 3 e tente novamente."
        exit 1
    fi
fi

"$VENV_PYTHON" -m pip install -r "$PROJECT_DIR/requirements.txt"
xdg-open "http://127.0.0.1:5000" >/dev/null 2>&1 &
exec "$VENV_PYTHON" "$PROJECT_DIR/app.py"
