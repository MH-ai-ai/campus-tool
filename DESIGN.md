# Campus Guard Design

## Scene
用户在校园环境里让笔记本后台运行，偶尔从托盘打开窗口快速确认网络和电源状态；环境可能是夜间宿舍或实验室，界面应克制、低亮度、易扫读。

## Visual Direction
- Register: product
- Theme: 系统原生 PyQt6 桌面工具，日志区使用低亮度深色背景，避免夜间刺眼。
- Color strategy: restrained。网络正常用绿色，警告用琥珀色，断网/关机风险用红色；颜色只服务状态。
- Typography: 系统字体，状态数字略大，正文紧凑。
- Layout: 状态、控制、日志、设置四个标签页直接呈现；状态页展示网络、电池、资源和最近事件，不使用装饰性卡片堆叠。

## Components
- Status panel: 网络、电池、资源占用、最近事件的紧凑文本总览。
- Log panel: 增量读取本地日志，避免重复加载完整日志文件。
- Control tab: 手动重连 WiFi、校园网认证、锁屏、截屏、重启和打开日志。
- Settings form: 只展示会影响运行的配置，危险项保留明确标签。

## Interaction
- 常驻后台时只通过托盘和 Bot 通知打扰用户。
- UI 刷新不得执行阻塞网络请求。
- 错误文案应说明原因和下一步动作。
