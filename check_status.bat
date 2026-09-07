@echo off
REM ========================================
REM Widget Status Checker
REM ========================================

echo.
echo ========================================
echo   TikTok Widget Status Check
echo ========================================
echo.

REM Check if Python is running
echo [1] Checking if Python is running...
tasklist | findstr python.exe >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo    [OK] Python is running
    tasklist | findstr python.exe
) else (
    echo    [X] Python is NOT running
)
echo.

REM Check if port 5000 is responding
echo [2] Checking if widget server is responding...
curl -s --max-time 3 http://localhost:5000 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo    [OK] Widget server is responding on port 5000
) else (
    echo    [X] Widget server is NOT responding on port 5000
)
echo.

REM Check if Cloudflare is running
echo [3] Checking if Cloudflare tunnel is running...
tasklist | findstr cloudflared.exe >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo    [OK] Cloudflare tunnel is running
) else (
    echo    [X] Cloudflare tunnel is NOT running
)
echo.

REM Check log files
echo [4] Checking log files...
if exist logs\*.log (
    echo    Log files found:
    dir /b /o-d logs\*.log
    echo.
    echo    Last 10 lines of most recent log:
    for /f %%f in ('dir /b /o-d logs\*.log') do (
        powershell "Get-Content logs\%%f -Tail 10 -ErrorAction SilentlyContinue"
        goto DONE_LOGS
    )
    :DONE_LOGS
) else (
    echo    [X] No log files found in logs\ directory
)
echo.

REM Check TikTok user setting
echo [5] Checking configuration...
if "%TIKTOK_USER%"=="" (
    echo    [!] TIKTOK_USER not set
) else (
    echo    [OK] TIKTOK_USER = %TIKTOK_USER%
)
echo.

REM Summary
echo ========================================
echo   SUMMARY
echo ========================================
echo.
echo If everything shows [OK], widget is running fine.
echo If you see [X], that component is not working.
echo.
echo NEXT STEPS:
echo   - If Python not running: start_simple.bat
echo   - If not responding: Check Widget Server window
echo   - If no logs: Widget never started properly
echo.

pause
