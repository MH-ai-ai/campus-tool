# Campus Guard 人工测试手册

本文档用于人工验收 Campus Guard 的桌面 App、Telegram Bot、网络重连、Clash 兼容、电量提醒、自动关机取消、资源占用和清理恢复流程。

低电量关机测试采用安全模式：只验证 60 秒关机倒计时触发和取消能力，不让电脑真正关机。

## 测试记录

建议每次人工测试记录以下信息：

| 项目 | 内容 |
| --- | --- |
| 测试日期 |  |
| Windows 版本 |  |
| Python 版本 |  |
| 校园 WiFi SSID |  |
| Clash 模式 | 关闭 / 全局代理 / TUN |
| App 启动方式 | `python.exe campus_guard.pyw` / `pythonw.exe campus_guard.pyw` |
| 结论 | 通过 / 有缺陷 / 阻塞 |

不要把 `config.json`、Bot token、校园网账号密码、日志中的敏感片段或桌面截图提交到公共仓库。

## 1. 基础准备

1. 确认只运行一个 Campus Guard 实例。

   如果已经有旧实例在运行，先从系统托盘右键退出。不要同时启动多个实例，否则 Bot polling、日志和网络检测结果会互相干扰。

2. 确认测试环境满足条件。

   - 当前电脑在 Windows 上运行。
   - 当前环境可以连接校园 WiFi。
   - `config.json` 已填入真实校园网账号、Telegram Bot token、Telegram 用户 ID 和校园 WiFi SSID。
   - Telegram Bot 能从你的授权账号收发消息。
   - 如需测试 Clash，Clash 可以手动切换全局代理和 TUN。

3. 在仓库根目录执行基础检查。

   ```powershell
   git status --short --branch
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   .\.venv\Scripts\python.exe -m py_compile campus_guard.pyw tests/test_campus_guard.py campus_guard\models.py campus_guard\config.py campus_guard\auth.py campus_guard\system.py campus_guard\battery.py campus_guard\network.py campus_guard\telegram_bot.py campus_guard\runtime.py campus_guard\ui.py
   .\.venv\Scripts\python.exe -c "import campus_guard; from campus_guard.auth import build_auth_params; import sys; print('PyQt6' in sys.modules)"
   .\.venv\Scripts\python.exe -c "from PyQt6.QtWidgets import QApplication; print('pyqt ok')"
   ```

   预期结果：

   - `git status` 不显示待提交的敏感文件。
   - 单元测试全部通过。
   - `py_compile` 无输出。
   - 核心导入命令打印 `False`，说明包导入未加载 PyQt6。
   - PyQt6 检查打印 `pyqt ok`。

4. 备份本地配置到仓库外。

   ```powershell
   Copy-Item config.json "$env:TEMP\campus_guard_config_backup.json"
   ```

   后续低电量测试会临时改本地配置。备份文件放在系统临时目录，避免误提交到 Git。

## 2. 桌面 App 启动与基础 UI

1. 用控制台方式启动 App，便于观察启动错误。

   ```powershell
   .\.venv\Scripts\python.exe campus_guard.pyw
   ```

2. 验证主窗口。

   预期结果：

   - 窗口标题为 `Campus Guard`。
   - 有“状态”“控制”“日志”“设置”四个标签页。
   - 系统托盘出现 Campus Guard 图标。
   - 程序启动后不会立即卡死或退出。

3. 验证“状态”页。

   在状态页等待 10 秒，至少经历两次 UI 刷新。

   预期结果：

   - 能看到电池和供电状态。
   - 能看到 WiFi、本机 IP、网关、直连外网、代理外网、Clash/TUN。
   - 能看到最近事件、磁盘剩余和内存占用。
   - 页面刷新时没有明显卡顿。

4. 验证托盘行为。

   - 点击窗口右上角关闭。
   - 预期窗口隐藏，但程序仍在托盘运行。
   - 双击托盘图标。
   - 预期窗口恢复显示。

5. 验证“日志”页。

   切换到日志页，等待几秒。

   预期结果：

   - 日志可以增量显示。
   - 切换页面和滚动日志不卡顿。
   - 日志页不会重复加载完整日志导致明显延迟。

6. 验证“设置”页输入校验。

   - 打开“设置”页。
   - 确认 `campus_password` 和 `telegram_bot_token` 等敏感字段是密码输入框。
   - 把 `battery_warning_thresholds` 临时填成 `abc` 并保存。
   - 预期出现“battery_warning_thresholds 必须是数字列表”错误。
   - 恢复为 `50, 30, 20` 并保存。
   - 预期显示配置保存成功。

