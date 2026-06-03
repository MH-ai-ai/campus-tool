# Campus Guard

Campus Guard 是一个 Windows 桌面守护工具，用于在校园网环境中自动维持联网状态，并通过 Telegram Bot 提醒网络、电源、电量和资源异常。

当前版本保留 `campus_guard.pyw` 作为兼容入口，核心逻辑已拆到 `campus_guard/` 包内，便于测试和后续维护。

## 功能

- 网络断开后快速检测并自动重连校园 WiFi 与 Dr.COM 认证。
- 网络探测分为直连与代理两个平面，校园网认证请求会绕过 Python 代理环境，适配 Clash 全局代理或 TUN 场景。
- 检测到 `198.18.x.x` 或 `198.19.x.x` 本机地址时，在网络状态和通知中标明 Clash/TUN 状态。
- 断网、重连成功、断电、电量阈值、自动关机等事件通过 Telegram Bot 通知；Telegram 不可达时先本地排队，恢复后补发。
- 电量在 50%、30%、20% 阈值各提醒一次；20% 及以下触发 60 秒后自动关机，可通过 Bot 取消。
- 桌面端使用 PyQt6，提供状态、控制、日志、设置四个页面，并常驻托盘后台运行。
- 空闲状态下使用低频定时与缓存，避免 UI 定时器执行阻塞公网请求，并限制日志读取长度。

## 环境

- Windows
- Python 3.12，项目声明支持 `>=3.12,<3.14`
- 依赖见 `requirements.txt`

建议在 PowerShell 中创建本地虚拟环境：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`.venv/` 已被 `.gitignore` 忽略，不应提交。

## 配置

复制无敏感值模板：

```powershell
Copy-Item config.example.json config.json
```

然后填写本地配置：

- `campus_auth_url`：校园网认证地址。
- `campus_gateway`：校园网网关探测地址。
- `campus_account` / `campus_password`：校园网账号与密码。
- `wlan_ac_ip`：Dr.COM 认证参数中的 AC IP。
- `campus_wifi_ssids`：可自动重连的校园 WiFi 名称列表。
- `telegram_bot_token` / `telegram_user_id`：Telegram Bot token 与允许控制的用户 ID。
- `network_check_interval_seconds`：网络探测间隔，默认 2 秒。
- `battery_warning_thresholds`：电量提醒阈值，默认 `[50, 30, 20]`。
- `auto_shutdown_threshold` / `auto_shutdown_delay`：自动关机阈值与倒计时，默认 20% 和 60 秒。
- `reconnect_max_retries` / `reconnect_verify_delay_seconds` / `reconnect_fast_retry_seconds`：重连次数与验证节奏。

首次运行时，`campus_password` 和 `telegram_bot_token` 会在本地 `config.json` 中加密，并生成 `campus_guard.key`。`config.json`、`campus_guard.key`、`campus_guard.log*` 都已被 `.gitignore` 忽略。

## 运行

开发时可使用：

```powershell
.\.venv\Scripts\python.exe campus_guard.pyw
```

如果希望无控制台窗口运行，可使用对应环境的 `pythonw.exe`：

```powershell
.\.venv\Scripts\pythonw.exe campus_guard.pyw
```

程序启动后会初始化日志、读取并加密本地配置、启动监控线程、启动 Telegram Bot 线程，并显示 PyQt6 主窗口。开启 `autostart` 时，会在 Windows Task Scheduler 注册自启动任务。

## 打包

生成本地 Windows 桌面程序：

```powershell
.\scripts\package_windows.ps1
```

打包产物位于：

```text
dist\CampusGuard\CampusGuard.exe
```

`dist/` 和 `build/` 已被 `.gitignore` 忽略，不会上传到公共仓库。打包版需要在 `dist\CampusGuard\` 中放置本地 `config.json`，详见 [docs/packaging.md](docs/packaging.md)。

## Telegram 命令

Telegram 的 slash command 名称必须使用英文、数字或下划线；Bot 菜单使用英文命令名加中文描述。

| 命令 | 说明 |
| --- | --- |
| `/status` | 查看电量、电源、网络状态 |
| `/network` | 查看网络、网关、代理和 Clash/TUN 状态 |
| `/battery` | 查看电量、供电和关机阈值 |
| `/shutdown` | 远程关机，需二次确认 |
| `/cancel_shutdown` | 取消关机倒计时 |
| `/cancel` | 兼容的取消关机别名 |
| `/reconnect` | 手动重连校园网 |
| `/lock` | 锁定屏幕 |
| `/screenshot` | 截取屏幕，需二次确认 |
| `/ip` | 查看局域网与公网 IP |
| `/ping` | 测试 Bot 是否在线 |
| `/log [N]` | 查看最近 N 行日志，默认 20 行，最多 200 行 |
| `/restart` | 重启程序 |
| `/config` | 查看当前配置，敏感字段会遮罩 |
| `/help` | 显示帮助 |

## 测试

核心包导入不应读取真实 `config.json`、初始化日志文件或导入 PyQt6：

```powershell
.\.venv\Scripts\python.exe -c "import campus_guard; from campus_guard.auth import build_auth_params"
```

运行单元测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

语法检查：

```powershell
.\.venv\Scripts\python.exe -m py_compile campus_guard.pyw tests/test_campus_guard.py campus_guard\models.py campus_guard\config.py campus_guard\auth.py campus_guard\system.py campus_guard\battery.py campus_guard\network.py campus_guard\telegram_bot.py campus_guard\runtime.py campus_guard\ui.py
```

验证 PyQt6 安装：

```powershell
.\.venv\Scripts\python.exe -c "from PyQt6.QtWidgets import QApplication"
```

## 项目结构

| 路径 | 作用 |
| --- | --- |
| `campus_guard.pyw` | 兼容启动器 |
| `campus_guard/models.py` | 配置、运行状态、网络状态类型 |
| `campus_guard/config.py` | 配置加载、保存、加密、热重载 |
| `campus_guard/auth.py` | Dr.COM 参数构造、响应解析、校园网认证 |
| `campus_guard/system.py` | IP、MAC、WiFi、网络探测、磁盘和内存工具 |
| `campus_guard/network.py` | 网络状态机、快速探测、自动重连 |
| `campus_guard/battery.py` | 电量阈值、断电提醒、自动关机 |
| `campus_guard/telegram_bot.py` | Telegram Bot、命令菜单、通知队列 |
| `campus_guard/ui.py` | PyQt6 桌面窗口、托盘和设置页 |
| `campus_guard/runtime.py` | 运行入口、线程启动、定时监控 |
| `tests/test_campus_guard.py` | 核心测试契约 |

## 文档

- `PRODUCT.md`：产品目标、用户和原则。
- `DESIGN.md`：当前桌面 UI 的设计约束。
- [docs/packaging.md](docs/packaging.md)：Windows 打包和打包版运行说明。
- [docs/manual-testing.md](docs/manual-testing.md)：桌面 App、Bot、网络、电量和资源占用的人工测试手册。
- `config.example.json`：无敏感值配置模板。

## 隐私与提交

公共仓库只应提交源码、测试和无敏感值文档。不要提交：

- `config.json`
- `campus_guard.key`
- `campus_guard.log*`
- `.venv/`
- 本地截图和临时脚本

本轮不处理历史凭据轮换或既有本地明文文件；仓库卫生配置只负责阻止后续误提交。
