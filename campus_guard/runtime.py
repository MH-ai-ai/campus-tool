from __future__ import annotations

import asyncio
import os
import platform
import subprocess
import sys
import threading
import time

from .battery import BatteryMonitor, BatteryTracker
from .config import check_config_reload, encrypt_config_file, get_config_dict, initialize_runtime_config
from .logging_setup import get_logger, setup_logging
from .network import NetworkMonitor
from .paths import APP_DIR
from .system import get_disk_free_gb
from .telegram_bot import TelegramBot


log = get_logger()


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
                next_network_check = now + net_interval
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
        time.sleep(0.5)

    log.warning("监控循环已退出")


def build_autostart_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    script_path = str(APP_DIR / "campus_guard.pyw")
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    return f'"{pythonw}" "{script_path}"'


def setup_autostart() -> None:
    if platform.system() != "Windows":
        return
    try:
        main_tr = build_autostart_command()
        subprocess.run(
            [
                "schtasks",
                "/create",
                "/tn",
                "CampusGuard",
                "/tr",
                main_tr,
                "/sc",
                "onlogon",
                "/rl",
                "highest",
                "/f",
            ],
            capture_output=True,
            text=True,
            creationflags=0x08000000,
        )
        subprocess.run(
            [
                "schtasks",
                "/create",
                "/tn",
                "CampusGuardRecovery",
                "/tr",
                main_tr,
                "/sc",
                "onstart",
                "/delay",
                "0000:30",
                "/f",
            ],
            capture_output=True,
            text=True,
            creationflags=0x08000000,
        )
        log.info("已注册 Windows Task Scheduler 自启动任务")
    except Exception as err:
        log.error("注册 Task Scheduler 失败: %s", err)


def main() -> None:
    setup_logging()
    log.info("=" * 40)
    log.info("Campus Guard 启动")
    log.info("Python: %s", sys.version)
    log.info("应用路径: %s", APP_DIR)

    initialize_runtime_config()
    encrypt_config_file()
    initialize_runtime_config()

    tracker = BatteryTracker()
    tg_bot = TelegramBot(None, None, tracker)
    battery = BatteryMonitor(tg_bot.send_notification, tracker)
    network = NetworkMonitor(tg_bot.send_notification, tracker)
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

    from PyQt6.QtWidgets import QApplication

    from .ui import MainWindow

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow(battery, network, tg_bot)
    window.show()
    log.info("PyQt6 主窗口已显示")
    sys.exit(app.exec())
