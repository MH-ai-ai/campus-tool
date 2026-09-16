from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ..auth import campus_login
from ..config import (
    decrypt_config,
    encrypt_sensitive_fields,
    load_config_raw,
    save_config_raw,
    update_runtime_config,
)
from ..logging_setup import get_logger
from .styles import _APPLE_COLORS, _STYLESHEET, get_apple_font
from .widgets import _Worker


log = get_logger()


class QuickSetupDialog(QDialog):
    """小白首次一键智能配网打通对话框（苹果设计风格）。"""

    def __init__(self, detected_params: dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self.detected = detected_params
        self.setWindowTitle("⚡ 一键智能打通校园网")
        self.setFixedWidth(460)
        self.setStyleSheet(_STYLESHEET)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # 头部标题与副标题
        title = QLabel("⚡ 校园网一键打通")
        title.setFont(get_apple_font(16, QFont.Weight.Bold))
        root.addWidget(title)

        subtitle = QLabel("系统已自动嗅探捕获您的校园网参数，仅需填写学号和密码即可全自动打通守护。")
        subtitle.setProperty("secondary", True)
        subtitle.setWordWrap(True)
        subtitle.setFont(get_apple_font(10))
        root.addWidget(subtitle)

        # 自动识别参数详情卡片
        info_card = QFrame()
        info_card.setObjectName("appleCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(6)

        ssid = detected_params.get("campus_wifi_ssid", "当前 Wi-Fi")
        auth_url = detected_params.get("campus_auth_url", "自动捕获")
        ac_ip = detected_params.get("wlan_ac_ip", "自动捕获")
        gw_ip = detected_params.get("campus_gateway", "自动捕获")

        l1 = QLabel(f"📶 识别校园 Wi-Fi:  <b>{ssid}</b>")
        l2 = QLabel(f"🌐 认证服务器:  <b>{auth_url}</b>")
        l3 = QLabel(f"🎯 网关 / AC IP:  <b>{gw_ip} / {ac_ip}</b>")
        for lbl in (l1, l2, l3):
            lbl.setFont(get_apple_font(10))
            info_layout.addWidget(lbl)
        root.addWidget(info_card)

        # 账号与密码表单
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("请输入您的学号 / 校园网账号")

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("请输入校园网密码")

        form.addRow("学号 / 账号", self.account_input)
        form.addRow("校园网密码", self.password_input)
        root.addLayout(form)

        # 反馈文本
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(get_apple_font(10))
        root.addWidget(self.status_label)

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("capsuleBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.confirm_btn = QPushButton("🚀 一键保存并登录")
        self.confirm_btn.setObjectName("successCapsuleBtn")
        self.confirm_btn.clicked.connect(self._do_quick_connect)
        btn_row.addWidget(self.confirm_btn)

        root.addLayout(btn_row)

        self._worker: _Worker | None = None

    def _do_quick_connect(self) -> None:
        account = self.account_input.text().strip()
        password = self.password_input.text().strip()

        if not account or not password:
            self.status_label.setText("⚠️ 请先填写学号和密码")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['warning']};")
            return

        self.status_label.setText("⏳ 正在保存配置并执行认证登录...")
        self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['text_secondary']};")
        self.confirm_btn.setEnabled(False)

        try:
            cfg = load_config_raw()
            cfg["campus_account"] = account
            cfg["campus_password"] = password

            # 写入自动嗅探到的网络参数
            if "campus_auth_url" in self.detected:
                cfg["campus_auth_url"] = self.detected["campus_auth_url"]
            if "campus_gateway" in self.detected:
                cfg["campus_gateway"] = self.detected["campus_gateway"]
            if "wlan_ac_ip" in self.detected:
                cfg["wlan_ac_ip"] = self.detected["wlan_ac_ip"]
            if "campus_wifi_ssid" in self.detected:
                ssid = self.detected["campus_wifi_ssid"]
                ssids = list(cfg.get("campus_wifi_ssids", []))
                if ssid not in ssids:
                    ssids.append(ssid)
                cfg["campus_wifi_ssids"] = ssids

            encrypted = encrypt_sensitive_fields(cfg)
            save_config_raw(encrypted)
            update_runtime_config(decrypt_config(encrypted))
            log.info("一键配网配置已保存")
        except Exception as err:
            self.status_label.setText(f"❌ 配置保存失败: {err}")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['danger']};")
            self.confirm_btn.setEnabled(True)
            return

        # 执行首次登录验证
        def _done(result):
            self.confirm_btn.setEnabled(True)
            self._worker = None
            if isinstance(result, Exception):
                self.status_label.setText(f"❌ 认证出错: {result}")
                self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['danger']};")
            else:
                ok, msg = result
                if ok:
                    self.status_label.setText("🎉 校园网已成功打通并连通外网！")
                    self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['success']};")
                    self.confirm_btn.setText("完成")
                    self.confirm_btn.clicked.disconnect()
                    self.confirm_btn.clicked.connect(self.accept)
                else:
                    self.status_label.setText(f"❌ 认证未通过: {msg}")
                    self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['danger']};")

        self._worker = _Worker(campus_login, parent=self)
        self._worker.finished.connect(_done)
        self._worker.start()
