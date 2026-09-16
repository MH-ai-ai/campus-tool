# 🛡️ Campus Guard (全国高校通用校园网守护神器)

<p align="center">
  <img src="https://img.shields.io/badge/Origin-%E5%BB%B6%E5%AE%89%E5%A4%A7%E5%AD%A6%20(Yan'an%20Univ)-C8102E?style=for-the-badge" alt="Yan'an University" />
  <img src="https://img.shields.io/badge/Compatibility-%E5%85%A8%E5%9B%BD%E4%B8%BB%E6%B5%81%E9%AB%98%E6%A0%A1%E9%80%9A%E7%94%A8-0078D6?style=for-the-badge" alt="National Universities" />
  <img src="https://img.shields.io/badge/Protocols-Srun%20%7C%20Dr.COM%20%7C%20Ruijie%20%7C%20Portal-FF8800?style=for-the-badge" alt="Protocols" />
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Platform" />
  <img src="https://img.shields.io/badge/UI-Apple%20HIG%20%7C%20PyQt6-000000?style=for-the-badge&logo=apple&logoColor=white" alt="Apple Design System" />
  <img src="https://img.shields.io/badge/Memory-4.8MB~15MB%20RAM-30D158?style=for-the-badge" alt="Low Memory" />
  <img src="https://img.shields.io/badge/Notifications-Telegram%20%7C%20%E9%A3%9E%E4%B9%A6%20%7C%20%E9%92%89%E9%92%89-FF8800?style=for-the-badge" alt="Multi-Channel Notifications" />
  <img src="https://img.shields.io/badge/Tests-37%20Passed-30D158?style=for-the-badge" alt="Tests" />
</p>

> 🎓 **以延安大学（Yan'an University, YAU）校园网为核心原型深度量身定制，现已全面升级打通国内各大高校主流认证体系（深澜 Srun 4000/Portal、城市热点 Dr.COM Web、锐捷 Ruijie RG-ePortal/SAM 与通用 Web Portal）。**  
> 
> 本工具开箱默认预置延安大学（新城校区、杨家岭校区及萃园）Dr.COM 网页认证体系的最佳参数；同时内置全国高校离线规则库与智能 Captive Portal 嗅探引擎，支持自适应识别全国数百所高校校园网。具备掉线毫秒级自动重连、家庭与校园网智能感知、国内免梯（飞书/钉钉）双向告警、20% 电量安全关机守护，并配备全新 **Apple HIG 苹果深色设计系统**与 **小白「⚡ 10秒一键打通」**。

---

## ⚡ 核心痛点与 Campus Guard 创新解法

| 传统校园网痛点 | Campus Guard 创新解法 |
| :--- | :--- |
| **高校系统林立，协议互不兼容**：清北浙大用深澜、吉大延大用城市热点、工科院校用锐捷，换个学校或设备脚本失效。 | **全国高校插件化协议引擎**：解耦实现 **深澜 Srun**（纯 Python 原生 xEncode/HMAC-MD5 加密）、**城市热点 Dr.COM**、**锐捷 Ruijie** 与通用 Portal 独立适配器，全国高校即选即用。 |
| **夜间/就寝时频繁断网掉线**：半夜离开实验室或宿舍就寝后网络意外断开，跑模型下载中断、远程桌面无法连接。 | **全自动毫秒感知与重连**：后台非阻塞探针毫秒级侦测断网，自愈引擎毫秒感知并自动唤醒重连与登录认证。 |
| **小白配网门槛高**：不清楚什么是网关 IP、AC IP、Portal 认证地址，参数填写繁琐劝退。 | **「⚡ 一键智能打通」双轨体验**：自动拦截 302 重定向并根据指纹自适应反推归属高校及协议体系；同时支持全拼/首字母模糊检索全国高校。 |
| **告警通知依赖翻墙**：Telegram Bot 在国内宿舍无梯环境下无法接收报警消息。 | **国内免梯平台直通**：原生集成**飞书自适应彩色交互卡片**与**钉钉 HMAC-SHA256 加签 Markdown**，手机即时弹窗，与 Telegram 互为容灾。 |
| **后台频繁弹系统定位提示**：后台高频执行 Wi-Fi 探针导致 Windows 任务栏频繁闪烁“正在使用您的位置”小圆点，非常烦扰。 | **长效缓存与内核被动监听**：采用 `psutil` 内核链路被动监听与 120 秒智能缓存，彻底消灭 Windows 位置提示。 |
| **寝室深夜断电电池过放损坏**：宿舍半夜拉闸断电导致笔记本电池耗尽过放损坏，或意外断电关机导致未保存数据丢失。 | **三档电量告警与安全关机**：50%、30%、20% 梯次报警；20% 自动启动 60 秒可撤销安全关机保护。 |
| **后台挂机卡顿、发热掉电快**：后台长时间挂机占用过大 CPU 和内存，传统 UI 粗糙刺眼。 | **极致低功耗 + 苹果设计**：实测 **0.0% CPU 占用 · 4.8MB~15MB 极寒内存**，微光深空灰平滑圆角卡片，夜间视觉温和。 |

