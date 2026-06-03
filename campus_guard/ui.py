from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from datetime import datetime

import psutil
from PIL import ImageGrab
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .auth import campus_login
from .battery import BatteryMonitor
from .config import (
    SENSITIVE_FIELDS,
    decrypt_config,
    encrypt_sensitive_fields,
    get_config_dict,
    load_config_dict,
    load_config_raw,
    save_config_raw,
    update_runtime_config,
)
from .logging_setup import get_logger
from .models import GuardState
from .network import NetworkMonitor
from .paths import LOG_PATH, APP_DIR
from .system import (
    get_disk_free_gb,
    get_local_ip,
    get_memory_usage,
    get_public_ip,
    get_wifi_info,
    reconnect_wifi,
)
from .telegram_bot import TelegramBot
from .tray import create_tray_icon, get_tray_color, pil_image_to_qicon


log = get_logger()


class StatusTab(QWidget):
    def __init__(
        self,
        battery_monitor: BatteryMonitor,
        network_monitor: NetworkMonitor,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.battery = battery_monitor
        self.network = network_monitor

        layout = QVBoxLayout(self)
        self.title_label = QLabel("📊 实时状态")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(self.title_label)

        self.info_label = QLabel("加载中...")
        self.info_label.setStyleSheet("font-size: 13px; line-height: 1.6;")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.info_label)
        layout.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(5000)
        self.refresh()

    def refresh(self) -> None:
        lines = []
        bat = psutil.sensors_battery()
        if bat is None:
            lines.append("🔋 电池: 未检测到电池（台式机或无电池设备）")
        else:
            plug = "🔌 供电中" if bat.power_plugged else "🔋 电池供电"
            lines.append(f"🔋 电池: {plug} — {bat.percent}%")
            lines.append(f"   剩余时间: {BatteryMonitor._format_time(bat.secsleft)}")

        lines.append(f"📶 WiFi: {get_wifi_info()}")
        net_icon = "🟢 在线" if self.network.is_online else "🔴 离线"
        lines.append(f"🌐 网络: {net_icon}")
        lines.append(f"🌐 公网 IP: {get_public_ip()}")
        lines.append(f"🏠 局域网 IP: {get_local_ip()}")
        try:
            lines.append(f"💾 磁盘剩余: {get_disk_free_gb():.1f} GB")
        except Exception:
            lines.append("💾 磁盘剩余: 未知")
        lines.append(f"🧠 内存: {get_memory_usage()}")
        lines.append(f"🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.info_label.setText("\n".join(lines))


class ControlTab(QWidget):
    def __init__(
        self,
        battery_monitor: BatteryMonitor,
        network_monitor: NetworkMonitor,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.battery = battery_monitor
        self.network = network_monitor

        layout = QVBoxLayout(self)
        title = QLabel("🕹️ 控制")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title)

        btn_layout = QHBoxLayout()
        self.btn_wifi = QPushButton("📶 重连 WiFi")
        self.btn_wifi.clicked.connect(self._reconnect_wifi)
        btn_layout.addWidget(self.btn_wifi)

        self.btn_auth = QPushButton("🔐 校园网认证")
        self.btn_auth.clicked.connect(self._auth_campus)
        btn_layout.addWidget(self.btn_auth)

        self.btn_lock = QPushButton("🔒 锁屏")
        self.btn_lock.clicked.connect(self._lock_screen)
        btn_layout.addWidget(self.btn_lock)

        self.btn_screenshot = QPushButton("📸 截屏")
        self.btn_screenshot.clicked.connect(self._screenshot)
        btn_layout.addWidget(self.btn_screenshot)

        self.btn_restart = QPushButton("🔁 重启工具")
        self.btn_restart.clicked.connect(self._restart)
        btn_layout.addWidget(self.btn_restart)

        self.btn_view_log = QPushButton("📜 查看日志文件")
        self.btn_view_log.clicked.connect(self._view_log)
        btn_layout.addWidget(self.btn_view_log)

        layout.addLayout(btn_layout)
        layout.addStretch()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("margin-top: 8px;")
        layout.addWidget(self.status_label)

    def _reconnect_wifi(self) -> None:
        self.status_label.setText("📶 正在重连 WiFi...")
        QApplication.processEvents()
        cfg = get_config_dict()
        ssids = cfg.get("campus_wifi_ssids", [])
        if not ssids:
            old = cfg.get("campus_wifi_ssid", "")
            ssids = [old] if old else []
        for ssid in ssids:
            if reconnect_wifi(str(ssid)):
                self.status_label.setText(f"✅ WiFi 已重连: {ssid}")
                return
        self.status_label.setText("❌ WiFi 重连失败")

    def _auth_campus(self) -> None:
        self.status_label.setText("🔐 正在认证校园网...")
        QApplication.processEvents()
        success, msg = campus_login()
        self.status_label.setText(f"{'✅' if success else '❌'} 认证{'成功' if success else '失败'}: {msg}")

    def _lock_screen(self) -> None:
        try:
            ctypes.windll.user32.LockWorkStation()
            self.status_label.setText("🔒 已锁屏")
        except Exception as err:
            self.status_label.setText(f"❌ 锁屏失败: {err}")

    def _screenshot(self) -> None:
        self.status_label.setText("📸 正在截屏...")
        QApplication.processEvents()
        tmp_path = APP_DIR / "screenshot_tmp.png"
        ps_script = APP_DIR / "_screenshot.ps1"
        try:
            save_path = str(tmp_path).replace("\\", "\\\\")
            ps_content = (
                "Add-Type -AssemblyName System.Windows.Forms\n"
                "Add-Type -AssemblyName System.Drawing\n"
                "$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds\n"
                "$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)\n"
                "$g = [System.Drawing.Graphics]::FromImage($bmp)\n"
                "$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)\n"
                f"$bmp.Save('{save_path}')\n"
                "$g.Dispose()\n"
                "$bmp.Dispose()\n"
            )
            with open(ps_script, "w", encoding="utf-8") as f:
                f.write(ps_content)
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)],
                capture_output=True,
                timeout=15,
                creationflags=0x08000000,
            )
            if tmp_path.exists() and tmp_path.stat().st_size > 1000:
                self.status_label.setText(f"✅ 截屏已保存: {tmp_path}")
            else:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
                screenshot = ImageGrab.grab()
                screenshot.save(tmp_path, "PNG")
                if tmp_path.exists() and tmp_path.stat().st_size > 1000:
                    self.status_label.setText(f"✅ 截屏已保存 (PIL): {tmp_path}")
                else:
                    self.status_label.setText("❌ 截屏失败：无法获取桌面画面")
        except Exception as err:
            self.status_label.setText(f"❌ 截屏失败: {err}")
        finally:
            if ps_script.exists():
                try:
                    os.remove(ps_script)
                except OSError:
                    pass

    def _restart(self) -> None:
        reply = QMessageBox.question(
            self,
            "确认重启",
            "确定要重启 Campus Guard 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            log.info("用户触发重启")
            os.execv(sys.executable, [sys.executable] + sys.argv)

    def _view_log(self) -> None:
        if LOG_PATH.exists():
            os.startfile(str(LOG_PATH))
        else:
            self.status_label.setText("❌ 日志文件不存在")


class LogTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 9))
        self.log_view.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        layout.addWidget(self.log_view)
        self._last_size = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._read_new_lines)
        self._timer.start(2000)
        self._read_new_lines()

    def _read_new_lines(self) -> None:
        if not LOG_PATH.exists():
            return
        try:
            size = LOG_PATH.stat().st_size
            if size < self._last_size:
                self._last_size = 0
                self.log_view.clear()
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._last_size)
                new_data = f.read()
                self._last_size = f.tell()
            if new_data:
                self.log_view.appendPlainText(new_data.rstrip("\n"))
                sb = self.log_view.verticalScrollBar()
                sb.setValue(sb.maximum())
        except Exception:
            pass


class SettingsTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel("⚙️ 配置设置")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        form = QFormLayout(scroll_widget)
        self.fields: dict[str, QWidget] = {}
        raw_cfg = load_config_dict()

        for key in [
            "campus_account",
            "campus_password",
            "campus_auth_url",
            "campus_gateway",
            "wlan_ac_ip",
            "telegram_bot_token",
            "telegram_user_id",
        ]:
            field = QLineEdit(str(raw_cfg.get(key, "")))
            if key in SENSITIVE_FIELDS:
                field.setEchoMode(QLineEdit.EchoMode.Password)
            form.addRow(key, field)
            self.fields[key] = field

        ssids = raw_cfg.get("campus_wifi_ssids", [])
        ssid_text = QLineEdit(", ".join(str(s) for s in ssids))
        form.addRow("campus_wifi_ssids (逗号分隔)", ssid_text)
        self.fields["campus_wifi_ssids"] = ssid_text

        for key, default in [
            ("check_interval_seconds", 5),
            ("network_check_interval_seconds", 30),
            ("low_battery_threshold", 30),
            ("auto_shutdown_threshold", 10),
            ("auto_shutdown_delay", 120),
        ]:
            spin = QSpinBox()
            spin.setRange(1, 3600)
            spin.setValue(int(raw_cfg.get(key, default)))
            form.addRow(key, spin)
            self.fields[key] = spin

        autostart_cb = QCheckBox()
        autostart_cb.setChecked(bool(raw_cfg.get("autostart", True)))
        form.addRow("autostart (开机自启动)", autostart_cb)
        self.fields["autostart"] = autostart_cb

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("💾 保存配置")
        self.save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(self.save_btn)
        self.reload_btn = QPushButton("🔄 重新加载")
        self.reload_btn.clicked.connect(self._load_from_file)
        btn_row.addWidget(self.reload_btn)
        layout.addLayout(btn_row)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

    def _save_config(self) -> None:
        try:
            cfg = load_config_raw()
            for key in [
                "campus_account",
                "campus_password",
                "campus_auth_url",
                "campus_gateway",
                "wlan_ac_ip",
                "telegram_bot_token",
            ]:
                cfg[key] = self.fields[key].text()

            try:
                cfg["telegram_user_id"] = int(self.fields["telegram_user_id"].text())
            except ValueError:
                self.status_label.setText("❌ telegram_user_id 必须是数字")
                return

            ssid_raw = self.fields["campus_wifi_ssids"].text()
            cfg["campus_wifi_ssids"] = [s.strip() for s in ssid_raw.split(",") if s.strip()]

            for key in [
                "check_interval_seconds",
                "network_check_interval_seconds",
                "low_battery_threshold",
                "auto_shutdown_threshold",
                "auto_shutdown_delay",
            ]:
                cfg[key] = self.fields[key].value()
            cfg["autostart"] = self.fields["autostart"].isChecked()

            encrypted_cfg = encrypt_sensitive_fields(cfg)
            save_config_raw(encrypted_cfg)
            update_runtime_config(decrypt_config(encrypted_cfg))
            self.status_label.setText(f"✅ 配置已保存 — {datetime.now().strftime('%H:%M:%S')}")
            log.info("配置已通过 GUI 保存")
        except Exception as err:
            self.status_label.setText(f"❌ 保存失败: {err}")
            log.error("配置保存失败: %s", err)

    def _load_from_file(self) -> None:
        try:
            raw_cfg = load_config_dict()
            for key in [
                "campus_account",
                "campus_password",
                "campus_auth_url",
                "campus_gateway",
                "wlan_ac_ip",
                "telegram_bot_token",
            ]:
                if key in self.fields:
                    self.fields[key].setText(str(raw_cfg.get(key, "")))

            if "telegram_user_id" in self.fields:
                self.fields["telegram_user_id"].setText(str(raw_cfg.get("telegram_user_id", "")))

            ssids = raw_cfg.get("campus_wifi_ssids", [])
            if "campus_wifi_ssids" in self.fields:
                self.fields["campus_wifi_ssids"].setText(", ".join(str(s) for s in ssids))

            for key, default in [
                ("check_interval_seconds", 5),
                ("network_check_interval_seconds", 30),
                ("low_battery_threshold", 30),
                ("auto_shutdown_threshold", 10),
                ("auto_shutdown_delay", 120),
            ]:
                if key in self.fields:
                    self.fields[key].setValue(int(raw_cfg.get(key, default)))

            if "autostart" in self.fields:
                self.fields["autostart"].setChecked(bool(raw_cfg.get("autostart", True)))
            self.status_label.setText("🔄 已从文件重新加载")
        except Exception as err:
            self.status_label.setText(f"❌ 加载失败: {err}")


