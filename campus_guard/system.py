from __future__ import annotations

import gc
import platform
import re
import socket
import subprocess
import sys
import time
import uuid

import psutil
import requests

from .config import get_config_dict
from .logging_setup import get_logger


log = get_logger()
_wifi_info_cache: tuple[float, str] = (0.0, "未知")
_wifi_signal_cache: tuple[float, int] = (0.0, -1)


def decode_subprocess_output(raw: bytes) -> str:
    for enc in ("gbk", "cp936", "utf-8"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def get_primary_interface_info() -> tuple[str, str, str]:
    """动态探测当前处于活跃状态的物理网卡（以太网或 Wi-Fi）。
    返回元组: (网卡名称, IPv4 地址, MAC 地址)
    """
    try:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()

        candidates: list[tuple[str, str, str, int]] = []
        for name, stat in stats.items():
            if not stat.isup:
                continue
            lower_name = name.lower()
            if any(virt in lower_name for virt in ("vethernet", "virtual", "vmware", "vbox", "wsl", "loopback", "tap", "tun", "vgate", "tailscale", "wintun", "sing-box", "wireguard", "clash", "zerotier", "openvpn")):
                continue

            ipv4 = ""
            mac = ""
            for addr in addrs.get(name, []):
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    if ip and not ip.startswith("127.") and not ip.startswith("169.254.") and not is_clash_tun_ip(ip):
                        ipv4 = ip
                elif hasattr(psutil, "AF_LINK") and addr.family == psutil.AF_LINK:
                    mac = addr.address.replace("-", "").replace(":", "").lower()

            if ipv4:
                # 优先级打分：WLAN/Wi-Fi 与以太网优先
                score = 0
                if any(k in lower_name for k in ("wlan", "wi-fi", "wifi", "wireless")):
                    score = 20
                elif any(k in lower_name for k in ("ethernet", "以太网", "本地连接")):
                    score = 15
                else:
                    score = 5
                candidates.append((name, ipv4, mac, score))

        if candidates:
            candidates.sort(key=lambda x: x[3], reverse=True)
            best_name, best_ip, best_mac, _ = candidates[0]
            return best_name, best_ip, best_mac
    except Exception as err:
        log.debug("动态网卡扫描异常: %s", err)

    # 回退探测
    fallback_ip = "未知"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            fallback_ip = s.getsockname()[0]
    except Exception:
        pass

    fallback_mac = uuid.getnode()
    mac_str = "".join(f"{(fallback_mac >> i) & 0xFF:02x}" for i in range(40, -1, -8))
    return "未知网卡", fallback_ip, mac_str


def get_local_ip() -> str:
    name, ip, _mac = get_primary_interface_info()
    if ip and ip != "未知":
        if is_clash_tun_ip(ip):
            return f"{ip} (Clash TUN)"
        return ip

    # 若 Wi-Fi 链路已断开，严禁回退读取断网前的残留僵尸 IP
    if not is_wifi_link_up():
        return "未知"

    # 兼容历史逻辑: 针对特定名称回退查找
    try:
        result = subprocess.run(
            ["netsh", "interface", "ip", "show", "addresses", "WLAN"],
            capture_output=True,
            timeout=5,
            creationflags=0x08000000,
        )
        output = decode_subprocess_output(result.stdout)
        for line in output.splitlines():
            stripped = line.strip()
            if "IP" in stripped and ":" in stripped:
                found_ip = stripped.split(":", 1)[1].strip()
                if found_ip and found_ip != "127.0.0.1" and not is_clash_tun_ip(found_ip):
                    return found_ip
    except Exception:
        pass
    return "未知"


_cached_mac: str | None = None


def get_local_mac() -> str:
    """获取活动物理网卡 MAC 地址；断网回退时不污染全局缓存。"""
    global _cached_mac
    name, _ip, mac = get_primary_interface_info()
    if name != "未知网卡" and mac and len(mac) == 12:
        _cached_mac = mac
        return _cached_mac

    if _cached_mac:
        return _cached_mac

    # 断网无活跃物理网卡时临时返回回退 MAC，严禁写入 _cached_mac 防止蓝牙等虚拟节点污染
    fallback_mac = uuid.getnode()
    return "".join(f"{(fallback_mac >> i) & 0xFF:02x}" for i in range(40, -1, -8))


def tcp_check(host: str, port: int, timeout: int = 3) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
        return True
    except Exception:
        return False


def http_check(url: str, timeout: int = 3, trust_env: bool = False) -> bool:
    try:
        session = requests.Session()
        session.trust_env = trust_env
        resp = session.head(url, timeout=timeout)
        return resp.status_code < 500
    except Exception:
        return False


_gw_cache: tuple[float, str] = (0.0, "")
GW_CACHE_TTL = 5.0


def get_default_gateway() -> str:
    """提取操作系统当前网络活动网卡的默认路由网关 IP。"""
    global _gw_cache
    now = time.time()
    cached_at, cached_gw = _gw_cache
    if cached_gw and (now - cached_at < GW_CACHE_TTL):
        return cached_gw

    try:
        if sys.platform == "win32":
            creationflags = 0x08000000 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            # 1. 优先从 route print 0.0.0.0 提取
            res = subprocess.run(
                ["route", "print", "0.0.0.0"],
                capture_output=True,
                timeout=3,
                creationflags=creationflags,
            )
            out = decode_subprocess_output(res.stdout)
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                    gw = parts[2].strip()
                    if gw and gw != "0.0.0.0" and not gw.startswith("127."):
                        _gw_cache = (now, gw)
                        return gw

            # 2. 回退尝试从 netsh interface ip show config 提取
            res2 = subprocess.run(
                ["netsh", "interface", "ip", "show", "config"],
                capture_output=True,
                timeout=3,
                creationflags=creationflags,
            )
            out2 = decode_subprocess_output(res2.stdout)
            for line in out2.splitlines():
                stripped = line.strip()
                if any(k in stripped for k in ("Default Gateway", "默认网关")) and ":" in stripped:
                    gw = stripped.split(":", 1)[1].strip().split("(")[0].strip()
                    if gw and gw != "0.0.0.0" and not gw.startswith("127."):
                        _gw_cache = (now, gw)
                        return gw
        else:
            # Linux / macOS 环境
            res = subprocess.run(["ip", "route", "show", "default"], capture_output=True, timeout=2)
            out = decode_subprocess_output(res.stdout)
            parts = out.strip().split()
            if len(parts) >= 3 and parts[0] == "default" and parts[1] == "via":
                gw = parts[2].strip()
                _gw_cache = (now, gw)
                return gw
    except Exception as err:
        log.debug("获取系统默认网关失败: %s", err)
    return ""


def ping_check(host: str, timeout_ms: int = 800) -> bool:
    """通过系统原生 ICMP Ping 指令极速测试主机是否可达。"""
    if not host or host in ("0.0.0.0", "未知") or host.startswith("127."):
        return False
    try:
        if sys.platform == "win32":
            cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host]
        else:
            cmd = ["ping", "-c", "1", "-W", str(max(1, int(timeout_ms / 1000))), host]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=(timeout_ms / 1000) + 0.5,
        )
        return proc.returncode == 0
    except Exception:
        return False


