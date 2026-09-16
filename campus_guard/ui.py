from __future__ import annotations

import psutil
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStackedWidget,
    QSystemTrayIcon,
    QWidget,
)

from .battery import BatteryMonitor
from .logging_setup import get_logger
from .models import GuardState
from .network import NetworkMonitor
from .system import trim_process_memory
from .telegram_bot import TelegramBot
from .tray import create_tray_icon, get_tray_color, pil_image_to_qicon

# 导出子模块组件与配置 Schema，保持对外导入完全兼容
from .ui_modules.dashboard_page import _DashboardPage
from .ui_modules.log_page import _LogPage
from .ui_modules.settings_page import _SETTINGS_SCHEMA, _SettingsPage
from .ui_modules.styles import _COLORS, _STYLESHEET
from .ui_modules.widgets import _SideBar, _Worker

__all__ = [
    "MainWindow",
    "_SETTINGS_SCHEMA",
    "_DashboardPage",
    "_LogPage",
    "_SettingsPage",
    "_SideBar",
    "_Worker",
    "_COLORS",
    "_STYLESHEET",
]

log = get_logger()


class MainWindow(QMainWindow):
    """Campus Guard 桌面端主窗口。"""

    def __init__(
        self,
        battery: BatteryMonitor,
        network: NetworkMonitor,
        tg_bot: TelegramBot,
    ) -> None:
        super().__init__()
        self.battery = battery
        self.network = network
        self.tg_bot = tg_bot

        self.setWindowTitle("Campus Guard")
        self.resize(800, 560)
        self.setStyleSheet(_STYLESHEET)

        # 整体中央控件
        central = QWidget()
        central.setObjectName("centralWidget")
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧边栏导航
        self._sidebar = _SideBar()
        main_layout.addWidget(self._sidebar)

        # 右侧多页栈
        self._stack = QStackedWidget()
        self._dashboard_page = _DashboardPage(battery, network)
        self._log_page = _LogPage()
        self._settings_page = _SettingsPage()

        self._stack.addWidget(self._dashboard_page)
        self._stack.addWidget(self._log_page)
        self._stack.addWidget(self._settings_page)
        main_layout.addWidget(self._stack, 1)

        self._sidebar.page_changed.connect(self._stack.setCurrentIndex)
        self.setCentralWidget(central)

        # 系统托盘
        self._last_tray_color: str | None = None
        self._cached_qicons: dict[str, Any] = {}
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip("Campus Guard")
        menu = QMenu()

        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.showNormal)
        menu.addAction(show_action)

        menu.addSeparator()

        reconnect_action = QAction("重连 WiFi", self)
        reconnect_action.triggered.connect(self._dashboard_page._reconnect_wifi)
        menu.addAction(reconnect_action)

        auth_action = QAction("校园网认证", self)
        auth_action.triggered.connect(self._dashboard_page._auth_campus)
        menu.addAction(auth_action)

        logout_action = QAction("注销下线", self)
        logout_action.triggered.connect(self._dashboard_page._logout_campus)
        menu.addAction(logout_action)

        menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)

        self._update_tray()
        self.tray.show()

        # 托盘图标定时刷新（低频10秒，增量比对状态，避免重复绘图）
        self._icon_timer = QTimer(self)
        self._icon_timer.timeout.connect(self._update_tray)
        self._icon_timer.start(10000)

    def _update_tray(self) -> None:
        try:
            bat = psutil.sensors_battery()
            percent = int(bat.percent) if bat else None
            plugged = bool(bat.power_plugged) if bat else None
            net_ok = self.network.is_online if self.network else None

            state = GuardState(
                network_ok=net_ok,
                power_plugged=plugged,
                battery_percent=percent,
            )
            color = get_tray_color(state)
            # 增量按需更新：仅在状态颜色变化时才重新生成并设置图标
            if color != self._last_tray_color:
                if color not in self._cached_qicons:
                    self._cached_qicons[color] = pil_image_to_qicon(create_tray_icon(color))
                self.tray.setIcon(self._cached_qicons[color])
                self._last_tray_color = color

            mode_str = "校园网" if (self.network and self.network.last_snapshot and self.network.last_snapshot.is_campus_network) else "通用网"
            tip = f"Campus Guard [{mode_str}]\n网络: {'在线' if net_ok else '离线'}"
            if percent is not None:
                tip += f"\n电量: {percent}% ({'供电' if plugged else '电池'})"
            self.tray.setToolTip(tip)
        except Exception as err:
            log.error("托盘更新失败: %s", err)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def showEvent(self, event) -> None:
        """主窗口从托盘唤醒：恢复前端定时器并立即刷新一次。"""
        super().showEvent(event)
        self._dashboard_page.resume()
        self._log_page.resume()

    def hideEvent(self, event) -> None:
        """主窗口隐藏至托盘：进入极寒休眠状态，停止前端所有定时器并修剪物理工作集。"""
        super().hideEvent(event)
        self._dashboard_page.pause()
        self._log_page.pause()
        # 延迟 600ms 等待 UI 卸载完成后整理修剪物理内存工作集
        QTimer.singleShot(600, trim_process_memory)

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "Campus Guard",
            "程序已最小化到系统托盘并进入极寒低功耗模式，后台持续守护网络与电源。",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    def _quit_app(self) -> None:
        reply = QMessageBox.question(
            self,
            "退出确认",
            "确定要退出 Campus Guard 吗？\n退出后将停止网络自动重连与电量告警守护。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.tray.hide()
            QApplication.quit()
