from __future__ import annotations

import json
import random
import re
from typing import Any, Mapping
from urllib.parse import parse_qs, urlparse

import requests

from .adapters import get_adapter, guess_adapter_by_url
from .config import get_config
from .logging_setup import get_logger
from .models import Config
from .system import get_local_ip, get_local_mac, get_wifi_info
from .universities import get_university_manager

log = get_logger()


def _config_get(config: Config | Mapping[str, Any], key: str, default: Any = "") -> Any:
    if isinstance(config, Config):
        return getattr(config, key)
    return config.get(key, default)


# ---------------------------------------------------------
# 向后兼容导出函数（延安大学与通用 Dr.COM 保持一致）
# ---------------------------------------------------------

def build_auth_params(
    config: Config | Mapping[str, Any],
    local_ip: str,
    local_mac: str,
) -> dict[str, str]:
    adapter = get_adapter("drcom")
    cfg = Config.from_mapping(config) if isinstance(config, Mapping) else config
    return adapter.build_auth_params(cfg, local_ip, local_mac)  # type: ignore[attr-defined]


def build_logout_params(
    config: Config | Mapping[str, Any],
    local_ip: str,
    local_mac: str,
) -> dict[str, str]:
    adapter = get_adapter("drcom")
    cfg = Config.from_mapping(config) if isinstance(config, Mapping) else config
    return adapter.build_logout_params(cfg, local_ip, local_mac)  # type: ignore[attr-defined]


def parse_drcom_response(text: str) -> tuple[bool, str]:
    from .adapters.drcom import parse_drcom_response as _parse
    return _parse(text)


# ---------------------------------------------------------
# 全国高校统一认证入口
# ---------------------------------------------------------

def campus_login(config: Config | None = None) -> tuple[bool, str]:
    """根据当前配置的协议体系执行认证登录。"""
    active_config = config or get_config()
    protocol = getattr(active_config, "auth_protocol", "drcom") or "drcom"
    adapter = get_adapter(protocol)

    url = str(getattr(active_config, "campus_auth_url", "") or "").strip()
    if not url:
        return False, "未配置校园网认证接口地址，请点击上方「一键极速打通」快速填入"
    if not url.startswith(("http://", "https://")):
        return False, f"认证地址 URL 格式无效（缺少 http:// 或 https://）: {url}"

    account = str(getattr(active_config, "campus_account", "") or "").strip()
    if not account:
        return False, "未配置校园网学号/账号，请点击上方「一键极速打通」或在偏好设置中填写"

    password = str(getattr(active_config, "campus_password", "") or "").strip()
    if not password:
        return False, "未配置校园网密码，请在偏好设置或一键打通中填写密码"

    local_ip = get_local_ip()
    
    # 前置保护：如果当前无线断开或未获取到有效局域网 IP，尝试自动唤醒恢复 Wi-Fi 连接
    if not local_ip or local_ip == "未知" or local_ip.startswith("169.254."):
        log.warning("检测到尚未获取有效局域网 IP，正在尝试自动恢复 Wi-Fi 链路...")
        from .system import reconnect_wifi
        reconnect_wifi()
        local_ip = get_local_ip()

    # 如果自动重连后依然无法获得 IP，友善提示用户，避免触发底层套接字网络不可达异常 (WinError 10051)
    if not local_ip or local_ip == "未知" or local_ip.startswith("169.254."):
        msg = "电脑尚未连入校园 Wi-Fi (未获取到局域网 IP)，请先确认已连接校园无线网络"
        log.warning("校园网认证前置拦截: %s", msg)
        return False, msg

    local_mac = get_local_mac()

    log.info(
        "开始校园网认证: 协议=%s, 高校=%s, IP=%s",
        adapter.display_name,
        getattr(active_config, "university_name", "默认"),
        local_ip,
    )
    try:
        return adapter.login(active_config, local_ip, local_mac)
    except requests.exceptions.MissingSchema:
        return False, f"认证地址 URL 格式错误（缺少 http://）: {url}"
    except requests.exceptions.ConnectionError:
        return False, "无法连接到认证网关服务器，请确认已连接校园 Wi-Fi 且网关地址正确"
    except requests.exceptions.Timeout:
        return False, "校园网认证网关请求超时，请检查当前 Wi-Fi 信号"
    except Exception as err:
        return False, f"认证请求异常: {err}"


