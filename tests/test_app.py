import re

from fastapi.testclient import TestClient

import app.main as main_module

client = TestClient(main_module.app)


def test_default_english_ui_has_no_chinese_text() -> None:
    page_response = client.get("/")
    script_response = client.get("/static/app.js")

    assert page_response.status_code == 200
    assert script_response.status_code == 200

    english_translations = script_response.text.partition("  \"zh-TW\": {")[0].rpartition(
        "  \"en-US\": {"
    )[2]
    assert english_translations
    assert re.search(r"[\u3400-\u9fff]", page_response.text) is None
    assert re.search(r"[\u3400-\u9fff]", english_translations) is None


def test_page_has_no_status_banner_or_spinner() -> None:
    page_response = client.get("/")
    script_response = client.get("/static/app.js")
    styles_response = client.get("/static/styles.css")

    assert "id=\"statusBanner\"" not in page_response.text
    assert "id=\"spinner\"" not in page_response.text
    assert "statusBanner" not in script_response.text
    assert ".status-banner" not in styles_response.text
    assert ".spinner" not in styles_response.text


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_convert_upload(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "convert_bytes", lambda data, extension: "# Converted\n")
    response = client.post(
        "/api/convert",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "notes.txt"
    assert payload["output_filename"] == "notes.md"
    assert payload["markdown"] == "# Converted\n"


def test_rejects_unknown_extension() -> None:
    response = client.post(
        "/api/convert",
        files={"file": ("malware.exe", b"not really", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_static_assets_have_browser_mime_types() -> None:
    script_response = client.get("/static/app.js")
    styles_response = client.get("/static/styles.css")

    assert script_response.headers["content-type"].startswith("text/javascript")
    assert styles_response.headers["content-type"].startswith("text/css")
