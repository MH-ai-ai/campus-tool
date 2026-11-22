from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import psutil

from .config import get_config_dict
from .logging_setup import get_logger
from .system import tcp_check

log = get_logger()

DEFAULT_PROXY_SERVER = "127.0.0.1:7897"
DEFAULT_PROXY_BYPASS = (
    "localhost;127.*;192.168.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;"
    "172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;"
    "172.28.*;172.29.*;172.30.*;172.31.*;*.edu.cn;*.local;<local>"
)
KNOWN_PROXY_EXECUTABLES = (
    "clash-verge.exe",
    "Clash Verge.exe",
    "clash-nyanpasu.exe",
    "mihomo-party.exe",
    "FlClash.exe",
    "Clash for Windows.exe",
    "v2rayN.exe",
)
KNOWN_CORE_EXECUTABLES = (
    "verge-mihomo.exe",
    "mihomo.exe",
    "clash.exe",
)

_INTERNET_SETTINGS_KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
_INTERNET_OPTION_REFRESH = 37
_INTERNET_OPTION_SETTINGS_CHANGED = 39
_DETACHED_PROCESS = 0x00000008
_CREATE_NEW_PROCESS_GROUP = 0x00000200

_launch_lock = threading.Lock()
_last_proxy_status: dict[str, Any] = {
    "last_message": "尚未触发代理联动",
    "last_updated": 0.0,
}


def _normalize_proxy_server(proxy_server: str) -> str:
    """规范化代理服务器地址，去除协议前缀并保留 host:port。"""
    raw = str(proxy_server or "").strip()
    if not raw:
        return DEFAULT_PROXY_SERVER
    raw = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", raw)
    raw = raw.split("/", 1)[0].strip()
    return raw or DEFAULT_PROXY_SERVER


def parse_proxy_host_port(proxy_server: str) -> tuple[str, int]:
    """解析代理地址字符串（如 '127.0.0.1:7897' 或 'http://127.0.0.1:7897'），失败回退默认。"""
    cleaned = _normalize_proxy_server(proxy_server)
    if not cleaned:
        return ("127.0.0.1", 7897)

    # 支持多协议格式（如 http=127.0.0.1:7897;https=127.0.0.1:7897）取第一段有效值
    if "=" in cleaned and ";" in cleaned:
        first_part = cleaned.split(";", 1)[0]
        if "=" in first_part:
            cleaned = first_part.split("=", 1)[1].strip()
    elif "=" in cleaned:
        cleaned = cleaned.split("=", 1)[1].strip()

    if ":" not in cleaned:
        return (cleaned, 7897)

    host, port_str = cleaned.rsplit(":", 1)
    host = host.strip().strip("[]") or "127.0.0.1"
    try:
        port = int(port_str.strip())
        if 1 <= port <= 65535:
            return (host, port)
    except ValueError:
        pass
    return ("127.0.0.1", 7897)


def get_windows_system_proxy() -> dict[str, Any]:
    """读取 Windows 当前用户的系统代理设置；非 Windows 返回安全默认值。"""
    result: dict[str, Any] = {
        "enabled": False,
        "proxy_server": "",
        "proxy_override": "",
    }
    if platform.system() != "Windows":
        return result

    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _INTERNET_SETTINGS_KEY, 0, winreg.KEY_READ) as key:
            try:
                val, _ = winreg.QueryValueEx(key, "ProxyEnable")
                result["enabled"] = bool(int(val))
            except OSError:
                pass
            try:
                val, _ = winreg.QueryValueEx(key, "ProxyServer")
                result["proxy_server"] = str(val or "").strip()
            except OSError:
                pass
            try:
                val, _ = winreg.QueryValueEx(key, "ProxyOverride")
                result["proxy_override"] = str(val or "").strip()
            except OSError:
                pass
    except Exception as err:
        log.debug("读取 Windows 系统代理失败: %s", err)
    return result


def _merge_proxy_bypass(existing: str, custom: str) -> str:
    """合并代理绕过地址列表，确保包含校园网常见内网网段与 *.edu.cn。"""
    if custom and custom.strip():
        return custom.strip()
    if not existing or not existing.strip():
        return DEFAULT_PROXY_BYPASS

    existing_parts = [p.strip() for p in existing.split(";") if p.strip()]
    seen = {p.lower() for p in existing_parts}
    for item in DEFAULT_PROXY_BYPASS.split(";"):
        cleaned = item.strip()
        if cleaned and cleaned.lower() not in seen:
            existing_parts.append(cleaned)
            seen.add(cleaned.lower())
    return ";".join(existing_parts)


