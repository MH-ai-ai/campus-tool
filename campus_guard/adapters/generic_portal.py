from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlparse

import requests

from ..logging_setup import get_logger
from .base import BaseAuthAdapter

if TYPE_CHECKING:
    from ..models import Config

log = get_logger()


class GenericPortalAdapter(BaseAuthAdapter):
    """通用 Web Captive 表单认证适配器（兜底通用高校 Web 认证体系）。"""

    name = "portal"
    display_name = "通用 Web Portal 表单认证"

    def login(
        self,
        config: Config,
        local_ip: str,
        local_mac: str,
    ) -> tuple[bool, str]:
        session = requests.Session()
        session.trust_env = False
        try:
            # 尝试最常见的表单字段名称
            form_data = {
                "username": config.campus_account,
                "password": config.campus_password,
                "user": config.campus_account,
                "userId": config.campus_account,
                "account": config.campus_account,
                "pwd": config.campus_password,
                "ip": local_ip,
                "mac": local_mac,
            }
            resp = session.post(config.campus_auth_url, data=form_data, timeout=10)
            text = resp.text.lower()
            if any(k in text for k in ("success", "ok", "成功", "登录成功", "认证成功", '"result":1')):
                log.info("通用 Portal 认证响应成功")
                return True, "认证成功"
            if any(k in text for k in ("fail", "error", "失败", "密码错误", "欠费")):
                return False, "认证失败，请核对账号密码"
            return True, "认证已提交"
        except Exception as err:
            log.error("通用 Portal 认证异常: %s", err)
            return False, f"认证请求失败: {err}"

    def logout(
        self,
        config: Config,
        local_ip: str,
        local_mac: str,
    ) -> tuple[bool, str]:
        session = requests.Session()
        session.trust_env = False
        try:
            logout_url = config.campus_auth_url
            for suffix in ("/logout", "/logoff", "/signout", "?action=logout"):
                if suffix not in logout_url:
                    logout_url = urljoin(config.campus_auth_url, suffix)
                    break
            session.get(logout_url, timeout=8)
            return True, "下线请求已发送"
        except Exception as err:
            log.error("通用 Portal 下线异常: %s", err)
            return False, str(err)

    @classmethod
    def inspect_fingerprint(cls, url: str, html: str = "") -> float:
        # 通用兜底适配器，基准得分 0.1
        return 0.1
