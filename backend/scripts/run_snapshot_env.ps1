param(
  [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

Set-Location $ProjectRoot

# Windows Task Scheduler example:
# Program/script: powershell.exe
# Arguments: -NoProfile -ExecutionPolicy Bypass -File backend\scripts\run_snapshot_env.ps1
# Start in: D:\projects\coin87\coin87Project
#
# Schedule: every 5–15 minutes

Write-Host "Running coin87 Job C snapshot environment..." -ForegroundColor Cyan
python backend\snapshot\job\run_snapshot_env.py
exit $LASTEXITCODE

