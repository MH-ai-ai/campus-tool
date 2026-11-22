from __future__ import annotations

import asyncio
import os
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path

from .battery import BatteryMonitor, BatteryTracker
from .config import check_config_reload, encrypt_config_file, get_config_dict, initialize_runtime_config
from .logging_setup import get_logger, setup_logging
from .network import NetworkMonitor
from .paths import APP_DIR
from .system import get_disk_free_gb
from .telegram_bot import TelegramBot


log = get_logger()

# 开机自启项名称：改名后使用 AnLan；旧版（CampusGuard）名称仅用于迁移清理
AUTOSTART_NAME = "AnLan"
LEGACY_AUTOSTART_NAME = "CampusGuard"


def check_disk_space(notify_callback) -> None:
    try:
        free_gb = get_disk_free_gb()
        log.debug("磁盘剩余空间: %.1f GB", free_gb)
        if free_gb < 2:
            msg = f"⚠️ 磁盘空间不足！C盘剩余 {free_gb:.1f} GB"
            log.warning(msg)
            notify_callback(msg)
    except Exception as err:
        log.error("磁盘空间检查失败: %s", err)


def monitor_loop(
    battery: BatteryMonitor,
    network: NetworkMonitor,
    config_check_interval: int = 60,
) -> None:
    cfg = get_config_dict()
    bat_interval = int(cfg.get("check_interval_seconds", 5))
    net_interval = int(cfg.get("network_check_interval_seconds", 2))
    disk_interval = 600
    next_battery_check = 0.0
    next_network_check = 0.0
    next_config_check = time.monotonic() + config_check_interval
    next_disk_check = time.monotonic() + disk_interval

    log.info(
        "监控循环启动: 电池检查=%ds, 网络检查=%ds, 磁盘检查=%ds",
        bat_interval,
        net_interval,
        disk_interval,
    )

    while battery.running and network.running:
        now = time.monotonic()
        try:
            if now >= next_battery_check:
                battery.check()
                next_battery_check = now + bat_interval
            if now >= next_network_check:
                network.check()
                current_net_interval = network.effective_check_interval(net_interval)
                next_network_check = now + current_net_interval
            if now >= next_config_check:
                check_config_reload()
                cfg = get_config_dict()
                bat_interval = int(cfg.get("check_interval_seconds", bat_interval))
                net_interval = int(cfg.get("network_check_interval_seconds", net_interval))
                next_config_check = now + config_check_interval
            if now >= next_disk_check:
                check_disk_space(battery.notify)
                next_disk_check = now + disk_interval
        except Exception as err:
            log.error("监控循环异常: %s", err, exc_info=True)

        # 动态深度睡眠：根据下一次最近任务的剩余时间自适应休眠，降低CPU唤醒与能耗
        next_deadline = min(next_battery_check, next_network_check, next_config_check, next_disk_check)
        sleep_secs = max(0.2, min(next_deadline - time.monotonic(), 5.0))
        time.sleep(sleep_secs)

    log.warning("监控循环已退出")


def unblock_motw_files(base_dir: Path | None = None) -> int:
    """在 Windows 下自动解除应用目录内二进制文件的 Zone.Identifier (MOTW) 锁定标记。
    防止从浏览器/GitHub 下载解压后因缺少解除锁定而触发 .NET CLR CAS 加载 Python.Runtime.dll 失败。
    """
    if sys.platform != "win32":
        return 0

    root = Path(base_dir) if base_dir is not None else Path(APP_DIR)
    if not root.exists():
        return 0

    target_suffixes = {".dll", ".exe", ".pyd"}
    unblocked_count = 0

    scan_roots: list[Path] = [root]
    internal_dir = root / "_internal"
    if internal_dir.is_dir():
        for dirpath, _dirnames, filenames in os.walk(internal_dir):
            dp = Path(dirpath)
            for fname in filenames:
                if Path(fname).suffix.lower() in target_suffixes:
                    ads_path = f"{dp / fname}:Zone.Identifier"
                    try:
                        os.remove(ads_path)
                        unblocked_count += 1
                    except OSError:
                        pass

    for top_dir in scan_roots:
        try:
            for item in top_dir.iterdir():
                if item.is_file() and item.suffix.lower() in target_suffixes:
                    ads_path = f"{item}:Zone.Identifier"
                    try:
                        os.remove(ads_path)
                        unblocked_count += 1
                    except OSError:
                        pass
        except OSError:
            pass

    if unblocked_count > 0:
        log.info("已自动解除 %d 个二进制文件的 Windows 下载安全锁定标记 (Zone.Identifier)", unblocked_count)
    return unblocked_count


