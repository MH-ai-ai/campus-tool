from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .logging_setup import get_logger
from .models import Config
from .paths import APP_DIR, CONFIG_PATH, KEY_PATH


SENSITIVE_FIELDS = ("campus_password", "telegram_bot_token")
ENCRYPTED_PREFIX = "ENC:"

_runtime_config: dict[str, Any] = {}
_config_mtime: float | None = None
log = get_logger()


def _default_config_dict() -> dict[str, Any]:
    return Config.from_mapping({}).to_dict()


def ensure_config_file() -> None:
    if CONFIG_PATH.exists():
        return

    example_path = Path(APP_DIR) / "config.example.json"
    internal_example = Path(APP_DIR) / "_internal" / "config.example.json"
    target_example = example_path if example_path.exists() else (internal_example if internal_example.exists() else None)
    if target_example:
        CONFIG_PATH.write_text(
            target_example.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        log.warning("config.json 不存在，已从模板创建: %s", CONFIG_PATH)
        return

    CONFIG_PATH.write_text(
        json.dumps(_default_config_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.warning("config.json 不存在，已创建默认配置: %s", CONFIG_PATH)


def _load_or_generate_key() -> bytes:
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes()
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        log.warning("cryptography 未安装，配置文件将不加密")
        return b""

    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key)
    log.info("已生成配置加密密钥: %s", KEY_PATH)
    return key


def load_config_raw() -> dict[str, Any]:
    ensure_config_file()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("config.json 必须是 JSON object")
    return data


def save_config_raw(config: dict[str, Any]) -> None:
    temp_path = CONFIG_PATH.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(temp_path, CONFIG_PATH)


SETTINGS_SCHEMA: list[tuple[str, str, str, str, dict]] = [
    # 校园网凭据与高校体系
    ("university_name", "所属高校名称", "🏫 高校与认证体系", "text", {}),
    ("auth_protocol", "核心协议体系", "🏫 高校与认证体系", "protocol_combo", {}),
    ("campus_account", "校园网账号 / 学号", "🔑 账号与凭据", "text", {}),
    ("campus_password", "校园网密码", "🔑 账号与凭据", "text", {"sensitive": True}),
    # 国内免梯推送平台
    ("feishu_webhook_url", "飞书机器人 Webhook 地址", "🚀 国内通知通道 (无需梯子)", "text", {}),
    ("dingtalk_webhook_url", "钉钉机器人 Webhook 地址", "🚀 国内通知通道 (无需梯子)", "text", {}),
    ("dingtalk_secret", "钉钉加签密钥 (SEC...)", "🚀 国内通知通道 (无需梯子)", "text", {"sensitive": True}),
    # Telegram Bot
    ("telegram_bot_token", "Telegram Bot Token", "✈️ Telegram 远程控制", "text", {"sensitive": True}),
    ("telegram_user_id", "Telegram 用户 ID", "✈️ Telegram 远程控制", "text", {}),
    # 网络与认证参数
    ("campus_auth_url", "认证接口 URL", "🌐 网络与认证", "text", {}),
    ("campus_gateway", "校园网网关 IP", "🌐 网络与认证", "text", {}),
    ("wlan_ac_ip", "AC IP (认证参数)", "🌐 网络与认证", "text", {}),
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


def decrypt_config(config: dict[str, Any]) -> dict[str, Any]:
    def _is_encrypted(val: object) -> bool:
        return isinstance(val, str) and (
            val.startswith(ENCRYPTED_PREFIX) or val.startswith("gAAAAA")
        )

    def _strip_prefix(val: str) -> str:
        if val.startswith(ENCRYPTED_PREFIX):
            return val[len(ENCRYPTED_PREFIX):]
        return val

    try:
        from cryptography.fernet import Fernet
    except ImportError:
        for field in SENSITIVE_FIELDS:
            if _is_encrypted(config.get(field, "")):
                log.warning("⚠️ %s 已加密但 cryptography 未安装，无法解密", field)
        return config

    key = _load_or_generate_key()
    if not key:
        return config

    fernet = Fernet(key)
    result = config.copy()
    for field in SENSITIVE_FIELDS:
        val = result.get(field, "")
        if _is_encrypted(val):
            try:
                result[field] = fernet.decrypt(_strip_prefix(val).encode()).decode()
            except Exception:
                log.warning("解密 %s 失败", field)
    return result


def encrypt_config_file() -> None:
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return

    key = _load_or_generate_key()
    if not key:
        return

    cfg = load_config_raw()
    fernet = Fernet(key)
    changed = False
    for field in SENSITIVE_FIELDS:
        val = cfg.get(field, "")
        if isinstance(val, str) and val and not val.startswith(ENCRYPTED_PREFIX) and not val.startswith("gAAAAA"):
            cfg[field] = ENCRYPTED_PREFIX + fernet.encrypt(val.encode()).decode()
            changed = True
    if changed:
        save_config_raw(cfg)
        log.info("配置文件敏感字段已加密")


def encrypt_sensitive_fields(config: dict[str, Any]) -> dict[str, Any]:
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return config

    key = _load_or_generate_key()
    if not key:
        return config

    result = config.copy()
    fernet = Fernet(key)
    for field in SENSITIVE_FIELDS:
        val = result.get(field, "")
        if isinstance(val, str) and val and not val.startswith(ENCRYPTED_PREFIX) and not val.startswith("gAAAAA"):
            result[field] = ENCRYPTED_PREFIX + fernet.encrypt(val.encode()).decode()
    return result


def load_config_dict() -> dict[str, Any]:
    return decrypt_config(load_config_raw())


def load_config() -> Config:
    return Config.from_mapping(load_config_dict())


def initialize_runtime_config() -> dict[str, Any]:
    global _config_mtime
    _runtime_config.clear()
    _runtime_config.update(load_config_dict())
    _config_mtime = os.path.getmtime(CONFIG_PATH)
    return _runtime_config


def get_config_dict() -> dict[str, Any]:
    return _runtime_config


def get_config() -> Config:
    return Config.from_mapping(_runtime_config)


def update_runtime_config(config: dict[str, Any]) -> None:
    global _config_mtime
    _runtime_config.clear()
    _runtime_config.update(config)
    if CONFIG_PATH.exists():
        _config_mtime = os.path.getmtime(CONFIG_PATH)


def check_config_reload() -> None:
    global _config_mtime
    try:
        new_mtime = os.path.getmtime(CONFIG_PATH)
        if _config_mtime is not None and new_mtime == _config_mtime:
            return

        old_cfg = _runtime_config.copy()
        _runtime_config.update(load_config_dict())
        _config_mtime = new_mtime
        log.info("配置文件已热重载")
        for key in ("telegram_bot_token", "telegram_user_id"):
            if old_cfg.get(key) != _runtime_config.get(key):
                log.warning("⚠️ 检测到 %s 已变更，需要重启程序才能生效", key)
    except Exception as err:
        log.error("配置热重载失败: %s", err)
