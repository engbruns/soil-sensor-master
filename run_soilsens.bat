@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

%PYTHON_EXE% -m pip show PyQt6 >nul 2>&1
if errorlevel 1 (
    echo [SoilSens] Installing dependencies...
    %PYTHON_EXE% -m pip install -r requirements.txt
)

echo [SoilSens] Starting application...
%PYTHON_EXE% main.py

if errorlevel 1 (
    echo.
    echo [SoilSens] Application exited with an error.
    pause
)

endlocal
