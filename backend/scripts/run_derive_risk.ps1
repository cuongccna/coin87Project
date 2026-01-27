param(
  [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

Set-Location $ProjectRoot

# Windows Task Scheduler example:
# Program/script: powershell.exe
# Arguments: -NoProfile -ExecutionPolicy Bypass -File backend\scripts\run_derive_risk.ps1
# Start in: D:\projects\coin87\coin87Project
#
# Schedule: every 5–15 minutes

Write-Host "Running coin87 Job B derive risk..." -ForegroundColor Cyan
python backend\derive\job\run_derive_risk.py
exit $LASTEXITCODE

