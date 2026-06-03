# Campus Guard Design

## Scene
用户在校园环境里让笔记本后台运行，偶尔从托盘打开窗口快速确认网络和电源状态；环境可能是夜间宿舍或实验室，界面应克制、低亮度、易扫读。

## Visual Direction
- Register: product
- Theme: tinted dark-neutral desktop utility，降低夜间刺眼感。
- Color strategy: restrained。网络正常用绿色，警告用琥珀色，断网/关机风险用红色；颜色只服务状态。
- Typography: 系统字体，状态数字略大，正文紧凑。
- Layout: 首页为状态总览 + 最近事件流；控制和设置分区直接呈现，不使用装饰性卡片堆叠。

## Components
- Status strip: 网络、电池、Bot、资源四个状态块。
- Event timeline: 断网、认证、重连、供电、电量阈值等最近事件。
- Action bar: 手动重连、取消关机、刷新状态、打开日志。
- Settings form: 只展示会影响运行的配置，危险项保留明确标签。

## Interaction
- 常驻后台时只通过托盘和 Bot 通知打扰用户。
- UI 刷新不得执行阻塞网络请求。
- 错误文案应说明原因和下一步动作。
