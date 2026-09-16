from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
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
from ..universities import UniversityProfile, get_university_manager
from .styles import _APPLE_COLORS, _STYLESHEET, get_apple_font
from .widgets import _Worker

log = get_logger()


class QuickSetupDialog(QDialog):
    """小白首次一键智能配网打通对话框（支持全国高校自动识别与检索切换）。"""

    def __init__(self, detected_params: dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self.detected = detected_params
        self.uni_manager = get_university_manager()
        self.setWindowTitle("⚡ 一键智能打通校园网（全国高校通用）")
        self.setFixedWidth(500)
        self.setStyleSheet(_STYLESHEET)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # 头部标题与副标题
        title = QLabel("⚡ 校园网一键打通")
        title.setFont(get_apple_font(16, QFont.Weight.Bold))
        root.addWidget(title)

        subtitle = QLabel("系统已自适应嗅探您的校园网特征。仅需确认所属高校并输入账号密码，即可极速打通。")
        subtitle.setProperty("secondary", True)
        subtitle.setWordWrap(True)
        subtitle.setFont(get_apple_font(10))
        root.addWidget(subtitle)

        # 自动识别参数详情卡片
        info_card = QFrame()
        info_card.setObjectName("appleCard")
        info_card.setFrameShape(QFrame.Shape.StyledPanel)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(6)

        ssid = detected_params.get("campus_wifi_ssid", "当前 Wi-Fi")
        auth_url = detected_params.get("campus_auth_url", "自动捕获")
        proto = detected_params.get("auth_protocol", "drcom").upper()
        uni_name = detected_params.get("university_name", "延安大学 (默认)")

        self.info_proto_lbl = QLabel(f"🏫 识别高校与体系:  <b>{uni_name}</b> <span style='color: {_APPLE_COLORS['accent']};'>[{proto}]</span>")
        self.info_ssid_lbl = QLabel(f"📶 识别校园 Wi-Fi:  <b>{ssid}</b>")
        self.info_url_lbl = QLabel(f"🌐 认证网关地址:  <b>{auth_url}</b>")
        for lbl in (self.info_proto_lbl, self.info_ssid_lbl, self.info_url_lbl):
            lbl.setFont(get_apple_font(10))
            info_layout.addWidget(lbl)
        root.addWidget(info_card)

        # 高校选择与账号密码表单
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # 高校检索选择下拉框
        self.uni_combo = QComboBox()
        self.uni_combo.setEditable(True)
        self.uni_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.profiles = self.uni_manager.get_all_profiles()

        names = []
        target_idx = 0
        target_uni_id = detected_params.get("university_id", "yau")

        for idx, p in enumerate(self.profiles):
            label = f"{p.name}  [{p.protocol.upper()}]"
            names.append(label)
            self.uni_combo.addItem(label, p.id)
            if p.id == target_uni_id:
                target_idx = idx

        # 配置自动补全
        completer = QCompleter(names, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.uni_combo.setCompleter(completer)
        self.uni_combo.setCurrentIndex(target_idx)
        self.uni_combo.currentIndexChanged.connect(self._on_university_changed)

        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("请输入您的学号 / 校园网账号")

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("请输入校园网密码")

        form.addRow("所属高校 / 协议", self.uni_combo)
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

    def _on_university_changed(self, index: int) -> None:
        if 0 <= index < len(self.profiles):
            p = self.profiles[index]
            self.info_proto_lbl.setText(
                f"🏫 目标高校与体系:  <b>{p.name}</b> <span style='color: {_APPLE_COLORS['accent']};'>[{p.protocol.upper()}]</span>"
            )
            if not self.detected.get("campus_auth_url"):
                self.info_url_lbl.setText(f"🌐 默认认证地址:  <b>{p.auth_url}</b>")

    def _do_quick_connect(self) -> None:
        account = self.account_input.text().strip()
        password = self.password_input.text().strip()

        if not account or not password:
            self.status_label.setText("⚠️ 请先填写学号和密码")
            self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['warning']};")
            return

        curr_idx = self.uni_combo.currentIndex()
        selected_prof = self.profiles[curr_idx] if (0 <= curr_idx < len(self.profiles)) else self.profiles[0]

        self.status_label.setText("⏳ 正在保存全国高校配置并执行认证登录...")
        self.status_label.setStyleSheet(f"color: {_APPLE_COLORS['text_secondary']};")
        self.confirm_btn.setEnabled(False)

        try:
            cfg = load_config_raw()
            cfg["campus_account"] = account
            cfg["campus_password"] = password
            cfg["auth_protocol"] = selected_prof.protocol
            cfg["university_id"] = selected_prof.id
            cfg["university_name"] = selected_prof.name

            # 写入自动嗅探或高校默认的网络参数
            auth_url = self.detected.get("campus_auth_url") or selected_prof.auth_url
            if auth_url:
                cfg["campus_auth_url"] = auth_url

            gw = self.detected.get("campus_gateway") or selected_prof.gateway
            if gw:
                cfg["campus_gateway"] = gw

            ac_ip = self.detected.get("wlan_ac_ip") or selected_prof.ac_ip
            if ac_ip:
                cfg["wlan_ac_ip"] = ac_ip

            # 写入 Wi-Fi SSID
            ssids = list(cfg.get("campus_wifi_ssids", []))
            detected_ssid = self.detected.get("campus_wifi_ssid")
            if detected_ssid and detected_ssid not in ssids:
                ssids.append(detected_ssid)
            for s in selected_prof.wifi_ssids:
                if s and s not in ssids:
                    ssids.append(s)
            cfg["campus_wifi_ssids"] = ssids

            encrypted = encrypt_sensitive_fields(cfg)
            save_config_raw(encrypted)
            update_runtime_config(decrypt_config(encrypted))
            log.info("全国高校配网配置已保存: 高校=%s, 协议=%s", selected_prof.name, selected_prof.protocol)
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
