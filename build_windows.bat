@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if not exist ".build-venv\Scripts\python.exe" (
    python -m venv .build-venv
    if errorlevel 1 goto :failed
)
".build-venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto :failed
".build-venv\Scripts\python.exe" build_windows.py
if errorlevel 1 goto :failed
echo.
echo Ready: dist\LiveWidget-Windows-x64.zip
pause
exit /b 0
:failed
echo.
echo Build failed. Review the error above. Use 64-bit Python 3.14 on Windows.
pause
exit /b 1
