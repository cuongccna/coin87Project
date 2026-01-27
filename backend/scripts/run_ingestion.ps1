param(
  [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$SourcesYaml = "",
  [string]$ProxyUrl = ""
)

Set-Location $ProjectRoot

# Optional overrides:
if ($SourcesYaml -ne "") { $env:C87_SOURCES_YAML = $SourcesYaml }
if ($ProxyUrl -ne "") { $env:C87_PROXY_URL = $ProxyUrl }

Write-Host "Running coin87 Job A ingestion..." -ForegroundColor Cyan
python backend\ingestion\jobs\run_ingestion.py
exit $LASTEXITCODE