---

## 🏫 原型背景与全国高校通用适配

### 1. 🎯 延安大学（Yan'an University）原型保留与专属优化
- **原型母体与长期验证**：
  本项目最初由延安大学学子针对延大校园网络实测环境进行抓包逆向、深度定制与长期验证开发。
- **延大网络环境特征已默认置顶内置**：
  - **默认认证服务地址**：`http://10.212.0.1:801/eportal/index.jsp`（延安大学 Dr.COM ePortal 核心登录入口）
  - **典型网关内网路由**：`10.212.0.1` / `10.200.84.3`
  - **全校区全面适配**：完美适配**新城校区**（新校区各个书院/宿舍楼、图书馆、学院实验楼）、**杨家岭校区**（老校区）以及**萃园校区**的无线 Wi-Fi（如 `YAU`、`YAU_5G` 等）与宿舍桌面插网线的有线以太网环境；
  - **多运营商账号支持**：全面支持延安大学校园网普通账号、校园宽带绑定账号（移动 CMCC、电信 ChinaNet、联通 Unicom）。

### 2. 🌐 全国高校主流校园网协议覆盖表

Campus Guard 已针对国内主流高校的四大校园网系统完成深度适配：

| 协议体系 | 覆盖代表高校 | 技术特征与 Campus Guard 适配能力 |
| :--- | :--- | :--- |
| **深澜 Srun 4000 / Portal** | **清华大学、浙江大学、北京邮电大学、深圳大学、电子科技大学、中南大学** 等多数 985/211 高校 | 采用 **纯 Python 原生算法** 实现深澜专有的 `xEncode`（XXTEA 变形）加密与自定义 64 码表 Base64，自动向 `/cgi-bin/get_challenge` 获取盐值并计算 HMAC-MD5，**零外部 Node.js 或 C 依赖**。 |
| **城市热点 Dr.COM Web** | **延安大学 (默认原型)、吉林大学** 及国内大量理工/师范类院校 | 完美支持 `dr1003` 回调与 `,0,` 账号前缀兼容，支持运营商后缀自动识别与错误码精准翻译。 |
| **锐捷网络 Ruijie ePortal / SAM** | **众多工科高校、农林与综合类大学** | 封装 `/eportal/InterFace.do?method=login` 接口，支持动态提取 `queryString` 并自适应表单提交。 |
| **通用 Web Captive 表单** | 各高校自研 Portal、华为/深信服网关 | 启发式通用认证适配器，自动解析表单提交凭据。 |

---

## 🌟 核心特性展示

### 1. ⚡ 小白首次「一键智能打通」（全国高校双轨模式）
- **自动嗅探识别**：新用户连上校园 Wi-Fi 后，点击「⚡ 校园网一键打通」，系统自动拦截未加密 HTTP 探针，提取 302 重定向目标，并根据指纹特征**秒级反推所在高校及所属体系（深澜/城市热点/锐捷）**；
- **高校模糊检索**：同时在界面提供全国高校下拉框，支持汉字、拼音首字母模糊检索（如搜 `yau` 快速定位延安大学，搜 `thu` 定位清华大学）；
- **极速开启守护**：仅需输入学号与密码，点击「🚀 一键保存并登录」，10 秒内打通认证并写入本地加密存储。

