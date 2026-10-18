from __future__ import annotations

import base64
import html
import re
import sys
import types

from app import desktop
from app.desktop import DesktopApi, _csp_hash, build_page


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def test_upload_in_chunks_then_convert(monkeypatch) -> None:
    captured = {}

    def fake_convert(data: bytes, extension: str) -> str:
        captured.update(data=data, extension=extension)
        return "# Result"

    monkeypatch.setattr(desktop, "convert_bytes", fake_convert)
    api = DesktopApi()
    upload_id = api.begin_upload("folder/report.PDF", 6)["upload_id"]
    assert api.upload_chunk(upload_id, _b64(b"abc")) == {"received": 3}
    assert api.upload_chunk(upload_id, _b64(b"def")) == {"received": 6}

    payload = api.finish_upload(upload_id)

    assert captured == {"data": b"abcdef", "extension": ".pdf"}
    assert payload["filename"] == "report.PDF"
    assert payload["output_filename"] == "report.md"
    assert payload["markdown"] == "# Result"
    assert payload["source_bytes"] == 6
    assert payload["markdown_chars"] == 8
    assert api.finish_upload(upload_id) == {"error": "The upload was cancelled."}


def test_rejects_unknown_extension_and_oversized_files() -> None:
    api = DesktopApi(max_upload_bytes=4)
    assert "Unsupported file format" in api.begin_upload("tool.exe", 1)["error"]
    assert "exceeds the 0 MB limit" in api.begin_upload("notes.txt", 5)["error"]

    upload_id = api.begin_upload("notes.txt", 4)["upload_id"]
    assert "exceeds" in api.upload_chunk(upload_id, _b64(b"12345"))["error"]
    assert api.finish_upload(upload_id) == {"error": "The upload was cancelled."}


def test_rejects_empty_and_damaged_uploads() -> None:
    api = DesktopApi()
    upload_id = api.begin_upload("notes.txt", 0)["upload_id"]
    assert api.finish_upload(upload_id) == {"error": "The file is empty."}

    upload_id = api.begin_upload("notes.txt", 3)["upload_id"]
    assert api.upload_chunk(upload_id, "not base64!") == {"error": "The file could not be read."}
    assert api.finish_upload(upload_id) == {"error": "The upload was cancelled."}


def test_conversion_errors_are_returned(monkeypatch) -> None:
    def fail(data: bytes, extension: str) -> str:
        raise RuntimeError("broken file")

    monkeypatch.setattr(desktop, "convert_bytes", fail)
    api = DesktopApi()
    upload_id = api.begin_upload("notes.txt", 1)["upload_id"]
    api.upload_chunk(upload_id, _b64(b"x"))
    assert api.finish_upload(upload_id) == {"error": "Conversion failed: broken file"}


def test_render_sanitizes_markdown() -> None:
    rendered = DesktopApi().render("# Title\n\n<script>alert(1)</script>")["html"]
    assert "<h1>Title</h1>" in rendered
    assert "<script>" not in rendered


def test_save_markdown_writes_chosen_file(monkeypatch, tmp_path) -> None:
    target = tmp_path / "out.md"
    calls = {}

    class FakeWindow:
        def create_file_dialog(self, dialog_type, save_filename, file_types):
            calls.update(dialog_type=dialog_type, save_filename=save_filename)
            return str(target)

    fake_webview = types.SimpleNamespace(
        active_window=FakeWindow,
        FileDialog=types.SimpleNamespace(SAVE=30),
    )
    monkeypatch.setitem(sys.modules, "webview", fake_webview)

    assert DesktopApi().save_markdown("..\\report.md", "# Hi\r\n") == {"saved": True}
    assert calls == {"dialog_type": 30, "save_filename": "report.md"}
    assert target.read_bytes() == b"# Hi\r\n"


def test_save_markdown_cancelled(monkeypatch) -> None:
    class FakeWindow:
        def create_file_dialog(self, *args, **kwargs):
            return None

    fake_webview = types.SimpleNamespace(
        active_window=FakeWindow,
        FileDialog=types.SimpleNamespace(SAVE=30),
    )
    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    assert DesktopApi().save_markdown("report.md", "x") == {"saved": False}


def test_page_inlines_assets_under_hash_based_csp() -> None:
    page = build_page()
    script = re.search(r"<script>(.*)</script>", page, re.S).group(1)
    styles = re.search(r"<style>(.*)</style>", page, re.S).group(1)
    csp = html.unescape(
        re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', page).group(1)
    )

    assert "/static/" not in page
    assert "const desktopApi" in script
    assert f"script-src '{_csp_hash(script)}'" in csp
    assert f"style-src '{_csp_hash(styles)}'" in csp
    assert "connect-src 'none'" in csp
