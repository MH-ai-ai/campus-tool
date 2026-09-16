from __future__ import annotations

from datetime import datetime
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..auth import auto_detect_portal_config
from ..config import (
    SENSITIVE_FIELDS,
    decrypt_config,
    encrypt_sensitive_fields,
    load_config_dict,
    load_config_raw,
    save_config_raw,
    update_runtime_config,
)
from ..logging_setup import get_logger
from .styles import _APPLE_COLORS, get_apple_font
from .widgets import _Worker


log = get_logger()

# ---------------------------------------------------------------------------
# macOS 偏好设置风格 Schema 定义
# ---------------------------------------------------------------------------

_SETTINGS_SCHEMA: list[tuple[str, str, str, str, dict]] = [
    # 校园网凭据
    ("campus_account", "校园网账号 / 学号", "🔑 账号与凭证", "text", {}),
    ("campus_password", "校园网密码", "🔑 账号与凭证", "text", {"sensitive": True}),
    # 国内免梯推送平台
    ("feishu_webhook_url", "飞书机器人 Webhook 地址", "🚀 国内通知通道 (无需梯子)", "text", {}),
    ("dingtalk_webhook_url", "钉钉机器人 Webhook 地址", "🚀 国内通知通道 (无需梯子)", "text", {}),
    ("dingtalk_secret", "钉钉加签密钥 (SEC...)", "🚀 国内通知通道 (无需梯子)", "text", {"sensitive": True}),
    # Telegram Bot
    ("telegram_bot_token", "Telegram Bot Token", "✈️ Telegram 远程控制", "text", {"sensitive": True}),
    ("telegram_user_id", "Telegram 用户 ID", "✈️ Telegram 远程控制", "text", {}),
    # 网络与认证参数
    ("campus_auth_url", "Dr.COM 认证接口 URL", "🌐 网络与认证", "text", {}),
    ("campus_gateway", "校园网网关 IP", "🌐 网络与认证", "text", {}),
    ("wlan_ac_ip", "AC IP (Dr.COM 认证参数)", "🌐 网络与认证", "text", {}),
    ("campus_wifi_ssids", "校园 WiFi SSID 列表", "🌐 网络与认证", "csv", {}),
    ("trusted_home_ssids", "家庭 / 信任免认证 WiFi", "🌐 网络与认证", "csv", {}),
    ("forced_network_mode", "强制网络模式 (auto/campus/home)", "🌐 网络与认证", "text", {}),
    ("network_check_interval_seconds", "网络探测间隔 (秒)", "🌐 网络与认证", "spin", {"min": 1, "max": 300}),
    ("reconnect_max_retries", "重连最大重试次数", "🌐 网络与认证", "spin", {"min": 1, "max": 30}),
    ("reconnect_verify_delay_seconds", "重连验证延迟 (秒)", "🌐 网络与认证", "spin", {"min": 1, "max": 30}),
    ("reconnect_fast_retry_seconds", "快速重试间隔 (秒)", "🌐 网络与认证", "spin", {"min": 1, "max": 30}),
    # 电源与自动关机
    ("battery_warning_thresholds", "电量提醒梯度 (逗号分隔)", "🔋 电源与电量保护", "csv_int", {}),
    ("auto_shutdown_threshold", "自动关机电量阈值 (%)", "🔋 电源与电量保护", "spin", {"min": 5, "max": 50}),
    ("auto_shutdown_delay", "关机倒计时 (秒)", "🔋 电源与电量保护", "spin", {"min": 10, "max": 600}),
    # 系统与运行
    ("check_interval_seconds", "主监控周期 (秒)", "⚙ 运行与守护", "spin", {"min": 1, "max": 60}),
    ("autostart", "开机自动在后台启动", "⚙ 运行与守护", "check", {}),
]


