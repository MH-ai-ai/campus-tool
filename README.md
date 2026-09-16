# 🛡️ Campus Guard (校园网守护者)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12%20%7C%203.13-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Platform" />
  <img src="https://img.shields.io/badge/UI-Apple%20HIG%20%7C%20PyQt6-000000?style=for-the-badge&logo=apple&logoColor=white" alt="Apple Design System" />
  <img src="https://img.shields.io/badge/Notifications-Telegram%20%7C%20%E9%A3%9E%E4%B9%A6%20%7C%20%E9%92%89%E9%92%89-FF8800?style=for-the-badge" alt="Multi-Channel Notifications" />
  <img src="https://img.shields.io/badge/Tests-24%20Passed-30D158?style=for-the-badge" alt="Tests" />
</p>

> **专为高校宿舍、实验室与图书馆打造的 Windows 全能网络与电源守护神器。**  
> **本工具以延安大学（Yan'an University）校园网（Dr.COM ePortal 体系）为原型开发并深度优化**，广泛兼容国内各类采用同架构 Web 认证的高校。支持掉线毫秒级自动重连、家庭与校园网智能感知、国内免梯（飞书/钉钉）双向告警、20% 电量安全关机守护，并配备全新 **Apple HIG 苹果深色设计系统**与 **小白「⚡ 10秒一键配网」**。

---

## ⚡ 痛点与解决方案

| 传统痛点 | Campus Guard 创新解法 |
| :--- | :--- |
| **夜间断网/掉线**：半夜或离开实验室时校园网断开，下载中断、远程无法连接。 | **全自动毫秒感知与重连**：后台非阻塞探针毫秒级侦测断网，全自动重连 Wi-Fi 并执行 Dr.COM 登录。 |
| **小白配网门槛高**：不清楚什么是网关 IP、AC IP、Portal 地址，配置复杂劝退。 | **「⚡ 一键智能打通」**：基于 Captive Portal 302 劫持自动嗅探网关与服务器，弹窗**仅需填写学号密码**即可瞬间打通。 |
| **通知受限**：Telegram Bot 在国内无梯环境下无法接收消息。 | **国内免梯平台直通**：原生支持**飞书自适应彩色交互卡片**与**钉钉加签 Markdown**，双通道并行推送、互为容灾。 |
| **频繁定位打扰**：后台高频执行 Wi-Fi 探针导致 Windows 任务栏频繁闪烁“正在使用您的位置”小圆点。 | **长效缓存与内核被动监听**：采用 `psutil` 内核链路监听与 120 秒智能缓存，彻底消灭 Windows 位置提示。 |
| **寝室断电电池耗尽**：宿舍半夜断电导致笔记本过放损坏电池或意外关机丢数据。 | **三档电量告警与安全关机**：50%、30%、20% 梯次报警；20% 自动启动 60 秒可撤销关机保护。 |
| **界面陈旧呆板**：传统工具 UI 简陋突兀，夜间刺眼。 | **Apple HIG 苹果设计系统**：深空灰微光背景、Squircle 连续平滑圆角、状态呼吸指示药丸与内嵌分组列表。 |

---

## 🏫 原型背景与高校通用性

- **🎯 原型母体（延安大学）**：
  本项目最初以**延安大学（Yan'an University, YAU）**校园网络环境为原型进行深度定制与测试。延安大学校园网采用标准的 **Dr.COM (城市热点) ePortal** 网页认证体系：
  - **默认认证服务地址**：`http://10.200.84.3:801/eportal/portal/login`
  - **默认 AC 控制器 IP**：`10.255.250.74`
  - **典型网关内网路由**：`10.212.0.1` / `10.200.84.3`
  - 完美适配新校区（新城校区）、杨家岭校区及萃园等学生宿舍区、图书馆与实验室的校园 Wi-Fi 及有线以太网环境。
- **🌐 广泛的高校通用性**：
  - 尽管扎根于延安大学，但国内绝大多数高校均采用同类的 Dr.COM / 锐捷 / 深信服等 Web 认证网关；
  - 借助全新升级的 **「⚡ 一键智能打通」** 嗅探引擎，其他高校的同学只需连上各自学校的校园 Wi-Fi 并点击一键打通，系统即可自适应捕获参数并瞬间打通；
  - 亦可直接在「偏好设置」中手动自定义输入任意高校的认证 Portal 地址与 AC 控制器 IP。

