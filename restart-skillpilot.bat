@echo off
REM ============================================================
REM  SkillPilot — full restart script
REM  Stops nginx + SkillPilot (service or manual), then starts
REM  them again. Run as Administrator.
REM ============================================================

echo.
echo ========================================
echo   SkillPilot Restart
echo ========================================
echo.

REM ---- 1) Stop SkillPilot Windows service if installed ----
echo [1/6] Stopping SkillPilot service (if installed)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "if (Get-Service SkillPilot -ErrorAction SilentlyContinue) { Stop-Service SkillPilot -Force -ErrorAction SilentlyContinue; Write-Host '      service stopped.' } else { Write-Host '      service not installed, skipping.' }"

REM ---- 2) Kill any manual Waitress (python serve.py) ----
echo [2/6] Killing any manual Waitress processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*serve.py*' } | ForEach-Object { Write-Host ('      killing PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

REM ---- 3) Stop nginx ----
echo [3/6] Stopping nginx...
"C:\nginx-1.28.0\nginx.exe" -p "C:\nginx-1.28.0" -s stop 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-Process nginx -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue"

REM ---- 4) Wait for ports to free up ----
echo [4/6] Waiting 3 seconds for ports to release...
timeout /t 3 /nobreak >nul

REM ---- 5) Start nginx ----
echo [5/6] Starting nginx...
pushd "C:\nginx-1.28.0"
start "" /B nginx.exe
popd
timeout /t 2 /nobreak >nul

REM ---- 6) Start SkillPilot (service if installed, else launch Waitress) ----
echo [6/6] Starting SkillPilot...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "if (Get-Service SkillPilot -ErrorAction SilentlyContinue) { Start-Service SkillPilot; Write-Host '      service started.' } else { Write-Host '      no service installed - launching Waitress in a new window...'; $env:CERTIFICATE_VERIFY_BASE_URL='https://futurecoverage.ai'; Start-Process -FilePath 'C:\Futurecoverage\skillpilot\.venv1\Scripts\python.exe' -ArgumentList 'serve.py','--port','5000','--threads','8' -WorkingDirectory 'C:\Futurecoverage\skillpilot' }"

REM ---- 7) Health check ----
echo.
echo ========================================
echo   Health check
echo ========================================
timeout /t 4 /nobreak >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { $r = Invoke-WebRequest http://127.0.0.1:5000/ -UseBasicParsing -TimeoutSec 10; Write-Host ('  Local  (Waitress): HTTP ' + $r.StatusCode) -ForegroundColor Green } catch { Write-Host '  Local  (Waitress): FAILED' -ForegroundColor Red }; try { $r = Invoke-WebRequest https://futurecoverage.ai/ -UseBasicParsing -TimeoutSec 10; Write-Host ('  Public (nginx)  : HTTP ' + $r.StatusCode) -ForegroundColor Green } catch { Write-Host '  Public (nginx)  : FAILED' -ForegroundColor Red }"

echo.
echo Done.
echo.
pause
