from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models import Config


class BaseAuthAdapter(ABC):
    """全国高校统一认证协议适配器抽象基类。"""

    name: str = "base"
    display_name: str = "基础认证适配器"

    @abstractmethod
    def login(
        self,
        config: Config,
        local_ip: str,
        local_mac: str,
    ) -> tuple[bool, str]:
        """执行校园网认证登录。返回 (是否成功, 提示信息)。"""
        raise NotImplementedError

    @abstractmethod
    def logout(
        self,
        config: Config,
        local_ip: str,
        local_mac: str,
    ) -> tuple[bool, str]:
        """执行校园网主动注销登出。返回 (是否成功, 提示信息)。"""
        raise NotImplementedError

    def check_status(
        self,
        config: Config,
        local_ip: str,
    ) -> tuple[bool, str]:
        """可选：主动查询当前设备在认证网关中的在线状态。默认未实现时返回 (False, '未支持状态查询')。"""
        return False, "当前协议适配器未实现主动状态查询"

    @classmethod
    def inspect_fingerprint(cls, url: str, html: str = "") -> float:
        """根据 Captive Portal 劫持重定向 URL 与返回 HTML 内容，评估该协议特征契合度。
        返回 0.0 ~ 1.0 之间的置信度分数。
        """
        return 0.0
