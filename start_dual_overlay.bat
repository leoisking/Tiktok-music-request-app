@echo off
setlocal EnableExtensions DisableDelayedExpansion

if exist "%~dp0spotify_env.example.bat" call "%~dp0spotify_env.example.bat"
if not defined PORT set "PORT=5000"
if not defined CONTROL_PASSWORD set "CONTROL_PASSWORD="

call :configure_control_password
if errorlevel 1 exit /b 1

:server_ready
echo [CLEANUP] Stopping existing widget server and overlay processes...
taskkill /F /FI "WINDOWTITLE eq Live Widget*" /T >nul 2>&1
for /f "skip=1 tokens=1" %%P in ('wmic process where "name='python.exe'" get ProcessId 2^>nul ^| findstr /R /V "^$"') do (
    if not "%%P"=="" taskkill /F /PID %%P >nul 2>&1
)

echo [INFO] Starting the local widget server.
echo [INFO] Server will listen on http://127.0.0.1:%PORT%
echo http://127.0.0.1:%PORT%/control
python "%~dp0live_widget.py"
exit /b %errorlevel%

:configure_control_password
rem The password is only ever read from the environment by Python, never expanded on a
rem command line, so quotes, ampersands, percent signs and other shell characters are safe.
set "_password_attempts=0"
call :validate_password
if not errorlevel 1 goto :password_configured

:prompt_for_password
set /a _password_attempts+=1
if %_password_attempts% GTR 6 (
    echo [ERROR] No valid control password entered. Set CONTROL_PASSWORD and try again.
    exit /b 1
)
set /p "CONTROL_PASSWORD=Control panel password: "
call :validate_password
if errorlevel 2 (
    echo [ERROR] Replace the placeholder password before continuing.
    goto :prompt_for_password
)
if errorlevel 1 (
    echo [ERROR] Password cannot be empty.
    goto :prompt_for_password
)
echo [INFO] No password is configured yet. Using the newly entered control password.
echo http://127.0.0.1:%PORT%/control
exit /b 0

:password_configured
echo [INFO] A password is already configured. Press Enter to keep it, or type a new one.
set /p "CONTROL_PASSWORD=Control panel password: "
call :validate_password
if errorlevel 1 (
    echo [ERROR] Replace the placeholder password before continuing.
    goto :password_configured
)
echo [INFO] Keep the control password private and do not expose it in browser sources.
echo http://127.0.0.1:%PORT%/control
exit /b 0

:validate_password
rem Exit code: 0 = usable, 1 = empty/whitespace, 2 = placeholder value.
python -c "import os, sys; p = os.environ.get('CONTROL_PASSWORD', '').strip(); sys.exit(1 if not p else 2 if p.lower() in ('your_password', 'your_secure_pass', 'yoursecurepassword') else 0)"
exit /b %errorlevel%
