$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\AI-Trading"
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogDirectory = Join-Path $ProjectRoot "Logs"
$LatestReport = Join-Path $ProjectRoot "Reports\latest\morning_report.html"

New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null

$Timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$LogFile = Join-Path $LogDirectory "morning_report_$Timestamp.log"

Set-Location $ProjectRoot

try {
    & $PythonExe -m Core.morning_report `
        --watchlist default `
        --tf 1d `
        --timeout 120 `
        *> $LogFile

    if ($LASTEXITCODE -ne 0) {
        throw "Morning Report returned exit code $LASTEXITCODE."
    }

    "PATCC Morning Report completed successfully at $(Get-Date)." |
        Add-Content $LogFile

    exit 0
}
catch {
    "PATCC Morning Report failed at $(Get-Date)." |
        Add-Content $LogFile

    $_ |
        Out-String |
        Add-Content $LogFile

    exit 1
}
