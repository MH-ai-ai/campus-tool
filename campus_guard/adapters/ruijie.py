from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from ..logging_setup import get_logger
from .base import BaseAuthAdapter

if TYPE_CHECKING:
    from ..models import Config

log = get_logger()


class RuijieAdapter(BaseAuthAdapter):
    """锐捷网络 RG-ePortal / SAM 系列认证协议适配器。"""

    name = "ruijie"
    display_name = "锐捷网络 Ruijie ePortal / SAM"

    def _build_ruijie_url(self, auth_url: str, method: str = "login") -> str:
        parsed = urlparse(auth_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if "InterFace.do" in parsed.path:
            return f"{origin}{parsed.path}?method={method}"
        return f"{origin}/eportal/InterFace.do?method={method}"

    def login(
        self,
        config: Config,
        local_ip: str,
        local_mac: str,
    ) -> tuple[bool, str]:
        session = requests.Session()
        session.trust_env = False
        try:
            target_url = self._build_ruijie_url(config.campus_auth_url, "login")
            
            # 提取原 URL query 参数以适配锐捷的 queryString 机制
            parsed = urlparse(config.campus_auth_url)
            query_string = parsed.query or ""

            form_data = {
                "userId": config.campus_account,
                "password": config.campus_password,
                "service": "",
                "queryString": query_string,
                "operatorPwd": "",
                "operatorUserId": "",
                "validcode": "",
                "passwordEncrypt": "false",
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }

            resp = session.post(target_url, data=form_data, headers=headers, timeout=10)
            text = resp.text.strip()

            try:
                data = json.loads(text)
                res = str(data.get("result", "")).lower()
                msg = str(data.get("message") or data.get("msg") or "").strip()
                if res in ("success", "1", "ok") or "success" in res:
                    log.info("锐捷校园网认证成功: %s", msg)
                    return True, msg or "认证成功"
                log.warning("锐捷校园网认证未通过: %s", msg)
                return False, msg or f"认证失败 ({res})"
            except json.JSONDecodeError:
                if "success" in text.lower() or "认证成功" in text:
                    return True, "认证成功"
                return False, f"锐捷响应异常: {text[:100]}"
        except Exception as err:
            log.error("锐捷认证请求异常: %s", err)
            return False, f"锐捷认证失败: {err}"

    def logout(
        self,
        config: Config,
        local_ip: str,
        local_mac: str,
    ) -> tuple[bool, str]:
        session = requests.Session()
        session.trust_env = False
        try:
            target_url = self._build_ruijie_url(config.campus_auth_url, "logout")
            form_data = {
                "userId": config.campus_account,
            }
            resp = session.post(target_url, data=form_data, timeout=8)
            if "success" in resp.text.lower():
                log.info("锐捷校园网已成功下线")
                return True, "已成功下线"
            return False, f"下线响应: {resp.text[:100]}"
        except Exception as err:
            log.error("锐捷下线异常: %s", err)
            return False, str(err)

    @classmethod
    def inspect_fingerprint(cls, url: str, html: str = "") -> float:
        score = 0.0
        target = (url + " " + html).lower()
        if "ruijie" in target or "rg_" in target:
            score += 0.5
        if "interface.do" in target:
            score += 0.6
        if "sam" in target and "portal" in target:
            score += 0.3
        return min(score, 1.0)
