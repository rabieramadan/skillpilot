@echo off
REM SkillPilot LMS - Install as Windows Service
REM Requires NSSM (Non-Sucking Service Manager)
REM Download from: https://nssm.cc/download

echo ============================================
echo   Installing SkillPilot as Windows Service
echo ============================================
echo.

REM Check if NSSM exists
where nssm >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: NSSM not found in PATH
    echo Download from: https://nssm.cc/download
    echo Add nssm.exe to C:\Windows or add to PATH
    pause
    exit /b 1
)

set PYTHON_PATH=C:\SkillPilot\venv\Scripts\python.exe
set SCRIPT_PATH=C:\SkillPilot\serve.py
set PROJECT_DIR=C:\SkillPilot

REM Install 4 worker services
echo Installing SkillPilot Worker 1...
nssm install SkillPilot-Worker1 "%PYTHON_PATH%" "%SCRIPT_PATH% --port 5001 --threads 8"
nssm set SkillPilot-Worker1 AppDirectory "%PROJECT_DIR%"
nssm set SkillPilot-Worker1 Start SERVICE_AUTO_START

echo Installing SkillPilot Worker 2...
nssm install SkillPilot-Worker2 "%PYTHON_PATH%" "%SCRIPT_PATH% --port 5002 --threads 8"
nssm set SkillPilot-Worker2 AppDirectory "%PROJECT_DIR%"
nssm set SkillPilot-Worker2 Start SERVICE_AUTO_START

echo Installing SkillPilot Worker 3...
nssm install SkillPilot-Worker3 "%PYTHON_PATH%" "%SCRIPT_PATH% --port 5003 --threads 8"
nssm set SkillPilot-Worker3 AppDirectory "%PROJECT_DIR%"
nssm set SkillPilot-Worker3 Start SERVICE_AUTO_START

echo Installing SkillPilot Worker 4...
nssm install SkillPilot-Worker4 "%PYTHON_PATH%" "%SCRIPT_PATH% --port 5004 --threads 8"
nssm set SkillPilot-Worker4 AppDirectory "%PROJECT_DIR%"
nssm set SkillPilot-Worker4 Start SERVICE_AUTO_START

echo.
echo ============================================
echo   Services installed successfully!
echo ============================================
echo.
echo Start services with:
echo   net start SkillPilot-Worker1
echo   net start SkillPilot-Worker2
echo   net start SkillPilot-Worker3
echo   net start SkillPilot-Worker4
echo.
echo Or start all at once:
echo   sc start SkillPilot-Worker1 ^& sc start SkillPilot-Worker2 ^& sc start SkillPilot-Worker3 ^& sc start SkillPilot-Worker4
echo.
pause
