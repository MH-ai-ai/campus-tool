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
    "512": "密码错误",
    "1024": "账号不存在",
    "2048": "账号欠费或已停机",
    "4096": "设备 MAC 绑定冲突",
    "8192": "在线设备数量已达上限",
    "16384": "当前时段暂停服务",
    "32768": "IP 地址绑定冲突",
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


def _get_account_candidates(account: str) -> list[str]:
    """生成 Dr.COM 候选账号列表。
    若用户显式指定逗号前缀（如 ,0,xxx）或运营商后缀（如 @cmcc），按原样优先；
    否则依次尝试 ,0, 前缀（延安大学等标准 Dr.COM Web 系统）与原始标准学号。
    """
    acc = account.strip()
    if not acc:
        return []
    if acc.startswith(",") or "@" in acc:
        return [acc]
    return [f",0,{acc}", acc]



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


def build_drcom_urls(raw_url: str) -> tuple[str, str]:
    """智能解析并构建标准 Dr.COM 登录和注销 API 端点。
    保证无论用户或探针输入 /index.jsp、/login、根目录还是缺少 801 端口，
    都能精准重构为标准的 /eportal/portal/login 与 /eportal/portal/logout。
    """
    from urllib.parse import urlparse
    from ..models import normalize_auth_url

    url = normalize_auth_url(raw_url)
    parsed = urlparse(url)

    scheme = parsed.scheme or "http"
    netloc = parsed.netloc
    path = parsed.path or ""

    # 针对延安大学等标准 Dr.COM，如果缺失端口且 host 为 10.200.84.3，补齐 :801
    host = parsed.hostname or ""
    port = parsed.port
    if not port and host in ("10.200.84.3", "10.211.0.1"):
        netloc = f"{host}:801"

    origin = f"{scheme}://{netloc}"

    # 统一提取/修正 path
    if "/portal/login" in path:
        login_path = path
        logout_path = path.replace("/portal/login", "/portal/logout")
    elif "/drcom/login" in path:
        login_path = path
        logout_path = path.replace("/drcom/login", "/drcom/logout")
    elif "/eportal" in path:
        # 如 /eportal/index.jsp, /eportal/, /eportal
        login_path = "/eportal/portal/login"
        logout_path = "/eportal/portal/logout"
    elif path.endswith("/login"):
        login_path = "/eportal/portal/login"
        logout_path = "/eportal/portal/logout"
    elif path.endswith("/logout"):
        login_path = "/eportal/portal/login"
        logout_path = "/eportal/portal/logout"
    else:
        # 兜底默认标准端点
        login_path = "/eportal/portal/login"
        logout_path = "/eportal/portal/logout"

    return f"{origin}{login_path}", f"{origin}{logout_path}"


class DrcomAdapter(BaseAuthAdapter):
    """城市热点 Dr.COM 系列（延安大学、吉林大学等）统一认证协议适配器。"""

    name = "drcom"
    display_name = "城市热点 Dr.COM / ePortal"

    def build_auth_params(
        self,
        config: Config,
        local_ip: str,
        local_mac: str,
        account_override: str | None = None,
    ) -> dict[str, str]:
        account_str = account_override if account_override is not None else _format_drcom_account(config.campus_account)
        return {
            "callback": "dr1003",
            "login_method": "1",
            "user_account": account_str,
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
            auth_url, _ = build_drcom_urls(config.campus_auth_url)
            session = requests.Session()
            session.trust_env = False
            log.info("Dr.COM 认证请求目标: %s", auth_url)

            candidates = _get_account_candidates(config.campus_account)
            last_msg = ""
            for idx, cand in enumerate(candidates):
                params = self.build_auth_params(config, local_ip, local_mac, account_override=cand)
                try:
                    resp = session.get(
                        auth_url,
                        params=params,
                        timeout=(3.0, 5.0),
                    )
                except requests.exceptions.ConnectionError as conn_err:
                    log.warning("Dr.COM 认证服务器连接失败 (请确认已连接校园 Wi-Fi): %s", conn_err)
                    return False, "无法连接延安大学认证网关 (10.200.84.3)，请确认电脑已连接校园 Wi-Fi (如 YADX-STU)"
                except requests.exceptions.Timeout:
                    return False, "连接延安大学认证网关服务器超时，请检查校园 Wi-Fi 信号"

                success, msg = parse_drcom_response(resp.text)
                if success:
                    log.info("Dr.COM 校园网认证成功: %s", msg)
                    return True, msg

                last_msg = msg
                # 若是密码错误/账号不存在且还有备选候选账号格式，尝试下一种格式
                if len(candidates) > 1 and idx < len(candidates) - 1:
                    if any(k in msg for k in ("密码错误", "512", "账号不存在", "1024")):
                        log.info(
                            "Dr.COM 账号格式 [%s] 认证未通过 (%s)，自动尝试备选格式 [%s]...",
                            cand,
                            msg,
                            candidates[idx + 1],
                        )
                        continue

            if "512" in last_msg or "密码错误" in last_msg:
                user_hint = (
                    "校园网认证失败：密码错误 (Dr.COM 512)。已自动尝试「,0,前缀」与「标准学号」双模验证均被网关拒绝，"
                    "请核对学号与密码大小写，或前往延安大学自助服务平台 self.yau.edu.cn 重置密码。"
                )
                log.warning("Dr.COM 校园网认证失败: %s", last_msg)
                return False, user_hint

            log.warning("Dr.COM 校园网认证失败: %s", last_msg)
            return False, last_msg
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
            _, logout_url = build_drcom_urls(config.campus_auth_url)
            params = self.build_logout_params(config, local_ip, local_mac)
            session = requests.Session()
            session.trust_env = False
            log.info("Dr.COM 注销下线请求目标: %s", logout_url)
            resp = session.get(
                logout_url,
                params=params,
                timeout=(3.0, 4.0),
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
