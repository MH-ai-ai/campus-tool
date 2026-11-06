@echo off
chcp 65001 >nul
title Campus Guard
cd /d "%~dp0"

echo ====================================================
echo        Campus Guard 高校校园网守护控制中心
echo ====================================================
echo.

:: 优先检测本地虚拟环境
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
) else (
    set "PY_CMD=python"
)

echo [1/2] 正在校验依赖环境...
call "%PY_CMD%" -m pip install -r requirements.txt --disable-pip-version-check

echo.
echo [2/2] 正在启动客户端...
call "%PY_CMD%" campus_guard.pyw

if errorlevel 1 (
    echo.
    echo ====================================================
    echo [提示] 客户端异常退出，已为您暂停窗口以查看详细原因。
    echo ====================================================
    pause
)
