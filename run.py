from __future__ import annotations

import socket
import sys

import uvicorn

from app.config import SETTINGS

PORT_ATTEMPTS = 20


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


if __name__ == "__main__":
    port = _find_free_port(SETTINGS.host, SETTINGS.port)
    if port is None:
        print(
            f"Ports {SETTINGS.port}-{SETTINGS.port + PORT_ATTEMPTS - 1} are all in use. "
            "Stop the other copy of the app or set MARKITDOWN_WEB_PORT.",
            file=sys.stderr,
        )
        sys.exit(1)
    if port != SETTINGS.port:
        print(
            f"Port {SETTINGS.port} is in use (is the app already running?); using {port}.",
            flush=True,
        )
    print(f"Server started at http://localhost:{port}", flush=True)
    uvicorn.run(
        "app.main:app",
        host=SETTINGS.host,
        port=port,
        reload=False,
        access_log=False,
        log_level="warning",
    )