def _probe_gw_target(gw_ip: str) -> bool:
    if not gw_ip or gw_ip in ("0.0.0.0", "未知") or gw_ip.startswith("127."):
        return False
    # 1. 并发探测常用网关/DNS/Portal 端口，大幅压缩超时等待
    ports = (801, 80, 8080, 53, 443)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(ports)) as executor:
        futures = [executor.submit(tcp_check, gw_ip, port, 0.6) for port in ports]
        try:
            for fut in concurrent.futures.as_completed(futures, timeout=0.8):
                if fut.result():
                    return True
        except Exception:
            pass
    # 2. 回退 ICMP Ping 测试
    return ping_check(gw_ip, timeout_ms=600)


def check_campus_gateway() -> bool:
    """探测校园网网关与认证服务器是否可达。
    并发探测认证服务器（campus_auth_url 中的主机与端口，如 10.200.84.3:801）、
    延安大学等高校已知端点、配置网关 (campus_gateway) 与系统当前路由默认网关 (sys_gw)。
    """
    from urllib.parse import urlparse
    import concurrent.futures

    cfg = get_config_dict()
    targets: list[tuple[str, int]] = []

    # 1. 优先提取配置的校园网认证服务器
    auth_url = str(cfg.get("campus_auth_url", "")).strip()
    if auth_url:
        try:
            parsed = urlparse(auth_url)
            auth_host = parsed.hostname
            auth_port = parsed.port or (443 if parsed.scheme == "https" else (801 if "801" in auth_url else 80))
            if auth_host and auth_host not in ("127.0.0.1", "localhost", "0.0.0.0"):
                targets.append((auth_host, auth_port))
        except Exception as err:
            log.debug("解析 campus_auth_url 探活目标异常: %s", err)

    # 2. 延安大学默认认证服务器与网关端点
    yau_endpoints = [("10.200.84.3", 801), ("10.200.84.3", 80)]
    for ep in yau_endpoints:
        if ep not in targets:
            targets.append(ep)

    # 3. 探测配置网关 (campus_gateway)
    cfg_gw = str(cfg.get("campus_gateway", "")).strip()
    if cfg_gw and cfg_gw not in ("0.0.0.0", "127.0.0.1", "未知"):
        targets.append((cfg_gw, 80))
        targets.append((cfg_gw, 801))

    # 4. 探测系统默认网关 (sys_gw)
    sys_gw = get_default_gateway()
    if sys_gw and sys_gw not in ("0.0.0.0", "127.0.0.1", "未知"):
        if (sys_gw, 80) not in targets:
            targets.append((sys_gw, 80))

    # 并发测试 targets 的 TCP 端口（0.6s 超时）
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(targets), 8)) as executor:
        futures = [executor.submit(tcp_check, host, port, 0.6) for host, port in targets]
        try:
            for fut in concurrent.futures.as_completed(futures, timeout=0.8):
                if fut.result():
                    return True
        except Exception:
            pass

    # 回退尝试 ping 系统网关与认证服务器
    gw_ping_candidates = list(dict.fromkeys([h for h, _ in targets]))
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(gw_ping_candidates), 4)) as executor:
        ping_futures = [executor.submit(ping_check, h, 500) for h in gw_ping_candidates[:4]]
        try:
            for fut in concurrent.futures.as_completed(ping_futures, timeout=0.6):
                if fut.result():
                    return True
        except Exception:
            pass

    return False


