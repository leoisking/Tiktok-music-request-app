@echo off
setlocal EnableExtensions DisableDelayedExpansion

REM ========================================
REM Live Chat Widget (TikTok/Twitch) - Cloudflare Tunnel Starter
REM ========================================

cd /d "%~dp0"

set "PORT=5000"
set "WIDGET_WINDOW_TITLE=Live Chat Widget - Output"
set "HEALTH_URL=http://127.0.0.1:%PORT%/"
set "QUEUE_WIDGET_URL=http://127.0.0.1:%PORT%/queue_widget"

REM Optional local Spotify env loader (create spotify_env.bat in project root)
if exist "%~dp0spotify_env.bat" (
    call "%~dp0spotify_env.bat"
)

echo.
echo ========================================
echo   Live Chat Widget with Cloudflare
echo ========================================
echo.

echo [CLEANUP] Stopping old server processes on port %PORT%...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    taskkill /PID %%P /F >nul 2>nul
)
taskkill /FI "WINDOWTITLE eq %WIDGET_WINDOW_TITLE%" /F >nul 2>nul
timeout /t 1 /nobreak >nul

REM Check prerequisites
where cloudflared >nul 2>nul
if errorlevel 1 (
    echo [ERROR] cloudflared not found.
    echo Install with: winget install Cloudflare.cloudflared
    echo Or download from: https://github.com/cloudflare/cloudflared/releases
    echo.
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Install Python 3.8+ from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [SETUP] Checking configuration...
echo.

if "%CHAT_SOURCE%"=="" (
    set /p CHAT_SOURCE=Chat source [tiktok/twitch/both] ^(default tiktok^): 
)
if "%CHAT_SOURCE%"=="" set "CHAT_SOURCE=tiktok"
set "CHAT_SOURCE=%CHAT_SOURCE:"=%"
if /I not "%CHAT_SOURCE%"=="tiktok" if /I not "%CHAT_SOURCE%"=="twitch" if /I not "%CHAT_SOURCE%"=="both" (
    echo [WARNING] Unknown CHAT_SOURCE "%CHAT_SOURCE%". Using tiktok.
    set "CHAT_SOURCE=tiktok"
)

if /I "%CHAT_SOURCE%"=="tiktok" (
    if not defined TIKTOK_USER set /p TIKTOK_USER=Enter your TikTok username: 
)
if /I "%CHAT_SOURCE%"=="both" (
    if not defined TIKTOK_USER set /p TIKTOK_USER=Enter your TikTok username: 
)
if /I "%CHAT_SOURCE%"=="twitch" (
    if not defined TWITCH_CHANNEL set /p TWITCH_CHANNEL=Enter your Twitch channel name: 
)
if /I "%CHAT_SOURCE%"=="both" (
    if not defined TWITCH_CHANNEL set /p TWITCH_CHANNEL=Enter your Twitch channel name: 
)

if defined TIKTOK_USER set "TIKTOK_USER=%TIKTOK_USER:@=%"

if /I "%CHAT_SOURCE%"=="tiktok" goto :validate_tiktok
if /I "%CHAT_SOURCE%"=="twitch" goto :validate_twitch
if /I "%CHAT_SOURCE%"=="both" goto :validate_both
goto :after_validate

:validate_tiktok
if not defined TIKTOK_USER (
    echo [ERROR] TikTok username is required for tiktok mode.
    echo.
    pause
    exit /b 1
)
goto :after_validate

:validate_twitch
if not defined TWITCH_CHANNEL (
    echo [ERROR] Twitch channel is required for twitch mode.
    echo.
    pause
    exit /b 1
)
goto :after_validate

:validate_both
if not defined TIKTOK_USER (
    echo [ERROR] TikTok username is required for both mode.
    echo.
    pause
    exit /b 1
)
if not defined TWITCH_CHANNEL (
    echo [ERROR] Twitch channel is required for both mode.
    echo.
    pause
    exit /b 1
)
goto :after_validate

:after_validate

echo.
echo [CHECK] Spotify auto-queue configuration...
if "%SPOTIFY_QUEUE_ON_REQUEST%"=="" set "SPOTIFY_QUEUE_ON_REQUEST=1"
if /I "%SPOTIFY_QUEUE_ON_REQUEST%"=="0" goto :spotify_check_done
if /I "%SPOTIFY_QUEUE_ON_REQUEST%"=="false" goto :spotify_check_done
if /I "%SPOTIFY_QUEUE_ON_REQUEST%"=="no" goto :spotify_check_done
if /I "%SPOTIFY_QUEUE_ON_REQUEST%"=="off" goto :spotify_check_done

if "%SPOTIFY_CLIENT_ID%"=="" (
    echo [WARN] SPOTIFY_CLIENT_ID is not set.
)
if "%SPOTIFY_CLIENT_SECRET%"=="" (
    echo [WARN] SPOTIFY_CLIENT_SECRET is not set.
)
if "%SPOTIFY_REFRESH_TOKEN%"=="" (
    echo [WARN] SPOTIFY_REFRESH_TOKEN is not set.
)
if "%SPOTIFY_CLIENT_ID%"=="" if "%SPOTIFY_CLIENT_SECRET%"=="" if "%SPOTIFY_REFRESH_TOKEN%"=="" (
    echo [WARN] Spotify queue API credentials are missing.
    echo       !req will only update local request list.
    echo       Create spotify_env.bat or run get_spotify_refresh_token.bat first.
)
:spotify_check_done

if "%SKIP_THRESHOLD%"=="" (
    set /p SKIP_THRESHOLD=Skip votes needed (default 10): 
)
if "%SKIP_THRESHOLD%"=="" set "SKIP_THRESHOLD=10"
if "%AUTO_NEXT_ON_THRESHOLD%"=="" set "AUTO_NEXT_ON_THRESHOLD=1"
set /a _threshold_check=%SKIP_THRESHOLD%+0 >nul 2>nul
if errorlevel 1 (
    echo [WARNING] Invalid SKIP_THRESHOLD "%SKIP_THRESHOLD%". Using 10.
    set "SKIP_THRESHOLD=10"
)

if not defined CONTROL_PASSWORD (
    echo [SECURITY] Set a control panel password to protect moderator actions.
    set /p "CONTROL_PASSWORD=Enter a unique control password (Enter disables browser controls): "
)

echo.
echo ========================================
echo Configuration:
echo ========================================
echo Chat Source: %CHAT_SOURCE%
if not "%TIKTOK_USER%"=="" echo TikTok User: %TIKTOK_USER%
if not "%TWITCH_CHANNEL%"=="" echo Twitch Channel: %TWITCH_CHANNEL%
echo Port: %PORT%
echo Skip Threshold: %SKIP_THRESHOLD%
echo Auto Next on Threshold: %AUTO_NEXT_ON_THRESHOLD%
if not defined CONTROL_PASSWORD (
    echo Control Password: NOT SET - browser controls disabled
) else (
    echo Control Password: *** SET ***
)
echo ========================================
echo.

echo [CHECK] Verifying Python packages...
python -c "import flask, flask_socketio, TikTokLive, winsdk" >nul 2>nul
if errorlevel 1 (
    echo [WARNING] Required packages not found. Installing...
    python -m pip install flask flask-socketio TikTokLive winsdk
    if errorlevel 1 (
        echo [ERROR] Failed to install required packages.
        echo.
        pause
        exit /b 1
    )
    echo [SUCCESS] Packages installed.
    echo.
)

REM Start widget in separate window
echo [START] Starting Live Chat Widget...
start "%WIDGET_WINDOW_TITLE%" /D "%~dp0" cmd /k python live_widget.py

REM Wait for widget health check (up to 30s)
set "SERVER_READY=0"
for /L %%I in (1,1,30) do (
    powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%HEALTH_URL%' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
    if not errorlevel 1 (
        set "SERVER_READY=1"
        goto :server_ready
    )
    timeout /t 1 /nobreak >nul
)

:server_ready
if "%SERVER_READY%"=="0" (
    echo [ERROR] Widget did not become ready on %HEALTH_URL%
    echo Check the "%WIDGET_WINDOW_TITLE%" window for errors.
    echo.
    taskkill /FI "WINDOWTITLE eq %WIDGET_WINDOW_TITLE%" /F >nul 2>nul
    pause
    exit /b 1
)

echo [SUCCESS] Widget is running on %HEALTH_URL%

REM Check queue widget route too
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%QUEUE_WIDGET_URL%' -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
if errorlevel 1 (
    echo [WARNING] Queue widget route did not respond at %QUEUE_WIDGET_URL%
    echo          Main widget may still be running, but /queue_widget could be unavailable.
) else (
    echo [SUCCESS] Queue widget is running on %QUEUE_WIDGET_URL%
)
echo.

echo [START] Starting Cloudflare Tunnel...
echo.
echo ========================================
echo   Both overlays open automatically
echo ========================================
echo.
echo The skip and queue HTTPS pages will open when reachable.
echo Both links will also be saved to last_tunnel_urls.txt.
echo Use those links for your two TikTok Studio browser sources.
echo Local controls: http://127.0.0.1:%PORT%/control
echo.

python "%~dp0_launch_overlay_tunnel.py" --port "%PORT%"

echo.
echo ========================================
echo   Tunnel closed. Shutting down...
echo ========================================
echo.

taskkill /FI "WINDOWTITLE eq %WIDGET_WINDOW_TITLE%" /F >nul 2>nul

echo [DONE] All services stopped.
echo.
pause
exit /b 0
