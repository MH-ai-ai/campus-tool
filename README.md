# 🛡️ Campus Guard

<p align="center">
  <img src="https://img.shields.io/badge/Origin-%E5%BB%B6%E5%AE%89%E5%A4%A7%E5%AD%A6%20(YAU)-C8102E?style=flat-square" alt="Yan'an University" />
  <img src="https://img.shields.io/badge/Protocols-Srun%20%7C%20Dr.COM%20%7C%20Ruijie%20%7C%20Portal-blue?style=flat-square" alt="Protocols" />
  <img src="https://img.shields.io/badge/UI-Apple%20HIG%20%7C%20PyQt6-black?style=flat-square" alt="Apple Design System" />
  <img src="https://img.shields.io/badge/Memory-4.8MB%20RAM-success?style=flat-square" alt="Low Memory" />
  <img src="https://img.shields.io/badge/Notifications-%E9%A3%9E%E4%B9%A6%20%7C%20%E9%92%89%E9%92%89%20%7C%20Telegram-orange?style=flat-square" alt="Notifications" />
  <img src="https://img.shields.io/badge/Tests-37%20Passed-brightgreen?style=flat-square" alt="Tests" />
</p>

> 🎓 **专为 Windows 打造的全国高校校园网守护神器（以延安大学校园网为核心原型深度量身定制）。**  
> 全面兼容国内各大高校主流认证体系（深澜 Srun 4000/Portal、城市热点 Dr.COM Web、锐捷 Ruijie 与通用 Web Portal）。具备掉线毫秒自愈、国内免梯（飞书/钉钉）报警、低电量安全关机守护，常驻内存仅 **4.8MB**，CPU 占用 **0.0%**。

---

## ⚡ 核心功能

* **🔌 全国高校全协议兼容**：
  * **深澜 Srun 4000 / Portal**：纯 Python 原生实现 xEncode / XXTEA 与 64 码表 Base64，自动获取挑战盐（清华、浙大、北邮等主流 985/211 高校开箱即用，零 Node.js 依赖）；
  * **城市热点 Dr.COM**：**延安大学全校区默认置顶**，深度兼容吉林大学等高校，支持多运营商账号及错误码翻译；
  * **锐捷 Ruijie RG-ePortal / SAM**：支持动态查询参数与表单提交；
  * **通用 Web Portal**：启发式表单适配，兜底自研认证系统。
* **⚡ 小白「一键智能打通」**：连入校园 Wi-Fi 即可自动拦截 302 重定向并推断所属高校体系；同时支持全拼/首字母模糊检索全国高校名录。
* **🍏 Apple HIG 苹果深色设计**：深空灰微光卡片、连续平滑圆角（Squircle）、发光状态呼吸药丸，视觉温和高级。
* **🚀 国内免梯通知通道**：原生支持**飞书自适应彩色卡片**与**钉钉加签 Markdown** 告警推送，无需代理直连手机。
* **🔕 零任务栏定位提示**：采用系统网络内核被动监听与 120 秒长效缓存，彻底根除 Windows 定位小圆点闪烁。
* **🔋 电池保护与安全关机**：50%、30%、20% 梯次报警；宿舍拉闸断电 20% 电量时触发 60 秒可撤销自动安全关机。
* **🍃 极寒轻量常驻**：窗口最小化深休眠 + 底层内存自动修剪，**实测挂机内存 4.8MB，CPU 占用 0.0%**。

---

## 🏫 高校认证体系对照

| 体系类型 | 覆盖高校与特征 | 适配方案 |
| :--- | :--- | :--- |
| **Dr.COM ePortal** | **延安大学 (默认原型 · 新校区/老校区/萃园)**、吉林大学等 | 默认内置置顶，支持 `,0,` 账号前缀与移动/电信/联通后缀自动兼容 |
| **深澜 Srun 4000** | **清华大学、浙江大学、北京邮电大学、深圳大学、电子科大** 等高校 | 纯 Python 原生算法获取 challenge 并完成 xEncode / HMAC-MD5 加密 |
| **锐捷 Ruijie** | 众多工科与综合类高校（RG-ePortal / SAM+） | 自动构造 `/eportal/InterFace.do` 接口并提交凭据 |
| **通用 Web Portal** | 各高校自研或 Web 表单网关 | 通用表单解析与凭据提交 |

---

## 🚀 快速上手

### 选项 A：直接下载绿色便携版（推荐）
1. 前往 [**Releases 发行版页面**](https://github.com/MH-ai-ai/campus-tool/releases) 下载最新的 `CampusGuard-v2.0.0-Windows-x64.zip`；
2. 解压到电脑任意文件夹，双击运行 **`CampusGuard.exe`**；
3. 连入学校 Wi-Fi，点击界面顶部 **「⚡ 校园网一键打通」**，填写学号与密码即可。

### 选项 B：从源码运行
```powershell
git clone https://github.com/MH-ai-ai/campus-tool.git
cd campus-tool

# 安装依赖
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 运行应用 (无控制台静默启动)
& ".\.venv\Scripts\pythonw.exe" "campus_guard.pyw"

# 运行单元测试
.\.venv\Scripts\python.exe -m unittest discover tests -v
```

---

## ⚙️ 核心配置参数 (`config.json`)

系统首次运行自动生成本地加密配置 `config.json`，敏感信息自动本地加密保护：

| 配置项 | 说明 | 示例 |
| :--- | :--- | :--- |
| `university_name` | 所属高校名称 | `"延安大学 (默认 · Dr.COM)"` |
| `auth_protocol` | 认证协议体系 | `"drcom"` / `"srun"` / `"ruijie"` / `"portal"` |
| `campus_account` | 校园网学号 / 账号 | `"20240001"` |
| `campus_password` | 校园网密码（本地加密） | `"******"` |
| `campus_auth_url` | 认证提交接口（支持自动嗅探） | `"http://10.212.0.1:801/eportal/index.jsp"` |
| `feishu_webhook_url` | 飞书机器人通知地址（免梯推荐） | `"https://open.feishu.cn/open-apis/bot/v2/hook/..."` |
| `dingtalk_webhook_url`| 钉钉机器人通知地址（免梯推荐） | `"https://oapi.dingtalk.com/robot/send?access_token=..."` |

---

## 🤝 贡献更多高校模板

如需收录您所在的高校，欢迎向 [`data/universities.json`](data/universities.json) 提交 PR：
```json
{
  "id": "your_school_id",
  "name": "某某大学 (深澜 Srun / Dr.COM / 锐捷)",
  "pinyin": "moumoudaxue mmdx",
  "protocol": "srun",
  "auth_url": "http://10.0.0.1/cgi-bin/srun_portal",
  "gateway": "10.0.0.1",
  "wifi_ssids": ["School-WiFi"],
  "domain_keywords": ["school.edu.cn"]
}
```

---

## 📄 License

MIT License. 特别致敬延安大学（Yan'an University）校园网络开发与测试支持。
