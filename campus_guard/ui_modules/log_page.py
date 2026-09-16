from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..paths import LOG_PATH
from .styles import _APPLE_COLORS, _COLORS, get_apple_font


class _LogReaderThread(QThread):
    lines_read = pyqtSignal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._max_lines = 1000

    def run(self) -> None:
        try:
            if not LOG_PATH.exists():
                self.lines_read.emit([])
                return
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            self.lines_read.emit(lines[-self._max_lines :])
        except Exception:
            self.lines_read.emit([])


class _LogPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._all_lines: list[str] = []
        self._active_level: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(10)

        # 头部标题
        header = QLabel("📜 运行日志")
        header.setFont(get_apple_font(16, QFont.Weight.Bold))
        root.addWidget(header)

        # 筛选工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._search = QLineEdit()
        self._search.setObjectName("searchBox")
        self._search.setPlaceholderText("🔍 搜索日志关键词...")
        self._search.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self._search, 1)

        self._level_btns: dict[str, QPushButton] = {}
        for lvl in ("全部", "INFO", "WARN", "ERROR"):
            btn = QPushButton(lvl)
            btn.setObjectName("filterChip")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, l=lvl: self._set_level(l))
            toolbar.addWidget(btn)
            self._level_btns[lvl] = btn

        self._auto_scroll = QCheckBox("自动滚屏")
        self._auto_scroll.setChecked(True)
        toolbar.addWidget(self._auto_scroll)

        clear_btn = QPushButton("清屏")
        clear_btn.setObjectName("filterChip")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_view)
        toolbar.addWidget(clear_btn)

        root.addLayout(toolbar)

        # 日志文本区域
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setMaximumBlockCount(2000)
        self.text.setFont(QFont("Consolas", 10))
        self.text.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: #131418;
                color: {_APPLE_COLORS['text_primary']};
                border: 1px solid {_APPLE_COLORS['card_border_solid']};
                border-radius: 12px;
                padding: 12px;
                selection-background-color: {_APPLE_COLORS['accent']};
                selection-color: #ffffff;
            }}
        """)
        root.addWidget(self.text, 1)

        self._set_level("全部")

        # 异步读取线程与定时器
        self._reader: _LogReaderThread | None = None
        self._last_mtime: float = 0.0
        self._last_size: int = -1
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._trigger_read)
        self._timer.start(3000)
        self._trigger_read(force=True)

    def pause(self) -> None:
        """进入后台休眠态：停用日志定时器，杜绝无谓读取磁盘与线程分配。"""
        if self._timer.isActive():
            self._timer.stop()

    def resume(self) -> None:
        """从后台唤醒：重新启动定时器并按需触发一次读取。"""
        if not self._timer.isActive():
            self._timer.start(3000)
        self._trigger_read()

    def _trigger_read(self, force: bool = False) -> None:
        if self._reader and self._reader.isRunning():
            return
        try:
            if not LOG_PATH.exists():
                return
            stat = LOG_PATH.stat()
            # 文件未修改且大小未变时，直接跳过，零磁盘读取与线程开销
            if not force and stat.st_mtime == self._last_mtime and stat.st_size == self._last_size:
                return
            self._last_mtime = stat.st_mtime
            self._last_size = stat.st_size
        except Exception:
            pass

        self._reader = _LogReaderThread(self)
        self._reader.lines_read.connect(self._on_lines_read)
        self._reader.start()

    def _on_lines_read(self, lines: list[str]) -> None:
        if lines != self._all_lines:
            self._all_lines = lines
            self._apply_filter()

    def _set_level(self, level: str) -> None:
        self._active_level = None if level == "全部" else level
        for name, btn in self._level_btns.items():
            btn.setProperty("active", name == level)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._apply_filter()

    def _apply_filter(self) -> None:
        query = self._search.text().lower()
        level = self._active_level

        filtered = []
        for line in self._all_lines:
            if level and f"[{level}" not in line and f" {level} " not in line:
                continue
            if query and query not in line.lower():
                continue
            filtered.append(line)

        scroll_val = self.text.verticalScrollBar().value()
        is_at_bottom = scroll_val >= self.text.verticalScrollBar().maximum() - 5

        self.text.setPlainText("".join(filtered))

        if self._auto_scroll.isChecked() or is_at_bottom:
            self.text.verticalScrollBar().setValue(self.text.verticalScrollBar().maximum())
        else:
            self.text.verticalScrollBar().setValue(scroll_val)

    def _clear_view(self) -> None:
        self._all_lines = []
        self.text.clear()
