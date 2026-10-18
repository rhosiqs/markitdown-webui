# Portable Windows executable

`MarkItDown-Web.exe` is a single file that bundles Python, MarkItDown, and the web UI.
It needs no installation and no Python on the target machine.

## Use

1. Double-click `MarkItDown-Web.exe`.
2. A console window opens and the browser opens `http://localhost:8765`
   (or the next free port).
3. Close the console window to stop the app.

The first start takes a few seconds while the executable unpacks itself to a temporary
folder, which is removed on exit. Uploads stay in memory, as in the source version.
`MARKITDOWN_WEB_PORT` and `MARKITDOWN_WEB_MAX_MB` work as usual;
`MARKITDOWN_WEB_OPEN_BROWSER=0` skips opening the browser.

Windows SmartScreen may warn about an unsigned executable: choose **More info → Run anyway**.

## Build

PyInstaller cannot cross-compile, so build on Windows:

```bat
build_exe.bat
```

The result is `dist\MarkItDown-Web.exe`. `build_exe.bat` uses uv when available, otherwise
`.venv` with `requirements-dev.txt`.

The GitHub Actions workflow `.github/workflows/windows-exe.yml` builds the executable on
`windows-latest`, runs `packaging/smoke_test.py` against it (health, static files, render, and
PDF/DOCX/XLSX/PPTX/HTML/CSV conversion), and uploads it as the `MarkItDown-Web-windows` artifact.
