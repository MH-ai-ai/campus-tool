from __future__ import annotations

# ---------------------------------------------------------------------------
# Apple HIG (Human Interface Guidelines) 苹果设计系统规范色彩与样式表
# ---------------------------------------------------------------------------

_APPLE_COLORS = {
    # 纯正深空灰阶 (macOS Sonoma / Sequoia 暗色层级)
    "window_bg": "#111216",         # 纯净深邃底色 (午夜微光)
    "sidebar_bg": "#16171d",        # 侧边栏微透深灰
    "card_bg": "#1c1e26",           # 苹果连续圆角卡片底色 (Squircle Surface)
    "card_hover": "#232630",        # 卡片悬停微呼吸亮感
    "card_border": "rgba(255, 255, 255, 0.07)", # 细腻高光半透明微边框
    "card_border_solid": "#282b36", # 实体保底微边框 (杜绝生硬切割)

    # 苹果文字阶梯
    "text_primary": "#f3f4f6",      # 主标题与正文 (温润白，杜绝刺眼眩光)
    "text_secondary": "#9ca3af",    # 辅助与次级说明文本
    "text_tertiary": "#6b7280",     # 微弱提示与占位符

    # 语义强调色体系 (明度柔和、色温协调、护眼舒适)
    "accent": "#0a84ff",            # SF Blue 苹果系统强调蓝
    "accent_hover": "#3b99ff",      # 强调色悬停
    "accent_subtle": "rgba(10, 132, 255, 0.12)", # 胶囊半透明底
    "accent_border": "rgba(10, 132, 255, 0.28)", # 胶囊柔光边框

    "success": "#32d74b",           # Apple Mint/Green 翡翠绿 (温润在线)
    "success_hover": "#38e053",
    "success_subtle": "rgba(50, 215, 75, 0.12)",
    "success_border": "rgba(50, 215, 75, 0.28)",

    "warning": "#ff9f0a",           # Apple Amber 暖琥珀橙 (温和提醒)
    "warning_hover": "#ffad33",
    "warning_subtle": "rgba(255, 159, 10, 0.12)",
    "warning_border": "rgba(255, 159, 10, 0.28)",

    "danger": "#ff453a",            # Apple Coral 柔珊红 (克制警示)
    "danger_hover": "#ff5e54",
    "danger_subtle": "rgba(255, 69, 58, 0.12)",
    "danger_border": "rgba(255, 69, 58, 0.28)",

    # 交互控件与表单质感
    "btn_capsule": "#252833",       # 苹果胶囊按钮沉稳底色
    "btn_capsule_hover": "#2e3240", # 按钮悬停轻提亮
    "btn_capsule_border": "rgba(255, 255, 255, 0.09)",
    "input_bg": "#15171e",          # 输入控件内嵌底色
    "input_border": "#282b36",      # 输入框微边框
    "separator": "#232631",         # 分割线
}

_COLORS = {
    **_APPLE_COLORS,
    "bg": _APPLE_COLORS["window_bg"],
    "card": _APPLE_COLORS["card_bg"],
    "card_hover": _APPLE_COLORS["card_hover"],
    "text": _APPLE_COLORS["text_primary"],
    "dim": _APPLE_COLORS["text_secondary"],
    "border": _APPLE_COLORS["card_border_solid"],
    "green": _APPLE_COLORS["success"],
    "orange": _APPLE_COLORS["warning"],
    "red": _APPLE_COLORS["danger"],
    "btn": _APPLE_COLORS["btn_capsule"],
    "btn_hover": _APPLE_COLORS["btn_capsule_hover"],
    "input": _APPLE_COLORS["input_bg"],
}  # 兼容旧代码引用

from PyQt6.QtGui import QFont

_FONT_FAMILY = '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "PingFang SC", "Segoe UI Variable Display", "Microsoft YaHei UI", "Segoe UI", sans-serif'


