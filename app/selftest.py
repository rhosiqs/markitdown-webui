"""Scripted run of the real desktop window, used by packaging/desktop_smoke.py.

Enabled only when MARKITDOWN_DESKTOP_SELFTEST names a folder of sample files. Each sample is
fed to the page's own convertFile(); the resulting editor and preview text is written to
result.json in that folder. The window then stays open for LINGER_SECONDS, so the harness
can catch background connections, and closes.
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path

LINGER_SECONDS = 15
READY_JS = "typeof convertFile === 'function' && !!(window.pywebview && window.pywebview.api"
READY_JS += " && window.pywebview.api.begin_upload)"
STATE_JS = (
    "({state: previewState.textContent, done: [t('synced'), t('failed'), t('previewError')]"
    ".includes(previewState.textContent), markdown: markdownEditor.value,"
    " preview: markdownPreview.textContent, meta: fileMeta.textContent})"
)


def _wait(window, script: str, timeout: float):
    deadline = time.monotonic() + timeout
    while True:
        value = window.evaluate_js(script)
        if value or time.monotonic() > deadline:
            return value
        time.sleep(0.25)


def run_self_test(window, folder: str) -> None:
    folder_path = Path(folder)
    result: dict[str, object] = {"samples": {}}
    try:
        window.events.loaded.wait(60)
        result["ready"] = bool(_wait(window, READY_JS, 60))
        for sample in sorted(folder_path.glob("sample.*")):
            encoded = base64.b64encode(sample.read_bytes()).decode("ascii")
            window.evaluate_js(
                "previewState.textContent = ''; convertFile(new File("
                f"[Uint8Array.from(atob('{encoded}'), (c) => c.charCodeAt(0))], "
                f"{json.dumps(sample.name)}))"
            )
            deadline = time.monotonic() + 120
            state = window.evaluate_js(STATE_JS)
            while not state["done"] and time.monotonic() < deadline:
                time.sleep(0.25)
                state = window.evaluate_js(STATE_JS)
            result["samples"][sample.name] = state
    except Exception as exc:  # reported to the harness instead of hanging the window
        result["error"] = repr(exc)
    finally:
        (folder_path / "result.json").write_text(json.dumps(result), encoding="utf-8")
        time.sleep(LINGER_SECONDS)
        window.destroy()
