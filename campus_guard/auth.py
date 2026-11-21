from __future__ import annotations

import concurrent.futures
import json
import random
import re
from typing import Any, Mapping
from urllib.parse import parse_qs, urljoin, urlparse

import requests

from .adapters import get_adapter, guess_adapter_by_url
from .config import get_config, get_config_dict
from .logging_setup import get_logger
from .models import Config, normalize_auth_url
from .system import get_default_gateway, get_local_ip, get_local_mac, get_wifi_info
from .universities import get_university_manager

log = get_logger()


def translate_network_error(err_msg: str) -> str:
    """将底层的网络与 HTTP 请求英文异常翻译为清晰友好的中文指引。"""
    lowered = str(err_msg).lower()
    if "no scheme supplied" in lowered or "missing schema" in lowered or "invalid url" in lowered:
        return "认证接口 URL 地址无效或缺少 http:// 前缀"
    if "connection refused" in lowered or "10061" in lowered:
        return "无法连接认证网关（目标服务器拒绝连接，请确认已连入校园 Wi-Fi）"
    if "host is unreachable" in lowered or "10065" in lowered or "10051" in lowered or "无法连接的主机" in err_msg or "不可达" in err_msg:
        return "当前网络无法直连校园网认证服务器（网络不通或未连接校园 Wi-Fi）"
    if "timed out" in lowered or "timeout" in lowered:
        return "请求认证服务器超时，请检查校园 Wi-Fi 信号强度"
    if "name resolution failure" in lowered or "gaierror" in lowered:
        return "域名解析失败，请检查 DNS 配置或网络连接"
    return err_msg



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

    raw_url = str(getattr(active_config, "campus_auth_url", "") or "").strip()
    url = normalize_auth_url(raw_url)
    if not url:
        return False, "未配置校园网认证接口地址，请点击上方「一键极速打通」快速填入"

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
        "开始校园网认证: 协议=%s, 高校=%s, IP=%s, 接口URL=%s",
        adapter.display_name,
        getattr(active_config, "university_name", "默认"),
        local_ip,
        url,
    )
    try:
        ok, msg = adapter.login(active_config, local_ip, local_mac)
        return ok, (msg if ok else translate_network_error(msg))
    except requests.exceptions.MissingSchema:
        return False, f"认证地址 URL 格式错误（缺少 http://）: {url}"
    except requests.exceptions.ConnectionError:
        return False, "无法连接到认证网关服务器，请确认已连接校园 Wi-Fi 且网关地址正确"
    except requests.exceptions.Timeout:
        return False, "校园网认证网关请求超时，请检查当前 Wi-Fi 信号"
    except Exception as err:
        return False, f"认证请求异常: {translate_network_error(str(err))}"


def campus_logout(config: Config | None = None) -> tuple[bool, str]:
    """主动注销校园网登录下线。"""
    active_config = config or get_config()
    protocol = getattr(active_config, "auth_protocol", "drcom") or "drcom"
    adapter = get_adapter(protocol)

    raw_url = str(getattr(active_config, "campus_auth_url", "") or "").strip()
    url = normalize_auth_url(raw_url)
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
        ok, msg = adapter.logout(active_config, local_ip, local_mac)
        return ok, (msg if ok else translate_network_error(msg))
    except requests.exceptions.ConnectionError:
        return False, "无法连接到认证网关服务器，当前可能已经离线"
    except requests.exceptions.Timeout:
        return False, "注销下线请求超时"
    except Exception as err:
        return False, f"注销请求异常: {translate_network_error(str(err))}"


