from __future__ import annotations

import json
import random
from typing import Any, Mapping

import requests

from .config import get_config
from .logging_setup import get_logger
from .models import Config
from .system import get_local_ip, get_local_mac


log = get_logger()


def _config_get(config: Config | Mapping[str, Any], key: str, default: Any = "") -> Any:
    if isinstance(config, Config):
        return getattr(config, key)
    return config.get(key, default)


def build_auth_params(
    config: Config | Mapping[str, Any],
    local_ip: str,
    local_mac: str,
) -> dict[str, str]:
    return {
        "callback": "dr1003",
        "login_method": "1",
        "user_account": f",0,{_config_get(config, 'campus_account')}",
        "user_password": str(_config_get(config, "campus_password")),
        "wlan_user_ip": local_ip,
        "wlan_user_ipv6": "",
        "wlan_user_mac": local_mac,
        "wlan_ac_ip": str(_config_get(config, "wlan_ac_ip", "")),
        "wlan_ac_name": "",
        "jsVersion": "4.2.1",
        "terminal_type": "1",
        "lang": "zh-cn",
        "v": str(random.randint(1000, 9999)),
    }


def parse_drcom_response(text: str) -> tuple[bool, str]:
    try:
        json_str = text[text.index("(") + 1 : text.rindex(")")]
        data = json.loads(json_str)
        result = data.get("result", "")
        msg = data.get("msg", "")
        if result == "1":
            return True, msg or "认证成功"
        return False, msg or f"result={result}"
    except (ValueError, json.JSONDecodeError):
        if "success" in text.lower() or '"result":"1"' in text:
            return True, "认证成功"
        return False, f"认证返回异常: {text[:200]}"


def campus_login(config: Config | None = None) -> tuple[bool, str]:
    active_config = config or get_config()
    try:
        params = build_auth_params(active_config, get_local_ip(), get_local_mac())
        resp = requests.get(
            active_config.campus_auth_url,
            params=params,
            timeout=10,
            proxies={"http": None, "https": None},
        )
        success, msg = parse_drcom_response(resp.text)
        if success:
            log.info("校园网认证成功: %s", msg)
            return True, msg
        log.warning("校园网认证失败: %s", msg)
        return False, msg
    except Exception as err:
        log.error("校园网认证失败: %s", err)
        return False, str(err)
