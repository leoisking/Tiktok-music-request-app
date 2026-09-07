@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo.
echo ========================================
echo   Spotify OAuth Helper
echo ========================================
echo.
echo This generates SPOTIFY_REFRESH_TOKEN for live_widget.py.
echo Required Spotify redirect URI in app settings:
echo   http://127.0.0.1:8888/callback
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    pause
    exit /b 1
)

if "%SPOTIFY_CLIENT_ID%"=="" (
    set /p SPOTIFY_CLIENT_ID=Enter SPOTIFY_CLIENT_ID: 
)
if "%SPOTIFY_CLIENT_SECRET%"=="" (
    set /p SPOTIFY_CLIENT_SECRET=Enter SPOTIFY_CLIENT_SECRET: 
)
if "%SPOTIFY_REDIRECT_URI%"=="" (
    set "SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback"
)

echo.
echo [INFO] Starting OAuth flow...
echo.

python spotify_oauth_helper.py
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo [ERROR] OAuth helper failed.
    pause
    exit /b %EXIT_CODE%
)

echo [DONE] Refresh token generated successfully.
echo.
pause
exit /b 0
