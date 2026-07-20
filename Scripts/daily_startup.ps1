$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\AI-Trading"
$ActivateScript = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
$MorningReport = Join-Path $ProjectRoot "Reports\latest\morning_report.html"
$LogFolder = Join-Path $ProjectRoot "Logs"

Set-Location $ProjectRoot

if (-not (Test-Path $ActivateScript)) {
    throw "PATCC virtual environment was not found: $ActivateScript"
}

& $ActivateScript

Write-Host ""
Write-Host ("=" * 72) -ForegroundColor Cyan
Write-Host "PATCC DAILY STARTUP" -ForegroundColor Cyan
Write-Host ("=" * 72) -ForegroundColor Cyan
Write-Host ("Date         : {0}" -f (Get-Date))
Write-Host ("Project root : {0}" -f $ProjectRoot)
Write-Host ("Python       : {0}" -f (Get-Command python).Source)
Write-Host ("Git branch   : {0}" -f (git branch --show-current))

Write-Host ""
Write-Host "MORNING REPORT" -ForegroundColor Cyan

if (Test-Path $MorningReport) {
    $reportItem = Get-Item $MorningReport
    $reportAge = (Get-Date) - $reportItem.LastWriteTime

    Write-Host ("Report       : {0}" -f $reportItem.FullName)
    Write-Host ("Last updated : {0}" -f $reportItem.LastWriteTime)
    Write-Host (
        "Report age   : {0}h {1}m" -f
        [math]::Floor($reportAge.TotalHours),
        $reportAge.Minutes
    )

    if ($reportAge.TotalHours -le 6) {
        Write-Host "Freshness    : FRESH" -ForegroundColor Green
    }
    elseif ($reportAge.TotalHours -le 24) {
        Write-Host "Freshness    : AGING" -ForegroundColor Yellow
    }
    else {
        Write-Host "Freshness    : STALE" -ForegroundColor Red
    }
}
else {
    Write-Host "Morning report not found." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "LATEST MORNING REPORT LOG" -ForegroundColor Cyan

$latestLog = Get-ChildItem `
    -Path $LogFolder `
    -Filter "morning_report_*.log" `
    -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($latestLog) {
    Write-Host ("Log          : {0}" -f $latestLog.FullName)
    Write-Host ("Last updated : {0}" -f $latestLog.LastWriteTime)

    $completionLine = Select-String `
        -Path $latestLog.FullName `
        -Pattern "completed successfully" `
        -SimpleMatch |
        Select-Object -Last 1

    if ($completionLine) {
        Write-Host "Status       : SUCCESS" -ForegroundColor Green
    }
    else {
        Write-Host "Status       : REVIEW LOG" -ForegroundColor Yellow
    }
}
else {
    Write-Host "No morning-report log found." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "GIT STATUS" -ForegroundColor Cyan
git status --short

Write-Host ""
Write-Host ("=" * 72) -ForegroundColor Cyan
Write-Host "PATCC startup completed." -ForegroundColor Green
Write-Host ("=" * 72) -ForegroundColor Cyan

