"""Offline desktop app: the UI runs in a native window and calls Python directly.

No HTTP server is started and no network port is opened. Packaged into the portable
Windows executable by packaging/markitdown-web.spec.
"""

from __future__ import annotations

import ctypes
import os
import sys

import webview

from app.config import SETTINGS
from app.desktop import DesktopApi, build_page

# WebView2 otherwise contacts Microsoft in the background (configuration, component updates,
# SmartScreen). These switches turn that off and make every host name fail to resolve, so the
# window stays offline. ElasticOverscroll repeats pywebview's own --disable-features value.
OFFLINE_BROWSER_ARGUMENTS = (
    "--disable-background-networking --disable-component-update --disable-domain-reliability "
    "--disable-sync --no-pings --disable-features=ElasticOverscroll,msSmartScreenProtection "
    '--host-resolver-rules="MAP * ~NOTFOUND"'
)
WEBVIEW2_MISSING = (
    "MarkItDown Web needs the Microsoft Edge WebView2 Runtime, which is included in "
    "Windows 11 and current Windows 10. Install it from Microsoft, then start the app again."
)


def _show_error(message: str) -> None:
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(None, message, SETTINGS.app_name, 0x10)
    else:
        print(message, file=sys.stderr)


def main() -> int:
    window = webview.create_window(
        SETTINGS.app_name,
        html=build_page(),
        js_api=DesktopApi(),
        width=1280,
        height=860,
        min_size=(820, 600),
    )
    func, args = None, None
    self_test = os.getenv("MARKITDOWN_DESKTOP_SELFTEST")
    if self_test:
        from app.selftest import run_self_test

        func, args = run_self_test, (window, self_test)

    os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = OFFLINE_BROWSER_ARGUMENTS
    # The packaged app has no console, so startup failures must surface in a dialog.
    try:
        if sys.platform == "win32":
            from webview.platforms import winforms

            # Without WebView2, pywebview falls back to Internet Explorer, which cannot run the UI.
            if winforms.renderer != "edgechromium":
                _show_error(WEBVIEW2_MISSING)
                return 1
        # private_mode keeps WebView2 from persisting cookies, storage, or cache after exit.
        webview.start(func, args, private_mode=True)
    except Exception as exc:
        _show_error(f"{SETTINGS.app_name} could not start: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
