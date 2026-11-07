# 变更日志 (Changelog)

本项目遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/) 语义化版本规范。

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
