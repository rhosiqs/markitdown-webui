from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from app.config import SETTINGS

PORT_ATTEMPTS = 20
# Set by PyInstaller when running as the portable Windows executable.
FROZEN = getattr(sys, "frozen", False)


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _find_free_port(host: str, start: int) -> int | None:
    for port in range(start, min(start + PORT_ATTEMPTS, 65536)):
        if _port_is_free(host, port):
            return port
    return None


def _open_browser_when_ready(host: str, port: int, url: str, timeout: float = 120.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                break
        except OSError:
            time.sleep(0.2)
    else:
        return
    webbrowser.open(url)


def _should_open_browser() -> bool:
    default = "1" if FROZEN else "0"
    return os.getenv("MARKITDOWN_WEB_OPEN_BROWSER", default) != "0"


def _exit(code: int) -> None:
    # A double-clicked executable closes its console at once; keep errors readable.
    if FROZEN and code and sys.stdin and sys.stdin.isatty():
        input("Press Enter to close this window.")
    sys.exit(code)


def main() -> None:
    from app.main import app

    port = _find_free_port(SETTINGS.host, SETTINGS.port)
    if port is None:
        print(
            f"Ports {SETTINGS.port}-{SETTINGS.port + PORT_ATTEMPTS - 1} are all in use. "
            "Stop the other copy of the app or set MARKITDOWN_WEB_PORT.",
            file=sys.stderr,
        )
        _exit(1)
    if port != SETTINGS.port:
        print(
            f"Port {SETTINGS.port} is in use (is the app already running?); using {port}.",
            flush=True,
        )
    url = f"http://localhost:{port}"
    print(f"Server started at {url}", flush=True)
    if FROZEN:
        print("Close this window to stop the app.", flush=True)
    if _should_open_browser():
        threading.Thread(
            target=_open_browser_when_ready,
            args=(SETTINGS.host, port, url),
            daemon=True,
        ).start()
    uvicorn.run(
        app,
        host=SETTINGS.host,
        port=port,
        reload=False,
        access_log=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
