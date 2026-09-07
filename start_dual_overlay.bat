@echo off
setlocal EnableExtensions DisableDelayedExpansion

REM Always run in a persistent cmd window so errors remain visible.
if /I not "%~1"=="--child" (
    start "Dual Overlay Starter" cmd /k ""%~f0" --child"
    exit /b
)
shift /1

REM ========================================
REM Live Chat Widget - Dual Overlay Tunnel Starter
REM ========================================

cd /d "%~dp0"

set "PORT=5000"
set "WIDGET_WINDOW_TITLE=Live Chat Widget - Output"
set "HEALTH_URL=http://127.0.0.1:%PORT%/"
set "QUEUE_WIDGET_URL=http://127.0.0.1:%PORT%/queue_widget"
set "URLS_FILE=%~dp0last_tunnel_urls.txt"

if exist "%~dp0spotify_env.bat" (
    call "%~dp0spotify_env.bat"
)

echo.
echo ========================================
echo   Dual Overlay Starter (Cloudflare)
echo ========================================
echo.

echo [CLEANUP] Stopping old server processes on port %PORT%...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    taskkill /PID %%P /F >nul 2>nul
)
taskkill /FI "WINDOWTITLE eq %WIDGET_WINDOW_TITLE%" /F >nul 2>nul
timeout /t 1 /nobreak >nul

where cloudflared >nul 2>nul
if errorlevel 1 (
    echo [ERROR] cloudflared not found.
    echo Install with: winget install Cloudflare.cloudflared
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

REM --- FIX 1: Prompt for CHAT_SOURCE using a dedicated label block ---
if not "%CHAT_SOURCE%"=="" goto :chat_source_set
set /p CHAT_SOURCE=Chat source [tiktok/twitch/both] (default tiktok): 
:chat_source_set
if "%CHAT_SOURCE%"=="" set "CHAT_SOURCE=tiktok"

REM --- FIX 2: Validate CHAT_SOURCE without chained if /I not ---
set "CHAT_SOURCE_VALID=0"
if /I "%CHAT_SOURCE%"=="tiktok" set "CHAT_SOURCE_VALID=1"
if /I "%CHAT_SOURCE%"=="twitch" set "CHAT_SOURCE_VALID=1"
if /I "%CHAT_SOURCE%"=="both"   set "CHAT_SOURCE_VALID=1"
if "%CHAT_SOURCE_VALID%"=="0" (
    echo [WARNING] Unknown CHAT_SOURCE "%CHAT_SOURCE%". Using tiktok.
    set "CHAT_SOURCE=tiktok"
)

if /I "%CHAT_SOURCE%"=="tiktok" goto :ask_tiktok
if /I "%CHAT_SOURCE%"=="both"   goto :ask_tiktok
goto :skip_tiktok
:ask_tiktok
if "%TIKTOK_USER%"=="" set /p TIKTOK_USER=Enter your TikTok username: 
:skip_tiktok

if /I "%CHAT_SOURCE%"=="twitch" goto :ask_twitch
if /I "%CHAT_SOURCE%"=="both"   goto :ask_twitch
goto :skip_twitch
:ask_twitch
if "%TWITCH_CHANNEL%"=="" set /p TWITCH_CHANNEL=Enter your Twitch channel name: 
:skip_twitch

REM Normalize TikTok username - remove leading @
if not "%TIKTOK_USER%"=="" (
    set "TIKTOK_USER=%TIKTOK_USER:@=%"
)

if /I "%CHAT_SOURCE%"=="tiktok" if "%TIKTOK_USER%"=="" (
    echo [ERROR] TikTok username is required.
    pause
    exit /b 1
)
if /I "%CHAT_SOURCE%"=="both" if "%TIKTOK_USER%"=="" (
    echo [ERROR] TikTok username is required.
    pause
    exit /b 1
)
if /I "%CHAT_SOURCE%"=="twitch" if "%TWITCH_CHANNEL%"=="" (
    echo [ERROR] Twitch channel is required.
    pause
    exit /b 1
)
if /I "%CHAT_SOURCE%"=="both" if "%TWITCH_CHANNEL%"=="" (
    echo [ERROR] Twitch channel is required.
    pause
    exit /b 1
)

REM --- FIX 3: SKIP_THRESHOLD prompt and validation without set /a in if block ---
if not "%SKIP_THRESHOLD%"=="" goto :threshold_set
set /p SKIP_THRESHOLD=Skip votes needed (default 10): 
:threshold_set
if "%SKIP_THRESHOLD%"=="" set "SKIP_THRESHOLD=10"

REM Validate threshold is numeric using set /a safely OUTSIDE any if block
set "_threshold_check=0"
set /a "_threshold_check=%SKIP_THRESHOLD%+0"
if "%_threshold_check%"=="0" if not "%SKIP_THRESHOLD%"=="0" (
    echo [WARNING] Invalid SKIP_THRESHOLD "%SKIP_THRESHOLD%". Using 10.
    set "SKIP_THRESHOLD=10"
)

echo.
echo [CHECK] Spotify auto-queue configuration...
if "%SPOTIFY_QUEUE_ON_REQUEST%"=="" set "SPOTIFY_QUEUE_ON_REQUEST=1"
if /I "%SPOTIFY_QUEUE_ON_REQUEST%"=="0"     goto :spotify_check_done
if /I "%SPOTIFY_QUEUE_ON_REQUEST%"=="false" goto :spotify_check_done
if /I "%SPOTIFY_QUEUE_ON_REQUEST%"=="no"    goto :spotify_check_done
if /I "%SPOTIFY_QUEUE_ON_REQUEST%"=="off"   goto :spotify_check_done

if "%SPOTIFY_CLIENT_ID%"==""      echo [WARN] SPOTIFY_CLIENT_ID is not set.
if "%SPOTIFY_CLIENT_SECRET%"==""  echo [WARN] SPOTIFY_CLIENT_SECRET is not set.
if "%SPOTIFY_REFRESH_TOKEN%"==""  echo [WARN] SPOTIFY_REFRESH_TOKEN is not set.

if "%SPOTIFY_CLIENT_ID%"=="" if "%SPOTIFY_CLIENT_SECRET%"=="" if "%SPOTIFY_REFRESH_TOKEN%"=="" (
    echo [WARN] Spotify queue API credentials are missing.
    echo       !req will only update local request list.
    echo       Create spotify_env.bat or run get_spotify_refresh_token.bat first.
)
:spotify_check_done

echo.
echo [CHECK] Verifying Python packages...
python -c "import flask, flask_socketio, TikTokLive, winsdk" >nul 2>nul
if errorlevel 1 (
    echo [WARNING] Required packages not found. Installing...
    python -m pip install flask flask-socketio TikTokLive winsdk
    if errorlevel 1 (
        echo [ERROR] Failed to install required packages.
        pause
        exit /b 1
    )
)

echo.
echo [START] Launching widget server...
start "%WIDGET_WINDOW_TITLE%" /D "%~dp0" cmd /k "python live_widget.py || (echo. & echo [ERROR] live_widget.py crashed. & pause)"

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
    echo [ERROR] Main widget did not become ready on %HEALTH_URL%
    echo Check the "%WIDGET_WINDOW_TITLE%" window for errors.
    taskkill /FI "WINDOWTITLE eq %WIDGET_WINDOW_TITLE%" /F >nul 2>nul
    pause
    exit /b 1
)

