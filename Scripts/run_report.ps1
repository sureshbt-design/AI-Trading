param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("morning")]
    [string]$ReportType
)

$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\AI-Trading"
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogDirectory = Join-Path $ProjectRoot "Logs"

New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
Set-Location $ProjectRoot

$Timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$LogFile = Join-Path $LogDirectory "${ReportType}_report_$Timestamp.log"

try {
    switch ($ReportType) {
        "morning" {
            & $PythonExe -m Core.morning_report `
                --watchlist default `
                --tf 1d `
                --timeout 120 `
                *> $LogFile
        }
    }

    if ($LASTEXITCODE -ne 0) {
        throw "$ReportType report returned exit code $LASTEXITCODE."
    }

    "PATCC $ReportType report completed successfully at $(Get-Date)." |
        Add-Content $LogFile

    exit 0
}
catch {
    "PATCC $ReportType report failed at $(Get-Date)." |
        Add-Content $LogFile

    $_ | Out-String | Add-Content $LogFile
    exit 1
}
