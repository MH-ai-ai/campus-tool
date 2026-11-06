# Campus Guard 一键启动脚本 (PowerShell)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "       Campus Guard 高校校园网守护控制中心          " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1/2] 正在校验依赖环境..." -ForegroundColor Yellow
python -m pip install -r requirements.txt --quiet

Write-Host "[2/2] 正在启动全新 WebView2 桌面控制中心..." -ForegroundColor Green
Start-Process "pythonw.exe" -ArgumentList "campus_guard.pyw"

Write-Host ""
Write-Host "启动成功！客户端已在后台与 Windows 系统托盘就绪。" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Cyan
Start-Sleep -Seconds 2