## 3. Telegram Bot 与菜单

1. 打开 Telegram 中的 Campus Guard Bot。

   预期左下角命令菜单已注册。命令名应为英文、数字或下划线，描述为中文。

2. 依次发送命令。

   ```text
   /ping
   /status
   /network
   /battery
   /config
   /log 20
   /help
   ```

3. 验证响应内容。

   预期结果：

   - `/ping` 返回程序运行正常。
   - `/status` 包含电量、电源、WiFi、网络和运行时间。
   - `/network` 包含 WiFi、本机 IP、网关、直连外网、代理外网、Clash/TUN。
   - `/battery` 包含电量、提醒阈值和自动关机策略。
   - `/config` 中 `campus_password` 和 `telegram_bot_token` 被遮罩。
   - `/log 20` 返回最近日志，不超过 Telegram 消息长度限制。
   - `/help` 列出当前支持的命令。

4. 验证授权边界。

   从非授权 Telegram 账号发送 `/status`。

   预期结果：Bot 不返回敏感信息。若无响应，视为通过。

## 4. 网络断开与自动重连

1. 建立基线。

   - 关闭 Clash。
   - 保持校园 WiFi 在线。
   - 发送 `/network`。

   预期结果：网络状态在线，网关和直连外网可用。

2. 执行 WiFi 断开测试。

   使用 Windows 快捷面板断开 WLAN，或执行：

   ```powershell
   netsh wlan disconnect
   ```

   预期结果：

   - 2 到 5 秒内，桌面状态页变为离线，或最近事件显示网络断开。
   - 如果电脑完全没有通向 Telegram 的网络路径，断网提醒可以暂时不到达。

3. 等待自动重连。

   App 会尝试连接配置中的 `campus_wifi_ssids`，随后执行校园网认证和连通性验证。

   预期结果：

   - WiFi 可自动恢复连接。
   - 恢复后 Bot 收到重连成功通知。
   - 通知包含 WiFi、本机 IP、网关、直连外网、代理外网、Clash/TUN、耗时和尝试次数。

   如果 30 秒仍未恢复，手动重新连接校园 WiFi，继续后续测试，并记录自动重连失败。

4. 执行校园网认证失效测试。

   在校园网门户执行注销，或用学校提供的方式让认证失效，同时保持 WiFi 链路不断开。

   预期结果：

   - App 识别为网关可达但直连外网不通。
   - App 自动调用 Dr.COM 认证。
   - 成功后桌面状态页和 Bot 都显示网络恢复。

## 5. Clash 全局代理和 TUN 兼容

1. 开启 Clash 全局代理。

   发送：

   ```text
   /network
   ```

   预期结果：

   - 代理外网为 OK。
   - 直连外网仍应可用于校园网认证。
   - 如果 App 显示 Clash/TUN 检测到，后续断网和恢复通知中也应出现该状态。

2. 开启 Clash TUN。

   如果系统本机地址实际进入 `198.18.x.x` 或 `198.19.x.x`，预期 App 显示：

   ```text
   Clash/TUN: 检测到
   ```

   如果 TUN 已开启但 App 仍显示未检测到，记录为缺陷。

3. 在 Clash 开启状态下再次执行校园网认证失效测试。

   预期结果：

   - 校园网认证请求不走 Python 代理环境。
   - App 仍能恢复校园网。
   - 若关闭 Clash 后恢复成功、开启 Clash 时失败，记录为 Clash DIRECT 规则或 TUN 路由问题。

## 6. 电量、断电和安全关机

1. 建立电源基线。

   - 保持 App 运行。
   - 接通电源。
   - 等待状态页出现初始电源状态。

2. 测试断电提醒。

   拔掉电源。

   预期结果：

   - Bot 收到断电提醒。
   - 桌面状态页显示电池供电。

3. 快速验证电量阈值提醒。

   不等待自然放电。打开“设置”页，把 `battery_warning_thresholds` 临时设置为高于当前电量的三个值。

   示例：当前电量为 80%，填：

   ```text
   85, 84, 83
   ```

   保存后保持电池供电。

   预期结果：

   - Bot 发送三个阈值提醒。
   - 每个阈值只提醒一次。
   - 恢复供电后，阈值提醒状态被重置。

4. 安全验证自动关机倒计时。

   确认网络在线，然后把 `auto_shutdown_threshold` 临时设置为高于当前电量，`auto_shutdown_delay` 保持 `60`。

   保存后拔掉电源。

   预期结果：

   - Bot 收到“将在 60 秒后自动关机”提醒。
   - Windows 已启动关机倒计时。

