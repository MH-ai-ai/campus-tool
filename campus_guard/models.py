from __future__ import annotations

from dataclasses import dataclass, field
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
    autostart: bool = True
    campus_gateway: str = "10.212.0.1"
    campus_wifi_ssid: str = ""
    campus_wifi_ssids: tuple[str, ...] = field(default_factory=tuple)
    auto_shutdown_threshold: int = 10
    auto_shutdown_delay: int = 120
    bot_watchdog_stale_seconds: int = 300

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Config":
        ssids = data.get("campus_wifi_ssids", ())
        if isinstance(ssids, str):
            ssid_tuple = tuple(s.strip() for s in ssids.split(",") if s.strip())
        else:
            ssid_tuple = tuple(str(s) for s in ssids if str(s))

        return cls(
            telegram_bot_token=str(data.get("telegram_bot_token", "")),
            telegram_user_id=int(data.get("telegram_user_id", 0)),
            campus_auth_url=str(data.get("campus_auth_url", "")),
            campus_account=str(data.get("campus_account", "")),
            campus_password=str(data.get("campus_password", "")),
            wlan_ac_ip=str(data.get("wlan_ac_ip", "")),
            check_interval_seconds=int(data.get("check_interval_seconds", 5)),
            network_check_interval_seconds=int(
                data.get("network_check_interval_seconds", 30)
            ),
            low_battery_threshold=int(data.get("low_battery_threshold", 30)),
            autostart=bool(data.get("autostart", True)),
            campus_gateway=str(data.get("campus_gateway", "10.212.0.1")),
            campus_wifi_ssid=str(data.get("campus_wifi_ssid", "")),
            campus_wifi_ssids=ssid_tuple,
            auto_shutdown_threshold=int(data.get("auto_shutdown_threshold", 10)),
            auto_shutdown_delay=int(data.get("auto_shutdown_delay", 120)),
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
            "autostart": self.autostart,
            "campus_gateway": self.campus_gateway,
            "campus_wifi_ssid": self.campus_wifi_ssid,
            "campus_wifi_ssids": list(self.campus_wifi_ssids),
            "auto_shutdown_threshold": self.auto_shutdown_threshold,
            "auto_shutdown_delay": self.auto_shutdown_delay,
            "bot_watchdog_stale_seconds": self.bot_watchdog_stale_seconds,
        }


@dataclass(frozen=True)
class GuardState:
    network_ok: bool | None
    power_plugged: bool | None
    battery_percent: int | None
