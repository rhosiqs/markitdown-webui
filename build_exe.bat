@echo off
rem Build the portable dist\MarkItDown-Web.exe with PyInstaller.
rem Uses uv when available, otherwise .venv (created from Python 3.10 to 3.13 if missing).
setlocal
set "UV_LINK_MODE=copy"
cd /d "%~dp0"
set "SPEC=packaging\markitdown-web.spec"

where uv >nul 2>nul
if not errorlevel 1 (
    echo Using uv.
    uv run --group build pyinstaller --noconfirm --clean "%SPEC%" || goto :fail
    goto :built
)

if exist ".venv\Scripts\python.exe" goto :install

set "BASE="
for %%V in (3.13 3.12 3.11 3.10) do (
    if not defined BASE py -%%V -c "import sys" >nul 2>nul && set "BASE=py -%%V"
)
if not defined BASE python -c "import sys; sys.exit(not (3, 10) <= sys.version_info[:2] <= (3, 13))" >nul 2>nul && set "BASE=python"
if not defined BASE (
    echo Python 3.10 to 3.13 was not found. Install uv or Python, then run this file again.
    goto :fail
)
echo Creating .venv.
%BASE% -m venv .venv || goto :fail

:install
echo Installing build dependencies.
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt || goto :fail
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "%SPEC%" || goto :fail

:built
echo Built dist\MarkItDown-Web.exe
goto :done

:fail
pause
exit /b 1

:done
endlocal