---

## 🌟 核心特性概览

### 1. ⚡ 小白首次「一键智能配网」
- 新用户首次连上校园 Wi-Fi 后，只需点击仪表盘顶部的「⚡ 校园网一键打通」横幅；
- 引擎自动通过未加密 HTTP 直连探针拦截 Captive Portal 重定向，提取认证服务器 URL、网关 IP、AC IP 与 SSID；
- 弹窗仅需输入**学号**与**密码**，点击「立即保存并连接」，10 秒内打通全流程并写入高强度本地加密存储。

### 2. 🍏 全新 Apple HIG (Human Interface Guidelines) 苹果设计系统
- **深空灰微光层次**：主背景采用 macOS 原生深空灰（`#141417`），搭配精致毛玻璃卡片（`#212128`）与半透明高光微边框；
- **Squircle 连续平滑圆角**：卡片统一采用 14px 苹果平滑圆角（`_AppleCard`），视觉浑然一体；
- **状态呼吸药丸 (Status Pills)**：发光状态指示灯（● 绿色在线、▲ 橙色告警、■ 红色故障、○ 离线），状态扫视一目了然；
- **macOS Grouped Insets 分组内嵌列表**：设置面板重构为 macOS 系统偏好设置风格，内嵌微阴影输入框，层级井然；
- **高质量平滑抗锯齿字体**：全界面采用矢量字体栈，杜绝 Windows DirectWrite 字体回退警告。

### 3. 🔕 彻底消除任务栏频繁定位烦扰
- 深入排查并根治 `netsh wlan show interfaces` 唤醒底层 AP 扫描被 Windows 判定为位置请求的底层逻辑；
- 采用 **内核网络链路被动监听**（`psutil.net_if_stats`）结合 **120 秒长效状态缓存**，在稳定在线时零主动触发外部探针，保持极致静默。

### 4. 🔔 多平台通知引擎与容灾中心
- **飞书自定义机器人**：
  - 发送高颜值自适应彩色交互卡片（Interactive Cards）；
  - 故障报警显示亮红、恢复上线显示翠绿、弱网与电量提示显示橙色；
  - 手机端飞书即时振动推送，排版美观、层次清晰。
- **钉钉自定义机器人**：
  - 支持企业级安全的 HMAC-SHA256 动态加签防重放攻击；
  - 消息自动生成易读的结构化 Markdown 排版。
- **Telegram Bot 远程运维**：
  - 支持 Telegram 双向交互、快捷内联按钮面板与远程控制菜单。
  - 三大平台多通道并行异步广播，无梯环境国内通道稳定送达，互为容灾备份。

### 5. 🌐 智能网络环境感知 (Campus vs. Home)
- 根据连接 Wi-Fi SSID 自动感知当前处于「校园网环境」还是「家庭/常用免认证网络」；
- 在家庭网络或手机热点下，系统自动屏蔽校园网关超时报警与重复登录重试，仅保持网络连通性与电源电量守护。

---

## 🚀 快速上手指南

### 1. 环境准备
- **操作系统**：Windows 10 / Windows 11
- **Python 环境**：Python 3.12 或 3.13（推荐使用独立虚拟环境）

