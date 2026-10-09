@echo off
rem Start MarkItDown Web with whichever Python setup is available:
rem uv, then .venv, then the md_webui Conda environment, then a new .venv.
setlocal
cd /d "%~dp0"
set "CHECK=import sys, markitdown, fastapi, uvicorn; sys.exit(not (3, 10) <= sys.version_info[:2] <= (3, 13))"

where uv >nul 2>nul
if not errorlevel 1 (
    echo Using uv.
    uv run --no-dev python run.py
    goto :done
)

if exist ".venv\Scripts\python.exe" (
    echo Using .venv.
    set "PY=.venv\Scripts\python.exe"
    goto :install
)

where conda >nul 2>nul
if not errorlevel 1 (
    call conda run -n md_webui python -c "%CHECK%" >nul 2>nul
    if not errorlevel 1 (
        echo Using Conda environment md_webui.
        call conda run -n md_webui --no-capture-output python run.py
        goto :done
    )
)

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
set "PY=.venv\Scripts\python.exe"

:install
"%PY%" -c "%CHECK%" >nul 2>nul
if errorlevel 1 (
    echo Installing dependencies.
    "%PY%" -m pip install -r requirements.txt || goto :fail
)
"%PY%" run.py
goto :done

:fail
pause
exit /b 1

:done
endlocal
