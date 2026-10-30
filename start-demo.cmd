@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto fail
".venv\Scripts\python.exe" -c "import PySide6, ebooklib, lxml.html" >nul 2>&1
if errorlevel 1 goto fail
if not exist "demo-data\northdiary.sqlite3" (
    ".venv\Scripts\python.exe" scripts\generate_demo.py "%~dp0demo-data"
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" main.py --data-dir "%~dp0demo-data"
if errorlevel 1 goto fail
exit /b 0
:fail
echo Demo startup failed. Run start.cmd once to install dependencies, then close it and retry.
pause
exit /b 1
