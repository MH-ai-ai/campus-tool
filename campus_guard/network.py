from __future__ import annotations

import time
from datetime import timedelta
from threading import Event
from typing import Callable

from .auth import campus_login
from .battery import BatteryTracker
from .bot_health import trigger_bot_health_check
from .config import get_config_dict
from .logging_setup import get_logger
from .models import ConnectivitySnapshot, ConnectivityState
from .system import (
    check_campus_gateway,
    check_internet,
    check_proxy_internet,
    get_local_ip,
    get_wifi_info,
    get_wifi_signal_percent,
    is_clash_tun_ip,
    is_wifi_link_up,
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
        self.weak_signal_count = 0
        self.aggressive_mode = False
        self.aggressive_start_time: float | None = None
        self.offline_since: float | None = None
        self.last_snapshot: ConnectivitySnapshot | None = None
        self.last_event = "等待首次网络检测"
        self._stop_event = Event()

    def check(self) -> None:
        snapshot = self.probe_connectivity()
        online = snapshot.online
        self.last_snapshot = snapshot

        if snapshot.wifi_ok:
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
            self.last_event = f"初始网络状态: {snapshot.reason}"
            log.info(
                "初始网络状态: %s (WiFi=%s, 网关=%s, 直连外网=%s, 代理外网=%s, TUN=%s)",
                "在线" if online else "离线",
                "OK" if snapshot.wifi_ok else "断开",
                "OK" if snapshot.gateway_ok else "不可达",
                "OK" if snapshot.internet_direct_ok else "不通",
                "OK" if snapshot.internet_proxy_ok else "不通",
                "YES" if snapshot.clash_tun else "NO",
            )
            if not online:
                self.offline_since = time.time()
                self.notify(self._format_down_message(snapshot))
                self._try_reconnect()
            return

        if self.is_online and not online:
            self.offline_since = time.time()
            self.last_event = f"网络断开: {snapshot.reason}"
            log.warning("检测到网络断开（%s），尝试重连...", snapshot.reason)
            self.notify(self._format_down_message(snapshot))
            self._try_reconnect()

        self.is_online = online

    def stop(self) -> None:
        self.running = False
        self._stop_event.set()

    def probe_connectivity(self) -> ConnectivitySnapshot:
        local_ip = get_local_ip()
        wifi_ok = is_wifi_link_up()
        gateway_ok = check_campus_gateway() if wifi_ok else False
        internet_direct_ok = check_internet() if gateway_ok else False
        internet_proxy_ok = check_proxy_internet()
        clash_tun = is_clash_tun_ip(local_ip)

        if not wifi_ok:
            state = ConnectivityState.WIFI_DOWN
            reason = "WiFi 链路断开"
        elif not gateway_ok:
            state = ConnectivityState.GATEWAY_DOWN
            reason = "校园网网关不可达"
        elif not internet_direct_ok:
            state = ConnectivityState.INTERNET_DOWN
            reason = "直连外网不通，可能需要重新认证"
        else:
            state = ConnectivityState.ONLINE
            reason = "网络在线"

        return ConnectivitySnapshot(
            state=state,
            wifi_ok=wifi_ok,
            gateway_ok=gateway_ok,
            internet_direct_ok=internet_direct_ok,
            internet_proxy_ok=internet_proxy_ok,
            local_ip=local_ip,
            wifi_info=get_wifi_info(),
            clash_tun=clash_tun,
            reason=reason,
        )

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

        if not is_wifi_link_up():
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

        cfg = get_config_dict()
        max_retries = int(cfg.get("reconnect_max_retries", 3))
        verify_delay = int(cfg.get("reconnect_verify_delay_seconds", 3))
        fast_retry_delay = int(cfg.get("reconnect_fast_retry_seconds", 2))

        for attempt in range(1, max_retries + 1):
            log.info("校园网重连尝试 %d/%d", attempt, max_retries)
            success, msg = campus_login()
            if success:
                if self._wait(verify_delay):
                    return
                snapshot = self.probe_connectivity()
                if snapshot.online:
                    self.is_online = True
                    self.retry_count = 0
                    self.tracker.record_reconnect()
                    self.last_snapshot = snapshot
                    self.last_event = "网络重连成功"
                    self.notify(self._format_restore_message(snapshot, attempt))
                    self.aggressive_mode = False
                    trigger_bot_health_check()
                    return
                log.warning(
                    "重连尝试 %d: 认证已发送但验证失败 (网关=%s, 直连外网=%s)",
                    attempt,
                    "OK" if snapshot.gateway_ok else "不可达",
                    "OK" if snapshot.internet_direct_ok else "不通",
                )

            if self.aggressive_mode and self.aggressive_start_time:
                elapsed = time.time() - self.aggressive_start_time
                if elapsed < 120:
                    if self._wait(fast_retry_delay):
                        return
                    continue
            self.aggressive_mode = False
            if self._wait(fast_retry_delay):
                return

        self.retry_count += 1
        self.last_event = f"重连失败: 连续失败 {self.retry_count} 次"
        self.notify(f"❌ 校园网重连失败\n已连续失败 {self.retry_count} 次")

    def get_status(self) -> str:
        status = "在线" if self.is_online else "离线"
        snapshot = self.last_snapshot
        if not snapshot:
            return f"网络: {status}\nWiFi: {get_wifi_info()}\n本机 IP: {get_local_ip()}"
        return (
            f"网络: {status}\n"
            f"原因: {snapshot.reason}\n"
            f"WiFi: {snapshot.wifi_info}\n"
            f"本机 IP: {snapshot.local_ip}\n"
            f"网关: {'OK' if snapshot.gateway_ok else '不可达'}\n"
            f"直连外网: {'OK' if snapshot.internet_direct_ok else '不通'}\n"
            f"代理外网: {'OK' if snapshot.internet_proxy_ok else '不通'}\n"
            f"Clash/TUN: {'检测到' if snapshot.clash_tun else '未检测到'}"
        )

    def _wait(self, seconds: int | float) -> bool:
        return self._stop_event.wait(seconds)

    def _format_down_message(self, snapshot: ConnectivitySnapshot) -> str:
        return (
            f"⚠️ 校园网断开：{snapshot.reason}\n"
            f"WiFi: {snapshot.wifi_info}\n"
            f"本机 IP: {snapshot.local_ip}\n"
            f"网关: {'OK' if snapshot.gateway_ok else '不可达'}\n"
            f"直连外网: {'OK' if snapshot.internet_direct_ok else '不通'}\n"
            f"代理外网: {'OK' if snapshot.internet_proxy_ok else '不通'}\n"
            f"Clash/TUN: {'检测到' if snapshot.clash_tun else '未检测到'}\n"
            "正在自动重连..."
        )

    def _format_restore_message(self, snapshot: ConnectivitySnapshot, attempt: int) -> str:
        downtime = "未知"
        if self.offline_since:
            downtime = str(timedelta(seconds=int(time.time() - self.offline_since)))
        return (
            "✅ 校园网重连成功\n"
            f"耗时: {downtime}\n"
            f"尝试次数: {attempt}\n"
            f"WiFi: {snapshot.wifi_info}\n"
            f"本机 IP: {snapshot.local_ip}\n"
            f"网关: {'OK' if snapshot.gateway_ok else '不可达'}\n"
            f"直连外网: {'OK' if snapshot.internet_direct_ok else '不通'}\n"
            f"代理外网: {'OK' if snapshot.internet_proxy_ok else '不通'}\n"
            f"Clash/TUN: {'检测到' if snapshot.clash_tun else '未检测到'}"
        )
