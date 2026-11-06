@echo off
chcp 65001 >nul
title Campus Guard 一键编译独立 EXE 应用程序
cd /d "%~dp0"

echo ====================================================
echo    Campus Guard 编译独立 Windows 桌面程序 (.EXE)
echo ====================================================
echo.

:: 优先检测本地虚拟环境
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
) else (
    set "PY_CMD=python"
)

echo [1/3] 正在校验编译依赖 (PyInstaller, pythonnet, pywebview)...
call "%PY_CMD%" -m pip install -r requirements.txt pyinstaller --disable-pip-version-check

echo.
echo [2/3] 正在使用 PyInstaller 深度编译独立 EXE 二进制文件...
call "%PY_CMD%" -m PyInstaller CampusGuard.spec --noconfirm --clean

if errorlevel 1 (
    echo.
    echo ====================================================
    echo [错误] 编译生成失败，请检查上方日志。
    echo ====================================================
    pause
    exit /b 1
)

echo.
echo ====================================================
echo [3/3] 编译成功！独立原生应用已生成：
echo 路径: %~dp0dist\CampusGuard\CampusGuard.exe
echo.
echo 提示：您可以直接双击运行 CampusGuard.exe，或者将该快捷方式发送到桌面。
echo 运行时完全脱离控制台黑框与 Python 环境，自带专属 Cyber Shield 图标！
echo ====================================================
echo.
pause