def check_internet() -> bool:
    # 并发测试国内主流 DNS 与公网 DNS 53 端口，1 秒内快速判定
    dns_targets = [("223.5.5.5", 53), ("114.114.114.114", 53), ("8.8.8.8", 53)]
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(dns_targets)) as executor:
        futures = [executor.submit(tcp_check, host, port, 0.8) for host, port in dns_targets]
        try:
            for fut in concurrent.futures.as_completed(futures, timeout=1.2):
                if fut.result():
                    return True
        except Exception:
            pass
    return http_check("http://www.baidu.com", timeout=1.5, trust_env=False)


def check_proxy_internet() -> bool:
    return http_check("https://api.telegram.org", timeout=2, trust_env=True)


def is_clash_tun_ip(ip: str) -> bool:
    return ip.startswith("198.18.") or ip.startswith("198.19.")


def is_wifi_link_up() -> bool:
    for name, stats in psutil.net_if_stats().items():
        lowered = name.lower()
        if any(marker in lowered for marker in ("wlan", "wi-fi", "wifi", "wireless")):
            if stats.isup:
                return True
    return is_wifi_connected()


_wlan_cache: tuple[float, str, int] = (0.0, "未知", -1)
_wlan_sig_cache: tuple[bool, str] | None = None
WLAN_CACHE_TTL = 120.0  # 兼容旧配置常量；稳态下由网卡状态签名锁定，零触发 Windows 定位服务


