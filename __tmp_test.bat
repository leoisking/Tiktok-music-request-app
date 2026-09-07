@echo off
setlocal EnableExtensions DisableDelayedExpansion
if "%CHAT_SOURCE%"=="" set "CHAT_SOURCE=tiktok"
set "CHAT_SOURCE=%CHAT_SOURCE:\"=%"
if /I "%CHAT_SOURCE%"=="tiktok" goto :validate_tiktok
if /I "%CHAT_SOURCE%"=="twitch" goto :validate_twitch
if /I "%CHAT_SOURCE%"=="both" goto :validate_both
goto :after_validate
:validate_tiktok
if not defined TIKTOK_USER (
 echo missing
 exit /b 1
)
goto :after_validate
:validate_twitch
if not defined TWITCH_CHANNEL (
 echo missingtw
 exit /b 1
)
goto :after_validate
:validate_both
if not defined TIKTOK_USER exit /b 1
if not defined TWITCH_CHANNEL exit /b 1
goto :after_validate
:after_validate
echo ok %CHAT_SOURCE% %TIKTOK_USER%
