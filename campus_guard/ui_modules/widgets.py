from __future__ import annotations

from typing import Callable
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .styles import _APPLE_COLORS, get_apple_font


class _Worker(QThread):
    finished = pyqtSignal(object)

    def __init__(self, fn: Callable, *args, parent=None, **kwargs) -> None:
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as err:
            self.finished.emit(err)


class _NavButton(QPushButton):
    def __init__(self, text: str, index: int, parent=None) -> None:
        super().__init__(text, parent)
        self.index = index
        self.setObjectName("navBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class _SideBar(QWidget):
    page_changed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(56)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(10)

        self._buttons: list[_NavButton] = []
        icons = [("📊", "仪表盘"), ("📜", "运行日志"), ("⚙", "偏好设置")]
        for idx, (icon, tooltip) in enumerate(icons):
            btn = _NavButton(icon, idx, self)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda _, i=idx: self.select_page(i))
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch()
        self.select_page(0)

    def select_page(self, index: int) -> None:
        for btn in self._buttons:
            btn.setProperty("active", btn.index == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.page_changed.emit(index)


class _StatusPill(QLabel):
    """苹果风状态指示药丸标签（自带发光小圆点指示灯与半透明底色）。"""

    def __init__(self, text: str = "", state_type: str = "neutral", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusPill")
        self.set_state(text, state_type)

    def set_state(self, text: str, state_type: str = "neutral") -> None:
        color_map = {
            "success": (_APPLE_COLORS["success"], _APPLE_COLORS["success_subtle"], "●"),
            "warning": (_APPLE_COLORS["warning"], _APPLE_COLORS["warning_subtle"], "▲"),
            "danger": (_APPLE_COLORS["danger"], _APPLE_COLORS["danger_subtle"], "■"),
            "info": (_APPLE_COLORS["accent"], _APPLE_COLORS["accent_subtle"], "●"),
            "neutral": (_APPLE_COLORS["text_secondary"], "rgba(255, 255, 255, 0.05)", "○"),
        }
        fg, bg, dot = color_map.get(state_type, color_map["neutral"])
        self.setText(f"{dot}  {text}")
        self.setStyleSheet(f"""
            QLabel#statusPill {{
                color: {fg};
                background-color: {bg};
                border: 1px solid {fg}40;
                border-radius: 11px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)


class _AppleCard(QFrame):
    """苹果连续平滑圆角卡片基础容器。"""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("appleCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 16)
        self._layout.setSpacing(8)

        # 头部行
        self.header_row = QHBoxLayout()
        self.header_row.setSpacing(8)

        self.title_lbl = QLabel(title)
        self.title_lbl.setProperty("secondary", True)
        self.title_lbl.setFont(get_apple_font(10, QFont.Weight.Medium))
        self.header_row.addWidget(self.title_lbl)
        self.header_row.addStretch()

        self._layout.addLayout(self.header_row)

    def update_data(self) -> None:
        pass


_StatusCard = _AppleCard  # 保持兼容旧代码引用
