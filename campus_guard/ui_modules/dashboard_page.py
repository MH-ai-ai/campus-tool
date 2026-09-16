from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil
from PIL import ImageGrab
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..auth import auto_detect_portal_config, campus_login, campus_logout
from ..battery import BatteryMonitor
from ..config import get_config_dict
from ..logging_setup import get_logger
from ..network import NetworkMonitor
from ..paths import APP_DIR
from ..system import (
    get_disk_free_gb,
    get_local_ip,
    get_memory_usage,
    get_wifi_info,
    reconnect_wifi,
)
from .quick_setup_dialog import QuickSetupDialog
from .styles import _APPLE_COLORS, get_apple_font
from .widgets import _AppleCard, _StatusPill, _Worker


log = get_logger()


class _BatteryCard(_AppleCard):
    def __init__(self, parent=None) -> None:
        super().__init__("电源与电池", parent)

        # 状态药丸
        self._pill = _StatusPill("检测中", "neutral")
        self.header_row.addWidget(self._pill)

        # 大号数值展示
        self._pct_label = QLabel("--%")
        self._pct_label.setFont(get_apple_font(26, QFont.Weight.Bold))
        self._layout.addWidget(self._pct_label)

        # 极细苹果风进度条
        self._bar = QProgressBar()
        self._bar.setFixedHeight(6)
        self._bar.setTextVisible(False)
        self._layout.addWidget(self._bar)

        self._status_label = QLabel("正在读取供电状态...")
        self._status_label.setProperty("secondary", True)
        self._status_label.setFont(get_apple_font(10))
        self._layout.addWidget(self._status_label)
        self._layout.addStretch()

    def update_data(self) -> None:
        bat = psutil.sensors_battery()
        if not bat:
            self._pct_label.setText("未检测到电池")
            self._bar.setValue(0)
            self._pill.set_state("台式机", "neutral")
            self._status_label.setText("使用交流电源持续供电")
            return

        pct = int(bat.percent)
        self._pct_label.setText(f"{pct}%")
        self._bar.setValue(pct)

        if pct <= 20:
            color = _APPLE_COLORS["danger"]
            pill_type = "danger"
        elif pct <= 50:
            color = _APPLE_COLORS["warning"]
            pill_type = "warning"
        else:
            color = _APPLE_COLORS["success"]
            pill_type = "success"

        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 0.06);
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background-color: {color};
            }}
        """)

        plug = "交流供电中" if bat.power_plugged else "电池供电"
        self._pill.set_state(plug, pill_type)

        if bat.power_plugged:
            time_str = "正在充电"
        else:
            time_str = f"预计可用 {BatteryMonitor._format_time(bat.secsleft)}"
        self._status_label.setText(time_str)


class _NetworkCard(_AppleCard):
    def __init__(self, network_monitor: NetworkMonitor, parent=None) -> None:
        super().__init__("网络连接", parent)
        self._network = network_monitor

        self._pill = _StatusPill("检测中", "neutral")
        self.header_row.addWidget(self._pill)

        self._state_label = QLabel("检测中...")
        self._state_label.setFont(get_apple_font(22, QFont.Weight.Bold))
        self._layout.addWidget(self._state_label)

        self._details = QLabel("")
        self._details.setProperty("secondary", True)
        self._details.setFont(get_apple_font(10))
        self._details.setWordWrap(True)
        self._layout.addWidget(self._details)
        self._layout.addStretch()

    def update_data(self) -> None:
        snap = self._network.last_snapshot
        online = self._network.is_online

        if online is True:
            is_campus = snap and snap.is_campus_network
            self._state_label.setText("在线")
            self._state_label.setStyleSheet(f"color: {_APPLE_COLORS['success']};")
            self._pill.set_state("校园网" if is_campus else "家庭网", "success" if is_campus else "info")
        elif online is False:
            self._state_label.setText("离线")
            self._state_label.setStyleSheet(f"color: {_APPLE_COLORS['danger']};")
            self._pill.set_state("网络断开", "danger")
        else:
            self._state_label.setText("就绪中")
            self._pill.set_state("等待检测", "neutral")

        wifi = get_wifi_info()
        ip = get_local_ip()
        tun_str = " · TUN" if (snap and snap.clash_tun) else ""
        if_str = f"[{snap.active_interface}] " if (snap and snap.active_interface) else ""
        gw_str = " · 网关畅通" if (snap and snap.gateway_ok) else ""
        
        cfg = get_config_dict()
        uni_name = cfg.get("university_name", "延安大学")
        proto = str(cfg.get("auth_protocol", "drcom")).upper()
        campus_info = f"\n🏫 适配: {uni_name} [{proto}]" if (snap and snap.is_campus_network) else ""
        self._details.setText(f"📶 {wifi}\n🌐 {if_str}{ip}{tun_str}{gw_str}{campus_info}")


class _SystemCard(_AppleCard):
    def __init__(self, start_time: float, parent=None) -> None:
        super().__init__("系统状态", parent)
        self._start_time = start_time

        self._pill = _StatusPill("正常运行", "info")
        self.header_row.addWidget(self._pill)

        self._uptime_label = QLabel("0h 00m")
        self._uptime_label.setFont(get_apple_font(22, QFont.Weight.Bold))
        self._layout.addWidget(self._uptime_label)

        self._info = QLabel("读取中...")
        self._info.setProperty("secondary", True)
        self._info.setFont(get_apple_font(10))
        self._layout.addWidget(self._info)
        self._layout.addStretch()

    def update_data(self) -> None:
        uptime = int(time.time() - self._start_time)
        h, m = divmod(uptime // 60, 60)
        self._uptime_label.setText(f"{h}h {m:02d}m")
        try:
            disk = f"{get_disk_free_gb():.1f} GB"
        except Exception:
            disk = "未知"
        mem = get_memory_usage()
        self._info.setText(f"💾 C盘可用 {disk}   🧠 内存占用 {mem}")


class _EventCard(_AppleCard):
    def __init__(self, network_monitor: NetworkMonitor, parent=None) -> None:
        super().__init__("最近守护动态", parent)
        self._network = network_monitor

        self._pill = _StatusPill("守护活跃", "success")
        self.header_row.addWidget(self._pill)

        self._time_label = QLabel("--:--:--")
        self._time_label.setFont(get_apple_font(16, QFont.Weight.Bold))
        self._layout.addWidget(self._time_label)

        self._event_label = QLabel("正在等待事件产生...")
        self._event_label.setProperty("secondary", True)
        self._event_label.setFont(get_apple_font(10))
        self._event_label.setWordWrap(True)
        self._layout.addWidget(self._event_label)
        self._layout.addStretch()

    def update_data(self) -> None:
        event = self._network.last_event or "持续监测中"
        now = datetime.now().strftime("%H:%M:%S")
        self._time_label.setText(now)
        self._event_label.setText(event)


class _DashboardPage(QWidget):
    def __init__(
        self,
        battery_monitor: BatteryMonitor,
        network_monitor: NetworkMonitor,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.battery = battery_monitor
        self.network = network_monitor
        self._worker: _Worker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 20)
        root.setSpacing(16)

        # 头部标题
        header_box = QHBoxLayout()
        header = QLabel("Campus Guard")
        header.setFont(get_apple_font(18, QFont.Weight.Bold))
        header_box.addWidget(header)
        header_box.addStretch()
        root.addLayout(header_box)

        # -------------------------------------------------------------------
        # 小白首次智能打通醒目横幅 (Smart Onboarding Banner)
        # -------------------------------------------------------------------
        banner = QFrame()
        banner.setObjectName("bannerCard")
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(18, 14, 18, 14)
        banner_layout.setSpacing(16)

        icon_lbl = QLabel("⚡")
        icon_lbl.setFont(get_apple_font(24))
        banner_layout.addWidget(icon_lbl)

        desc_box = QVBoxLayout()
        desc_box.setSpacing(2)
        b_title = QLabel("小白一键智能打通校园网")
        b_title.setFont(get_apple_font(12, QFont.Weight.Bold))
        b_desc = QLabel("自动嗅探 Captive Portal 捕获认证服务器与网关，只需输入账号密码即可瞬间搞定！")
        b_desc.setProperty("secondary", True)
        b_desc.setFont(get_apple_font(10))
        desc_box.addWidget(b_title)
        desc_box.addWidget(b_desc)
        banner_layout.addLayout(desc_box, 1)

        self.btn_quick_setup = QPushButton("⚡ 一键极速打通")
        self.btn_quick_setup.setObjectName("primaryCapsuleBtn")
        self.btn_quick_setup.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_quick_setup.clicked.connect(self._on_click_quick_setup)
        banner_layout.addWidget(self.btn_quick_setup)

        root.addWidget(banner)

        # -------------------------------------------------------------------
        # 2×2 苹果 Squircle 卡片网格
        # -------------------------------------------------------------------
        grid = QGridLayout()
        grid.setSpacing(14)
        self._bat_card = _BatteryCard()
        self._net_card = _NetworkCard(network_monitor)
        self._sys_card = _SystemCard(time.time())
        self._evt_card = _EventCard(network_monitor)
        grid.addWidget(self._bat_card, 0, 0)
        grid.addWidget(self._net_card, 0, 1)
        grid.addWidget(self._sys_card, 1, 0)
        grid.addWidget(self._evt_card, 1, 1)
        root.addLayout(grid, 1)

        # -------------------------------------------------------------------
        # 底部苹果胶囊快捷操作栏
        # -------------------------------------------------------------------
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        self.btn_wifi = self._make_btn("📶 重连 WiFi")
        self.btn_wifi.clicked.connect(self._reconnect_wifi)
        action_bar.addWidget(self.btn_wifi)

        self.btn_auth = self._make_btn("🔐 校园网认证")
        self.btn_auth.clicked.connect(self._auth_campus)
        action_bar.addWidget(self.btn_auth)

        self.btn_logout = self._make_btn("🚪 注销下线")
        self.btn_logout.clicked.connect(self._logout_campus)
        action_bar.addWidget(self.btn_logout)

        self.btn_screenshot = self._make_btn("📸 截取屏幕")
        self.btn_screenshot.clicked.connect(self._screenshot)
        action_bar.addWidget(self.btn_screenshot)

        self.btn_lock = self._make_btn("🔒 锁定屏幕")
        self.btn_lock.clicked.connect(self._lock_screen)
        action_bar.addWidget(self.btn_lock)

        self.btn_restart = self._make_btn("🔁 重启守护")
        self.btn_restart.clicked.connect(self._restart)
        action_bar.addWidget(self.btn_restart)

        root.addLayout(action_bar)

        # 状态反馈行
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(get_apple_font(10))
        root.addWidget(self.status_label)

        # 5秒定时轮询刷新
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_cards)
        self._timer.start(5000)
        self._refresh_cards()

    @staticmethod
    def _make_btn(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("actionBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _refresh_cards(self) -> None:
        self._bat_card.update_data()
        self._net_card.update_data()
        self._sys_card.update_data()
        self._evt_card.update_data()

    def pause(self) -> None:
        """进入后台休眠态：彻底停止卡片定时器与数据读取。"""
        if self._timer.isActive():
            self._timer.stop()

    def resume(self) -> None:
        """从后台唤醒：重新启动定时器并毫秒级刷新一次最新状态。"""
        if not self._timer.isActive():
            self._timer.start(5000)
        self._refresh_cards()

    def _on_click_quick_setup(self) -> None:
        self.status_label.setText("🔍 正在探测当前网络重定向并捕获认证网关...")
        self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['accent']};")

        def _do_detect():
            return auto_detect_portal_config()

        def _done(result):
            self._worker = None
            detected: dict[str, str] = {}
            if not isinstance(result, Exception):
                _ok, _msg, detected = result

            dlg = QuickSetupDialog(detected, parent=self)
            if dlg.exec():
                self.status_label.setText("✅ 校园网配置已保存并尝试连接上线！")
                self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['success']};")
                self.network.check()
            else:
                self.status_label.setText("")

        self._worker = _Worker(_do_detect, parent=self)
        self._worker.finished.connect(_done)
        self._worker.start()

    def _reconnect_wifi(self) -> None:
        self.status_label.setText("📶 正在尝试恢复与重连 WiFi...")
        self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['accent']};")

        def _do():
            cfg = get_config_dict()
            candidates: list[str] = []

            # 1. 优先提取当前正在连接的 Wi-Fi 名称
            wifi_raw = get_wifi_info(force=True)
            current_ssid = wifi_raw.split("(", 1)[0].strip() if "(" in wifi_raw else wifi_raw.strip()
            if current_ssid and current_ssid not in ("未连接", "未知"):
                candidates.append(current_ssid)

            # 2. 用户配置中的校园 SSID
            configured = cfg.get("campus_wifi_ssids", [])
            if isinstance(configured, (list, tuple)):
                for s in configured:
                    s_str = str(s).strip()
                    if s_str and s_str not in candidates:
                        candidates.append(s_str)
            single = str(cfg.get("campus_wifi_ssid", "")).strip()
            if single and single not in candidates:
                candidates.append(single)

            # 3. 系统中保存的无线配置文件 (netsh wlan profiles)
            from ..system import get_saved_wifi_profiles
            saved = get_saved_wifi_profiles()
            for p in saved:
                if any(k in p.lower() for k in ("yadx", "yau", "campus", "wlan", "wifi", "stu", "tea")):
                    if p not in candidates:
                        candidates.append(p)

            # 依次尝试已找到的候选 SSID
            for target_ssid in candidates:
                if reconnect_wifi(target_ssid):
                    return True, target_ssid

            # 兜底：直接执行系统智能自愈重连
            if reconnect_wifi():
                active = get_wifi_info(force=True)
                active_name = active.split("(", 1)[0].strip() if "(" in active else active
                return True, active_name

            return False, current_ssid

        def _done(result):
            self._worker = None
            if isinstance(result, Exception):
                self.status_label.setText(f"❌ WiFi 重连异常: {result}")
                self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['danger']};")
            elif result[0]:
                self.status_label.setText(f"✅ WiFi 已恢复连接并获取 IP: {result[1]}")
                self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['success']};")
                self.network.check()
            else:
                self.status_label.setText("⚠️ 未找到系统已存可用 WiFi，请先在 Windows 网络列表中连接一次")
                self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['warning']};")

        self._worker = _Worker(_do, parent=self)
        self._worker.finished.connect(_done)
        self._worker.start()

    def _auth_campus(self) -> None:
        cfg = get_config_dict()
        acc = str(cfg.get("campus_account", "") or "").strip()
        pwd = str(cfg.get("campus_password", "") or "").strip()
        url = str(cfg.get("campus_auth_url", "") or "").strip()

        if not acc or not pwd or not url:
            self.status_label.setText("⚠️ 尚未配置学号密码，已为您打开一键配置窗口...")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['warning']};")
            self._on_click_quick_setup()
            return

        self.status_label.setText("🔐 正在发起校园网认证登录...")
        self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['accent']};")

        def _done(result):
            self._worker = None
            if isinstance(result, Exception):
                self.status_label.setText(f"❌ 认证异常: {result}")
                self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['danger']};")
            else:
                ok, msg = result
                self.status_label.setText(f"{'✅' if ok else '❌'} {msg}")
                self.status_label.setStyleSheet(
                    f"color: {_APPLE_COLORS['success'] if ok else _APPLE_COLORS['danger']};"
                )
                self.network.check()

        self._worker = _Worker(campus_login, parent=self)
        self._worker.finished.connect(_done)
        self._worker.start()

    def _logout_campus(self) -> None:
        self.status_label.setText("🚪 正在向网关注销下线...")
        self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['accent']};")

        def _done(result):
            self._worker = None
            if isinstance(result, Exception):
                self.status_label.setText(f"❌ 注销下线异常: {result}")
                self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['danger']};")
            else:
                ok, msg = result
                self.status_label.setText(f"{'✅' if ok else '❌'} {msg}")
                self.status_label.setStyleSheet(
                    f"color: {_APPLE_COLORS['success'] if ok else _APPLE_COLORS['danger']};"
                )
                self.network.check()

        self._worker = _Worker(campus_logout, parent=self)
        self._worker.finished.connect(_done)
        self._worker.start()

    def _lock_screen(self) -> None:
        try:
            ctypes.windll.user32.LockWorkStation()
            self.status_label.setText("🔒 屏幕锁定命令已执行")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['success']};")
        except Exception as err:
            self.status_label.setText(f"❌ 锁屏失败: {err}")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['danger']};")

    def _screenshot(self) -> None:
        try:
            tmp = Path(APP_DIR) / "screenshot_tmp.png"
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            img = ImageGrab.grab()
            img.save(tmp, "PNG")
            os.startfile(tmp)
            self.status_label.setText("📸 截图已保存至应用目录并已打开预览")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['success']};")
        except Exception as err:
            self.status_label.setText(f"❌ 截图失败: {err}")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['danger']};")

    def _restart(self) -> None:
        from PyQt6.QtWidgets import QApplication

        log.info("用户请求重启守护程序")
        if getattr(sys, "frozen", False):
            cmd = [sys.executable]
        else:
            script = str(APP_DIR / "campus_guard.pyw")
            python = sys.executable
            cmd = [python, script]

        subprocess.Popen(cmd, creationflags=0x08000000)
        QApplication.quit()