def campus_logout(config: Config | None = None) -> tuple[bool, str]:
    """主动注销校园网登录下线。"""
    active_config = config or get_config()
    protocol = getattr(active_config, "auth_protocol", "drcom") or "drcom"
    adapter = get_adapter(protocol)

    url = str(getattr(active_config, "campus_auth_url", "") or "").strip()
    if not url:
        return False, "未配置校园网认证接口地址，无法执行下线注销"

    local_ip = get_local_ip()
    local_mac = get_local_mac()

    log.info(
        "请求注销校园网下线: 协议=%s, 高校=%s",
        adapter.display_name,
        getattr(active_config, "university_name", "默认"),
    )
    try:
        return adapter.logout(active_config, local_ip, local_mac)
    except requests.exceptions.ConnectionError:
        return False, "无法连接到认证网关服务器，当前可能已经离线"
    except requests.exceptions.Timeout:
        return False, "注销下线请求超时"
    except Exception as err:
        return False, f"注销请求异常: {err}"


def auto_detect_portal_config() -> tuple[bool, str, dict[str, Any]]:
    """通过 Captive Portal 劫持探针，全自动嗅探校园网认证网关与参数。
    支持自动识别全国高校所属认证体系（深澜 Srun、城市热点 Dr.COM、锐捷 Ruijie、Portal）。
    返回元组: (是否成功捕获, 状态说明, 提取到的配置字典)
    """
    extracted: dict[str, Any] = {}

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
    captured_html = ""
    for url in probe_urls:
        try:
            resp = session.get(url, allow_redirects=False, timeout=3)
            # 捕获 HTTP 30x 重定向
            if resp.status_code in (301, 302, 303, 307, 308) and "Location" in resp.headers:
                target_redirect_url = resp.headers["Location"]
                captured_html = resp.text or ""
                break
            # 捕获 HTML 内部 JS 或 meta 刷新跳转
            if resp.text:
                js_match = re.search(r"location\.(?:href|replace)\s*=\s*['\"]([^'\"]+)['\"]", resp.text, re.I)
                if js_match:
                    target_redirect_url = js_match.group(1)
                    captured_html = resp.text
                    break
                meta_match = re.search(r"url=([^'\">]+)", resp.text, re.I)
                if meta_match:
                    target_redirect_url = meta_match.group(1).strip()
                    captured_html = resp.text
                    break
        except Exception:
            continue

    if not target_redirect_url:
        return False, "未捕获到校园网重定向，可能网络已畅通或尚未连接校园 Wi-Fi", extracted

    # 4. 解析目标重定向 URL 并智能识别高校体系
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
            if any(key in k_lower for key in ("ac_ip", "wlanacip", "nasip", "ac-ip")):
                extracted["wlan_ac_ip"] = v[0]
            elif any(key in k_lower for key in ("user_ip", "wlanuserip", "userip", "user-ip")):
                extracted["wlan_user_ip"] = v[0]

        # 5. 调用高校知识库反推归属高校及协议
        uni_mgr = get_university_manager()
        prof, protocol = uni_mgr.infer_by_url_and_html(target_redirect_url, captured_html)
        extracted["auth_protocol"] = protocol
        if prof:
            extracted["university_id"] = prof.id
            extracted["university_name"] = prof.name
            if prof.gateway and not extracted.get("campus_gateway"):
                extracted["campus_gateway"] = prof.gateway
            log.info("智能嗅探命中高校: %s (协议: %s)", prof.name, protocol)
        else:
            extracted["university_id"] = f"generic_{protocol}"
            extracted["university_name"] = f"通用 {protocol.upper()} 模板"

        return True, f"已成功捕获校园网认证参数！(识别体系: {protocol.upper()})", extracted
    except Exception as err:
        return False, f"重定向地址解析异常: {err}", extracted
