# 变更日志 (Changelog)

本项目遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/) 语义化版本规范。

---

## [2.3.2] - 2026-11-22

### 新增 (Added)
- **版本号单一真源同步** (`campus_guard/version.py`)：新增 `APP_VERSION = "2.3.2"` 唯一版本真源，前端侧边栏版本号由后端状态接口实时下发并同步至 `pyproject.toml`、`frontend/package.json` 及 Windows `AppUserModelID`，同时新增自动化防呆一致性单元测试。
- **点击窗口关闭按钮 (×) 选择弹窗** (`campus_guard/ui.py`、`bridge.py`、`frontend/src/App.tsx`)：拦截关闭事件并在界面弹出 iOS 浅色磨砂确认对话框，支持选择「最小化到托盘」「直接退出程序」及勾选「记住我的选择」，核心配置页同步新增 `close_action` 下拉开关，退出时优雅停止监控并清理系统托盘图标。
- **国内免代理消息通知配置与一键测试** (`campus_guard/bridge.py`、`frontend/src/components/SettingsView.tsx`)：在核心配置页补全飞书 Webhook、钉钉 Webhook 与加签密钥输入卡片，并新增 `test_domestic_notify` 测试推送接口。
- **一键网络诊断与脱敏诊断包导出** (`campus_guard/diagnostics.py`、`runtime.py`、`bridge.py`、`LogView.tsx`)：新增 `--diagnose`、`--export-diagnostics` CLI 开关及界面「诊断包」按钮，生成自动遮蔽敏感凭据与日志的 `anlan_diagnostic_*.zip`。
- **开源仓库标准件与 Release SHA256 校验** (`LICENSE`、`CONTRIBUTING.md`、`SECURITY.md`、`.github/workflows/ci.yml`)：补齐 MIT 协议与社区安全文档，CI 发布自动生成并上传 `SHA256SUMS.txt`。

### 修复 (Fixed)
- **Telegram Bot 热挂载、初始化竞态与冻结版 HTTPS/SSL 修复** (`campus_guard/telegram_bot.py`、`scripts/rthook_ssl_compat.py`)：
  - 保存 Telegram 凭据后立即在后台热启动或热重载 Bot，无需重启软件；修复 Bot 未就绪时测试握手误把消息写入本地队列并返回假成功的问题；
  - 为 `_health_check()` 增加 `_ready` 守卫并将 `register_bot_health_check()` 延后至就绪后注册，修复 Bot 初始化重试期被网络恢复事件提前触发健康检查导致的 `This Updater was not initialized via Updater.initialize!` 竞态告警；
  - 新增 PyInstaller 运行时 SSL 兼容钩子 `rthook_ssl_compat.py` 与 `ensure_frozen_ssl_compat()` 双保险，解决冻结环境下 `ssl.SSLContext` 相对路径 CA 文件缺失引发的 Bot 与 HTTPS 请求失败。
- **断网自愈精度强化** (`campus_guard/system.py`、`network.py`)：
  - 过滤 Windows 移动热点虚拟网卡（`本地连接*`、`192.168.137.*` 等），防止重连 Wi-Fi 时提前误判已拿到 IP 而退出等待；
  - 将 `check_internet()` 升级为严格 Captive Portal 204 / 特征正文 / HTTPS 证书并发校验，彻底消除高校未认证前放行 DNS 53 端口导致的假在线漏认证问题。
- **测试脱敏**：完成 109 项全量单元测试覆盖与测试占位数据脱敏。

---

## [2.3.1] - 2026-11-22

### 修复 (Fixed)
- **彻底修复下载便携包无法运行的问题**：
  - 修复 Windows 解压 GitHub 下载压缩包后因文件附带 `Zone.Identifier` (MOTW) 锁定标记导致的 `Failed to resolve Python.Runtime.Loader.Initialize` 启动报错；
  - 新增 `unblock_motw_files()` 启动前置自动解除锁定机制，并随包附带开启 `loadFromRemoteSources` 的 `AnLan.exe.config`；
  - 在 `AnLan.spec` 关闭 UPX 压缩，提升托管二进制与安全软件兼容性。
- **重连候选 SSID 兜底完善** (`campus_guard/network.py`)：合并家庭信任 SSID 与校园 SSID 候选，避免配置家庭 Wi-Fi 后开机在校园网场景下无法回退连接校园网。

