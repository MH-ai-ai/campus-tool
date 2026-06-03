from __future__ import annotations

import time
from typing import Callable

from .auth import campus_login
from .battery import BatteryTracker
from .bot_health import trigger_bot_health_check
from .config import get_config_dict
from .logging_setup import get_logger
from .system import (
    check_campus_gateway,
    check_internet,
    get_local_ip,
    get_wifi_info,
    get_wifi_signal_percent,
    is_wifi_connected,
    reconnect_wifi,
)


NotifyCallback = Callable[[str], None]
log = get_logger()


class NetworkMonitor:
    def __init__(self, notify_callback: NotifyCallback, tracker: BatteryTracker) -> None:
        self.notify = notify_callback
        self.tracker = tracker
        self.is_online: bool | None = None
        self.running = True
        self.retry_count = 0
        self.max_retries = 3
        self.weak_signal_count = 0
        self.aggressive_mode = False
        self.aggressive_start_time: float | None = None

    def check(self) -> None:
        wifi_ok = is_wifi_connected()
        gateway_ok = check_campus_gateway() if wifi_ok else False
        internet_ok = check_internet() if gateway_ok else False
        online = wifi_ok and gateway_ok and internet_ok

        if wifi_ok:
            signal_pct = get_wifi_signal_percent()
            if 0 <= signal_pct < 30:
                self.weak_signal_count += 1
                log.warning("WiFi 信号弱: %d%% (连续第 %d 次)", signal_pct, self.weak_signal_count)
                if self.weak_signal_count >= 3:
                    self.notify(
                        f"⚠️ WiFi 信号持续偏弱！\n"
                        f"连续 {self.weak_signal_count} 次检测低于 30%\n"
                        f"当前信号: {signal_pct}%\n"
                        "建议靠近路由器或检查天线"
                    )
                    self.weak_signal_count = 0
            else:
                self.weak_signal_count = 0

        if self.is_online is None:
            self.is_online = online
            log.info(
                "初始网络状态: %s (WiFi=%s, 网关=%s, 外网=%s)",
                "在线" if online else "离线",
                "OK" if wifi_ok else "断开",
                "OK" if gateway_ok else "不可达",
                "OK" if internet_ok else "不通",
            )
            if not online:
                self._try_reconnect()
            return

        if self.is_online and not online:
            if not wifi_ok:
                reason = "WiFi 断开"
            elif not gateway_ok:
                reason = "校园网网关不可达（可能认证过期）"
            else:
                reason = "外网不通（认证未生效）"
            log.warning("检测到网络断开（%s），尝试重连...", reason)
            self.notify(f"⚠️ 校园网断开（{reason}）！正在自动重连...")
            self._try_reconnect()

        self.is_online = online

    def _get_campus_ssids(self) -> list[str]:
        cfg = get_config_dict()
        ssids = cfg.get("campus_wifi_ssids", [])
        if not ssids:
            old_ssid = cfg.get("campus_wifi_ssid", "")
            ssids = [old_ssid] if old_ssid else []
        return [str(s) for s in ssids if str(s)]

    def _try_reconnect(self) -> None:
        campus_ssids = self._get_campus_ssids()
        self.aggressive_mode = True
        self.aggressive_start_time = time.time()

        if not is_wifi_connected():
            wifi_connected = False
            for ssid in campus_ssids:
                self.notify(f"📶 WiFi 已断开，正在重连 {ssid}...")
                if reconnect_wifi(ssid):
                    wifi_connected = True
                    self.notify(f"✅ WiFi 已重连: {ssid}")
                    break
                log.warning("WiFi %s 重连失败，尝试下一个...", ssid)
            if not wifi_connected:
                self.aggressive_mode = False
                self.notify("❌ WiFi 重连失败，所有 SSID 均不可用")
                return

        for attempt in range(1, self.max_retries + 1):
            log.info("校园网重连尝试 %d/%d", attempt, self.max_retries)
            success, msg = campus_login()
            if success:
                time.sleep(3)
                if check_campus_gateway() and check_internet():
                    self.is_online = True
                    self.retry_count = 0
                    self.tracker.record_reconnect()
                    self.notify(f"✅ 校园网重连成功\n尝试次数: {attempt}")
                    self.aggressive_mode = False
                    trigger_bot_health_check()
                    return
                log.warning(
                    "重连尝试 %d: 认证已发送但验证失败 (网关=%s, 外网=%s)",
                    attempt,
                    "OK" if check_campus_gateway() else "不可达",
                    "OK" if check_internet() else "不通",
                )

            if self.aggressive_mode and self.aggressive_start_time:
                elapsed = time.time() - self.aggressive_start_time
                if elapsed < 120:
                    time.sleep(10)
                    continue
            self.aggressive_mode = False
            time.sleep(2)

        self.retry_count += 1
        self.notify(f"❌ 校园网重连失败\n已连续失败 {self.retry_count} 次")

    def get_status(self) -> str:
        status = "在线" if self.is_online else "离线"
        return f"网络: {status}\nWiFi: {get_wifi_info()}\n本机 IP: {get_local_ip()}"
