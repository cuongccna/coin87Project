param(
  [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

Set-Location $ProjectRoot

# Windows Task Scheduler example:
# Program/script: powershell.exe
# Arguments: -NoProfile -ExecutionPolicy Bypass -File backend\scripts\run_housekeeping.ps1
# Start in: D:\projects\coin87\coin87Project
#
# Schedule: daily (or before IC meetings)

Write-Host "Running coin87 Job D housekeeping/audit..." -ForegroundColor Cyan
python backend\audit\job\run_housekeeping.py
exit $LASTEXITCODE

