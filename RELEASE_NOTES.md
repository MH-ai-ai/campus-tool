# AutoCampusNet v2.3.2 发布说明 (Windows x64)

**AutoCampusNet** v2.3.2 正式将项目及桌面应用命名统一为 `AutoCampusNet`，进一步完善桌面交互、版本号统一管理、Telegram Bot 热挂载与冻结包 TLS 兼容性，并彻底解决 Windows 移动热点、未认证假在线及后台网关探测黑框闪烁问题。

---

## 核心更新亮点

### 1. 断网自愈精度强化（告别假在线与热点干扰）
- **过滤 Windows 移动热点虚拟网卡**：屏蔽 `本地连接*`、`192.168.137.*` 等虚拟共享网卡地址，确保 `reconnect_wifi()` 真正等到校园网物理网卡 DHCP IP 到位后再继续；
- **严格直连外网校验**：`check_internet()` 升级为并发 Captive Portal 204 / 特征正文 / 严格 HTTPS 证书校验，不再受高校未认证前放行 DNS 53 端口影响，彻底杜绝跳过登录认证的问题；
- **静默网关探针**：为 Windows 下 `ping_check()` 补充 `CREATE_NO_WINDOW` 隐藏窗口标志，彻底消除后台网关 ICMP 探测偶发闪烁终端黑框的问题。

### 2. Telegram Bot 凭据热挂载与冻结包 SSL 兼容修复
- **实时热挂载**：在界面填入或修改 Bot Token / 用户 ID 并保存后，后台自动热启动或重载 Bot，无需重启软件；同步修复测试握手按钮未就绪时假返回成功的问题；
- **初始化期竞态修复**：修复 Bot 刚启动重试时被网络恢复事件提前触发健康检查导致的 `This Updater was not initialized via Updater.initialize!` 竞态告警；
- **冻结包 HTTPS/SSL 兼容**：新增 PyInstaller 运行时钩子与启动双保险，修复打包环境下 `ssl.SSLContext` 初始化抛出 `FileNotFoundError` 导致 Bot 无法连接及 HTTPS 探测失败的隐蔽问题。

### 3. 点击关闭按钮 (×) 确认弹窗与托盘清理
- 点击窗口右上角 `×` 时弹出居中磨砂选择框，可自由选择「最小化到托盘」「直接退出程序」或「记住选择」，完全退出时自动清理监控线程与系统托盘图标；在核心配置页也可随时切换关闭行为。

### 4. 版本号单一真源同步
- 引入 `campus_guard/version.py` (`APP_VERSION = "2.3.2"`) 并由后端状态接口实时驱动前端展示，配合自动化一致性单测防止版本号再次脱节。

### 5. 国内免代理消息通知（飞书 / 钉钉）界面与一键测试
- 在核心配置页补全飞书 Webhook、钉钉 Webhook 与加签密钥配置卡片，并新增 `test_domestic_notify` 一键测试推送接口，校园网直连即可实时接收断网自愈与电量告警通知。

### 6. 一键网络诊断、脱敏诊断包与开源规范完善
- 新增「运行日志 → 诊断包」按钮及 `--diagnose` / `--export-diagnostics` 命令行参数，一键导出含 Wi-Fi、网关、外网、Clash 状态与脱敏配置/日志的 `autocampusnet_diagnostic_*.zip`；
- 补齐 `LICENSE` (MIT)、`CONTRIBUTING.md`、`SECURITY.md`，Release 资产同步附带 `SHA256SUMS.txt` 校验文件。

---

## 资产下载与使用方式

| 资产名称 | 平台架构 | 打包形式 | 运行方式 |
| :--- | :--- | :--- | :--- |
| `AutoCampusNet-v2.3.2-Windows-x64.zip` | Windows 10 / 11 (x64) | 绿色便携免安装 | 解压后双击 `AutoCampusNet.exe` 即可运行 |

> 完整变更记录请参阅 [CHANGELOG.md](https://github.com/Lunar-mh/AutoCampusNet/blob/main/CHANGELOG.md)。