def _get_wlan_signature() -> tuple[bool, str, str]:
    """仅通过内存级 psutil 探测无线网卡活跃状态、接口名与 IPv4（绝对零触发位置服务）。"""
    has_wlan_up = False
    wlan_name = "WLAN"
    wlan_ipv4 = ""
    try:
        stats = psutil.net_if_stats()
        for name, stat in stats.items():
            lowered = name.lower()
            if any(virt in lowered for virt in ("vethernet", "virtual", "vmware", "vbox", "wsl", "loopback", "tap", "tun", "vgate", "tailscale", "wintun", "sing-box", "wireguard", "clash", "zerotier", "openvpn")):
                continue
            if any(marker in lowered for marker in ("wlan", "wi-fi", "wifi", "wireless")):
                if stat.isup:
                    has_wlan_up = True
                    wlan_name = name
                    break
        if has_wlan_up:
            addrs = psutil.net_if_addrs()
            for addr in addrs.get(wlan_name, []):
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    if ip and not ip.startswith("127.") and not ip.startswith("169.254.") and not is_clash_tun_ip(ip):
                        wlan_ipv4 = ip
                        break
    except Exception:
        pass
    return has_wlan_up, wlan_name, wlan_ipv4


def _parse_netsh_wlan_output(output: str) -> tuple[str, int] | None:
    """解析 netsh wlan show interfaces 文本，提取 (ssid, signal_pct)。"""
    ssid = "未知"
    signal = "未知"
    signal_pct = -1
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("SSID") and "BSSID" not in stripped and ":" in stripped:
            ssid = stripped.split(":", 1)[1].strip()
        elif ("信号" in stripped or "Signal" in stripped) and ":" in stripped:
            signal = stripped.split(":", 1)[1].strip()
            try:
                signal_pct = int(signal.replace("%", "").strip())
            except ValueError:
                signal_pct = -1
    if ssid != "未知" and ssid:
        return (f"{ssid} ({signal})" if signal != "未知" else ssid), signal_pct
    return None


def _clean_nla_profile_name(raw_name: str) -> str:
    """去除 Windows NLA 自动附加的数字编号后缀（如 'YADX-STU 6' -> 'YADX-STU'）。"""
    name = raw_name.strip()
    if not name:
        return ""
    base = re.sub(r"\s+\d+$", "", name).strip()
    if base and base != name:
        # 优先核对已知校园/家庭 SSID 列表，确认是 Windows 重名编号才剥离，不误伤原名带数字的 Wi-Fi
        try:
            cfg = get_config_dict()
            known = []
            for key in ("campus_wifi_ssid",):
                v = str(cfg.get(key, "")).strip()
                if v:
                    known.append(v.lower())
            for key in ("campus_wifi_ssids", "trusted_home_ssids"):
                vals = cfg.get(key, [])
                if isinstance(vals, (list, tuple)):
                    known.extend(str(x).strip().lower() for x in vals if x)
            if base.lower() in known or any(k in base.lower() for k in ("yadx", "yau", "-stu", "-tea", "campus")):
                return base
        except Exception:
            pass
    return name


