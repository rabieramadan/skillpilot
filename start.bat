@echo off
REM ===========================================================================
REM  SkillPilot - start the server (Windows, production)
REM
REM  Runs the application under Waitress. Edit PORT and THREADS below if you
REM  need to; everything else comes from .env.
REM ===========================================================================
setlocal
cd /d "%~dp0"

set PORT=5000
set THREADS=8
set FLASK_ENV=production

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   ERROR: not installed yet. Run install.bat first.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   SkillPilot starting on http://0.0.0.0:%PORT%
echo   Local access:  http://localhost:%PORT%
echo   Press Ctrl+C to stop.
echo ============================================================
echo.

.venv\Scripts\python.exe serve.py --host 0.0.0.0 --port %PORT% --threads %THREADS%

if errorlevel 1 (
    echo.
    echo   The server exited with an error. See server.log for details.
    echo.
    pause
)
