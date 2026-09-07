@echo off
REM ========================================
REM TikTok Live Widget - Control Panel Launcher
REM ========================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Control Panel Launcher
echo ========================================
echo.

echo Choose your connection method:
echo.
echo   1. Local Server (http://localhost:5000/control)
echo   2. Cloudflare Tunnel URL (I have my tunnel URL)
echo   3. Manual entry (I'll type the full URL)
echo.
set /p CHOICE="Enter your choice (1-3): "

set CONTROL_URL=

if "%CHOICE%"=="1" (
    set CONTROL_URL=http://localhost:5000/control
    echo.
    echo [INFO] Opening local control panel...
) else if "%CHOICE%"=="2" (
    echo.
    echo Enter your Cloudflare tunnel URL (without /control).
    echo Example: https://abc-xyz-123.trycloudflare.com
    echo.
    set /p TUNNEL_URL="Cloudflare URL: "

    REM Remove trailing slash if present
    if "!TUNNEL_URL:~-1!"=="/" (
        set TUNNEL_URL=!TUNNEL_URL:~0,-1!
    )

    REM Validate URL format
    echo !TUNNEL_URL! | findstr /R /C:"https://.*trycloudflare\.com" >nul
    if errorlevel 1 (
        echo !TUNNEL_URL! | findstr /R /C:"http" >nul
        if errorlevel 1 (
            echo.
            echo [WARNING] URL doesn't look like a valid HTTP/HTTPS URL.
            echo Proceeding anyway...
        )
    )

    set CONTROL_URL=!TUNNEL_URL!/control
) else if "%CHOICE%"=="3" (
    echo.
    echo Enter the full control panel URL.
    echo Example: https://abc-xyz.trycloudflare.com/control
    echo.
    set /p CONTROL_URL="Control URL: "
) else (
    echo.
    echo [ERROR] Invalid choice!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Opening Control Panel
echo ========================================
echo.
echo URL: !CONTROL_URL!
echo.

echo Enter your control password on the page, then select Unlock.
echo Never include passwords in URLs.

echo.
echo Opening in default browser...
echo.

REM Open in default browser
start "" "!CONTROL_URL!"

timeout /t 2 /nobreak >nul

echo [SUCCESS] Control panel opened!
echo.
echo ========================================
echo   Quick Tips
echo ========================================
echo.
echo - Check the connection status at the top of the page
echo - If it shows "Disconnected", verify your server URL
echo - For Cloudflare, make sure your tunnel is running
echo - Press F12 in browser to see console logs
echo.
echo Connection Status Guide:
echo   [Green] Connected    = Ready to use!
echo   [Red]   Disconnected = Check server URL
echo   [Red]   Error        = Check server is running
echo.

pause