class MainWindow(QMainWindow):
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
        self.resize(760, 520)

        tabs = QTabWidget()
        tabs.addTab(StatusTab(battery, network), "状态")
        tabs.addTab(ControlTab(battery, network), "控制")
        tabs.addTab(LogTab(), "日志")
        tabs.addTab(SettingsTab(), "设置")
        self.setCentralWidget(tabs)

        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip("Campus Guard")
        menu = QMenu()
        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self._show_from_tray)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self._update_tray()
        self.tray.show()

        self._icon_timer = QTimer(self)
        self._icon_timer.timeout.connect(self._update_tray)
        self._icon_timer.start(5000)

    def _update_icon(self) -> None:
        self._update_tray()

    def _update_tray(self) -> None:
        try:
            bat = psutil.sensors_battery()
            state = GuardState(
                network_ok=self.network.is_online,
                power_plugged=bat.power_plugged if bat else None,
                battery_percent=int(bat.percent) if bat else None,
            )
            self.tray.setIcon(pil_image_to_qicon(create_tray_icon(get_tray_color(state))))
        except Exception as err:
            log.error("更新托盘图标失败: %s", err)

    def _tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "Campus Guard",
            "程序仍在后台运行，可从托盘恢复窗口。",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    def _quit_app(self) -> None:
        log.info("用户退出程序")
        self.battery.running = False
        self.network.running = False
        self.tray.hide()
        QApplication.quit()