def auto_detect_portal_config() -> tuple[bool, str, dict[str, Any]]:
    """通过 Captive Portal 劫持探针与高校智能库，全自动嗅探校园网认证网关与参数。
    支持自动识别全国高校所属认证体系（深澜 Srun、城市热点 Dr.COM、锐捷 Ruijie、Portal）。
    优先采用纯 IP 零 DNS 探针并发探测，并支持根据 SSID/IP 与内网认证服务器主动探活智能回退。
    返回元组: (是否成功捕获, 状态说明, 提取到的配置字典)
    """
    extracted: dict[str, Any] = {}

    # 1. 尝试获取当前连接的 Wi-Fi 名称（基于网卡签名实时感知且不触发定位）
    wifi_raw = get_wifi_info(force=False)
    current_ssid = wifi_raw.split("(", 1)[0].strip() if "(" in wifi_raw else wifi_raw.strip()
    if current_ssid and current_ssid not in ("未连接", "未知"):
        extracted["campus_wifi_ssid"] = current_ssid

    # 2. 获取本机 IP
    local_ip = get_local_ip()
    if local_ip and local_ip != "未知" and "clash" not in local_ip.lower():
        extracted["wlan_user_ip"] = local_ip

    # 3. 构造零 DNS 延迟的优先 IP 探针列表 + 备选域名探针
    system_gw = get_default_gateway()
    if system_gw and system_gw != "0.0.0.0" and not system_gw.startswith("127."):
        extracted["campus_gateway"] = system_gw

    ip_probes = []
    if system_gw and system_gw != "0.0.0.0" and not system_gw.startswith("127."):
        ip_probes.append(f"http://{system_gw}/")
    ip_probes.extend([
        "http://1.2.3.4/",
        "http://123.123.123.123/",
        "http://10.255.255.254/",
    ])

    domain_probes = [
        "http://connect.rom.miui.com/generate_204",
        "http://wifi.vivo.com.cn/generate_204",
        "http://connectivitycheck.platform.hicloud.com/generate_204",
        "http://captive.apple.com/hotspot-detect.html",
        "http://www.msftconnecttest.com/connecttest.txt",
    ]

    def _is_captive_redirect(probe_url: str, redirect_candidate: str) -> bool:
        if not redirect_candidate:
            return False
        try:
            cand_parsed = urlparse(redirect_candidate)
            cand_host = (cand_parsed.hostname or "").lower()
            probe_parsed = urlparse(probe_url)
            probe_host = (probe_parsed.hostname or "").lower()
            if not cand_host:
                return False

            # 排除公网 CDN / 常见探针原站自身跳转 (如 apple 跳 apple)
            ignored_domains = (
                "1.1.1.1", "cloudflare", "apple.com", "google", "gstatic",
                "msftconnecttest", "microsoft", "miui.com", "hicloud.com", "vivo.com.cn"
            )
            if any(dom in cand_host for dom in ignored_domains):
                return False

            # 如果探针是公共探测 IP（如 1.2.3.4），发生跳转且目标非原探针即为合法劫持
            if probe_host in ("1.2.3.4", "123.123.123.123", "10.255.255.254"):
                return cand_host != probe_host

            # 如果探针是网关 IP（如 10.211.0.1），同一 IP 下包含特征路径也算成功
            if probe_host == cand_host:
                cand_lower = redirect_candidate.lower()
                return any(k in cand_lower for k in ("portal", "login", "auth", "drcom", "srun", "eportal", ":801", ":8080", "userip", "wlan", "index.jsp"))

            return cand_host != probe_host
        except Exception:
            return False

    def _extract_redirect_from_html(resp_text: str, base_url: str) -> str:
        if not resp_text:
            return ""
        # 1. 匹配 location.replace('url') 或 location.assign('url') 或 window.navigate('url')
        call_match = re.search(
            r"(?:location\.(?:replace|assign)|window\.navigate)\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
            resp_text,
            re.I,
        )
        if call_match:
            return urljoin(base_url, call_match.group(1).strip())

        # 2. 匹配 [window.|top.|self.|top.self.]location[.href] = 'url'
        assign_match = re.search(
            r"(?:(?:window|top|self|top\.self)\.)*(?:location|document\.location)(?:\.href)?\s*=\s*['\"]([^'\"]+)['\"]",
            resp_text,
            re.I,
        )
        if assign_match:
            return urljoin(base_url, assign_match.group(1).strip())

        # 3. 匹配 HTML meta refresh: url=...
        meta_match = re.search(r"content=['\"][^'\"]*url=([^'\">]+)['\"]?", resp_text, re.I)
        if meta_match:
            return urljoin(base_url, meta_match.group(1).strip())

        # 4. 匹配 form action 包含 portal/login/eportal
        form_match = re.search(r"<form[^>]+action=['\"]([^'\"]+)['\"]", resp_text, re.I)
        if form_match:
            action_cand = urljoin(base_url, form_match.group(1).strip())
            if any(k in action_cand.lower() for k in ("portal", "login", "auth", "drcom", "srun", "eportal")):
                return action_cand

        return ""

    def _probe_single(probe_url: str) -> tuple[str, str]:
        """探测单条 URL，返回 (redirect_url, html_content)"""
        try:
            session = requests.Session()
            session.trust_env = False
            resp = session.get(probe_url, allow_redirects=False, timeout=(1.5, 2.0))
            raw_url = getattr(resp, "url", None)
            base_url = raw_url if isinstance(raw_url, str) and raw_url else probe_url
            raw_text = getattr(resp, "text", "")
            resp_text = raw_text if isinstance(raw_text, str) else ""

            # 捕获 HTTP 30x 重定向
            if resp.status_code in (301, 302, 303, 307, 308) and "Location" in resp.headers:
                loc = str(resp.headers["Location"]).strip()
                full_loc = urljoin(base_url, loc)
                if _is_captive_redirect(probe_url, full_loc):
                    return full_loc, resp_text

            # 捕获 HTML 内部 JS 或 meta 刷新跳转
            html_redir = _extract_redirect_from_html(resp_text, base_url)
            if html_redir and _is_captive_redirect(probe_url, html_redir):
                return html_redir, resp_text
        except Exception:
            pass
        return "", ""

    target_redirect_url = ""
    captured_html = ""

    # Phase 1: 极速纯 IP 并发探测（0 DNS 延迟，5~50ms 即可完成）
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(ip_probes), 1)) as executor:
        futures = {executor.submit(_probe_single, url): url for url in ip_probes}
        try:
            for fut in concurrent.futures.as_completed(futures, timeout=2.0):
                redir, html = fut.result()
                if redir:
                    target_redirect_url = redir
                    captured_html = html
                    break
        except Exception:
            pass

    # Phase 2: 若纯 IP 探针未捕获，并发尝试备选域名探针（最多等待 1.5s）
    if not target_redirect_url:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(domain_probes), 1)) as executor:
            futures = {executor.submit(_probe_single, url): url for url in domain_probes}
            try:
                for fut in concurrent.futures.as_completed(futures, timeout=1.5):
                    redir, html = fut.result()
                    if redir:
                        target_redirect_url = redir
                        captured_html = html
                        break
            except Exception:
                pass

    # Phase 3: 智能高校回退推导与主动探活机制
    # 当网络已畅通（公网探针未被 302 劫持）或处于特定校园无线环境时，根据当前 SSID/IP 与高校库智能推导
    uni_mgr = get_university_manager()
    if not target_redirect_url:
        matched_prof = uni_mgr.infer_by_ssid_and_ip(current_ssid, local_ip)
        if not matched_prof:
            cfg = get_config_dict()
            ssid_lower = current_ssid.lower()
            saved_uni = str(cfg.get("university_id", "")).strip()
            if saved_uni and saved_uni not in ("generic_portal", ""):
                candidate_prof = uni_mgr.get_profile(saved_uni)
                if candidate_prof:
                    match_ssid = any(s and s.lower() in ssid_lower for s in candidate_prof.wifi_ssids)
                    match_ip = any(k.endswith(".") and local_ip.startswith(k) for k in candidate_prof.domain_keywords if local_ip)
                    if match_ssid or match_ip:
                        matched_prof = candidate_prof

        if matched_prof:
            candidate_auth_url = matched_prof.auth_url
            extracted["auth_protocol"] = matched_prof.protocol
            extracted["university_id"] = matched_prof.id
            extracted["university_name"] = matched_prof.name
            extracted["campus_auth_url"] = matched_prof.auth_url
            extracted["campus_gateway"] = system_gw or matched_prof.gateway or "10.211.0.1"
            if matched_prof.ac_ip:
                extracted["wlan_ac_ip"] = matched_prof.ac_ip
            if current_ssid and current_ssid not in ("未连接", "未知"):
                extracted["campus_wifi_ssid"] = current_ssid
            if local_ip and local_ip != "未知":
                extracted["wlan_user_ip"] = local_ip

            # 针对匹配到的高校认证网关主动探活
            gw_alive = False
            try:
                cand_parsed = urlparse(candidate_auth_url)
                cand_host = cand_parsed.hostname or ""
                cand_port = cand_parsed.port or (443 if cand_parsed.scheme == "https" else (801 if "801" in candidate_auth_url else 80))
                from .system import tcp_check
                if cand_host and tcp_check(cand_host, cand_port, timeout=0.8):
                    gw_alive = True
                    log.info("高校智能库主动探活成功: %s -> %s:%d", matched_prof.name, cand_host, cand_port)
            except Exception as err:
                log.debug("主动探活候选高校异常: %s", err)

            status_msg = (
                f"已智能识别{matched_prof.name}校园网环境，认证网关与参数已自动同步校准！"
                if gw_alive
                else f"已根据网络特征识别{matched_prof.name}，认证参数已成功同步校准！"
            )
            return True, status_msg, extracted

        return False, "未捕获到校园网重定向，可能网络已畅通或尚未连接校园 Wi-Fi", extracted

    # 4. 解析目标重定向 URL 并智能识别高校体系
    try:
        parsed = urlparse(target_redirect_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        extracted["campus_auth_url"] = base_url

        host = parsed.hostname
        if host and host not in ("1.1.1.1", "1.0.0.1", "cloudflare.com"):
            extracted["campus_gateway"] = host
        else:
            if system_gw and system_gw != "0.0.0.0" and not system_gw.startswith("127."):
                extracted["campus_gateway"] = system_gw

        qs = parse_qs(parsed.query)
        for k, v in qs.items():
            k_lower = k.lower()
            if any(key in k_lower for key in ("ac_ip", "wlanacip", "nasip", "ac-ip")):
                extracted["wlan_ac_ip"] = v[0]
            elif any(key in k_lower for key in ("user_ip", "wlanuserip", "userip", "user-ip")):
                extracted["wlan_user_ip"] = v[0]

        # 5. 调用高校知识库反推归属高校及协议
        prof, protocol = uni_mgr.infer_by_url_and_html(target_redirect_url, captured_html)
        if not prof and current_ssid:
            prof = uni_mgr.infer_by_ssid_and_ip(current_ssid, local_ip)
            if prof:
                protocol = prof.protocol

        extracted["auth_protocol"] = protocol
        if prof:
            extracted["university_id"] = prof.id
            extracted["university_name"] = prof.name
            if prof.gateway and not extracted.get("campus_gateway"):
                extracted["campus_gateway"] = prof.gateway
            if prof.ac_ip and not extracted.get("wlan_ac_ip"):
                extracted["wlan_ac_ip"] = prof.ac_ip
            log.info("智能嗅探命中高校: %s (协议: %s)", prof.name, protocol)
        else:
            extracted["university_id"] = f"generic_{protocol}"
            extracted["university_name"] = f"通用 {protocol.upper()} 模板"

        # 根据识别到的协议体系，自动纠正并规范化认证 API 端点（彻底杜绝 index.jsp 造成的 404）
        if protocol == "drcom":
            from .adapters.drcom import build_drcom_urls
            login_url, _ = build_drcom_urls(base_url)
            extracted["campus_auth_url"] = login_url
        elif protocol == "srun":
            origin = f"{parsed.scheme}://{parsed.netloc}"
            extracted["campus_auth_url"] = f"{origin}/cgi-bin/srun_portal"
        elif protocol == "ruijie":
            origin = f"{parsed.scheme}://{parsed.netloc}"
            extracted["campus_auth_url"] = f"{origin}/eportal/InterFace.do?method=login"
        else:
            extracted["campus_auth_url"] = base_url

        return True, f"已成功捕获校园网认证参数！(识别体系: {protocol.upper()})", extracted
    except Exception as err:
        return False, f"重定向地址解析异常: {err}", extracted
