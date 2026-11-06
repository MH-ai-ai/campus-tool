# Campus Guard 一键启动脚本 (PowerShell)
Set-Location $PSScriptRoot

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "       Campus Guard 高校校园网守护控制中心          " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

$py = "python"
if (Test-Path "$PSScriptRoot\.venv\Scripts\python.exe") {
    $py = "$PSScriptRoot\.venv\Scripts\python.exe"
}

Write-Host "[1/2] 正在校验依赖环境..." -ForegroundColor Yellow
$prevEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $py -m pip install -r requirements.txt --disable-pip-version-check
$ErrorActionPreference = $prevEAP

Write-Host ""
Write-Host "[2/2] 正在启动全新 WebView2 桌面控制中心..." -ForegroundColor Green
& $py campus_guard.pyw
