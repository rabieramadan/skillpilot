# SkillPilot Patch Deployer — Safe Edition
$ErrorActionPreference = 'Stop'
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerRoot = "C:\Futurecoverage\skillpilot"
$Port       = 5000
Write-Host "`n  SkillPilot Patch Deployer (Safe Edition)" -ForegroundColor Cyan
Write-Host "  ==========================================" -ForegroundColor Cyan
if (-not (Test-Path $ServerRoot)) { Write-Host "  ERROR: $ServerRoot not found" -ForegroundColor Red; Read-Host; exit 1 }
Write-Host "`n  [1/3] Stopping SkillPilot on port $Port only..." -ForegroundColor Yellow
try {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) { foreach ($c in $conn) { $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue; if ($p) { Stop-Process -Id $p.Id -Force; Write-Host "        Stopped $($p.Name) PID $($p.Id)" -ForegroundColor Gray } }; Start-Sleep 2; Write-Host "        Done." -ForegroundColor Green }
    else { Write-Host "        Nothing on port $Port." -ForegroundColor Gray }
} catch { Write-Host "        Could not check port — continuing." -ForegroundColor DarkYellow }
Write-Host "  [2/3] Copying files..." -ForegroundColor Yellow
foreach ($f in @("app","static","templates")) { $s=Join-Path $ScriptDir $f; if(Test-Path $s){Copy-Item $s $ServerRoot -Recurse -Force; Write-Host "        OK: $f" -ForegroundColor Gray} }
Write-Host "`n  [3/3] Done!`n" -ForegroundColor Green
Write-Host "  Start server:" -ForegroundColor Cyan
Write-Host "    cd $ServerRoot" -ForegroundColor Yellow
Write-Host "    .venv1\Scripts\python serve.py`n" -ForegroundColor Yellow
Write-Host "  Then visit: https://futurecoverage.ai/clear-cache`n" -ForegroundColor Yellow
Read-Host "  Press Enter to close"
