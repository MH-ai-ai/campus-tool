from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    telegram_user_id: int
    campus_auth_url: str
    campus_account: str
    campus_password: str
    wlan_ac_ip: str
    check_interval_seconds: int = 5
    network_check_interval_seconds: int = 30
    low_battery_threshold: int = 30
    battery_warning_thresholds: tuple[int, ...] = (50, 30, 20)
    autostart: bool = True
    campus_gateway: str = "10.212.0.1"
    campus_wifi_ssid: str = ""
    campus_wifi_ssids: tuple[str, ...] = field(default_factory=tuple)
    auto_shutdown_threshold: int = 20
    auto_shutdown_delay: int = 60
    reconnect_max_retries: int = 3
    reconnect_verify_delay_seconds: int = 3
    reconnect_fast_retry_seconds: int = 2
    bot_watchdog_stale_seconds: int = 300

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Config":
        ssids = data.get("campus_wifi_ssids", ())
        if isinstance(ssids, str):
            ssid_tuple = tuple(s.strip() for s in ssids.split(",") if s.strip())
        else:
            ssid_tuple = tuple(str(s) for s in ssids if str(s))

        battery_thresholds = data.get("battery_warning_thresholds", (50, 30, 20))
        if isinstance(battery_thresholds, int):
            threshold_tuple = (battery_thresholds,)
        else:
            threshold_tuple = tuple(
                sorted({int(t) for t in battery_thresholds}, reverse=True)
            )

        return cls(
            telegram_bot_token=str(data.get("telegram_bot_token", "")),
            telegram_user_id=int(data.get("telegram_user_id", 0)),
            campus_auth_url=str(data.get("campus_auth_url", "")),
            campus_account=str(data.get("campus_account", "")),
            campus_password=str(data.get("campus_password", "")),
            wlan_ac_ip=str(data.get("wlan_ac_ip", "")),
            check_interval_seconds=int(data.get("check_interval_seconds", 5)),
            network_check_interval_seconds=int(
                data.get("network_check_interval_seconds", 2)
            ),
            low_battery_threshold=int(data.get("low_battery_threshold", 30)),
            battery_warning_thresholds=threshold_tuple,
            autostart=bool(data.get("autostart", True)),
            campus_gateway=str(data.get("campus_gateway", "10.212.0.1")),
            campus_wifi_ssid=str(data.get("campus_wifi_ssid", "")),
            campus_wifi_ssids=ssid_tuple,
            auto_shutdown_threshold=int(data.get("auto_shutdown_threshold", 20)),
            auto_shutdown_delay=int(data.get("auto_shutdown_delay", 60)),
            reconnect_max_retries=int(data.get("reconnect_max_retries", 3)),
            reconnect_verify_delay_seconds=int(
                data.get("reconnect_verify_delay_seconds", 3)
            ),
            reconnect_fast_retry_seconds=int(data.get("reconnect_fast_retry_seconds", 2)),
            bot_watchdog_stale_seconds=int(
                data.get("bot_watchdog_stale_seconds", 300)
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "telegram_bot_token": self.telegram_bot_token,
            "telegram_user_id": self.telegram_user_id,
            "campus_auth_url": self.campus_auth_url,
            "campus_account": self.campus_account,
            "campus_password": self.campus_password,
            "wlan_ac_ip": self.wlan_ac_ip,
            "check_interval_seconds": self.check_interval_seconds,
            "network_check_interval_seconds": self.network_check_interval_seconds,
            "low_battery_threshold": self.low_battery_threshold,
            "battery_warning_thresholds": list(self.battery_warning_thresholds),
            "autostart": self.autostart,
            "campus_gateway": self.campus_gateway,
            "campus_wifi_ssid": self.campus_wifi_ssid,
            "campus_wifi_ssids": list(self.campus_wifi_ssids),
            "auto_shutdown_threshold": self.auto_shutdown_threshold,
            "auto_shutdown_delay": self.auto_shutdown_delay,
            "reconnect_max_retries": self.reconnect_max_retries,
            "reconnect_verify_delay_seconds": self.reconnect_verify_delay_seconds,
            "reconnect_fast_retry_seconds": self.reconnect_fast_retry_seconds,
            "bot_watchdog_stale_seconds": self.bot_watchdog_stale_seconds,
        }


@dataclass(frozen=True)
class GuardState:
    network_ok: bool | None
    power_plugged: bool | None
    battery_percent: int | None


class ConnectivityState(str, Enum):
    ONLINE = "online"
    WIFI_DOWN = "wifi_down"
    GATEWAY_DOWN = "gateway_down"
    INTERNET_DOWN = "internet_down"
    RECONNECTING = "reconnecting"
    RESTORED = "restored"


@dataclass(frozen=True)
class ConnectivitySnapshot:
    state: ConnectivityState
    wifi_ok: bool
    gateway_ok: bool
    internet_direct_ok: bool
    internet_proxy_ok: bool
    local_ip: str
    wifi_info: str
    clash_tun: bool
    reason: str

    @property
    def online(self) -> bool:
        return self.state in {ConnectivityState.ONLINE, ConnectivityState.RESTORED}
