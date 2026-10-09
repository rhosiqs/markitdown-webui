# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                                   # create/update .venv with dev tools
uv run pytest                             # all tests
uv run pytest tests/test_app.py::test_health   # single test
uv run ruff check .                       # lint
./start.sh                                # run the app (start.bat on Windows)
```

The app serves at `http://localhost:8765`; `run.py` falls back to the next free port if 8765 is busy. `MARKITDOWN_WEB_PORT` and `MARKITDOWN_WEB_MAX_MB` (1–512, default 64) override defaults.

## Dependencies and Python version

- `pyproject.toml` + `uv.lock` are the source of truth. `requirements.txt` and `requirements-dev.txt` are generated exports used by the venv and Conda paths (`environment.yml` → env `md_webui`, `environment-dev.yml` → `md_webui-dev`). After changing dependencies: `uv lock`, then regenerate both files with the `uv export` command recorded in their headers.
- Python is capped at 3.10–3.13 (`.python-version` pins 3.12 for uv) because `onnxruntime`, pulled in by `markitdown` → `magika`, has no 3.14 wheels in the locked version. Keep the cap consistent across `pyproject.toml`, both Conda files, and both launchers.
- `start.bat` / `start.sh` pick the first available setup: uv → existing `.venv` → Conda `md_webui` → create `.venv` from a system Python. `.gitattributes` forces LF everywhere except `*.bat` (CRLF, required by cmd.exe).

## Architecture

Local-only FastAPI app (binds `127.0.0.1`) wrapping Microsoft MarkItDown, with a framework-free browser frontend.

- `app/main.py`: routes and security headers. `POST /api/convert` reads the upload in memory with a size cap, validates name/extension (`app/security.py`), and runs `convert_bytes` in a thread. `POST /api/render` turns edited Markdown into HTML for the live preview.
- `app/converter.py`: calls `MarkItDown.convert_stream()` on a `BytesIO`; uploads are never written to disk. Large PDFs can take minutes (pdfplumber page pass plus a pdfminer pass); pdfminer warnings are silenced here.
- `app/preview.py`: markdown-it with raw HTML disabled, then Bleach with an allowlist. All preview HTML goes through this server-side sanitizer; the frontend inserts it as-is.
- `app/static/app.js` + `app/templates/index.html`: the whole UI. The strict CSP in `main.py` forbids inline scripts and styles, so all JS/CSS must live in `app/static/`. `main.py` registers `.js`/`.css` MIME types explicitly because the Windows registry can map `.js` to `text/plain`, which the `nosniff` header then blocks.

## UI language

- The UI defaults to en-US; zh-TW is available via the language switch. Strings live in the `translations` object in `app.js`, and every `data-i18n` key in `index.html` needs both locales. The English fallback text in `index.html` and the en-US block must contain no CJK characters (enforced by `tests/test_app.py`).
- Server error messages are English.
- There is intentionally no status banner or spinner; progress is shown as text in the file summary (tests assert their absence).

## Project constraints

- Zero persistent retention: no upload, filename, or result is stored after a request. See `CONTEXT.md` for the domain vocabulary (written in zh-TW).
- Cloud deployment was rejected under current constraints; see `docs/adr/0001-stop-cloud-deployment-under-current-constraints.md` before proposing hosting work.
- `README.md` and `README.zh-TW.md` are parallel; keep them in sync when either is changed.
