from __future__ import annotations

import json
import random
import re
from typing import TYPE_CHECKING, Any

import requests

from ..logging_setup import get_logger
from .base import BaseAuthAdapter

if TYPE_CHECKING:
    from ..models import Config

log = get_logger()

# 常见 Dr.COM 错误代码与中文释义映射
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


def _format_drcom_account(account: str) -> str:
    """格式化 Dr.COM 账号。延安大学等标准 Dr.COM Web 系统需要 ,0, 前缀。"""
    acc = account.strip()
    if acc.startswith(","):
        return acc
    return f",0,{acc}"


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


class DrcomAdapter(BaseAuthAdapter):
    """城市热点 Dr.COM 系列（延安大学、吉林大学等）统一认证协议适配器。"""

    name = "drcom"
    display_name = "城市热点 Dr.COM / ePortal"

    def build_auth_params(
        self,
        config: Config,
        local_ip: str,
        local_mac: str,
    ) -> dict[str, str]:
        return {
            "callback": "dr1003",
            "login_method": "1",
            "user_account": _format_drcom_account(config.campus_account),
            "user_password": str(config.campus_password),
            "wlan_user_ip": local_ip,
            "wlan_user_ipv6": "",
            "wlan_user_mac": local_mac,
            "wlan_ac_ip": str(config.wlan_ac_ip or ""),
            "wlan_ac_name": "",
            "jsVersion": "4.2.1",
            "terminal_type": "1",
            "lang": "zh-cn",
            "v": str(random.randint(1000, 9999)),
        }

    def build_logout_params(
        self,
        config: Config,
        local_ip: str,
        local_mac: str,
    ) -> dict[str, str]:
        return {
            "callback": "dr1004",
            "login_method": "1",
            "user_account": _format_drcom_account(config.campus_account),
            "wlan_user_ip": local_ip,
            "wlan_user_ipv6": "",
            "wlan_user_mac": local_mac,
            "wlan_ac_ip": str(config.wlan_ac_ip or ""),
            "jsVersion": "4.2.1",
            "v": str(random.randint(1000, 9999)),
        }

    def login(
        self,
        config: Config,
        local_ip: str,
        local_mac: str,
    ) -> tuple[bool, str]:
        try:
            from ..models import normalize_auth_url

            auth_url = normalize_auth_url(config.campus_auth_url)
            params = self.build_auth_params(config, local_ip, local_mac)
            session = requests.Session()
            session.trust_env = False
            resp = session.get(
                auth_url,
                params=params,
                timeout=10,
            )
            success, msg = parse_drcom_response(resp.text)
            if success:
                log.info("Dr.COM 校园网认证成功: %s", msg)
                return True, msg
            log.warning("Dr.COM 校园网认证失败: %s", msg)
            return False, msg
        except Exception as err:
            log.error("Dr.COM 校园网认证请求异常: %s", err)
            return False, str(err)

    def logout(
        self,
        config: Config,
        local_ip: str,
        local_mac: str,
    ) -> tuple[bool, str]:
        try:
            from ..models import normalize_auth_url

            logout_url = normalize_auth_url(config.campus_auth_url)
            if "/login" in logout_url:
                logout_url = logout_url.replace("/login", "/logout")

            params = self.build_logout_params(config, local_ip, local_mac)
            session = requests.Session()
            session.trust_env = False
            resp = session.get(
                logout_url,
                params=params,
                timeout=8,
            )
            raw = resp.text
            if "result" in raw or "dr1004" in raw or "success" in raw.lower():
                log.info("Dr.COM 校园网下线成功")
                return True, "已成功下线"
            return False, f"下线反馈异常: {raw[:100]}"
        except Exception as err:
            log.error("Dr.COM 校园网下线异常: %s", err)
            return False, str(err)

    @classmethod
    def inspect_fingerprint(cls, url: str, html: str = "") -> float:
        score = 0.0
        target = (url + " " + html).lower()
        if "dr1003" in target or "dr1002" in target:
            score += 0.6
        if "drcom" in target:
            score += 0.5
        if "wlanuserip" in target or "wlanacip" in target:
            score += 0.4
        if "eportal" in target:
            score += 0.3
        return min(score, 1.0)