def build_autostart_command(minimized: bool = False) -> str:
    if getattr(sys, "frozen", False):
        cmd = f'"{sys.executable}"'
    else:
        script_path = str(APP_DIR / "campus_guard.pyw")
        import ntpath
        p_module = ntpath if ("\\" in sys.executable or os.name == "nt") else os.path
        pythonw = p_module.join(p_module.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        cmd = f'"{pythonw}" "{script_path}"'

    if minimized:
        return f"{cmd} --minimized"
    return cmd


def _remove_legacy_autostart() -> None:
    """清理改名前（CampusGuard）遗留的自启项，避免开机重复拉起两个实例。"""
    if platform.system() != "Windows":
        return
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, LEGACY_AUTOSTART_NAME)
            log.info("已迁移并清理旧版开机自启项: %s", LEGACY_AUTOSTART_NAME)
        except FileNotFoundError:
            pass
        finally:
            winreg.CloseKey(key)
    except Exception:
        pass
    try:
        subprocess.run(
            ["schtasks", "/delete", "/tn", LEGACY_AUTOSTART_NAME, "/f"],
            capture_output=True,
            creationflags=0x08000000,
        )
    except Exception:
        pass


def setup_autostart() -> None:
    if platform.system() != "Windows":
        return
    cfg = get_config_dict()
    minimized = bool(cfg.get("start_minimized_on_boot", True))
    cmd = build_autostart_command(minimized=minimized)
    # 1. 优先使用 Windows 官方推荐 HKCU Run 注册表（100% 免管理员提权，开机登录桌面可靠启动托盘）
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        log.info("已成功注册 Windows 开机自启动 (HKCU Run): %s", cmd)
    except Exception as err:
        log.error("写入注册表自启动项失败: %s", err)

    # 2. 尝试配置用户级计划任务作为备用容灾（不使用 /rl highest 避免提权拦截）
    try:
        subprocess.run(
            [
                "schtasks",
                "/create",
                "/tn",
                AUTOSTART_NAME,
                "/tr",
                cmd,
                "/sc",
                "onlogon",
                "/f",
            ],
            capture_output=True,
            creationflags=0x08000000,
        )
    except Exception:
        pass

    # 3. 迁移：清理改名前遗留的旧自启项
    _remove_legacy_autostart()


def remove_autostart() -> None:
    if platform.system() != "Windows":
        return
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, AUTOSTART_NAME)
        winreg.CloseKey(key)
        log.info("已注销 Windows 自启动项")
    except Exception:
        pass
    try:
        subprocess.run(
            ["schtasks", "/delete", "/tn", AUTOSTART_NAME, "/f"],
            capture_output=True,
            creationflags=0x08000000,
        )
    except Exception:
        pass
    _remove_legacy_autostart()


def _run_main() -> None:
    setup_logging()
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MH.AnLan.Desktop.2.2")
        except Exception:
            pass

    log.info("=" * 40)
    log.info("安澜 启动")
    log.info("Python: %s", sys.version)
    log.info("应用路径: %s", APP_DIR)

    # 启动早期先解除 Windows 下载锁定流（Zone.Identifier），确保后续 pythonnet/WebView2 加载顺畅
    unblock_motw_files()

    initialize_runtime_config()
    encrypt_config_file()
    initialize_runtime_config()

    from .notifier import UnifiedNotifier

    tracker = BatteryTracker()
    tg_bot = TelegramBot(None, None, tracker)
    notifier = UnifiedNotifier(tg_bot)
    battery = BatteryMonitor(notifier.notify, tracker)
    network = NetworkMonitor(notifier.notify, tracker)
    tg_bot.battery = battery
    tg_bot.network = network

    if get_config_dict().get("autostart", True):
        setup_autostart()

    monitor_thread = threading.Thread(target=monitor_loop, args=(battery, network), daemon=True)
    monitor_thread.start()
    log.info("监控线程已启动")

    def run_bot() -> None:
        asyncio.run(tg_bot.start())

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    log.info("Telegram Bot 线程已启动")

    start_minimized = "--minimized" in sys.argv[1:]
    if start_minimized:
        log.info("检测到 --minimized 参数，以系统托盘静默模式启动")

    from .ui import launch_gui

    log.info("启动现代控制中心 Webview 窗口与托盘守护")
    launch_gui(battery, network, tg_bot, start_minimized=start_minimized)


def main() -> None:
    try:
        _run_main()
    except Exception as err:
        import traceback

        tb = traceback.format_exc()
        try:
            log.critical("安澜 启动异常: %s\n%s", err, tb)
        except Exception:
            pass
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"安澜 启动异常:\n{err}\n\n详细调用栈:\n{tb[:800]}",
                    "安澜 错误拦截",
                    0x10,
                )
            except Exception:
                pass
        raise

