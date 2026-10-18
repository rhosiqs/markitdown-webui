# Portable Windows desktop app

`MarkItDown-Web.exe` is a single file that bundles Python, MarkItDown, and the UI.
Double-click it to open the app in its own window. It needs no installation, no Python,
and no network: no server starts, no port opens, and it works offline.

## Use

1. Double-click `MarkItDown-Web.exe`.
2. Drop or choose a file, edit the Markdown, then **Copy** or **Download .md**
   (Download asks where to save).
3. Close the window to quit.

The first start takes a few seconds while the executable unpacks itself to a temporary
folder, which is removed on exit. Files are read into memory only; nothing is kept after
the window closes. `MARKITDOWN_WEB_MAX_MB` still sets the size limit (default 64 MB).

Requirements: 64-bit Windows 10 or 11 with the Microsoft Edge WebView2 Runtime, which
Windows 11 and current Windows 10 already include. Without it the app shows a message
instead of starting.

Windows SmartScreen may warn about an unsigned executable: choose **More info → Run anyway**.

## How it stays offline

- The page talks to Python through pywebview's in-process bridge (`app/desktop.py`)
  instead of HTTP.
- The page's Content-Security-Policy blocks all network requests (`connect-src 'none'`,
  images only from `data:`/`blob:`).
- WebView2 is started with background networking, component updates, and SmartScreen
  disabled, and with every host name mapped to "not found" (`desktop.py`).

## Build

PyInstaller cannot cross-compile, so build on Windows:

```bat
build_exe.bat
```

The result is `dist\MarkItDown-Web.exe`. `build_exe.bat` uses uv when available, otherwise
`.venv` with `requirements-dev.txt`.

The GitHub Actions workflow `.github/workflows/windows-exe.yml` builds the executable on
`windows-latest` and runs `packaging/desktop_smoke.py`: the exe converts PDF, DOCX, XLSX,
PPTX, HTML, and CSV samples in its real window, and the job fails if the app or its WebView2
processes open any socket. The exe is uploaded as the `MarkItDown-Web-windows` artifact.