### 新增 (Added)
- **开机自启静默最小化到系统托盘** (`--minimized`、`start_minimized_on_boot`)：开机自启自动隐藏主窗口并常驻托盘，保存配置时实时同步 Windows 自启注册表与计划任务。
- **校园网连通后自动启动 Clash 并开启系统代理** (`campus_guard/proxy_manager.py`)：
  - 支持自动探测本机 Clash Verge 等客户端路径与混合端口，或手动指定路径；
  - 确认校园网外网畅通后自动拉起 Clash、轮询等待端口监听就绪，并开启 Windows 系统代理（自动合入校园网内网段绕过规则）且广播 WinINet 立即生效；
  - 前端设置页新增「连网后自动启动代理（Clash 联动）」配置卡片（含一键探测与立即测试启动），托盘右键菜单同步新增「启动代理并开系统代理」快捷入口。
- **测试与脱敏**：新增 `tests/test_proxy_manager.py` 等单元测试，全量测试增至 92 项并完成仓库测试占位数据与本机路径脱敏。

---

## [2.3.0] - 2026-11-21

### 品牌与图标焕新 (Rebrand & Visuals)
- **正式更名为「安澜」**：取「愿河海安澜」之意，桌面端窗口标题、侧边栏、托盘菜单与提示、多通道消息通知及安装包产物全面升级为「安澜」（内部包名 `campus_guard` 与配置文件保持兼容），开机自启动自动迁移并清理旧 `CampusGuard` 遗留项。
- **全新水波应用图标** (`scripts/generate_icon.py`、`assets/app_icon.ico`)：重绘 iOS 连续圆角黛蓝底板与三道平缓水波图标（含 `16px`~`256px` 全尺寸）；托盘状态点同步升级为低饱和配色配白色描边环。

### 前端体验与浅色典雅重构 (UI Overhaul)
- **iOS 浅色典雅微透磨砂玻璃主题**：全面替代原有暗黑与紫粉渐变风格，采用柔和冷雾瓷白画布、磨砂玻璃卡片、单一典雅黛蓝主强调色与低饱和语义状态色，窗口初始底色同步为 `#eef2f7` 消除启动闪黑屏。
- **全局悬浮 Toast 与日志页布局修复** (`frontend/src/components/ToastContext.tsx`、`LogView.tsx`)：
  - 将全站提示迁移至右上角固定悬浮卡片，彻底解决导出日志时内联提示挤压按钮栏造成文字折行、标题截断及卡片顶跳的问题；
  - 重构日志页为「页头 + 固定单行工具栏 + 浅色瓷白日志流」，支持导出原地微反馈、行内二次确认清空、文本划选复制，并修复 `exportLogs()` 读取字段错位导致未导出全量日志的 Bug；
  - 重构配置页为独立固定顶栏与独立滚动表单区，消除滚动时卡片与标题栏重叠遮挡。

### 断网自动重连与零定位闪烁 (Reliability & Privacy)
- **彻底解决断网无法自动重连**：
  - 修复 `NetworkMonitor` 使用不可重入 `Lock()` 在 `_run_probe_and_handle` 持有锁时调用 `_trigger_reconnect()` 导致的同线程自死锁，改用 `RLock` 并将通知与重连调度移出锁外执行；
  - 修复 `ApiBridge.reconnect_wifi()` 解包 `bool` 返回值崩溃的 Bug，增强 `quick_connect()` 在断网时先强力拉起无线再认证；
  - 强化 `reconnect_wifi(force=True)`：先断开假死关联再连接，并将未获取有效 IP 时的假返回 `True` 修正为继续尝试下一候选配置；
  - 修复断网时 `get_local_ip()` 读取僵尸 IP 与 `get_local_mac()` 将蓝牙回退 MAC 永久写入缓存的问题；
  - 新增持续离线周期重连调度与并发端口网关探活。
- **彻底根除 Windows 定位图标闪烁** (`campus_guard/system.py`)：
  - 基于 `psutil` 无线网卡状态与 IPv4 签名锁定缓存，稳态挂机不再周期性触发外部查询；
  - 优先通过不触发位置权限的 Windows NLA（`Get-NetConnectionProfile`）获取当前网络配置名并自动剥离重名编号；
  - 扩充延安大学新校区 `172.30.` / `172.31.` 私网段，新增 Dr.COM 已在线 512 防误判与 Telegram Bot `/boost`、`/sniff` 指令。

---

## [2.2.2] - 2026-11-07