### 2. 🍏 Apple HIG 苹果深色设计系统
- **深空灰微光层次**：主背景采用 macOS 原生深空灰（`#141417`），搭配精致毛玻璃卡片（`#212128`）与半透明高光微边框；
- **Squircle 连续平滑圆角**：卡片统一采用 14px 苹果平滑圆角（`_AppleCard`），视觉浑然一体；
- **状态呼吸药丸 (Status Pills)**：发光状态指示灯（● 绿色在线、▲ 橙色告警、■ 红色故障、○ 离线），状态扫视一目了然；
- **macOS Grouped Insets 分组内嵌列表**：设置面板重构为 macOS 系统偏好设置风格，内嵌微阴影输入框，层级井然；
- **高质量平滑抗锯齿字体**：全界面采用矢量字体栈，杜绝 Windows DirectWrite 字体回退警告。

### 3. ☁️ 高校规则库双保险与云端热更新
- **离线全量兜底**：本地内置离线全国高校知识库（`data/universities.json`），免网环境下开箱即用；
- **远程静默同步**：偏好设置提供「☁️ 更新高校规则库」按钮，可从 GitHub/Gitee 仓库一键静默同步最新的高校认证模板，随时扩充更多高校而不必频繁重装程序。

### 4. 🔕 彻底消除任务栏频繁定位烦扰
- 采用 **内核网络链路被动监听**（`psutil.net_if_stats`）结合 **120 秒长效状态缓存**，在稳定在线时零主动触发无线 AP 扫描，保持极致静默。

### 5. 🔔 多平台通知引擎与容灾中心
- **飞书自定义机器人**：发送高颜值自适应彩色交互卡片（Interactive Cards），手机即时推送；
- **钉钉自定义机器人**：企业级 HMAC-SHA256 动态加签防重放，自动生成结构化 Markdown；
- **Telegram Bot 远程运维**：支持 Telegram 双向交互、快捷内联按钮面板与远程控制菜单。

### 6. 🍃 极致低耗常驻（0.0% CPU 占用 · 4.8MB 极寒内存）
- **界面层极寒深休眠**：主窗口最小化至系统托盘挂起时，彻底停用前端所有图表重绘、定时器与日志文件读取；
- **自适应智能心跳**：在线时探活周期平缓延长至 10 秒，主监控循环依据任务倒计时自适应深睡眠；掉线时毫秒级切入 1~2 秒冲刺重连；
- **Windows 物理工作集修剪**：托盘挂机时主动调用系统底层内存修剪，实测挂机内存稳定在 **4.8MB ~ 15MB** 之间，CPU 占用率稳定在 **0.0%**。

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

### 3. 运行全量单元测试
```powershell
.\.venv\Scripts\python.exe -m unittest discover tests -v
```
*(实测 37 项单元测试全部 100% 通过)*

---

## 🤝 欢迎贡献更多高校规则

如果您所在的大学尚未收录，或者您抓取到了自己学校的认证参数，欢迎通过 Pull Request 为全国高校学子贡献规则！
只需在 [`data/universities.json`](data/universities.json) 中添加您的学校信息：

```json
{
  "id": "your_school_id",
  "name": "某某大学 (深澜 Srun / 城市热点 / 锐捷)",
  "pinyin": "moumoudaxue mmdx",
  "protocol": "srun",
  "auth_url": "http://10.0.0.1/cgi-bin/srun_portal",
  "gateway": "10.0.0.1",
  "ac_ip": "1",
  "wifi_ssids": ["School-WiFi"],
  "domain_keywords": ["school.edu.cn"],
  "description": "某某大学校园网 Portal 认证"
}
```

---

## 📄 开源许可证

本项目基于 MIT License 开放源代码。
特别致敬延安大学（Yan'an University）校园网络开发与测试支持。