class _SettingsPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 16)
        root.setSpacing(12)

        # 头部标题与嗅探工具按钮
        header_bar = QHBoxLayout()
        header = QLabel("偏好设置")
        header.setFont(get_apple_font(18, QFont.Weight.Bold))
        header_bar.addWidget(header)
        header_bar.addStretch()

        sniff_btn = QPushButton("🔍 自动嗅探填入网络参数")
        sniff_btn.setObjectName("actionBtn")
        sniff_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sniff_btn.setToolTip("自动发起未加密 HTTP 探针，捕获校园网重定向并填入认证 URL 与网关")
        sniff_btn.clicked.connect(self._auto_sniff_and_fill)
        header_bar.addWidget(sniff_btn)
        root.addLayout(header_bar)

        # 苹果分组内嵌滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 16)
        scroll_layout.setSpacing(14)

        self.fields: dict[str, QWidget] = {}
        raw_cfg = load_config_dict()

        # 按 Group 组织表单
        groups: dict[str, list] = {}
        for key, label, group, wtype, extra in _SETTINGS_SCHEMA:
            groups.setdefault(group, []).append((key, label, wtype, extra))

        for group_name, items in groups.items():
            gbox = QGroupBox(group_name)
            form = QFormLayout()
            form.setContentsMargins(16, 16, 16, 14)
            form.setSpacing(12)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            for key, label, wtype, extra in items:
                widget = self._create_widget(wtype, key, raw_cfg, extra)
                form.addRow(label, widget)
                self.fields[key] = widget
            gbox.setLayout(form)
            scroll_layout.addWidget(gbox)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        root.addWidget(scroll, 1)

        # 底部操作栏
        btn_row = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setFont(get_apple_font(10))
        btn_row.addWidget(self.status_label)
        btn_row.addStretch()

        reload_btn = QPushButton("重新载入")
        reload_btn.setObjectName("actionBtn")
        reload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reload_btn.clicked.connect(self._load_from_file)
        btn_row.addWidget(reload_btn)

        save_btn = QPushButton("保存所有设置")
        save_btn.setObjectName("primaryCapsuleBtn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(save_btn)

        root.addLayout(btn_row)

        self._worker: _Worker | None = None

    def _create_widget(self, wtype: str, key: str, cfg: dict, extra: dict) -> QWidget:
        val = cfg.get(key, "")
        if wtype == "text":
            w = QLineEdit(str(val) if val is not None else "")
            if extra.get("sensitive") or key in SENSITIVE_FIELDS or "password" in key or "secret" in key:
                w.setEchoMode(QLineEdit.EchoMode.Password)
            return w
        if wtype == "csv":
            items = val if isinstance(val, list) else []
            return QLineEdit(", ".join(str(s) for s in items))
        if wtype == "csv_int":
            items = val if isinstance(val, (list, tuple)) else [50, 30, 20]
            return QLineEdit(", ".join(str(t) for t in items))
        if wtype == "spin":
            w = QSpinBox()
            w.setRange(extra.get("min", 1), extra.get("max", 3600))
            w.setValue(int(val) if val else 0)
            return w
        if wtype == "check":
            w = QCheckBox()
            w.setChecked(bool(val) if val != "" else True)
            return w
        return QLineEdit(str(val))

    def _read_field(self, key: str, wtype: str) -> object:
        w = self.fields[key]
        if wtype == "text":
            return w.text().strip()
        if wtype == "csv":
            return [s.strip() for s in w.text().split(",") if s.strip()]
        if wtype == "csv_int":
            return [int(s.strip()) for s in w.text().split(",") if s.strip()]
        if wtype == "spin":
            return w.value()
        if wtype == "check":
            return w.isChecked()
        return w.text().strip()

    def _save_config(self) -> None:
        try:
            cfg = load_config_raw()
            for key, _label, _group, wtype, _extra in _SETTINGS_SCHEMA:
                raw = self._read_field(key, wtype)
                if key == "telegram_user_id":
                    raw = int(raw) if raw else 0
                cfg[key] = raw

            encrypted_cfg = encrypt_sensitive_fields(cfg)
            save_config_raw(encrypted_cfg)
            update_runtime_config(decrypt_config(encrypted_cfg))
            self.status_label.setText(f"✅ 配置已保存并在后台生效 — {datetime.now().strftime('%H:%M:%S')}")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['success']};")
            log.info("配置已通过苹果风设置页成功保存")
        except ValueError as err:
            self.status_label.setText(f"❌ 输入格式错误: {err}")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['danger']};")
        except Exception as err:
            self.status_label.setText(f"❌ 保存失败: {err}")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['danger']};")
            log.error("配置保存失败: %s", err)

    def _load_from_file(self) -> None:
        try:
            raw_cfg = load_config_dict()
            for key, _label, _group, wtype, _extra in _SETTINGS_SCHEMA:
                w = self.fields.get(key)
                if w is None:
                    continue
                val = raw_cfg.get(key, "")
                if wtype == "text":
                    w.setText(str(val) if val is not None else "")
                elif wtype == "csv":
                    items = val if isinstance(val, list) else []
                    w.setText(", ".join(str(s) for s in items))
                elif wtype == "csv_int":
                    items = val if isinstance(val, (list, tuple)) else []
                    w.setText(", ".join(str(t) for t in items))
                elif wtype == "spin":
                    w.setValue(int(val) if val else 0)
                elif wtype == "check":
                    w.setChecked(bool(val))
            self.status_label.setText("🔄 已从本地配置文件重新同步")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['text_secondary']};")
        except Exception as err:
            self.status_label.setText(f"❌ 加载失败: {err}")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['danger']};")

    def _auto_sniff_and_fill(self) -> None:
        self.status_label.setText("🔍 正在探测 Captive Portal 重定向...")
        self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['accent']};")

        def _done(result):
            self._worker = None
            if isinstance(result, Exception):
                QMessageBox.warning(self, "嗅探失败", f"探测异常: {result}")
                self.status_label.setText("")
                return
            ok, msg, detected = result
            if not ok and not detected.get("campus_auth_url"):
                QMessageBox.information(self, "嗅探结果", f"{msg}\n请确保已连上校园 Wi-Fi 且尚未登录认证。")
                self.status_label.setText("")
                return

            # 填入表单字段
            filled_count = 0
            for k in ("campus_auth_url", "campus_gateway", "wlan_ac_ip"):
                if k in detected and k in self.fields:
                    self.fields[k].setText(detected[k])
                    filled_count += 1
            if "campus_wifi_ssid" in detected and "campus_wifi_ssids" in self.fields:
                cur = self.fields["campus_wifi_ssids"].text().strip()
                ssid = detected["campus_wifi_ssid"]
                if ssid and ssid not in cur:
                    new_val = f"{cur}, {ssid}" if cur else ssid
                    self.fields["campus_wifi_ssids"].setText(new_val)
                    filled_count += 1

            self.status_label.setText(f"🎉 成功自动填入 {filled_count} 项校园网参数，请点击「保存」生效")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['success']};")

        self._worker = _Worker(auto_detect_portal_config, parent=self)
        self._worker.finished.connect(_done)
        self._worker.start()
