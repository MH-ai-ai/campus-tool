<div align="center">
  <img src="assets/app_icon.png" width="84" alt="AutoCampusNet Logo" />
  <h1>AutoCampusNet · 安澜</h1>
  <p>Windows 高校校园网全自动认证、断网自愈、Clash 代理联动与宿舍电源守护工具</p>

  <p>
    <a href="https://github.com/Lunar-mh/AutoCampusNet/releases/latest"><img src="https://img.shields.io/badge/Release-v2.3.2-2B5797?style=flat-square&logo=github" alt="Release" /></a>
    <a href="https://github.com/Lunar-mh/AutoCampusNet/stargazers"><img src="https://img.shields.io/github/stars/Lunar-mh/AutoCampusNet?style=flat-square&color=CF8A27&logo=github" alt="Stars" /></a>
    <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11%20x64-0078D4?style=flat-square&logo=windows" alt="Platform" />
    <img src="https://img.shields.io/badge/Tests-110%20Passed-1F7A53?style=flat-square" alt="Tests" />
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-64748B?style=flat-square" alt="License" /></a>
  </p>

  <p>
    <a href="#核心特性">核心特性</a> ·
    <a href="#快速开始">快速开始</a> ·
    <a href="#协议支持">协议支持</a> ·
    <a href="#诊断与配置">诊断与配置</a> ·
    <a href="#开源与联系">开源与联系</a>
  </p>
</div>

---

## 核心特性

* **多协议自动嗅探**：Zero-DNS 并发 IP 探针拦截 Captive Portal 302 重定向，自动识别校园网关与认证协议。
* **真外网校验与防误判**：通过无重定向 204、特征正文及 HTTPS 校验判定真实外网，自动屏蔽移动热点（`192.168.137.*`）与虚拟网卡干扰。
* **Clash 顺序联动**：仅在校园网打通外网后后台拉起 Clash Verge 等客户端，端口就绪后开启系统代理并配置校园内网绕过规则。
* **无定位闪烁挂机**：基于网卡签名缓存与 Windows NLA 静默查询，避免后台周期性触发任务栏定位图标闪烁；支持 `--minimized` 开机静默托盘。
* **宿舍断电保护**：监测交流供电与电量变化，支持多梯度预警与可撤销的低电量安全关机倒计时。
* **多通道远程通知与控制**：支持飞书卡片、钉钉加签免代理推送，以及 Telegram Bot 双向指令（`/status`、`/boost`、`/battery`、`/screenshot`、`/lock`、`/shutdown`）。
* **本地加密与脱敏诊断**：凭据使用本地 Fernet 对称加密存储（`config.json` + `campus_guard.key`）；支持一键导出自动脱敏的诊断压缩包。

---

## 快速开始

### 绿色便携版（推荐）

1. 前往 [Releases](https://github.com/Lunar-mh/AutoCampusNet/releases/latest) 下载 `AnLan-v2.3.2-Windows-x64.zip`（含 `SHA256SUMS.txt` 校验文件）。
2. 解压后直接运行 `AnLan.exe`（Windows 10/11 自带 WebView2，无需安装 Python / Node.js；启动自动解除下载 MOTW 锁定）。
3. 填入校园网账号密码并点击 **「一键极速联网」**；如需联动代理，在 **「核心配置」** 开启 Clash 自动启动即可。

### 从源码运行

```powershell
git clone https://github.com/Lunar-mh/AutoCampusNet.git
cd AutoCampusNet

# 构建前端静态页面 (Node.js 20+)
Push-Location frontend; npm install; npm run build; Pop-Location

# 安装依赖、运行单测 (Python 3.12+) 并启动
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe campus_guard.pyw
```

---

## 协议支持

| 协议体系 | 覆盖典型高校 / 网关特征 | 状态 |
| :--- | :--- | :--- |
| **Dr.COM / 城市热点** | ePortal / `10.200.84.3` / 运营商后缀（延安大学等） | ✅ 原生支持 |
| **Srun / 深澜 4000** | `srun_portal` / XEncode + HMAC-SHA1 动态签名 | ✅ 原生支持 |
| **Ruijie / 锐捷 ePortal** | `/eportal/InterFace.do` 表单动态参数提取 | ✅ 原生支持 |
| **Generic Portal** | 标准表单 HTML 解析与正则自动提交 | ✅ 自动回退 |

> 欢迎通过 PR 为 [data/universities.json](data/universities.json) 补充更多高校预设，详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 诊断与配置

界面「运行日志」页点击 **「诊断包」** 可生成脱敏诊断压缩包 `anlan_diagnostic_*.zip`，也支持命令行只读诊断：

```powershell
.\AnLan.exe --diagnose             # 输出当前网络、网关、Clash 与脱敏配置摘要
.\AnLan.exe --export-diagnostics   # 导出脱敏诊断压缩包 (.zip)
```

<details>
<summary>展开查看：常见故障排查与核心配置说明 (<code>config.json</code>)</summary>

| 常见现象 | 处理建议 |
| :--- | :--- |
| 下载解压后无法启动 | 随包已附带 `AnLan.exe.config` 并自动解除 `Zone.Identifier`；若仍被拦截，右键属性勾选「解除锁定」 |
| 开启移动热点后掉线不重连 | `v2.3.2+` 已自动过滤 `192.168.137.*` 热点虚拟网卡并启用严格 204 / HTTPS 校验 |
| Telegram Bot 无法上线 | 在「核心配置」开启 Clash 联动，或改用飞书 / 钉钉国内免代理推送 |

* **网络模式**：`network_mode`（`auto` / `campus` / `home`）、`university_id`、`auth_protocol`、`campus_auth_url`、`campus_gateway`
* **代理联动**：`auto_start_proxy`、`proxy_exe_path`、`proxy_port`（默认 `7897`）、`proxy_bypass_rules`
* **托盘与电源**：`autostart`、`start_minimized_on_boot`、`close_action`（`ask` / `tray` / `exit`）、`auto_shutdown_threshold`
* **通知凭据**：`telegram_bot_token`、`telegram_user_id`、`feishu_webhook`、`dingtalk_webhook`、`dingtalk_secret`

</details>

---

## 开源与联系

* **变更与安全**：[CHANGELOG.md](CHANGELOG.md) · [RELEASE_NOTES.md](RELEASE_NOTES.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) · [MIT License](LICENSE)
* **反馈与交流**：QQ `3202484369` · 邮箱 [lunar.mh722@gmail.com](mailto:lunar.mh722@gmail.com) · [GitHub Issues](https://github.com/Lunar-mh/AutoCampusNet/issues)
