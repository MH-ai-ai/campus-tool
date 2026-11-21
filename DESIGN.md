# 安澜 Design Specification (iOS Light Frosted Glass)

## Scene
用户在高校寝室、自习室或实验室长时间后台运行客户端，随时打开桌面控制中心查看网络、电量与日志或调整配置。界面需端庄大气、温和通透、扫视即懂，避免暗黑极客感与高饱和花哨渐变。

## Visual Direction
- **设计规范**：iOS / macOS 浅色典雅微透磨砂玻璃风格（Restrained Product UI）。
- **色彩策略 (Color Hierarchy)**：
  - **底层画布**：柔和冷雾瓷白渐变（`#edf1f7 -> #f5f7fb -> #e9eef5`），辅以极淡冷蓝漫反射柔光。
  - **微透侧栏与顶栏**：`rgba(247, 249, 253, 0.80)` / `rgba(243, 246, 251, 0.86)` + `backdrop-filter: blur(20px)` + `1px` 冷灰细边线。
  - **磨砂玻璃卡片**：`rgba(255, 255, 255, 0.74)` + `backdrop-filter: blur(18px)` + 顶缘 `1px` 内白高光 + 极轻扩散投影；内嵌指标块采用 `rgba(238, 242, 248, 0.66)`。
  - **唯一主强调色**：典雅黛蓝 `#2b5797`（Hover `#22477d`、Active `#1b3b68`）。
  - **文字层级**：主墨 `#18202c` / 次灰 `#526075` / 辅灰 `#7b8798`。
  - **低饱和语义状态色**：在线松绿 `#1f7a53`、警告柔珀 `#9a5b13`、异常绛红 `#b43a40`。
- **字体规范 (Typography)**：
  - 系统级抗锯齿字体栈（`-apple-system`, `SF Pro Display`, `PingFang SC`, `Microsoft YaHei UI`, `Segoe UI`）。
- **圆角与按钮规范**：
  - 主容器统一 `16px`（`rounded-2xl`），控件与内嵌块统一 `8px~12px`，工具栏按钮统一高度并禁止文本折行。

## Components
- **全局悬浮 Toast (`ToastProvider`)**：右上角固定堆叠悬浮提示，零布局挤压或卡片顶跳。
- **固定玻璃顶栏 + 单行工具栏 (`LogView` / `SettingsView` / `DashboardView`)**：所有操作按钮单行防折行，支持原地微反馈与行内二次确认。
- **浅色瓷白日志面板 (`LogView`)**：炭灰等宽字体 + 低饱和级别小徽章 + 支持直接划选复制。
- **快速配置向导 (`QuickSetupModal`)**：浅色磨砂玻璃模态弹窗，自动回显嗅探参数。

## Interaction
- **后台常驻**：关闭窗口无缝最小化至系统托盘，托盘图标动态指示状态。
- **非阻塞交互**：所有网络探测、嗅探与重连均在后台工作线程执行，界面保持流畅响应。