在 PowerShell 中拉取代码并初始化环境：
```powershell
git clone https://github.com/MH-ai-ai/campus-tool.git
cd campus-tool

# 创建并激活虚拟环境
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. 启动应用
- **🟢 推荐日常运行（静默无黑框，直接启动苹果风主窗口并常驻托盘）**：
  ```powershell
  & ".\.venv\Scripts\pythonw.exe" "campus_guard.pyw"
  ```
  *(或在资源管理器中直接双击 `campus_guard.pyw` 启动)*

- **🔍 调试开发运行（带控制台日志输出）**：
  ```powershell
  & ".\.venv\Scripts\python.exe" "campus_guard.pyw"
  ```

### 3. 小白 10 秒打通全流程
1. 启动程序后，主窗口将呈现全新的苹果风仪表盘；
2. 确保电脑已连接学校无线网，点击顶部的 **「⚡ 校园网一键打通」** 醒目横幅；
3. 程序自动嗅探并填充网关与服务器参数，在弹出的极简窗口中输入您的**学号**与**校园网密码**；
4. 点击「🚀 一键保存并登录」，即可打通全部网络并启动后台守护！

---

## ⚙️ 配置文件说明 (`config.json`)

系统首次运行时会自动根据 `config.example.json` 生成本地加密配置文件 `config.json`，敏感字段（校园网密码、Bot Token）均在本地通过 `cryptography.fernet` 自动加密存储，绝不泄露。

| 配置键名 | 类型 | 说明 | 示例 / 默认值 |
| :--- | :--- | :--- | :--- |
| `campus_auth_url` | 字符串 | 校园网 Dr.COM 认证提交地址（支持一键嗅探） | `"http://10.200.84.3:801/eportal/portal/login"` |
| `campus_gateway` | 字符串 | 校园网内网网关探测 IP（支持一键嗅探） | `"10.200.84.3"` |
| `campus_account` | 字符串 | 校园网认证学号 / 账号 | `""` |
| `campus_password` | 字符串 | 校园网认证密码（本地高强度加密） | `""` |
| `wlan_ac_ip` | 字符串 | 认证 AC 控制器 IP（支持一键嗅探） | `"10.255.250.74"` |
| `campus_wifi_ssids` | 列表 | 视为校园网的 Wi-Fi SSID 列表 | `["Campus-WiFi", "EDUROAM"]` |
| `trusted_home_ssids`| 列表 | 信任的家庭 / 免认证 Wi-Fi 列表 | `["Home_5G", "Pixel_Hotspot"]` |
| `forced_network_mode`| 字符串 | 网络环境模式：`auto` (自动感知) / `campus` / `home` | `"auto"` |
| `feishu_webhook_url`| 字符串 | 飞书自定义机器人 Webhook 地址（免梯推荐） | `""` |
| `dingtalk_webhook_url`| 字符串 | 钉钉自定义机器人 Webhook 地址（免梯推荐） | `""` |
| `dingtalk_secret` | 字符串 | 钉钉自定义机器人 HMAC-SHA256 加签密钥 | `""` |
| `telegram_bot_token`| 字符串 | Telegram Bot Token（可选容灾） | `""` |
| `telegram_user_id` | 整数 | 允许控制该 Bot 的 Telegram 个人数字 ID | `0` |
| `battery_warning_thresholds` | 列表 | 电量梯次报警百分比阈值 | `[50, 30, 20]` |
| `auto_shutdown_threshold` | 整数 | 触发自动安全关机的电量百分比 | `20` |
| `auto_shutdown_delay` | 整数 | 自动关机触发后的缓冲倒计时（秒） | `60` |
| `autostart` | 布尔 | 随 Windows 开机自动静默启动 | `true` |

---

## 🤖 远程控制指令集 (Telegram / 快捷按钮)

在 Telegram 中向 Bot 发送消息，或点击回复消息中附带的 **内联快捷按钮 (Inline Keyboard)** 即可完成远程控制：

| 命令 | 说明 |
| :--- | :--- |
| `/status` | 综合看板：即时查询网络、电量、供电及系统资源，附带全套快捷内联操作按钮 |
| `/network` | 网络专报：查看活动物理网卡、网关连通、外网连通与 Clash/TUN 状态 |
| `/battery` | 电量专报：查看供电状态、当前电量与关机保护阈值 |
| `/mode` | 环境模式：查看当前网络感知模式，支持一键切换模式（自动 / 校园网 / 家庭网） |
| `/wifi` | 无线扫描：扫描并列出周围所有可见 Wi-Fi 的 SSID、信号强度与加密类型 |
| `/reconnect`| 手动重连：立刻重新连接校园 Wi-Fi 并执行 Dr.COM 登录认证 |
| `/logout` | 主动下线：注销当前校园网登录状态，释放账号在线设备配额 |
| `/lock` | 远程锁屏：即时锁定 Windows 桌面屏幕，保护个人隐私 |
| `/screenshot`| 远程截屏：截取当前屏幕并通过消息发送（附带二次确认保护） |
| `/shutdown` | 远程关机：触发 60 秒关机倒计时（支持随时通过 `/cancel` 撤销） |
| `/log [N]` | 日志调阅：查看最近 N 行日志（默认 20 行，最多 200 行） |
| `/restart` | 程序重启：优雅重启守护主进程 |

---

## 📦 Windows 打包发布

本项目内置一键打包脚本，可生成完全独立、免安装的单目录便携式执行程序：

```powershell
.\scripts\package_windows.ps1
```

打包产物位于：
```text
dist\CampusGuard\CampusGuard.exe
```
打包版内置自动释放配置模板与加密机制，直接复制整个 `dist\CampusGuard` 目录即可在任意无 Python 环境的 Windows 电脑上运行。

---

## 🧪 测试与质量验证

项目包含严密的单元测试套件，全面覆盖 Captive Portal 嗅探、飞书/钉钉卡片构造、Wi-Fi 防频繁定位长效缓存与网络状态机：

- **运行全量自动化测试**：
  ```powershell
  .\.venv\Scripts\python.exe -m unittest discover -s tests -v
  ```
  *(24 项核心测试 100% 通过，平均执行耗时 < 0.3 秒)*

- **全量静态语法检查**：
  ```powershell
  .\.venv\Scripts\python.exe -m compileall -q campus_guard tests campus_guard.pyw
  ```

---

## 📁 项目工程结构

```text
campus-tool/
├── campus_guard.pyw            # 启动器入口（双击直接无黑框运行）
├── campus_guard/               # 核心源码包
│   ├── auth.py                 # Dr.COM 认证协议、注销下线与 Captive Portal 302 嗅探
│   ├── battery.py              # 电池电量多级告警、断电感知与自动关机守护
│   ├── config.py               # 配置加载、AES 加密存储、热重载与动态更新
│   ├── logging_setup.py        # 日志系统初始化与滚动日志记录
│   ├── models.py               # 数据模型（配置项、网络模式、守护状态枚举）
│   ├── network.py              # 智能环境感知、异步非阻塞探针与自动重连状态机
│   ├── notifier.py             # [新] 统一通知中心（飞书彩色卡片、钉钉加签、Telegram）
│   ├── paths.py                # 应用运行时路径与可执行文件定位
│   ├── runtime.py              # 并发监控循环、Windows 自启动任务与主装配入口
│   ├── security.py             # 敏感凭据本地加密与密钥管理
│   ├── system.py               # 物理网卡识别、Wi-Fi 120s 防定位长效缓存、系统工具
│   ├── telegram_bot.py         # Telegram 机器人、内联快捷按钮与命令菜单
│   ├── tray.py                 # 状态彩色托盘图标生成与绘制
│   ├── ui.py                   # 门面主窗口装配层与托盘交互
│   └── ui_modules/             # [新] 模块化苹果设计系统 UI 组件
│       ├── dashboard_page.py   # 苹果风格仪表盘看板与一键打通横幅
│       ├── log_page.py         # 苹果深色终端风格日志面板与关键词检索
│       ├── quick_setup_dialog.py # 小白 10 秒一键智能配网苹果风向导弹窗
│       ├── settings_page.py    # macOS Grouped Insets 分组内嵌式设置表单
│       ├── styles.py           # Apple HIG 色彩规范、抗锯齿矢量字体与 QSS 样式表
│       └── widgets.py          # Squircle 连续平滑圆角卡片与呼吸状态药丸
├── tests/                      # 自动化测试套件
│   └── test_campus_guard.py    # 24 项单元测试（涵盖协议、卡片、嗅探与缓存）
├── docs/                       # 架构与人工测试手册
├── scripts/                    # 打包脚本 (package_windows.ps1)
├── CampusGuard.spec            # PyInstaller 打包规格文件
├── config.example.json         # 无敏感凭据的配置文件模板
└── README.md                   # 项目综合介绍与使用文档
```

---

## 🔒 隐私与开源安全承诺

- **零凭据提交**：公共仓库不包含且永久忽略真实 `config.json`、`campus_guard.key` 与 `*.log` 文件；
- **本地高强度保护**：本地配置文件中的账号密码与 Bot 密钥通过系统独立生成的 Fernet 密钥加密存储；
- **无公网回传**：除与您自行配置的学校认证网关、飞书/钉钉 Webhook 及 Telegram 服务器通信外，绝无任何第三方数据上报或遥测代码。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。欢迎高校学子与开发者提交 Pull Request 或 Issue 共同完善！
