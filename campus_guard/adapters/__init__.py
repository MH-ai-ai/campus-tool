from __future__ import annotations

from typing import Type

from .base import BaseAuthAdapter
from .drcom import DrcomAdapter
from .generic_portal import GenericPortalAdapter
from .ruijie import RuijieAdapter
from .srun import SrunAdapter

_ADAPTER_REGISTRY: dict[str, BaseAuthAdapter] = {
    "drcom": DrcomAdapter(),
    "srun": SrunAdapter(),
    "ruijie": RuijieAdapter(),
    "portal": GenericPortalAdapter(),
}


def get_adapter(protocol: str | None = None) -> BaseAuthAdapter:
    """获取指定认证协议的适配器实例，默认返回 Dr.COM（延安大学兼容）。"""
    if not protocol:
        return _ADAPTER_REGISTRY["drcom"]
    key = protocol.strip().lower()
    return _ADAPTER_REGISTRY.get(key, _ADAPTER_REGISTRY["drcom"])


def guess_adapter_by_url(url: str, html: str = "") -> BaseAuthAdapter:
    """根据目标 URL 和 HTML 指纹评分，自动匹配最高契合度的协议适配器。"""
    best_adapter = _ADAPTER_REGISTRY["drcom"]
    best_score = -1.0

    for adapter in _ADAPTER_REGISTRY.values():
        score = adapter.inspect_fingerprint(url, html)
        if score > best_score:
            best_score = score
            best_adapter = adapter

    return best_adapter


__all__ = [
    "BaseAuthAdapter",
    "DrcomAdapter",
    "SrunAdapter",
    "RuijieAdapter",
    "GenericPortalAdapter",
    "get_adapter",
    "guess_adapter_by_url",
]