def _fetch_wlan_interfaces(force: bool = False) -> tuple[str, int]:
    """提取当前无线网络名称，基于网卡状态签名长效缓存并优先走无定位 NLA 接口，彻底杜绝定位图标闪烁。"""
    global _wlan_cache, _wlan_sig_cache
    now = time.time()
    cached_at, cached_info, cached_signal = _wlan_cache

    has_wlan_up, wlan_name, wlan_ipv4 = _get_wlan_signature()
    sig = (has_wlan_up, wlan_ipv4)

    # 1. 内核链路优先：无线网卡未连接时直接静默返回，绝不调用子进程
    if not has_wlan_up and not force:
        _wlan_cache = (now, "未连接", -1)
        _wlan_sig_cache = sig
        return "未连接", -1

    # 2. 状态签名未变化且已有有效缓存时，无限期复用缓存（彻底消灭 120s 定时定位闪烁）
    if not force and cached_at > 0.0:
        if _wlan_sig_cache == sig or (now - cached_at < WLAN_CACHE_TTL):
            return cached_info, cached_signal

    # 3. 优先通过 Windows NLA (Get-NetConnectionProfile) 获取当前连接配置名（不触发位置权限服务）
    if sys.platform == "win32":
        try:
            safe_alias = wlan_name.replace("'", "''")
            ps_cmd = (
                f"(Get-NetConnectionProfile -InterfaceAlias '{safe_alias}' "
                f"-ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Name)"
            )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                timeout=4,
                creationflags=0x08000000,
            )
            raw_out = decode_subprocess_output(res.stdout).strip()
            if raw_out:
                # 若测试 mock 返回了 netsh 格式文本，兼容解析
                parsed = _parse_netsh_wlan_output(raw_out)
                if parsed:
                    info, signal_pct = parsed
                    _wlan_cache = (now, info, signal_pct)
                    _wlan_sig_cache = sig
                    return info, signal_pct
                # 正常 NLA 返回单行网络配置名（无定位权限弹窗/图标闪烁）
                first_line = raw_out.splitlines()[0].strip()
                if first_line and "：" not in first_line and ":" not in first_line:
                    clean_name = _clean_nla_profile_name(first_line)
                    info = f"{clean_name} (已连接)"
                    _wlan_cache = (now, info, 100)
                    _wlan_sig_cache = sig
                    return info, 100
        except Exception as err:
            log.debug("NLA 获取网络名称异常: %s", err)

    # 4. 仅当 NLA 未能识别且明确处于 force 强制刷新或无缓存时，才按需回退 netsh（异常同样写入防抖缓存）
    if force or cached_at == 0.0:
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                timeout=5,
                creationflags=0x08000000,
            )
            output = decode_subprocess_output(result.stdout)
            parsed = _parse_netsh_wlan_output(output)
            if parsed:
                info, signal_pct = parsed
                _wlan_cache = (now, info, signal_pct)
                _wlan_sig_cache = sig
                return info, signal_pct
            _wlan_cache = (now, "未连接", -1)
            _wlan_sig_cache = sig
            return "未连接", -1
        except Exception as err:
            log.debug("获取 Wi-Fi 接口信息异常: %s", err)
            _wlan_cache = (now, cached_info if cached_at > 0.0 else "未知", cached_signal)
            _wlan_sig_cache = sig
            return _wlan_cache[1], _wlan_cache[2]

    return cached_info, cached_signal


def get_wifi_signal_percent(force: bool = False) -> int:
    _info, signal_pct = _fetch_wlan_interfaces(force=force)
    return signal_pct


def get_wifi_info(force: bool = False) -> str:
    info, _signal_pct = _fetch_wlan_interfaces(force=force)
    return info


def is_wifi_connected() -> bool:
    for name, stats in psutil.net_if_stats().items():
        lowered = name.lower()
        if any(marker in lowered for marker in ("wlan", "wi-fi", "wifi", "wireless")):
            if stats.isup:
                return True
    return False


