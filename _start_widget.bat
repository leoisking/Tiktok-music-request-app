@echo off
REM Helper script to start widget with environment variables

cd /d %~dp0

echo.
echo ==========================================
echo    LIVE CHAT WIDGET - OUTPUT
echo ==========================================
echo.
echo Chat Source: %CHAT_SOURCE%
if not "%TIKTOK_USER%"=="" echo TikTok User: %TIKTOK_USER%
if not "%TWITCH_CHANNEL%"=="" echo Twitch Channel: %TWITCH_CHANNEL%
echo Port: %PORT%
echo Skip Threshold: %SKIP_THRESHOLD%
echo.

:RESTART
echo [%date% %time%] Starting widget...
python live_widget.py

echo.
echo [WARNING] Widget stopped! Restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto RESTART