def get_apple_font(point_size: int = 10, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """获取高质量平滑抗锯齿矢量字体，杜绝Windows DirectWrite位图字体回退报警。"""
    font = QFont("Microsoft YaHei UI", point_size)
    font.setWeight(weight)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font

_STYLESHEET = f"""
/* --- 全局与窗口背景 --- */
QMainWindow, QDialog, QWidget#centralWidget {{
    background-color: {_APPLE_COLORS['window_bg']};
    font-family: {_FONT_FAMILY};
}}
QWidget {{
    font-family: {_FONT_FAMILY};
}}
QLabel {{
    color: {_APPLE_COLORS['text_primary']};
    background: transparent;
}}
QLabel[secondary="true"], QLabel[dim="true"] {{
    color: {_APPLE_COLORS['text_secondary']};
}}
QLabel[tertiary="true"] {{
    color: {_APPLE_COLORS['text_tertiary']};
}}

/* --- 苹果风格侧边栏导航 --- */
QWidget#sidebar {{
    background-color: {_APPLE_COLORS['sidebar_bg']};
    border-right: 1px solid {_APPLE_COLORS['card_border_solid']};
}}
QPushButton#navBtn {{
    background: transparent;
    border: none;
    border-radius: 12px;
    color: {_APPLE_COLORS['text_secondary']};
    font-size: 18px;
    margin: 4px 8px;
    min-height: 40px;
    max-height: 40px;
    min-width: 40px;
    max-width: 40px;
}}
QPushButton#navBtn:hover {{
    background-color: rgba(255, 255, 255, 0.07);
    color: {_APPLE_COLORS['text_primary']};
}}
QPushButton#navBtn[active="true"] {{
    background-color: {_APPLE_COLORS['accent_subtle']};
    color: {_APPLE_COLORS['accent']};
    font-weight: bold;
}}

/* --- 苹果 Squircle 连续圆角卡片 --- */
QFrame#card, QFrame#appleCard {{
    background-color: {_APPLE_COLORS['card_bg']};
    border-radius: 14px;
    border: 1px solid {_APPLE_COLORS['card_border_solid']};
}}
QFrame#card:hover, QFrame#appleCard:hover {{
    background-color: {_APPLE_COLORS['card_hover']};
}}
QFrame#bannerCard {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a2233, stop:0.6 #181d29, stop:1 #141720);
    border-radius: 14px;
    border: 1px solid rgba(64, 156, 255, 0.24);
}}

/* --- 苹果胶囊药丸按钮 (Capsule Buttons) --- */
QPushButton#actionBtn, QPushButton#capsuleBtn {{
    background-color: {_APPLE_COLORS['btn_capsule']};
    color: {_APPLE_COLORS['text_primary']};
    border: 1px solid {_APPLE_COLORS['card_border_solid']};
    border-radius: 15px;
    padding: 7px 18px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#actionBtn:hover, QPushButton#capsuleBtn:hover {{
    background-color: {_APPLE_COLORS['btn_capsule_hover']};
    border-color: rgba(255, 255, 255, 0.16);
    color: #ffffff;
}}
QPushButton#actionBtn:pressed, QPushButton#capsuleBtn:pressed {{
    background-color: #1e212b;
}}
QPushButton#actionBtn:disabled, QPushButton#capsuleBtn:disabled {{
    color: {_APPLE_COLORS['text_tertiary']};
    background-color: rgba(255, 255, 255, 0.02);
    border-color: transparent;
}}

/* 主强调胶囊按钮 (Primary Action) */
QPushButton#primaryCapsuleBtn {{
    background-color: {_APPLE_COLORS['accent']};
    color: #ffffff;
    border: none;
    border-radius: 15px;
    padding: 7px 20px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#primaryCapsuleBtn:hover {{
    background-color: {_APPLE_COLORS['accent_hover']};
}}
QPushButton#primaryCapsuleBtn:pressed {{
    background-color: #0071e3;
}}

/* 成功绿色胶囊按钮 (Success/Connect) */
QPushButton#successCapsuleBtn {{
    background-color: {_APPLE_COLORS['success']};
    color: #0d1e11;
    border: none;
    border-radius: 15px;
    padding: 7px 20px;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton#successCapsuleBtn:hover {{
    background-color: {_APPLE_COLORS['success_hover']};
}}

/* --- 状态指示药丸 (Status Pill) --- */
QLabel#statusPill {{
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}}

/* --- 苹果 macOS 设置风格分组内嵌卡片 (Grouped Inset Lists) --- */
QGroupBox {{
    background-color: {_APPLE_COLORS['card_bg']};
    border: 1px solid {_APPLE_COLORS['card_border_solid']};
    border-radius: 12px;
    margin-top: 22px;
    padding-top: 16px;
    padding-bottom: 8px;
    font-weight: 600;
    font-size: 13px;
    color: {_APPLE_COLORS['accent']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 2px;
    padding: 0 4px;
    color: {_APPLE_COLORS['text_secondary']};
    font-size: 11px;
    font-weight: 600;
    background: transparent;
    letter-spacing: 0.5px;
}}

/* --- 表单输入控件体系 --- */
QLineEdit, QSpinBox {{
    background-color: {_APPLE_COLORS['input_bg']};
    color: {_APPLE_COLORS['text_primary']};
    border: 1px solid {_APPLE_COLORS['card_border_solid']};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}}
QLineEdit:hover, QSpinBox:hover {{
    border-color: rgba(255, 255, 255, 0.16);
}}
QLineEdit:focus, QSpinBox:focus {{
    border-color: {_APPLE_COLORS['accent']};
    background-color: #191c24;
}}

/* --- 下拉选择框体系 (消除浅色回退与生硬边框) --- */
QComboBox {{
    background-color: {_APPLE_COLORS['input_bg']};
    color: {_APPLE_COLORS['text_primary']};
    border: 1px solid {_APPLE_COLORS['card_border_solid']};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: rgba(255, 255, 255, 0.16);
}}
QComboBox:focus {{
    border-color: {_APPLE_COLORS['accent']};
    background-color: #191c24;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {_APPLE_COLORS['text_secondary']};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {_APPLE_COLORS['card_bg']};
    color: {_APPLE_COLORS['text_primary']};
    border: 1px solid {_APPLE_COLORS['card_border_solid']};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {_APPLE_COLORS['accent_subtle']};
    selection-color: {_APPLE_COLORS['accent']};
    outline: none;
}}

QCheckBox {{
    color: {_APPLE_COLORS['text_primary']};
    spacing: 8px;
    font-size: 12px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid {_APPLE_COLORS['card_border_solid']};
    background-color: {_APPLE_COLORS['input_bg']};
}}
QCheckBox::indicator:hover {{
    border-color: rgba(255, 255, 255, 0.2);
}}
QCheckBox::indicator:checked {{
    background-color: {_APPLE_COLORS['accent']};
    border-color: {_APPLE_COLORS['accent']};
}}

/* --- 日志面板与搜索 --- */
QLineEdit#searchBox {{
    background-color: {_APPLE_COLORS['input_bg']};
    color: {_APPLE_COLORS['text_primary']};
    border: 1px solid {_APPLE_COLORS['card_border_solid']};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
}}
QLineEdit#searchBox:focus {{
    border-color: {_APPLE_COLORS['accent']};
}}
QPushButton#filterChip {{
    background-color: transparent;
    color: {_APPLE_COLORS['text_secondary']};
    border: 1px solid {_APPLE_COLORS['card_border_solid']};
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 11px;
}}
QPushButton#filterChip:hover {{
    background-color: rgba(255, 255, 255, 0.06);
    color: {_APPLE_COLORS['text_primary']};
}}
QPushButton#filterChip[active="true"] {{
    background-color: {_APPLE_COLORS['accent_subtle']};
    color: {_APPLE_COLORS['accent']};
    border-color: {_APPLE_COLORS['accent']};
    font-weight: bold;
}}
QPlainTextEdit {{
    background-color: #131418;
    color: {_APPLE_COLORS['text_primary']};
    border: 1px solid {_APPLE_COLORS['card_border_solid']};
    border-radius: 12px;
    padding: 12px;
    selection-background-color: {_APPLE_COLORS['accent']};
    selection-color: #ffffff;
}}

/* --- 滚动条极致简约 (macOS Scrollbar) --- */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.12);
    min-height: 24px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.24);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
"""
