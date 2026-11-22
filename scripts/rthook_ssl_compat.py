"""PyInstaller 运行时 SSLContext 兼容钩子。
当基础 Python 发行版的 ssl.SSLContext.__new__ 按 __file__ 相对路径加载附加 CA 文件、
在冻结 zipimport 环境下触发 FileNotFoundError 时，安全回退到原生 _SSLContext.__new__，
由后续 create_default_context 正常加载 certifi 根证书库。
"""
from __future__ import annotations

import ssl

_orig_ssl_context_new = ssl.SSLContext.__new__


def _safe_ssl_context_new(cls, protocol=None, *args, **kwargs):
    try:
        return _orig_ssl_context_new(cls, protocol, *args, **kwargs)
    except FileNotFoundError:
        if protocol is None:
            protocol = ssl.PROTOCOL_TLS
        return ssl._SSLContext.__new__(cls, protocol)


ssl.SSLContext.__new__ = _safe_ssl_context_new