def get_saved_wifi_profiles() -> list[str]:
    """获取本机 Windows 系统中已保存的所有无线网络配置文件名称。"""
    profiles: list[str] = []
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "profiles"],
            capture_output=True,
            timeout=5,
            creationflags=0x08000000,
        )
        output = decode_subprocess_output(result.stdout)
        for line in output.splitlines():
            if ":" in line and any(k in line for k in ("All User Profile", "所有用户配置文件", "User Profile")):
                name = line.split(":", 1)[1].strip()
                if name and name not in profiles:
                    profiles.append(name)
    except Exception as err:
        log.debug("获取系统 WiFi 配置文件异常: %s", err)
    return profiles


def reconnect_wifi(ssid: str = "", force: bool = False) -> bool:
    """智能恢复 Wi-Fi 连接。支持指定 SSID，或自动从候选列表与系统已保存配置中寻找最匹配的校园/家庭网络。
    当 force=True 时，即使当前显示有连接和 IP 也会强制向 Windows 发起重新关联与 DHCP 请求。
    """
    # 0. 若未指定 force 且当前网络已经连接且 IP 正常有效，直接判定成功
    if not force:
        current_wifi = get_wifi_info(force=False)
        current_name = current_wifi.split("(", 1)[0].strip() if "(" in current_wifi else current_wifi.strip()
        current_ip = get_local_ip()
        if (
            current_name
            and current_name not in ("未连接", "未知")
            and current_ip
            and current_ip != "未知"
            and not current_ip.startswith("169.254.")
        ):
            if not ssid or ssid.lower() in current_name.lower():
                log.info("当前 Wi-Fi 链路正常活跃且已获取有效 IP: %s (%s)", current_name, current_ip)
                return True

    candidates: list[str] = []
    if ssid:
        candidates.append(ssid.strip())

    # 从用户配置中载入候选（首选单数配置排在列表前）
    try:
        cfg = get_config_dict()
        single_ssid = str(cfg.get("campus_wifi_ssid", "")).strip()
        if single_ssid and single_ssid not in candidates:
            candidates.append(single_ssid)
        configured_ssids = cfg.get("campus_wifi_ssids", [])
        if isinstance(configured_ssids, (list, tuple)):
            for s in configured_ssids:
                s_str = str(s).strip()
                if s_str and s_str not in candidates:
                    candidates.append(s_str)
    except Exception:
        pass

    # 获取当前系统已保存的无线网络配置文件（过滤明显无效项）
    saved_profiles = [p for p in get_saved_wifi_profiles() if "无法使用" not in p]
    # 建立大小写不敏感映射字典: {lower_name: real_profile_name}
    profile_lookup = {p.strip().lower(): p.strip() for p in saved_profiles if p.strip()}

    # 延安大学及主流校园网默认特征候选 (如 YADX-STU, YADX-TEA 等)
    campus_keywords = ("yadx", "yau", "campus", "wlan", "wifi", "stu", "tea")
    for p in saved_profiles:
        p_lower = p.lower()
        if any(k in p_lower for k in campus_keywords):
            if p not in candidates:
                candidates.append(p)

    # 兜底将其他系统已保存网络也加入尝试队列
    for p in saved_profiles:
        if p not in candidates:
            candidates.append(p)

    if not candidates:
        log.warning("未找到可供连接的 Wi-Fi 配置文件")
        return False

    global _wlan_cache, _wlan_sig_cache
    # 强力刷新假死网卡时，若当前仍处于关联状态，先断开假死关联再重新握手
    if force and sys.platform == "win32" and is_wifi_link_up():
        try:
            log.info("检测到假死 Wi-Fi 链路，先执行断开以彻底刷新关联...")
            subprocess.run(
                ["netsh", "wlan", "disconnect"],
                capture_output=True,
                timeout=5,
                creationflags=0x08000000,
            )
            _wlan_cache = (0.0, "未知", -1)
            _wlan_sig_cache = None
            time.sleep(1.0)
        except Exception as err:
            log.debug("断开假死 Wi-Fi 异常: %s", err)

    for raw_target in candidates:
        target = raw_target.strip()
        if not target:
            continue
        # 优先解析为系统精确配置文件名称
        actual_profile = profile_lookup.get(target.lower(), target)

        try:
            log.info("尝试连接 Wi-Fi: %s (配置文件名: %s)", target, actual_profile)
            result = subprocess.run(
                ["netsh", "wlan", "connect", f"name={actual_profile}"],
                capture_output=True,
                timeout=10,
                creationflags=0x08000000,
            )
            output = decode_subprocess_output(result.stdout + result.stderr)
            if result.returncode == 0:
                # 清除旧缓存并循环等待最多 8 秒直到网卡完成握手并获取有效 IP
                _wlan_cache = (0.0, "未知", -1)
                _wlan_sig_cache = None
                for _ in range(16):
                    time.sleep(0.5)
                    ip = get_local_ip()
                    if ip and ip != "未知" and not ip.startswith("169.254."):
                        log.info("Wi-Fi 连接成功并已获得 IP: %s (IP=%s)", actual_profile, ip)
                        return True
                log.warning("Wi-Fi 连接超时未获取到有效 IP，尝试下一个候选配置: %s", actual_profile)
                continue
            log.warning("Wi-Fi 连接反馈: %s", output.strip())
        except Exception as err:
            log.debug("重连 Wi-Fi %s 异常: %s", target, err)

    return False