echo [SUCCESS] Main widget route ready: %HEALTH_URL%
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%QUEUE_WIDGET_URL%' -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
if errorlevel 1 (
    echo [WARNING] Queue widget route not responding: %QUEUE_WIDGET_URL%
) else (
    echo [SUCCESS] Queue widget route ready: %QUEUE_WIDGET_URL%
)

echo.
echo [START] Starting Cloudflare tunnel...
echo [INFO] Waiting for tunnel URL...
echo.

if exist "%URLS_FILE%" del /q "%URLS_FILE%" >nul 2>nul
set "CF_PS_CMD=$url=''; $urlFile='%URLS_FILE%'; & cloudflared tunnel --url 'http://127.0.0.1:%PORT%' 2>&1 | ForEach-Object { $line=[string]$_; Write-Host $line; if (-not $url) { $m=[regex]::Match($line,'https://[a-z0-9-]+\.trycloudflare\.com'); if($m.Success){ $url=$m.Value.TrimEnd('/'); Write-Host ''; Write-Host '========================================'; Write-Host '  COPY THESE URLs'; Write-Host '========================================'; Write-Host ('Main Overlay : ' + $url + '/'); Write-Host ('Queue Overlay: ' + $url + '/queue_widget'); Write-Host '========================================'; Write-Host ''; Set-Content -Path $urlFile -Value ('Main Overlay : ' + $url + '/'); Add-Content -Path $urlFile -Value ('Queue Overlay: ' + $url + '/queue_widget'); Write-Host ('[INFO] Saved to: ' + $urlFile); Write-Host ''; } } }"
powershell -NoProfile -ExecutionPolicy Bypass -Command "%CF_PS_CMD%"

echo.
echo ========================================
echo   Tunnel closed. Shutting down...
echo ========================================
echo.
taskkill /FI "WINDOWTITLE eq %WIDGET_WINDOW_TITLE%" /F >nul 2>nul
echo [DONE] Services stopped.
echo.
pause
exit /b 0