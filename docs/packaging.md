# Campus Guard 打包说明

本文档说明如何把 Campus Guard 打包成本地 Windows 桌面程序。

打包产物只保留在本地 `dist/` 目录中。`dist/`、`build/`、`config.json`、`campus_guard.key` 和日志文件都已被 `.gitignore` 忽略，不应提交到公共仓库。

## 前置条件

- Windows
- Python 3.12
- 已创建 `.venv`
- 已安装 `requirements.txt`

安装依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 一键打包

在仓库根目录执行：

```powershell
.\scripts\package_windows.ps1
```

脚本会先运行单元测试和语法检查，然后调用 PyInstaller：

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean CampusGuard.spec
```

成功后，可执行文件位于：

```text
dist\CampusGuard\CampusGuard.exe
```

脚本还会把 `config.example.json` 复制到 `dist\CampusGuard\`，方便在打包目录中创建本地配置。

如只想快速重新打包并跳过单元测试，可执行：

```powershell
.\scripts\package_windows.ps1 -SkipTests
```

## 首次运行打包版

进入打包目录：

```powershell
cd dist\CampusGuard
```

复制配置模板：

```powershell
Copy-Item config.example.json config.json
```

填写 `config.json` 中的本地配置，包括校园网账号、Bot token、Telegram 用户 ID 和校园 WiFi SSID。

启动程序：

```powershell
.\CampusGuard.exe
```

打包版运行时会把以下本地文件放在 `dist\CampusGuard\`：

- `config.json`
- `campus_guard.key`
- `campus_guard.log`
- `campus_guard.log.*`
- `screenshot_tmp.png`

这些文件包含本地配置、密钥、日志或截图，不要提交。

## 自启动行为

源码运行时，自启动任务会指向 `pythonw.exe` 和 `campus_guard.pyw`。

打包版运行时，自启动任务会直接指向：

```text
dist\CampusGuard\CampusGuard.exe
```

这样移动或发布打包版时，不需要依赖源码入口文件。

## 验证打包结果

建议按 [人工测试手册](manual-testing.md) 执行桌面 App、Bot、网络、电量和资源占用测试。

最小验证项：

1. 双击 `dist\CampusGuard\CampusGuard.exe` 能打开窗口。
2. 系统托盘出现 Campus Guard 图标。
3. “状态 / 控制 / 日志 / 设置”四个标签页可打开。
4. Telegram Bot 能响应 `/ping`。
5. 退出程序后没有残留异常进程。
