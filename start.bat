@echo off
chcp 65001 >nul
title Campus Guard 一键启动
cd /d "%~dp0"

echo ====================================================
echo        Campus Guard 高校校园网守护控制中心
echo ====================================================
echo.
echo [1/2] 正在校验依赖环境...
python -m pip install -r requirements.txt --quiet

echo.
echo [2/2] 正在启动全新 WebView2 桌面控制中心...
start "" pythonw campus_guard.pyw

echo.
echo ====================================================
echo  启动成功！客户端已在后台与 Windows 系统托盘就绪。
echo ====================================================
timeout /t 3 >nul
