from __future__ import annotations

import socket
import subprocess
import uuid

import psutil
import requests

from .config import get_config_dict
from .logging_setup import get_logger


log = get_logger()


def decode_subprocess_output(raw: bytes) -> str:
    for enc in ("gbk", "cp936", "utf-8"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def get_local_ip() -> str:
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
                ip = stripped.split(":", 1)[1].strip()
                if ip and ip != "127.0.0.1" and not ip.startswith("198.18."):
                    return ip

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        if ip.startswith("198.18."):
            return f"{ip} (Clash TUN)"
        return ip
    except Exception:
        return "未知"


def get_local_mac() -> str:
    mac = uuid.getnode()
    return "".join(f"{(mac >> i) & 0xFF:02x}" for i in range(40, -1, -8))


def tcp_check(host: str, port: int, timeout: int = 3) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
        return True
    except Exception:
        return False


def http_check(url: str, timeout: int = 3) -> bool:
    try:
        resp = requests.head(url, timeout=timeout, proxies={"http": None, "https": None})
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
    return http_check("http://www.baidu.com")


def get_wifi_signal_percent() -> int:
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
            if "信号" in stripped or "Signal" in stripped:
                value = stripped.split(":", 1)[1].strip().replace("%", "")
                return int(value)
    except Exception:
        return -1
    return -1


def get_wifi_info() -> str:
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            timeout=5,
            creationflags=0x08000000,
        )
        output = decode_subprocess_output(result.stdout)
        ssid = "未知"
        signal = "未知"
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("SSID") and "BSSID" not in stripped:
                ssid = stripped.split(":", 1)[1].strip()
            elif "信号" in stripped or "Signal" in stripped:
                signal = stripped.split(":", 1)[1].strip()
        return f"{ssid} ({signal})"
    except Exception as err:
        log.error("获取 WiFi 信息失败: %s", err)
        return "未知"


def is_wifi_connected() -> bool:
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            timeout=5,
            creationflags=0x08000000,
        )
        output = decode_subprocess_output(result.stdout)
        return "已连接" in output or "connected" in output.lower()
    except Exception:
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
