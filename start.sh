#!/usr/bin/env sh
# Start MarkItDown Web with whichever Python setup is available:
# uv, then .venv, then the md_webui Conda environment, then a new .venv.
set -e
cd "$(dirname "$0")"
CHECK='import sys, markitdown, fastapi, uvicorn; sys.exit(not (3, 10) <= sys.version_info[:2] <= (3, 13))'

if command -v uv >/dev/null 2>&1; then
    echo "Using uv."
    exec uv run --no-dev python run.py
fi

if [ ! -x .venv/bin/python ]; then
    if command -v conda >/dev/null 2>&1 && conda run -n md_webui python -c "$CHECK" >/dev/null 2>&1; then
        echo "Using Conda environment md_webui."
        exec conda run -n md_webui --no-capture-output python run.py
    fi
    if ! command -v python3 >/dev/null 2>&1 \
        || ! python3 -c 'import sys; sys.exit(not (3, 10) <= sys.version_info[:2] <= (3, 13))'; then
        echo "Python 3.10 to 3.13 was not found. Install uv or Python, then run this file again." >&2
        exit 1
    fi
    echo "Creating .venv."
    python3 -m venv .venv
else
    echo "Using .venv."
fi

if ! .venv/bin/python -c "$CHECK" >/dev/null 2>&1; then
    echo "Installing dependencies."
    .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python run.py