def get_public_ip() -> str:
    urls = (
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://ipinfo.io/ip",
    )
    for url in urls:
        try:
            resp = requests.get(url, timeout=5, proxies={"http": None, "https": None})
            if resp.status_code == 200:
                return resp.text.strip()
        except Exception:
            continue
    return "未知"


def get_disk_free_gb() -> float:
    return psutil.disk_usage("C:\\").free / (1024**3)


def get_memory_usage() -> str:
    mem = psutil.virtual_memory()
    return f"{mem.percent:.1f}% ({mem.used / 1024**3:.1f}/{mem.total / 1024**3:.1f} GB)"


def scan_available_wifis() -> list[dict[str, str]]:
    """扫描周围可见的 Wi-Fi 网络列表。
    返回列表，每个元素为: {"ssid": str, "signal": str, "auth": str}
    """
    results: list[dict[str, str]] = []
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            capture_output=True,
            timeout=8,
            creationflags=0x08000000,
        )
        output = decode_subprocess_output(result.stdout)
        current: dict[str, str] = {}
        for line in output.splitlines():
            line_str = line.strip()
            if line_str.startswith("SSID") and ":" in line_str and "BSSID" not in line_str:
                if current and current.get("ssid"):
                    results.append(current)
                ssid = line_str.split(":", 1)[1].strip()
                current = {"ssid": ssid, "signal": "未知", "auth": "未知"}
            elif ("信号" in line_str or "Signal" in line_str) and ":" in line_str:
                if current and current.get("signal") == "未知":
                    current["signal"] = line_str.split(":", 1)[1].strip()
            elif ("身份验证" in line_str or "Authentication" in line_str) and ":" in line_str:
                if current and current.get("auth") == "未知":
                    current["auth"] = line_str.split(":", 1)[1].strip()
        if current and current.get("ssid"):
            results.append(current)
    except Exception as err:
        log.debug("Wi-Fi 扫描异常: %s", err)
    return results


def trim_process_memory() -> bool:
    """主动整理并修剪进程的物理内存工作集（Working Set）。
    在后台挂机或窗口最小化到系统托盘时调用，能将常驻内存压制到 10MB~25MB 水平。
    """
    try:
        gc.collect()
        if platform.system() == "Windows":
            import ctypes
            # 调用 Windows 原生 API 释放非活跃物理内存页回操作系统
            ctypes.windll.kernel32.SetProcessWorkingSetSize(
                ctypes.windll.kernel32.GetCurrentProcess(), -1, -1
            )
        return True
    except Exception as err:
        log.debug("内存修剪执行异常: %s", err)
        return False

