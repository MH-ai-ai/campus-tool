from __future__ import annotations

import socket
import subprocess
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
            if any(virt in lower_name for virt in ("vethernet", "virtual", "vmware", "vbox", "wsl", "loopback", "tap", "tun")):
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


def get_local_mac() -> str:
    _name, _ip, mac = get_primary_interface_info()
    if mac and len(mac) == 12:
        return mac
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


def check_campus_gateway() -> bool:
    gateway = get_config_dict().get("campus_gateway", "10.212.0.1")
    return tcp_check(str(gateway), 80, timeout=3)


def check_internet() -> bool:
    if tcp_check("8.8.8.8", 53):
        return True
    if tcp_check("114.114.114.114", 53):
        return True
    return http_check("http://www.baidu.com", trust_env=False)


def check_proxy_internet() -> bool:
    return http_check("https://api.telegram.org", timeout=3, trust_env=True)


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
WLAN_CACHE_TTL = 120.0  # 平稳状态下 120 秒长效缓存，彻底杜绝高频调用触发 Windows 定位服务


def _fetch_wlan_interfaces(force: bool = False) -> tuple[str, int]:
    """单次提取 WLAN 接口信息并长效缓存，避免高频触发 Windows 位置服务扫描。"""
    global _wlan_cache
    now = time.time()
    cached_at, cached_info, cached_signal = _wlan_cache
    if not force and (now - cached_at < WLAN_CACHE_TTL):
        return cached_info, cached_signal

    # 内核链路优先：如果无线网卡未连接，直接静默返回，无需调用 netsh
    has_wlan_up = False
    for name, stat in psutil.net_if_stats().items():
        lowered = name.lower()
        if any(marker in lowered for marker in ("wlan", "wi-fi", "wifi", "wireless")):
            if stat.isup:
                has_wlan_up = True
                break
    if not has_wlan_up and not force:
        _wlan_cache = (now, "未连接", -1)
        return "未连接", -1

    ssid = "未知"
    signal = "未知"
    signal_pct = -1
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            timeout=5,
            creationflags=0x08000000,
        )
        output = decode_subprocess_output(result.stdout)
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("SSID") and "BSSID" not in stripped:
                ssid = stripped.split(":", 1)[1].strip()
            elif "信号" in stripped or "Signal" in stripped:
                signal = stripped.split(":", 1)[1].strip()
                try:
                    signal_pct = int(signal.replace("%", "").strip())
                except ValueError:
                    signal_pct = -1
        info = f"{ssid} ({signal})" if ssid != "未知" else "未连接"
        _wlan_cache = (now, info, signal_pct)
        return info, signal_pct
    except Exception as err:
        log.debug("获取 Wi-Fi 接口信息异常: %s", err)
        return "未知", -1


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


def reconnect_wifi(ssid: str) -> bool:
    if not ssid:
        return False
    try:
        log.info("尝试重连 WiFi: %s", ssid)
        subprocess.run(
            ["netsh", "wlan", "disconnect"],
            capture_output=True,
            timeout=10,
            creationflags=0x08000000,
        )
        result = subprocess.run(
            ["netsh", "wlan", "connect", f"name={ssid}"],
            capture_output=True,
            timeout=15,
            creationflags=0x08000000,
        )
        output = decode_subprocess_output(result.stdout + result.stderr)
        if result.returncode == 0:
            log.info("WiFi 重连成功: %s", ssid)
            return True
        log.warning("WiFi 重连失败: %s", output.strip())
        return False
    except Exception as err:
        log.error("WiFi 重连异常: %s", err)
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

