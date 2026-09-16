from __future__ import annotations

import json
import random
from typing import Any, Mapping

import requests

from .config import get_config
from .logging_setup import get_logger
from .models import Config
from .system import get_local_ip, get_local_mac, get_wifi_info


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


# 常见 Dr.COM 错误代码与提示映射
_DRCOM_ERROR_MAP = {
    "ldap auth error": "账号或密码错误",
    "userid error": "账号不存在",
    "password error": "密码错误",
    "user_tab error": "账号不存在或已注销",
    "ip error": "IP 与绑定的账号或 MAC 不匹配",
    "mac error": "MAC 地址未绑定或不匹配",
    "balance error": "账号已欠费停机",
    "timeout error": "认证服务响应超时",
    "online num error": "在线设备数量已达上限",
    "time error": "当前时段不允许上网",
    "portal auth error": "Portal 网关认证失败",
}


def parse_drcom_response(text: str) -> tuple[bool, str]:
    """解析 Dr.COM 认证接口返回的 JSONP/JSON 响应。"""
    try:
        raw_text = text.strip()
        if "(" in raw_text and ")" in raw_text:
            json_str = raw_text[raw_text.index("(") + 1 : raw_text.rindex(")")]
        else:
            json_str = raw_text

        data = json.loads(json_str)
        result = str(data.get("result", ""))
        msg = str(data.get("msg") or data.get("msga") or data.get("message") or "").strip()

        # 尝试中文映射
        msg_lower = msg.lower()
        for err_key, err_desc in _DRCOM_ERROR_MAP.items():
            if err_key in msg_lower:
                msg = f"{err_desc} ({msg})"
                break

        if result == "1":
            return True, msg or "认证成功"
        return False, msg or f"认证失败 (result={result})"
    except (ValueError, json.JSONDecodeError):
        lower = text.lower()
        if "success" in lower or '"result":1' in text or '"result":"1"' in text:
            return True, "认证成功"
        for err_key, err_desc in _DRCOM_ERROR_MAP.items():
            if err_key in lower:
                return False, f"{err_desc} ({text[:100]})"
        return False, f"认证返回异常: {text[:200]}"


def build_logout_params(
    config: Config | Mapping[str, Any],
    local_ip: str,
    local_mac: str,
) -> dict[str, str]:
    return {
        "callback": "dr1004",
        "login_method": "1",
        "user_account": f",0,{_config_get(config, 'campus_account')}",
        "wlan_user_ip": local_ip,
        "wlan_user_ipv6": "",
        "wlan_user_mac": local_mac,
        "wlan_ac_ip": str(_config_get(config, "wlan_ac_ip", "")),
        "jsVersion": "4.2.1",
        "v": str(random.randint(1000, 9999)),
    }


def campus_login(config: Config | None = None) -> tuple[bool, str]:
    active_config = config or get_config()
    try:
        params = build_auth_params(active_config, get_local_ip(), get_local_mac())
        session = requests.Session()
        session.trust_env = False
        resp = session.get(
            active_config.campus_auth_url,
            params=params,
            timeout=10,
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


def campus_logout(config: Config | None = None) -> tuple[bool, str]:
    """主动注销校园网登录下线。"""
    active_config = config or get_config()
    try:
        logout_url = active_config.campus_auth_url
        if "/login" in logout_url:
            logout_url = logout_url.replace("/login", "/logout")

        params = build_logout_params(active_config, get_local_ip(), get_local_mac())
        session = requests.Session()
        session.trust_env = False
        resp = session.get(
            logout_url,
            params=params,
            timeout=8,
        )
        success, msg = parse_drcom_response(resp.text)
        if success:
            log.info("校园网下线成功: %s", msg)
            return True, msg or "下线成功"
        log.warning("校园网下线返回: %s", msg)
        return False, msg
    except Exception as err:
        log.error("校园网下线失败: %s", err)
        return False, str(err)


def auto_detect_portal_config() -> tuple[bool, str, dict[str, str]]:
    """通过 Captive Portal 劫持探针，全自动嗅探校园网认证网关与参数。
    小白用户连上校园 Wi-Fi 后只需点击一次，无需手动寻找复杂配置。
    返回元组: (是否成功捕获, 状态说明, 提取到的配置字典)
    """
    import re
    from urllib.parse import parse_qs, urlparse

    extracted: dict[str, str] = {}

    # 1. 尝试获取当前连接的 Wi-Fi 名称
    wifi_raw = get_wifi_info(force=True)
    current_ssid = wifi_raw.split("(", 1)[0].strip() if "(" in wifi_raw else wifi_raw.strip()
    if current_ssid and current_ssid != "未连接" and current_ssid != "未知":
        extracted["campus_wifi_ssid"] = current_ssid

    # 2. 获取本机 IP
    local_ip = get_local_ip()
    if local_ip and local_ip != "未知" and "clash" not in local_ip.lower():
        extracted["wlan_user_ip"] = local_ip

    # 3. 探针目标列表（常见直连探针）
    probe_urls = (
        "http://connectivitycheck.gstatic.com/generate_204",
        "http://www.msftconnecttest.com/connecttest.txt",
        "http://1.1.1.1",
        "http://captive.apple.com/hotspot-detect.html",
    )

    session = requests.Session()
    session.trust_env = False

    target_redirect_url = ""
    for url in probe_urls:
        try:
            resp = session.get(url, allow_redirects=False, timeout=3)
            # 捕获 HTTP 30x 重定向
            if resp.status_code in (301, 302, 303, 307, 308) and "Location" in resp.headers:
                target_redirect_url = resp.headers["Location"]
                break
            # 捕获 HTML 内部 JS 或 meta 刷新跳转
            if resp.text:
                js_match = re.search(r"location\.(?:href|replace)\s*=\s*['\"]([^'\"]+)['\"]", resp.text, re.I)
                if js_match:
                    target_redirect_url = js_match.group(1)
                    break
                meta_match = re.search(r"url=([^'\">]+)", resp.text, re.I)
                if meta_match:
                    target_redirect_url = meta_match.group(1).strip()
                    break
        except Exception:
            continue

    if not target_redirect_url:
        return False, "未捕获到校园网重定向，可能网络已畅通或尚未连接校园 Wi-Fi", extracted

    # 4. 解析目标重定向 URL
    try:
        parsed = urlparse(target_redirect_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        extracted["campus_auth_url"] = base_url

        host = parsed.hostname
        if host:
            extracted["campus_gateway"] = host

        qs = parse_qs(parsed.query)
        for k, v in qs.items():
            k_lower = k.lower()
            if any(key in k_lower for key in ("ac_ip", "wlanacip", "nasip")):
                extracted["wlan_ac_ip"] = v[0]
            elif any(key in k_lower for key in ("user_ip", "wlanuserip", "userip")):
                extracted["wlan_user_ip"] = v[0]

        return True, "已成功捕获校园网认证参数！", extracted
    except Exception as err:
        return False, f"重定向地址解析异常: {err}", extracted


