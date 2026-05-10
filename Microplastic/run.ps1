# ══════════════════════════════════════════════════════
#  Microplastic Detection Dashboard — PowerShell Launcher
#  Usage (from any terminal in the project folder):
#    .\run.ps1
# ══════════════════════════════════════════════════════

$PYTHON = "D:\Miniconda3\envs\microplastic\python.exe"
$APP    = Join-Path $PSScriptRoot "app.py"

if (-not (Test-Path $PYTHON)) {
    Write-Host ""
    Write-Host " ERROR: Conda Python not found at:" -ForegroundColor Red
    Write-Host " $PYTHON" -ForegroundColor Red
    Write-Host ""
    Write-Host " Make sure Miniconda is installed at D:\Miniconda3" -ForegroundColor Yellow
    Write-Host " and that you ran: conda create -n microplastic python=3.10" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host " =====================================================" -ForegroundColor Cyan
Write-Host "   µPlastic Detection Dashboard" -ForegroundColor Cyan
Write-Host "   Python : $PYTHON" -ForegroundColor Green
Write-Host "   App    : $APP" -ForegroundColor Green
Write-Host " =====================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host " Open in browser: http://localhost:5000" -ForegroundColor Yellow
Write-Host " Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

& $PYTHON $APP