### 修复与优化 (Fixed & Improved)
- **Dr.COM 双模自动回退认证** (`campus_guard/adapters/drcom.py`)
  - 自动识别并提供「`,0,` 前缀」与「标准学号」双模候选探测；
  - 解决延安大学等高校部分账号因单向强制追加 `,0,` 前缀被服务端以 `512`（密码/凭据错误）拒绝的问题；
  - 增加对错误码 `512` 的明确排障指引，提示用户核实大小写或访问校网自助平台 `https://self.yau.edu.cn`。
- **全链路敏感凭据脱敏** (`campus_guard/logging_setup.py`)
  - 引入 `SensitiveDataFilter`，拦截并屏蔽文件日志与终端控制台中的 `user_password`、`password`、`pwd` 等字段明文；
  - 屏蔽 Telegram Bot Token 中的 secret hash，杜绝异常堆栈输出导致的凭据泄露。
- **Bot Polling 断网静默熔断与降噪** (`campus_guard/telegram_bot.py`)
  - 调整健康检查执行顺序，断网/离线状态下前置熔断退出，杜绝无网络时的无效探活；
  - 增加 120 秒重启冷却退避机制；
  - 将断网引发的 `httpx.ConnectError` 与 `NetworkError` 收敛为单行 Warning，彻底消除断网期间日志大段堆栈刷屏。
- **网络场景归属精准判定** (`campus_guard/network.py`)
  - 剔除 Wi-Fi 名称识别中过于宽泛的 `"wifi"`、`"wlan"`、`"tea"` 匹配词，避免手机热点（如 `HUAWEI-WiFi`）被误判为校园网；
  - 重连流程中增加即时二次探活，处于家庭网络或具备外网访问权限时直接判定在线并退出重连循环，防止非校园网络下持续请求内网认证服务器触发 `WinError 10065`。
- **前端调用超时保护** (`frontend/src/api.ts`)
  - 将一键联网超时阈值由 8s 放宽至 15s，网关嗅探放宽至 10s，预留充裕的双模验证与自愈重试时间。

---

## [2.2.1] - 2026-11-07

### 修复与优化 (Fixed & Improved)
- **Dr.COM 认证与注销 URL 规范化** (`campus_guard/adapters/drcom.py`)
  - 新增 `build_drcom_urls()` 解析函数，将输入或嗅探到的 `/login`、`/index.jsp` 等路径精准规整为标准端点 `/eportal/portal/login` 与 `/eportal/portal/logout`；
  - 自动补齐延安大学认证服务器缺失的 `:801` 端口，根除 404 Not Found (Nginx) 异常。
- **外网连通状态机优先级重构** (`campus_guard/network.py`)
  - 调整探测状态机判决分支：直连外网畅通时立即标记为 `ONLINE`，修复已能访问外网却因特定网关拦截探针被误报为「离线」的问题。
- **ICMP Ping 探活与多端口探测兜底** (`campus_guard/system.py`)
  - 网关探活增加跨平台 ICMP Ping 快速回退，并支持 80、801、8080 等多端口并发探测。
- **窗口关闭事件防抖** (`campus_guard/ui.py`)
  - 增加 1.0 秒防抖阈值，消除 Windows 快速连发 `WM_CLOSE` 导致的异常与假死。

---

## [2.2.0] - 2026-11-06

### 新增特性 (Added)
- **原生视窗架构重构**
  - 全面迁移至 Windows 原生 Edge Chromium WebView2 运行时，结合 React 19、Tailwind CSS 与 Twilight Crystal Glass（微光水晶）设计规范；
  - 注入硬件加速与平滑滚轮指令，消除界面卡顿；
  - 彻底私有化 `ApiBridge` 内部对象，杜绝 pywebview COM 反射遍历导致的递归与死锁。
- **零 DNS 延迟 Captive Portal 嗅探引擎**
  - 采用默认网关与纯 IP 并发探测，避开未认证状态下 DNS 解析超时导致的 30 秒系统卡死；
  - 支持首屏输入学号密码一键自动嗅探校园网类型并持久化配置。
- **全协议认证支持矩阵**
  - 内置城市热点 Dr.COM / ePortal、深澜 Srun 4000、锐捷 Ruijie 及通用 Web Portal 适配器。
- **多通道通知与远程中枢**
  - 新增飞书 Webhook 交互卡片与钉钉加签机器人推送；
  - 集成 Telegram 双向远程交互（查电量、截屏、锁屏与关机）；
  - 阶梯式电量预警与 20% 阈值延迟自动关机保护。
