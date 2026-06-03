from __future__ import annotations

import json
import os
from typing import Any

from .logging_setup import get_logger
from .models import Config
from .paths import CONFIG_PATH, KEY_PATH


SENSITIVE_FIELDS = ("campus_password", "telegram_bot_token")

_runtime_config: dict[str, Any] = {}
_config_mtime: float | None = None
log = get_logger()


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
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("config.json 必须是 JSON object")
    return data


def save_config_raw(config: dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def decrypt_config(config: dict[str, Any]) -> dict[str, Any]:
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        for field in SENSITIVE_FIELDS:
            val = config.get(field, "")
            if isinstance(val, str) and val.startswith("gAAAAA"):
                log.warning("⚠️ %s 已加密但 cryptography 未安装，无法解密", field)
        return config

    key = _load_or_generate_key()
    if not key:
        return config

    fernet = Fernet(key)
    result = config.copy()
    for field in SENSITIVE_FIELDS:
        val = result.get(field, "")
        if isinstance(val, str) and val.startswith("gAAAAA"):
            try:
                result[field] = fernet.decrypt(val.encode()).decode()
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
        if isinstance(val, str) and val and not val.startswith("gAAAAA"):
            cfg[field] = fernet.encrypt(val.encode()).decode()
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
        if isinstance(val, str) and val and not val.startswith("gAAAAA"):
            result[field] = fernet.encrypt(val.encode()).decode()
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