5. 立即取消关机。

   先在 Telegram 发送：

   ```text
   /cancel_shutdown
   ```

   再在本机 PowerShell 执行兜底取消：

   ```powershell
   shutdown /a
   ```

   预期结果：

   - Bot 回复已取消关机。
   - 电脑没有实际关机。

6. 恢复默认电量配置。

   在设置页恢复：

   ```text
   battery_warning_thresholds = 50, 30, 20
   auto_shutdown_threshold = 20
   auto_shutdown_delay = 60
   ```

   保存后发送 `/battery`。

   预期结果：Bot 显示阈值为 `50, 30, 20`，自动关机策略为 `≤20% 后 60s`。

## 7. 控制页功能

1. 点击“校园网认证”。

   预期结果：状态提示认证成功，或给出明确失败原因。

2. 点击“重连 WiFi”。

   此操作会短暂断网。测试前暂停下载、会议、远程连接等重要网络任务。

   预期结果：App 尝试连接配置中的校园 SSID，并显示成功或失败状态。

3. 点击“截屏”。

   测试前关闭隐私窗口。

   预期结果：

   - 生成 `screenshot_tmp.png`。
   - 没有异常弹窗。
   - `_screenshot.ps1` 仅作为临时脚本出现，执行后被清理。

4. 按需测试“锁屏”和“重启工具”。

   这两个操作会中断当前会话。只在确认可以中断时测试。

## 8. 资源占用与磁盘占用

1. 让 App 在线空闲运行 10 分钟。

   期间不要频繁点击 UI，也不要主动触发网络重连。

2. 用任务管理器观察进程。

   观察 `python.exe` 或 `pythonw.exe`。

   预期结果：

   - 空闲 CPU 平均低于 1%。
   - 内存没有持续上涨趋势。
   - UI 仍可响应。

3. 检查日志大小。

   `campus_guard.log` 使用轮转日志：

   - 单个日志文件最大约 1 MB。
   - 最多保留 3 个备份。
   - 日志总量约不超过 4 MB。

4. 检查状态页资源显示。

   预期结果：

   - 磁盘剩余和内存占用能显示。
   - 刷新时 UI 不因公网 IP 或网络请求卡死。

## 9. 清理恢复

1. 取消任何残留关机倒计时。

   ```powershell
   shutdown /a
   ```

2. 恢复测试前配置。

   ```powershell
   Copy-Item "$env:TEMP\campus_guard_config_backup.json" config.json
   ```

3. 重启 App。

   发送：

   ```text
   /battery
   ```

   预期结果：阈值和自动关机策略恢复为测试前配置。

4. 从托盘退出 App。

   预期结果：窗口关闭，托盘图标消失，后台线程结束。

5. 检查 Git 状态。

   ```powershell
   git status --short --branch
   ```

   预期结果：没有 `config.json`、`campus_guard.key`、`campus_guard.log*`、截图或临时脚本被加入 Git。

## 验收标准

- 桌面 App 可启动、隐藏到托盘、恢复窗口、退出，四个页面可用且不卡顿。
- Bot 菜单、授权、状态查询、日志查询、配置遮罩、重连和取消关机均工作。
- 网络断开后 2 秒级进入异常状态，可自动重连。
- Telegram 不可达时，断网通知可在恢复后补发。
- Clash 全局代理或 TUN 开启时，校园网认证仍可绕过 Python 代理环境完成。
- 断电、阈值提醒、关机倒计时和取消关机链路可验证，且测试中电脑不实际关机。
- 空闲 CPU、内存和日志体积符合低功耗、低磁盘占用目标。

## 常见问题

### 断网提醒没有立刻到 Telegram

如果电脑已经完全没有通向 Telegram 的网络路径，断网提醒无法实时送达。预期行为是先在本地排队，网络恢复后补发断网和恢复信息。

### Clash TUN 开启但 App 显示未检测到

当前检测依据是本机 IP 是否落在 `198.18.x.x` 或 `198.19.x.x`。如果 Clash TUN 没有让 App 看到这类地址，测试记录为缺陷或环境差异。

### 自动关机倒计时已经出现

立即发送 `/cancel_shutdown`，并在本机执行：

```powershell
shutdown /a
```

确认 Windows 不再提示即将关机后，再继续测试。

### WiFi 重连失败

先确认 `campus_wifi_ssids` 中的 SSID 与 Windows 已保存的 WiFi 配置名称一致。若 App 不能自动恢复，手动连回校园 WiFi，记录失败时间、SSID 和日志片段。
