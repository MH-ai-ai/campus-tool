# Campus Guard Design Specification (Apple HIG)

## Scene
用户在高校寝室、实验室让笔记本长时间后台值守运行，偶尔从任务栏托盘唤出窗口查看状态或调整配置。环境多为夜间或实验室，界面必须兼顾高级感、低照度微光与高扫视性。

## Visual Direction
- **设计规范**：Apple HIG (Human Interface Guidelines) 苹果设计系统规范。
- **色彩策略 (Color Hierarchy)**：
  - 深空灰微光背景（`#141417`）与微透侧边栏（`#1a1a20`）。
  - 毛玻璃卡片底色（`#212128`）辅以 `rgba(255, 255, 255, 0.08)` 单像素高光微边框。
  - 功能状态色：Apple Green (`#30d158`) 在线、Apple Orange (`#ff9f0a`) 警告、Apple Red (`#ff453a`) 故障断网、SF Blue (`#0a84ff`) 强调色。
- **字体规范 (Typography)**：
  - 采用系统级高质量抗锯齿矢量字体（`PingFang SC`, `SF Pro`, `Microsoft YaHei UI`, `Segoe UI`）。
  - 杜绝 Windows DirectWrite 位图回退报错。
- **圆角规范 (Continuous Smooth Corner)**：
  - 卡片统一采用 14px 苹果平滑连续圆角（Squircle），按钮采用 15px 胶囊圆角。

## Components
- **Squircle 卡片容器 (`_AppleCard`)**：带标题与状态药丸的自适应内容容器。
- **状态呼吸药丸 (`_StatusPill`)**：内置发光指示灯（●）、半透明色块与精炼文字。
- **小白首次打通向导 (`QuickSetupDialog`)**：极简双字段表单，自动回显嗅探参数。
- **Grouped Insets 分组列表 (`_SettingsPage`)**：macOS 系统偏好设置风格的卡片分组，内嵌微阴影输入框。
- **日志面板 (`_LogPage`)**：苹果终端微光风格，支持级别过滤与关键词秒级高亮。

## Interaction
- **后台常驻**：关闭窗口无缝最小化至系统托盘，托盘图标三色动态指示状态。
- **非阻塞交互**：所有网络探测、嗅探与重连均在异步后台工作线程执行，界面保持 60fps 丝滑流畅。
