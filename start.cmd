@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto fail
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto fail
)
rem Use the interpreter's matching DLLs before inherited third-party PATH entries.
set "ND_RUNTIME_HOME="
for /f "usebackq tokens=1,* delims==" %%A in (".venv\pyvenv.cfg") do if /i "%%A"=="home " set "ND_RUNTIME_HOME=%%B"
for /f "tokens=*" %%A in ("%ND_RUNTIME_HOME%") do set "ND_RUNTIME_HOME=%%A"
if exist "%ND_RUNTIME_HOME%\Library\bin\libssl-3-x64.dll" set "PATH=%ND_RUNTIME_HOME%\Library\bin;%PATH%"
".venv\Scripts\python.exe" -c "from northdiary.bootstrap import configure_runtime; configure_runtime(); import PySide6, ebooklib, lxml.html" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo Startup failed. Please keep this window and share the error message.
pause
exit /b 1