def set_windows_system_proxy(
    enable: bool,
    proxy_server: str = "",
    proxy_override: str = "",
) -> tuple[bool, str]:
    """设置 Windows 系统代理并向 WinINet 广播设置变更使其立即生效。"""
    if platform.system() != "Windows":
        return (False, "当前非 Windows 系统，不支持设置 Windows 系统代理")

    normalized_server = _normalize_proxy_server(proxy_server)
    current = get_windows_system_proxy()
    merged_override = _merge_proxy_bypass(current.get("proxy_override", ""), proxy_override)

    try:
        import ctypes
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _INTERNET_SETTINGS_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1 if enable else 0)
            if enable:
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, normalized_server)
                winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, merged_override)

        try:
            wininet = ctypes.windll.wininet
            wininet.InternetSetOptionW(0, _INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
            wininet.InternetSetOptionW(0, _INTERNET_OPTION_REFRESH, 0, 0)
        except Exception as notify_err:
            log.debug("WinINet 刷新系统代理广播异常: %s", notify_err)

        if enable:
            return (True, f"已开启 Windows 系统代理 ({normalized_server})")
        return (True, "已关闭 Windows 系统代理")
    except Exception as err:
        log.error("设置 Windows 系统代理失败: %s", err)
        return (False, f"设置 Windows 系统代理失败: {err}")


def _detect_clash_verge_port() -> int | None:
    """只读检测 Clash Verge Rev 配置文件中的混合端口。"""
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return None
    verge_dir = Path(appdata) / "io.github.clash-verge-rev.clash-verge-rev"
    for filename, pattern in (
        ("verge.yaml", r"(?m)^\s*verge_mixed_port\s*:\s*(\d+)"),
        ("clash-verge.yaml", r"(?m)^\s*mixed-port\s*:\s*(\d+)"),
        ("config.yaml", r"(?m)^\s*mixed-port\s*:\s*(\d+)"),
    ):
        cfg_file = verge_dir / filename
        if not cfg_file.exists():
            continue
        try:
            content = cfg_file.read_text(encoding="utf-8", errors="ignore")
            match = re.search(pattern, content)
            if match:
                port = int(match.group(1))
                if 1 <= port <= 65535:
                    return port
        except OSError:
            continue
    return None


def is_proxy_process_running(exe_path: str = "") -> bool:
    """检查指定路径代理程序或常见 Clash/代理进程是否正在运行。"""
    target_path_norm = os.path.normcase(os.path.abspath(exe_path.strip())) if exe_path and exe_path.strip() else ""
    target_name = os.path.basename(target_path_norm).lower() if target_path_norm else ""
    known_names = {n.lower() for n in (KNOWN_PROXY_EXECUTABLES + KNOWN_CORE_EXECUTABLES)}

    try:
        for proc in psutil.process_iter(["name", "exe"]):
            try:
                p_name = str(proc.info.get("name") or "").strip().lower()
                p_exe = str(proc.info.get("exe") or "").strip()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

            if target_path_norm:
                if p_exe and os.path.normcase(os.path.abspath(p_exe)) == target_path_norm:
                    return True
                if target_name and p_name == target_name:
                    return True
            else:
                if p_name in known_names:
                    return True
    except Exception as err:
        log.debug("检测代理进程异常: %s", err)
    return False


def _scan_uninstall_registry_for_proxy() -> list[tuple[str, str]]:
    """只读扫描 Windows 卸载表中的 Clash 类客户端安装位置。"""
    if platform.system() != "Windows":
        return []
    candidates: list[tuple[str, str]] = []
    try:
        import winreg

        roots = (
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        )
        keywords = ("clash", "verge", "nyanpasu", "mihomo", "flclash", "v2rayn")
        for hive, subkey in roots:
            try:
                with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as root_key:
                    count, _, _ = winreg.QueryInfoKey(root_key)
                    for idx in range(count):
                        try:
                            name = winreg.EnumKey(root_key, idx)
                            with winreg.OpenKey(root_key, name, 0, winreg.KEY_READ) as item_key:
                                display_name = ""
                                install_loc = ""
                                display_icon = ""
                                try:
                                    display_name = str(winreg.QueryValueEx(item_key, "DisplayName")[0] or "")
                                except OSError:
                                    pass
                                try:
                                    install_loc = str(winreg.QueryValueEx(item_key, "InstallLocation")[0] or "")
                                except OSError:
                                    pass
                                try:
                                    display_icon = str(winreg.QueryValueEx(item_key, "DisplayIcon")[0] or "")
                                except OSError:
                                    pass

                                combined = f"{name} {display_name}".lower()
                                if not any(k in combined for k in keywords):
                                    continue

                                for raw_icon in (display_icon,):
                                    cleaned = raw_icon.split(",", 1)[0].strip().strip('"')
                                    if cleaned.lower().endswith(".exe") and os.path.isfile(cleaned):
                                        candidates.append((display_name or os.path.basename(cleaned), cleaned))
                                if install_loc and os.path.isdir(install_loc):
                                    for exe_name in KNOWN_PROXY_EXECUTABLES:
                                        cand = os.path.join(install_loc, exe_name)
                                        if os.path.isfile(cand):
                                            candidates.append((display_name or exe_name, cand))
                        except OSError:
                            continue
            except OSError:
                continue
    except Exception as err:
        log.debug("扫描卸载注册表异常: %s", err)
    return candidates


def _scan_common_install_dirs_for_proxy() -> list[tuple[str, str]]:
    """只读扫描常见安装目录中的 Clash 客户端可执行文件。"""
    search_dirs: list[Path] = []
    env_dirs = [
        os.environ.get("ProgramFiles", ""),
        os.environ.get("ProgramFiles(x86)", ""),
        os.environ.get("LOCALAPPDATA", ""),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
        r"D:\Program Files",
    ]
    folder_names = (
        "Clash Verge",
        "Clash Verge Rev",
        "clash-verge",
        "Clash Nyanpasu",
        "Mihomo Party",
        "FlClash",
        "Clash for Windows",
        "v2rayN",
    )
    for base in env_dirs:
        if not base or not os.path.isdir(base):
            continue
        base_path = Path(base)
        for folder in folder_names:
            candidate_dir = base_path / folder
            if candidate_dir.is_dir():
                search_dirs.append(candidate_dir)

    found: list[tuple[str, str]] = []
    for folder_path in search_dirs:
        for exe_name in KNOWN_PROXY_EXECUTABLES:
            exe_file = folder_path / exe_name
            if exe_file.is_file():
                found.append((exe_file.stem, str(exe_file)))
    return found


def detect_clash_client() -> dict[str, Any]:
    """自动探测本机 Clash 等代理客户端可执行路径与推荐端口。"""
    sys_proxy = get_windows_system_proxy()
    verge_port = _detect_clash_verge_port()

    recommended_server = DEFAULT_PROXY_SERVER
    if verge_port:
        recommended_server = f"127.0.0.1:{verge_port}"
    elif sys_proxy.get("proxy_server"):
        recommended_server = _normalize_proxy_server(sys_proxy["proxy_server"])

    gui_priority = {name.lower(): idx for idx, name in enumerate(KNOWN_PROXY_EXECUTABLES)}
    core_priority = {name.lower(): idx + 100 for idx, name in enumerate(KNOWN_CORE_EXECUTABLES)}

    running_matches: list[tuple[int, str, str]] = []
    any_core_running = False
    try:
        for proc in psutil.process_iter(["name", "exe"]):
            try:
                p_name = str(proc.info.get("name") or "").strip()
                p_exe = str(proc.info.get("exe") or "").strip()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            low = p_name.lower()
            if low in gui_priority and p_exe:
                running_matches.append((gui_priority[low], p_name, p_exe))
            elif low in core_priority:
                any_core_running = True
                if p_exe:
                    running_matches.append((core_priority[low], p_name, p_exe))
    except Exception as err:
        log.debug("探测运行中代理客户端异常: %s", err)

    if running_matches:
        running_matches.sort(key=lambda item: item[0])
        prio, name, exe_path = running_matches[0]
        # 若仅捕获到核心进程，优先查看同目录下是否存在 Clash Verge 等 GUI 主程序
        if prio >= 100:
            exe_dir = Path(exe_path).parent
            for gui_name in KNOWN_PROXY_EXECUTABLES:
                gui_candidate = exe_dir / gui_name
                if gui_candidate.is_file():
                    name = gui_name
                    exe_path = str(gui_candidate)
                    break
        return {
            "found": True,
            "name": name,
            "exe_path": exe_path,
            "proxy_server": recommended_server,
            "running": True,
            "system_proxy_enabled": bool(sys_proxy.get("enabled", False)),
        }

    # 未在运行则依次扫描常见安装目录与卸载注册表
    for name, exe_path in _scan_common_install_dirs_for_proxy() + _scan_uninstall_registry_for_proxy():
        if os.path.isfile(exe_path):
            return {
                "found": True,
                "name": name,
                "exe_path": exe_path,
                "proxy_server": recommended_server,
                "running": any_core_running,
                "system_proxy_enabled": bool(sys_proxy.get("enabled", False)),
            }

    return {
        "found": False,
        "name": "",
        "exe_path": "",
        "proxy_server": recommended_server,
        "running": any_core_running,
        "system_proxy_enabled": bool(sys_proxy.get("enabled", False)),
    }


def wait_for_proxy_port(
    proxy_server: str,
    timeout_seconds: float = 15.0,
    poll_interval: float = 0.5,
) -> bool:
    """轮询等待本地代理端口开始监听，超时返回 False。"""
    host, port = parse_proxy_host_port(proxy_server)
    deadline = time.monotonic() + max(0.5, float(timeout_seconds))
    while True:
        if tcp_check(host, port, timeout=1):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(max(0.1, float(poll_interval)))


def launch_proxy_and_enable(
    cfg: dict[str, Any] | None = None,
    force: bool = False,
) -> tuple[bool, str]:
    """在确认校园网在线后，按配置自动启动代理客户端并开启 Windows 系统代理。"""
    with _launch_lock:
        active_cfg = cfg if cfg is not None else get_config_dict()
        if not force and not bool(active_cfg.get("auto_start_proxy", False)):
            return (False, "未启用连网后自动启动代理")

        exe_path = str(active_cfg.get("proxy_exe_path", "") or "").strip()
        proxy_server = _normalize_proxy_server(str(active_cfg.get("proxy_server", DEFAULT_PROXY_SERVER) or ""))
        auto_enable_sys = bool(active_cfg.get("auto_enable_system_proxy", True))
        proxy_bypass = str(active_cfg.get("proxy_bypass", "") or "").strip()
        wait_timeout = max(2, int(active_cfg.get("proxy_wait_timeout_seconds", 15) or 15))

        if not exe_path:
            detected = detect_clash_client()
            if detected.get("found") and detected.get("exe_path"):
                exe_path = str(detected["exe_path"])
                if not str(active_cfg.get("proxy_server", "") or "").strip() and detected.get("proxy_server"):
                    proxy_server = _normalize_proxy_server(str(detected["proxy_server"]))

        launched_now = False
        already_running = is_proxy_process_running(exe_path)
        host, port = parse_proxy_host_port(proxy_server)
        port_listening = tcp_check(host, port, timeout=1)

        if not already_running and not port_listening:
            if not exe_path or not os.path.isfile(exe_path):
                msg = "未找到可用的代理客户端可执行文件，请在设置中指定或点击探测"
                _record_status(msg)
                return (False, msg)

            try:
                creationflags = (_DETACHED_PROCESS | _CREATE_NEW_PROCESS_GROUP) if platform.system() == "Windows" else 0
                subprocess.Popen(
                    [exe_path],
                    cwd=str(Path(exe_path).parent),
                    creationflags=creationflags,
                )
                launched_now = True
                log.info("已自动拉起代理客户端: %s", exe_path)
            except Exception as err:
                msg = f"拉起代理客户端失败: {err}"
                log.error(msg)
                _record_status(msg)
                return (False, msg)

        # 等待代理监听端口就绪
        if not port_listening:
            if not wait_for_proxy_port(proxy_server, timeout_seconds=float(wait_timeout), poll_interval=0.5):
                msg = f"代理已拉起但端口 {proxy_server} 在 {wait_timeout}s 内未就绪"
                log.warning(msg)
                _record_status(msg)
                return (False, msg)

        if auto_enable_sys and platform.system() == "Windows":
            current = get_windows_system_proxy()
            current_srv = _normalize_proxy_server(current.get("proxy_server", "")) if current.get("proxy_server") else ""
            if current.get("enabled") and current_srv == proxy_server:
                action = "代理已启动且" if launched_now else "代理运行中且"
                msg = f"{action}系统代理已处于开启状态 ({proxy_server})"
                log.info(msg)
                _record_status(msg)
                return (True, msg)

            ok, sys_msg = set_windows_system_proxy(True, proxy_server, proxy_bypass)
            if not ok:
                _record_status(sys_msg)
                return (False, sys_msg)
            prefix = "已启动代理并" if launched_now else "代理端口就绪，"
            msg = f"{prefix}{sys_msg}"
            log.info(msg)
            _record_status(msg)
            return (True, msg)

        msg = (
            f"已成功启动代理客户端且端口 {proxy_server} 已就绪"
            if launched_now
            else f"代理客户端运行中且端口 {proxy_server} 已就绪"
        )
        log.info(msg)
        _record_status(msg)
        return (True, msg)


def _record_status(message: str) -> None:
    _last_proxy_status["last_message"] = message
    _last_proxy_status["last_updated"] = time.time()


def get_proxy_runtime_status(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """返回供前端展示的代理联动实时状态。"""
    active_cfg = cfg if cfg is not None else get_config_dict()
    exe_path = str(active_cfg.get("proxy_exe_path", "") or "").strip()
    proxy_server = _normalize_proxy_server(str(active_cfg.get("proxy_server", DEFAULT_PROXY_SERVER) or ""))
    sys_proxy = get_windows_system_proxy()
    return {
        "enabled": bool(active_cfg.get("auto_start_proxy", False)),
        "process_running": is_proxy_process_running(exe_path),
        "system_proxy_enabled": bool(sys_proxy.get("enabled", False)),
        "proxy_server": proxy_server,
        "last_message": str(_last_proxy_status.get("last_message", "")),
    }
