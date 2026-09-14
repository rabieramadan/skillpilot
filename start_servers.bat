@echo off
REM SkillPilot LMS - Windows Startup Script
REM Starts 4 Waitress instances for load balancing
REM Requires Python 3.9+ and nginx

echo ============================================
echo   SkillPilot LMS - Production Startup
echo ============================================
echo.

REM Configuration is read from the .env file in the project directory.
REM Do not put DATABASE_URL or SESSION_SECRET in this script.
set FLASK_ENV=production

REM Change to project directory
cd /d C:\SkillPilot

REM Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo Starting Waitress instances...
echo.

REM Start 4 Waitress workers on different ports
start "SkillPilot-Worker-1" cmd /c "python serve.py --port 5001 --threads 8"
timeout /t 2 /nobreak > nul

start "SkillPilot-Worker-2" cmd /c "python serve.py --port 5002 --threads 8"
timeout /t 2 /nobreak > nul

start "SkillPilot-Worker-3" cmd /c "python serve.py --port 5003 --threads 8"
timeout /t 2 /nobreak > nul

start "SkillPilot-Worker-4" cmd /c "python serve.py --port 5004 --threads 8"
timeout /t 2 /nobreak > nul

echo.
echo All workers started!
echo.
echo Ports: 5001, 5002, 5003, 5004
echo Total threads: 32 (8 per worker)
echo Estimated capacity: 500+ concurrent users
echo.

REM Start nginx
echo Starting Nginx...
cd C:\nginx
start nginx.exe

echo.
echo ============================================
echo   SkillPilot is now running!
echo   Access at: http://localhost
echo ============================================
echo.
echo Press any key to view status...
pause > nul

REM Show running processes
tasklist /fi "imagename eq python.exe" /fi "windowtitle eq SkillPilot*"
tasklist /fi "imagename eq nginx.exe"
