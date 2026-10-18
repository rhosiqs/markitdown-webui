"""In-process bridge for the desktop window: replaces the HTTP routes, so nothing opens a port."""

from __future__ import annotations

import base64
import binascii
import hashlib
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import BASE_DIR, SETTINGS
from .converter import convert_bytes, describe_conversion_error
from .preview import render_markdown
from .security import output_filename, safe_filename, validate_extension

# pywebview builds its JS bridge with new Function(), so the page needs 'unsafe-eval'.
# connect-src 'none' and the data:/blob:-only image sources keep the page off the network.
DESKTOP_CSP = (
    "default-src 'none'; script-src '{script}' 'unsafe-eval'; style-src '{style}'; "
    "img-src data: blob:; connect-src 'none'; object-src 'none'; base-uri 'none'; "
    "form-action 'none'"
)


def _csp_hash(source: str) -> str:
    digest = hashlib.sha256(source.encode("utf-8")).digest()
    return "sha256-" + base64.b64encode(digest).decode("ascii")


def build_page() -> str:
    """Render index.html with app.js and styles.css inlined, for loading without a server."""
    script = (BASE_DIR / "static" / "app.js").read_text(encoding="utf-8")
    styles = (BASE_DIR / "static" / "styles.css").read_text(encoding="utf-8")
    environment = Environment(
        loader=FileSystemLoader(BASE_DIR / "templates"),
        autoescape=select_autoescape(["html"]),
    )
    return environment.get_template("index.html").render(
        app_name=SETTINGS.app_name,
        max_upload_mb=SETTINGS.max_upload_bytes // (1024 * 1024),
        inline_assets={
            "script": script,
            "styles": styles,
            "csp": DESKTOP_CSP.format(script=_csp_hash(script), style=_csp_hash(styles)),
        },
    )


def _too_large(limit: int) -> str:
    return f"The file exceeds the {limit // (1024 * 1024)} MB limit."


@dataclass
class _Upload:
    filename: str
    extension: str
    started: float = field(default_factory=time.perf_counter)
    chunks: list[bytes] = field(default_factory=list)
    received: int = 0


class DesktopApi:
    """Exposed to the page as window.pywebview.api. Every method returns a JSON-able dict;
    failures come back as {"error": message} so the page shows them like HTTP errors.

    Files arrive in base64 chunks and stay in memory until converted or cancelled.
    """

    def __init__(self, max_upload_bytes: int = SETTINGS.max_upload_bytes) -> None:
        self._max_upload_bytes = max_upload_bytes
        self._uploads: dict[str, _Upload] = {}
        self._lock = threading.Lock()

    def begin_upload(self, name: str, size: int) -> dict[str, object]:
        try:
            filename = safe_filename(name)
            extension = validate_extension(filename)
        except ValueError as exc:
            return {"error": str(exc)}
        if int(size) > self._max_upload_bytes:
            return {"error": _too_large(self._max_upload_bytes)}
        upload_id = uuid.uuid4().hex
        with self._lock:
            self._uploads[upload_id] = _Upload(filename, extension)
        return {"upload_id": upload_id}

    def upload_chunk(self, upload_id: str, data: str) -> dict[str, object]:
        with self._lock:
            upload = self._uploads.get(upload_id)
        if upload is None:
            return {"error": "The upload was cancelled."}
        try:
            chunk = base64.b64decode(data, validate=True)
        except (binascii.Error, TypeError, ValueError):
            self.cancel_upload(upload_id)
            return {"error": "The file could not be read."}
        upload.received += len(chunk)
        if upload.received > self._max_upload_bytes:
            self.cancel_upload(upload_id)
            return {"error": _too_large(self._max_upload_bytes)}
        upload.chunks.append(chunk)
        return {"received": upload.received}

    def finish_upload(self, upload_id: str) -> dict[str, object]:
        with self._lock:
            upload = self._uploads.pop(upload_id, None)
        if upload is None:
            return {"error": "The upload was cancelled."}
        data = b"".join(upload.chunks)
        upload.chunks.clear()
        if not data:
            return {"error": "The file is empty."}
        try:
            markdown = convert_bytes(data, upload.extension)
        except Exception as exc:
            return {"error": describe_conversion_error(exc)}
        return {
            "filename": upload.filename,
            "output_filename": output_filename(upload.filename),
            "markdown": markdown,
            "source_bytes": len(data),
            "markdown_chars": len(markdown),
            "elapsed_ms": round((time.perf_counter() - upload.started) * 1000),
        }

    def cancel_upload(self, upload_id: str) -> dict[str, object]:
        with self._lock:
            self._uploads.pop(upload_id, None)
        return {}

    def render(self, markdown: str) -> dict[str, object]:
        if not isinstance(markdown, str) or len(markdown) > SETTINGS.max_markdown_chars:
            return {"error": "The Markdown content is too long to preview."}
        return {"html": render_markdown(markdown)}

    def save_markdown(self, filename: str, markdown: str) -> dict[str, object]:
        """Ask where to save, then write the Markdown there. Nothing is saved otherwise."""
        import webview

        try:
            suggested = output_filename(safe_filename(filename))
        except ValueError:
            suggested = "converted.md"
        window = webview.active_window()
        if window is None:
            return {"error": "The app window is not available."}
        selected = window.create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=suggested,
            file_types=("Markdown (*.md)", "All files (*.*)"),
        )
        if not selected:
            return {"saved": False}
        target = Path(selected if isinstance(selected, str) else selected[0])
        try:
            target.write_bytes(markdown.encode("utf-8"))
        except OSError as exc:
            return {"error": f"The file could not be saved: {exc.strerror or exc}"}
        return {"saved": True}
