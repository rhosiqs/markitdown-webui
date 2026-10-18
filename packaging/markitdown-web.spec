# PyInstaller spec for the portable single-file desktop executable (no server, no ports).
# Build on Windows with build_exe.bat; see packaging/README.md.
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parent  # noqa: F821 - injected by PyInstaller

datas = [
    (str(ROOT / "app" / "static"), "app/static"),
    (str(ROOT / "app" / "templates"), "app/templates"),
]
binaries = []
hiddenimports = []

# Packages that load models, templates, or cmaps from their own folders at runtime.
for package in ("markitdown", "magika", "pdfminer", "pdfplumber", "pptx", "mammoth"):
    package_datas, package_binaries, package_imports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports

a = Analysis(  # noqa: F821
    [str(ROOT / "desktop.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        "tkinter", "pytest", "_pytest", "ruff", "IPython", "matplotlib",
        # The HTTP server is not part of the desktop app.
        "fastapi", "starlette", "uvicorn",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MarkItDown-Web",
    console=False,
    upx=False,
    debug=False,
    strip=False,
    runtime_tmpdir=None,
)
