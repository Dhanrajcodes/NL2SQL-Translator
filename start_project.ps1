Param()

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path $pythonExe)) {
    Write-Host 'Python virtual environment not found at .venv\Scripts\python.exe' -ForegroundColor Red
    Write-Host 'Create it first, then install dependencies.' -ForegroundColor Yellow
    exit 1
}

Write-Host 'Starting NL2SQL services...' -ForegroundColor Cyan

$backend = Start-Process -FilePath $pythonExe -ArgumentList '-m','app.app' -WorkingDirectory $projectRoot -PassThru
$frontend = Start-Process -FilePath $pythonExe -ArgumentList '-m','streamlit','run','app/ui.py' -WorkingDirectory $projectRoot -PassThru

Write-Host "Backend PID: $($backend.Id) (http://localhost:5000)" -ForegroundColor Green
Write-Host "Frontend PID: $($frontend.Id) (http://localhost:8501)" -ForegroundColor Green
Write-Host 'Use Stop-Process -Id <PID> to stop a service.' -ForegroundColor Yellow
