from __future__ import annotations

import subprocess
import time
from datetime import datetime, timedelta
from typing import Callable

import psutil

from .config import get_config_dict
from .logging_setup import get_logger


NotifyCallback = Callable[[str], None]
log = get_logger()


class BatteryTracker:
    def __init__(self) -> None:
        self._daily_stats: dict[str, dict] = {}
        self._discharge_start_time: float | None = None
        self._discharge_start_percent: int | None = None

    def _ensure_today(self) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self._daily_stats:
            self._daily_stats[today] = {
                "power_outage_count": 0,
                "battery_time_secs": 0,
                "min_battery": 100,
                "max_battery": 0,
                "network_reconnect_count": 0,
                "sample_count": 0,
                "sample_sum": 0,
            }
        return self._daily_stats[today]

    def record_outage(self) -> None:
        self._ensure_today()["power_outage_count"] += 1

    def record_reconnect(self) -> None:
        self._ensure_today()["network_reconnect_count"] += 1

    def update_battery_level(self, percent: int, plugged: bool) -> None:
        stats = self._ensure_today()
        stats["min_battery"] = min(stats["min_battery"], percent)
        stats["max_battery"] = max(stats["max_battery"], percent)
        stats["sample_count"] += 1
        stats["sample_sum"] += percent

        if not plugged and self._discharge_start_time is None:
            self._discharge_start_time = time.time()
            self._discharge_start_percent = percent
        elif plugged and self._discharge_start_time is not None:
            stats["battery_time_secs"] += int(time.time() - self._discharge_start_time)
            self._discharge_start_time = None
            self._discharge_start_percent = None

    def get_today_stats(self) -> dict:
        return self._ensure_today()

    def get_weekly_stats(self) -> dict:
        cutoff = datetime.now() - timedelta(days=7)
        total = {
            "power_outage_count": 0,
            "battery_time_secs": 0,
            "network_reconnect_count": 0,
        }
        for day, stats in self._daily_stats.items():
            try:
                if datetime.strptime(day, "%Y-%m-%d") < cutoff:
                    continue
            except ValueError:
                continue
            total["power_outage_count"] += stats.get("power_outage_count", 0)
            total["battery_time_secs"] += stats.get("battery_time_secs", 0)
            total["network_reconnect_count"] += stats.get("network_reconnect_count", 0)
        return total

    def weekly_report(self) -> str:
        stats = self.get_weekly_stats()
        hours = stats["battery_time_secs"] // 3600
        minutes = (stats["battery_time_secs"] % 3600) // 60
        return (
            "📈 Campus Guard 周报\n"
            f"{'─' * 24}\n"
            f"⚡ 断电次数: {stats['power_outage_count']}\n"
            f"🔋 电池供电时长: {hours}小时{minutes}分钟\n"
            f"🔄 网络重连次数: {stats['network_reconnect_count']}"
        )

    def daily_report(self) -> str:
        stats = self.get_today_stats()
        avg = 0
        if stats["sample_count"]:
            avg = stats["sample_sum"] / stats["sample_count"]
        hours = stats["battery_time_secs"] // 3600
        minutes = (stats["battery_time_secs"] % 3600) // 60
        return (
            "📋 Campus Guard 日报\n"
            f"{'─' * 24}\n"
            f"⚡ 断电次数: {stats['power_outage_count']}\n"
            f"🔋 电池供电时长: {hours}小时{minutes}分钟\n"
            f"🔋 最低电量: {stats['min_battery']}%\n"
            f"🔋 平均电量: {avg:.1f}%\n"
            f"🔄 网络重连次数: {stats['network_reconnect_count']}"
        )


class BatteryMonitor:
    def __init__(self, notify_callback: NotifyCallback, tracker: BatteryTracker) -> None:
        self.notify = notify_callback
        self.tracker = tracker
        self.was_plugged: bool | None = None
        self.low_battery_notified = False
        self.notified_thresholds: set[int] = set()
        self.auto_shutdown_triggered = False
        self.running = True

    def check(self) -> None:
        bat = psutil.sensors_battery()
        if bat is None:
            return

        plugged = bool(bat.power_plugged)
        percent = int(bat.percent)
        self.tracker.update_battery_level(percent, plugged)

        if self.was_plugged is None:
            self.was_plugged = plugged
            log.info("初始电源状态: %s, 电量: %s%%", "供电中" if plugged else "电池供电", percent)
            return

        if self.was_plugged and not plugged:
            self.tracker.record_outage()
            self.low_battery_notified = False
            self.notified_thresholds.clear()
            self.auto_shutdown_triggered = False
            log.warning("检测到断电！")
            self.notify(f"⚠️ 断电警告！\n当前电量: {percent}%\n请尽快接通电源。")

        if not self.was_plugged and plugged:
            self.low_battery_notified = False
            self.notified_thresholds.clear()
            self.auto_shutdown_triggered = False
            log.info("供电恢复")
            self.notify(f"✅ 已恢复供电\n当前电量: {percent}%")

        if not plugged:
            cfg = get_config_dict()
            warning_thresholds = cfg.get("battery_warning_thresholds", [50, 30, 20])
            thresholds = sorted({int(t) for t in warning_thresholds}, reverse=True)
            for threshold in thresholds:
                if percent <= threshold and threshold not in self.notified_thresholds:
                    self.notified_thresholds.add(threshold)
                    if threshold <= 20:
                        level = "🚨 电量危险"
                    elif threshold <= 30:
                        level = "🔴 电量偏低"
                    else:
                        level = "🟠 电量提醒"
                    log.warning("电量达到阈值: %s%% <= %s%%", percent, threshold)
                    self.notify(f"{level}！当前 {percent}%（阈值 {threshold}%）")

            shutdown_threshold = int(cfg.get("auto_shutdown_threshold", 20))
            if percent <= shutdown_threshold and not self.auto_shutdown_triggered:
                self.auto_shutdown_triggered = True
                delay = int(cfg.get("auto_shutdown_delay", 60))
                msg = (
                    f"🚨 电量极低 ({percent}%)！\n"
                    f"电脑将在 {delay} 秒后自动关机（电量 ≤{shutdown_threshold}%）\n"
                    "发送 /cancel 可取消关机"
                )
                log.warning("电量极低 (%s%%)，%s秒后自动关机", percent, delay)
                self.notify(msg)
                subprocess.Popen(
                    ["shutdown", "/s", "/t", str(delay)],
                    creationflags=0x08000000,
                )

        self.was_plugged = plugged

    def get_status(self) -> str:
        bat = psutil.sensors_battery()
        if bat is None:
            return "未检测到电池"
        status = "🔌 供电中" if bat.power_plugged else "🔋 电池供电"
        return f"{status}\n电量: {bat.percent}%\n剩余: {self._format_time(bat.secsleft)}"

    @staticmethod
    def _format_time(secs: int) -> str:
        if secs == psutil.POWER_TIME_UNLIMITED:
            return "充电中"
        if secs == psutil.POWER_TIME_UNKNOWN or secs < 0:
            return "计算中..."
        hours = secs // 3600
        minutes = (secs % 3600) // 60
        if hours > 0:
            return f"{hours}小时{minutes}分钟"
        return f"{minutes}分钟"
