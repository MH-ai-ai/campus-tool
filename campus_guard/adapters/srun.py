from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import requests

from ..logging_setup import get_logger
from .base import BaseAuthAdapter
from .srun_crypto import (
    build_srun_chksum,
    build_srun_info,
    get_hmac_md5,
)

if TYPE_CHECKING:
    from ..models import Config

log = get_logger()

# 深澜常见错误码映射
_SRUN_ERROR_MAP = {
    "E2531": "用户不存在",
    "E2532": "两次密码不一致",
    "E2533": "密码错误",
    "E2534": "用户状态异常（已冻结或注销）",
    "E2536": "账号欠费停机",
    "E2553": "在线设备数量超额",
    "E2606": "用户组不允许在当前时段登录",
    "E2616": "已处于在线状态",
    "E2833": "IP 地址未绑定或 MAC 冲突",
}


def _extract_json_or_jsonp(text: str) -> dict[str, Any]:
    raw = text.strip()
    if "(" in raw and ")" in raw:
        raw = raw[raw.index("(") + 1 : raw.rindex(")")]
    return json.loads(raw)


class SrunAdapter(BaseAuthAdapter):
    """深澜软件 Srun 3000 / 4000 / Portal（清华、浙大、北邮、深大等顶尖高校主流）协议适配器。"""

    name = "srun"
    display_name = "深澜软件 Srun 4000 / Portal"

    def _get_portal_urls(self, auth_url: str) -> tuple[str, str]:
        """解析获取 challenge 接口与 portal 认证接口。"""
        parsed = urlparse(auth_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        challenge_url = f"{origin}/cgi-bin/get_challenge"
        
        path = parsed.path
        if path and path not in ("/", ""):
            portal_url = auth_url
        else:
            portal_url = f"{origin}/cgi-bin/srun_portal"
        return challenge_url, portal_url

    def _get_challenge(
        self,
        session: requests.Session,
        challenge_url: str,
        account: str,
        local_ip: str,
    ) -> str:
        resp = session.get(
            challenge_url,
            params={
                "username": account,
                "ip": local_ip,
                "double_stack": "0",
            },
            timeout=6,
        )
        data = _extract_json_or_jsonp(resp.text)
        token = data.get("challenge") or data.get("token") or ""
        if not token:
            raise ValueError(f"获取深澜 challenge 挑战值失败: {resp.text[:100]}")
        return str(token)

    def login(
        self,
        config: Config,
        local_ip: str,
        local_mac: str,
    ) -> tuple[bool, str]:
        session = requests.Session()
        session.trust_env = False
        try:
            challenge_url, portal_url = self._get_portal_urls(config.campus_auth_url)
            token = self._get_challenge(session, challenge_url, config.campus_account, local_ip)
            log.info("成功捕获深澜 Srun 挑战令牌 Token: %s", token)

            # 1. 计算 hex_hmac_md5
            hmd5 = get_hmac_md5(token, config.campus_password)

            # 2. 构造 info 参数并加密
            ac_id = str(config.wlan_ac_ip or "1")
            info_payload = {
                "username": config.campus_account,
                "password": config.campus_password,
                "ip": local_ip,
                "acid": ac_id,
                "enc_ver": "srun_bx1",
            }
            info_encrypted = build_srun_info(info_payload, token)

            # 3. 计算 chksum
            chksum = build_srun_chksum(
                token=token,
                username=config.campus_account,
                hmd5=hmd5,
                ac_id=ac_id,
                ip=local_ip,
                n=200,
                auth_type=1,
                info_encrypted=info_encrypted,
            )

            # 4. 发送认证请求 (POST 表单)
            form_data = {
                "action": "login",
                "username": config.campus_account,
                "password": f"{{MD5}}{hmd5}",
                "ac_id": ac_id,
                "ip": local_ip,
                "chksum": chksum,
                "info": info_encrypted,
                "n": "200",
                "type": "1",
                "os": "Windows 10",
                "name": "Windows",
                "double_stack": "0",
            }

            resp = session.post(portal_url, data=form_data, timeout=10)
            data = _extract_json_or_jsonp(resp.text)

            res = str(data.get("res", "")).lower()
            ecode = str(data.get("ecode", ""))
            error = str(data.get("error") or data.get("error_msg") or "").strip()

            if res == "ok" or ecode == "0" or "ok" in resp.text.lower():
                log.info("深澜 Srun 校园网认证成功")
                return True, "认证成功"

            # 映射错误码
            msg = error or f"认证失败 (res={res}, ecode={ecode})"
            for code_key, code_desc in _SRUN_ERROR_MAP.items():
                if code_key in msg or code_key == ecode:
                    msg = f"{code_desc} ({msg})"
                    break

            log.warning("深澜 Srun 认证未通过: %s", msg)
            return False, msg
        except Exception as err:
            log.error("深澜 Srun 认证异常: %s", err)
            return False, f"深澜认证请求失败: {err}"

    def logout(
        self,
        config: Config,
        local_ip: str,
        local_mac: str,
    ) -> tuple[bool, str]:
        session = requests.Session()
        session.trust_env = False
        try:
            _, portal_url = self._get_portal_urls(config.campus_auth_url)
            ac_id = str(config.wlan_ac_ip or "1")
            form_data = {
                "action": "logout",
                "username": config.campus_account,
                "ip": local_ip,
                "ac_id": ac_id,
            }
            resp = session.post(portal_url, data=form_data, timeout=8)
            data = _extract_json_or_jsonp(resp.text)
            res = str(data.get("res", "")).lower()
            if res == "ok" or "ok" in resp.text.lower() or "success" in resp.text.lower():
                log.info("深澜 Srun 校园网已成功下线")
                return True, "已成功下线"
            return False, f"下线反馈: {resp.text[:100]}"
        except Exception as err:
            log.error("深澜 Srun 下线异常: %s", err)
            return False, str(err)

    @classmethod
    def inspect_fingerprint(cls, url: str, html: str = "") -> float:
        score = 0.0
        target = (url + " " + html).lower()
        if "srun" in target:
            score += 0.5
        if "get_challenge" in target or "srun_portal" in target:
            score += 0.5
        if "srun_bx1" in target:
            score += 0.4
        return min(score, 1.0)
