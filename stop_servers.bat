@echo off
REM SkillPilot LMS - Windows Shutdown Script

echo ============================================
echo   Stopping SkillPilot LMS
echo ============================================
echo.

REM Stop nginx gracefully
echo Stopping Nginx...
cd C:\nginx
nginx.exe -s quit
timeout /t 2 /nobreak > nul

REM Kill nginx if still running
taskkill /f /im nginx.exe 2>nul

REM Kill Python workers
echo Stopping Python workers...
for /f "tokens=2" %%a in ('tasklist /fi "windowtitle eq SkillPilot*" /fo list ^| find "PID:"') do (
    taskkill /pid %%a /f 2>nul
)

REM Kill any remaining python processes on our ports
for %%p in (5001 5002 5003 5004) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%%p') do (
        taskkill /pid %%a /f 2>nul
    )
)

echo.
echo ============================================
echo   SkillPilot stopped successfully
echo ============================================
