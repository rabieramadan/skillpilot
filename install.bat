@echo off
REM ===========================================================================
REM  SkillPilot - one-time installer (Windows)
REM
REM  Creates a virtual environment, installs dependencies, checks the database
REM  connection, creates the schema and seeds the initial accounts.
REM
REM  Run this once. Afterwards use start.bat.
REM ===========================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo   SkillPilot installer
echo ============================================================
echo.

REM --- 1. Python -------------------------------------------------------------
echo [1/5] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo   ERROR: Python is not on PATH.
    echo   Install Python 3.11 or newer from https://www.python.org/downloads/
    echo   and tick "Add python.exe to PATH" during setup.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo       Found Python !PYVER!
python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
    echo.
    echo   ERROR: Python 3.11 or newer is required; this is !PYVER!.
    echo.
    pause
    exit /b 1
)

REM --- 2. Virtual environment ------------------------------------------------
echo [2/5] Creating virtual environment in .venv ...
if exist ".venv\Scripts\python.exe" (
    echo       Already exists, reusing it.
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo   ERROR: could not create the virtual environment.
        pause
        exit /b 1
    )
)
set PY=.venv\Scripts\python.exe

REM --- 3. Dependencies -------------------------------------------------------
echo [3/5] Installing dependencies ^(needs internet, takes 2-5 minutes^)...
"%PY%" -m pip install --upgrade pip --quiet
"%PY%" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo   ERROR: dependency installation failed. Scroll up for the reason.
    echo   The most common cause is no internet access or a proxy that blocks
    echo   pypi.org.
    echo.
    pause
    exit /b 1
)
echo       Done.

REM --- 4. Configuration and database ----------------------------------------
echo [4/5] Checking configuration and database...
if not exist "config.yaml" (
    if exist "config.example.yaml" (
        copy /y "config.example.yaml" "config.yaml" >nul
        echo       Created config.yaml from the example. Add your API keys to
        echo       its api_keys: block before the AI features will work.
    ) else (
        echo.
        echo   ERROR: neither config.yaml nor config.example.yaml is present.
        echo.
        pause
        exit /b 1
    )
)
if not exist ".env" (
    echo.
    echo   ERROR: .env is missing. Copy .env.example to .env and fill it in.
    echo.
    pause
    exit /b 1
)
"%PY%" check_install.py
if errorlevel 1 (
    echo.
    echo   Installation stopped. Fix the problem above and run install.bat again.
    echo.
    pause
    exit /b 1
)

REM --- 5. Seed accounts ------------------------------------------------------
REM Safe on an existing system: accounts that already exist are left alone,
REM passwords included.
echo [5/5] Creating any missing accounts...
"%PY%" run_seed_users.py
if errorlevel 1 (
    echo   WARNING: seeding failed. The application will still start, but you
    echo            will need to create an administrator account yourself.
)

echo.
echo ============================================================
echo   Installation complete.
echo.
echo   Start the server with:  start.bat
echo   Then open:              http://localhost:5000
echo.
echo   Sign in as  admin / admin123  and change that password
echo   immediately under Profile.
echo ============================================================
echo.
pause
