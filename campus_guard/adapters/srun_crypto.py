from __future__ import annotations

import hashlib
import hmac
import json
import math
from typing import Any


# 深澜 Srun 官方前端自定义 Base64 字符映射表 (标准 64 字符全集)
_SRUN_ALPHA = "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA"
_PADCHAR = "="


def _ord_at(msg: str, idx: int) -> int:
    if 0 <= idx < len(msg):
        return ord(msg[idx])
    return 0


def _srun_s(a: str, b: bool) -> list[int]:
    c = len(a)
    v = []
    for i in range(0, c, 4):
        val = (
            _ord_at(a, i)
            | (_ord_at(a, i + 1) << 8)
            | (_ord_at(a, i + 2) << 16)
            | (_ord_at(a, i + 3) << 24)
        )
        v.append(val)
    if b:
        v.append(c)
    return v


def _srun_l(a: list[int], b: bool) -> str:
    d = len(a)
    c = (d - 1) << 2
    if b:
        m = a[d - 1]
        if m < c - 3 or m > c:
            return ""
        c = m
    ret: list[str] = []
    for i in range(d):
        ret.append(chr(a[i] & 0xFF))
        ret.append(chr((a[i] >> 8) & 0xFF))
        ret.append(chr((a[i] >> 16) & 0xFF))
        ret.append(chr((a[i] >> 24) & 0xFF))
    if b:
        return "".join(ret[:c])
    return "".join(ret)


def srun_xencode(msg: str, key: str) -> str:
    """深澜 XXTEA / xEncode 算法原生纯 Python 实现。"""
    if not msg:
        return ""
    v = _srun_s(msg, True)
    k = _srun_s(key, False)
    if len(k) < 4:
        k = k + [0] * (4 - len(k))
    n = len(v) - 1
    z = v[n]
    y = v[0]
    q = math.floor(6 + 52 / (n + 1))
    d = 0
    while q > 0:
        d = (d + 0x9E3779B9) & 0xFFFFFFFF
        e = (d >> 2) & 3
        for p in range(n):
            y = v[p + 1]
            m = (
                ((z >> 5 ^ y << 2) + ((y >> 3 ^ z << 4) ^ (d ^ y)))
                + (k[(p & 3) ^ e] ^ z)
            ) & 0xFFFFFFFF
            v[p] = (v[p] + m) & 0xFFFFFFFF
            z = v[p]
        y = v[0]
        m = (
            ((z >> 5 ^ y << 2) + ((y >> 3 ^ z << 4) ^ (d ^ y)))
            + (k[(n & 3) ^ e] ^ z)
        ) & 0xFFFFFFFF
        v[n] = (v[n] + m) & 0xFFFFFFFF
        z = v[n]
        q -= 1
    return _srun_l(v, False)


def srun_base64(raw: str) -> str:
    """深澜专用码表的 Base64 编码。"""
    if not raw:
        return ""
    res: list[str] = []
    length = len(raw)
    i = 0
    while i < length:
        b1 = ord(raw[i]) & 0xFF
        i += 1
        if i == length:
            res.append(_SRUN_ALPHA[b1 >> 2])
            res.append(_SRUN_ALPHA[(b1 & 3) << 4])
            res.append(_PADCHAR)
            res.append(_PADCHAR)
            break
        b2 = ord(raw[i]) & 0xFF
        i += 1
        if i == length:
            res.append(_SRUN_ALPHA[b1 >> 2])
            res.append(_SRUN_ALPHA[((b1 & 3) << 4) | ((b2 & 0xF0) >> 4)])
            res.append(_SRUN_ALPHA[(b2 & 0x0F) << 2])
            res.append(_PADCHAR)
            break
        b3 = ord(raw[i]) & 0xFF
        i += 1
        res.append(_SRUN_ALPHA[b1 >> 2])
        res.append(_SRUN_ALPHA[((b1 & 3) << 4) | ((b2 & 0xF0) >> 4)])
        res.append(_SRUN_ALPHA[((b2 & 0x0F) << 2) | ((b3 & 0xC0) >> 6)])
        res.append(_SRUN_ALPHA[b3 & 0x3F])
    return "".join(res)


def get_sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def get_hmac_md5(token: str, password: str) -> str:
    """深澜 Srun hex_hmac_md5 计算：以 challenge token 为秘钥哈希密码。"""
    return hmac.new(token.encode("utf-8"), password.encode("utf-8"), hashlib.md5).hexdigest()


def build_srun_info(info_dict: dict[str, Any], token: str) -> str:
    """生成深澜 {SRUNBX1} 加密 info 字段。"""
    json_str = json.dumps(info_dict, separators=(",", ":"))
    encoded = srun_xencode(json_str, token)
    return "{SRUNBX1}" + srun_base64(encoded)


def build_srun_chksum(
    token: str,
    username: str,
    hmd5: str,
    ac_id: str,
    ip: str,
    n: int,
    auth_type: int,
    info_encrypted: str,
) -> str:
    """计算深澜认证请求的 chksum 校验和。"""
    raw = (
        token
        + username
        + token
        + hmd5
        + token
        + str(ac_id)
        + token
        + ip
        + token
        + str(n)
        + token
        + str(auth_type)
        + token
        + info_encrypted
    )
    return get_sha1(raw)
