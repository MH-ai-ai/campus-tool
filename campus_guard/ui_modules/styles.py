from __future__ import annotations

# ---------------------------------------------------------------------------
# Apple HIG (Human Interface Guidelines) 苹果设计系统规范色彩与样式表
# ---------------------------------------------------------------------------

_APPLE_COLORS = {
    "window_bg": "#141417",         # 深空灰主背景 (macOS Sonoma / Sequoia 深色模式)
    "sidebar_bg": "#1a1a20",        # 侧边栏微透深灰
    "card_bg": "#212128",           # 苹果毛玻璃卡片底色
    "card_hover": "#282832",        # 卡片悬停微光
    "card_border": "rgba(255, 255, 255, 0.08)", # 细腻高光微边框
    "card_border_solid": "#2d2d38", # 兼容实体微边框
    "text_primary": "#f5f5f7",      # 苹果主文本色
    "text_secondary": "#98989f",    # 苹果副文本色
    "text_tertiary": "#6e6e73",     # 苹果微弱说明文本
    "accent": "#0a84ff",            # SF Blue 苹果系统强调蓝
    "accent_hover": "#409cff",      # 强调色悬停
    "accent_subtle": "rgba(10, 132, 255, 0.15)", # 强调色半透明底
    "success": "#30d158",           # Apple Green 系统绿 (在线/安全)
    "success_subtle": "rgba(48, 209, 88, 0.15)",
    "warning": "#ff9f0a",           # Apple Orange 系统橙 (警告/弱网)
    "warning_subtle": "rgba(255, 159, 10, 0.15)",
    "danger": "#ff453a",            # Apple Red 系统红 (断网/危险)
    "danger_subtle": "rgba(255, 69, 58, 0.15)",
    "btn_capsule": "#2c2c36",       # 苹果胶囊按钮底色
    "btn_capsule_hover": "#363642", # 按钮悬停
    "input_bg": "#19191f",          # 输入框内嵌底色
    "separator": "#282834",         # 组内单像素分割线
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
QMainWindow, QWidget#centralWidget {{
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
    background-color: rgba(255, 255, 255, 0.06);
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
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a2744, stop:1 #212128);
    border-radius: 14px;
    border: 1px solid rgba(10, 132, 255, 0.35);
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
    border-color: rgba(255, 255, 255, 0.18);
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
    font-weight: bold;
}}
QPushButton#primaryCapsuleBtn:hover {{
    background-color: {_APPLE_COLORS['accent_hover']};
}}

/* 成功绿色胶囊按钮 (Success/Connect) */
QPushButton#successCapsuleBtn {{
    background-color: {_APPLE_COLORS['success']};
    color: #000000;
    border: none;
    border-radius: 15px;
    padding: 7px 20px;
    font-size: 13px;
    font-weight: bold;
}}
QPushButton#successCapsuleBtn:hover {{
    background-color: #34c759;
}}

/* --- 状态指示药丸 (Status Pill) --- */
QLabel#statusPill {{
    border-radius: 10px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
}}

/* --- 苹果 macOS 设置风格分组内嵌卡片 (Grouped Inset Lists) --- */
QGroupBox {{
    background-color: {_APPLE_COLORS['card_bg']};
    border: 1px solid {_APPLE_COLORS['card_border_solid']};
    border-radius: 12px;
    margin-top: 24px;
    padding-top: 14px;
    padding-bottom: 8px;
    font-weight: 600;
    font-size: 13px;
    color: {_APPLE_COLORS['accent']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 4px;
    padding: 0 4px;
    color: {_APPLE_COLORS['text_secondary']};
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
QLineEdit, QSpinBox {{
    background-color: {_APPLE_COLORS['input_bg']};
    color: {_APPLE_COLORS['text_primary']};
    border: 1px solid {_APPLE_COLORS['card_border_solid']};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}}
QLineEdit:focus, QSpinBox:focus {{
    border-color: {_APPLE_COLORS['accent']};
    background-color: #1f1f27;
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
QPushButton#filterChip {{
    background-color: transparent;
    color: {_APPLE_COLORS['text_secondary']};
    border: 1px solid {_APPLE_COLORS['card_border_solid']};
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 11px;
}}
QPushButton#filterChip[active="true"] {{
    background-color: {_APPLE_COLORS['accent_subtle']};
    color: {_APPLE_COLORS['accent']};
    border-color: {_APPLE_COLORS['accent']};
    font-weight: bold;
}}
QPlainTextEdit {{
    background-color: {_APPLE_COLORS['card_bg']};
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
    background: rgba(255, 255, 255, 0.15);
    min-height: 24px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.28);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
"""
