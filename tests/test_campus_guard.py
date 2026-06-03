import importlib
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from campus_guard import Config, GuardState, build_auth_params, get_tray_color, is_authorized
from campus_guard.battery import BatteryMonitor, BatteryTracker
from campus_guard.config import update_runtime_config
from campus_guard.models import ConnectivityState
from campus_guard.network import NetworkMonitor
from campus_guard.system import is_clash_tun_ip
from campus_guard.telegram_bot import TelegramBot, bot_command_specs


class CampusGuardTests(unittest.TestCase):
    def test_build_auth_params_uses_drcom_get_fields(self):
        config = Config(
            telegram_bot_token="token",
            telegram_user_id=8512030855,
            campus_auth_url="http://10.200.84.3:801/eportal/portal/login",
            campus_account="1110623014015",
            campus_password="secret",
            wlan_ac_ip="10.255.250.74",
            check_interval_seconds=5,
            network_check_interval_seconds=30,
            low_battery_threshold=30,
            autostart=True,
        )

        params = build_auth_params(config, "10.1.2.3", "aabbccddeeff")

        self.assertEqual(params["login_method"], "1")
        self.assertEqual(params["user_account"], ",0,1110623014015")
        self.assertEqual(params["user_password"], "secret")
        self.assertEqual(params["wlan_user_ip"], "10.1.2.3")
        self.assertEqual(params["wlan_user_mac"], "aabbccddeeff")
        self.assertEqual(params["wlan_ac_ip"], "10.255.250.74")
        self.assertIn("v", params)

    def test_authorized_only_rejects_other_users(self):
        update = SimpleNamespace(effective_user=SimpleNamespace(id=123))

        self.assertFalse(is_authorized(update, 8512030855))

    def test_tray_color_red_when_network_down(self):
        state = GuardState(network_ok=False, power_plugged=True, battery_percent=80)

        self.assertEqual(get_tray_color(state), "red")

    def test_tray_color_yellow_on_battery_with_network_ok(self):
        state = GuardState(network_ok=True, power_plugged=False, battery_percent=80)

        self.assertEqual(get_tray_color(state), "yellow")

    def test_package_import_has_no_runtime_side_effects(self):
        module = importlib.import_module("campus_guard")

        self.assertTrue(hasattr(module, "Config"))
        self.assertNotIn("campus_guard.ui", importlib.sys.modules)
        self.assertNotIn("PyQt6", importlib.sys.modules)

    def test_config_defaults_match_target_thresholds(self):
        config = Config.from_mapping({})

        self.assertEqual(config.network_check_interval_seconds, 2)
        self.assertEqual(config.battery_warning_thresholds, (50, 30, 20))
        self.assertEqual(config.auto_shutdown_threshold, 20)
        self.assertEqual(config.auto_shutdown_delay, 60)

    def test_clash_tun_detection(self):
        self.assertTrue(is_clash_tun_ip("198.18.0.12"))
        self.assertTrue(is_clash_tun_ip("198.19.1.2"))
        self.assertFalse(is_clash_tun_ip("10.1.2.3"))

    def test_network_probe_classifies_clash_tun_and_direct_outage(self):
        update_runtime_config({"campus_wifi_ssids": ["Campus"]})
        monitor = NetworkMonitor(lambda _: None, BatteryTracker())

        with (
            patch("campus_guard.network.is_wifi_link_up", return_value=True),
            patch("campus_guard.network.check_campus_gateway", return_value=True),
            patch("campus_guard.network.check_internet", return_value=False),
            patch("campus_guard.network.check_proxy_internet", return_value=True),
            patch("campus_guard.network.get_local_ip", return_value="198.18.1.2"),
            patch("campus_guard.network.get_wifi_info", return_value="Campus (80%)"),
        ):
            snapshot = monitor.probe_connectivity()

        self.assertEqual(snapshot.state, ConnectivityState.INTERNET_DOWN)
        self.assertTrue(snapshot.clash_tun)
        self.assertFalse(snapshot.internet_direct_ok)
        self.assertTrue(snapshot.internet_proxy_ok)

    def test_battery_thresholds_notify_once_and_shutdown_at_20(self):
        messages = []
        update_runtime_config(
            {
                "battery_warning_thresholds": [50, 30, 20],
                "auto_shutdown_threshold": 20,
                "auto_shutdown_delay": 60,
            }
        )
        monitor = BatteryMonitor(messages.append, BatteryTracker())
        monitor.was_plugged = True

        battery_49 = SimpleNamespace(power_plugged=False, percent=49, secsleft=3600)
        battery_29 = SimpleNamespace(power_plugged=False, percent=29, secsleft=1800)
        battery_19 = SimpleNamespace(power_plugged=False, percent=19, secsleft=900)

        with patch("campus_guard.battery.psutil.sensors_battery", return_value=battery_49):
            monitor.check()
        with patch("campus_guard.battery.psutil.sensors_battery", return_value=battery_29):
            monitor.check()
        with (
            patch("campus_guard.battery.psutil.sensors_battery", return_value=battery_19),
            patch("campus_guard.battery.subprocess.Popen") as popen,
        ):
            monitor.check()

        joined = "\n".join(messages)
        self.assertIn("阈值 50%", joined)
        self.assertIn("阈值 30%", joined)
        self.assertIn("阈值 20%", joined)
        popen.assert_called_once()
        self.assertEqual(popen.call_args.args[0], ["shutdown", "/s", "/t", "60"])

    def test_telegram_notification_queue_flushes_after_recovery(self):
        class FakeBot:
            def __init__(self):
                self.fail = True
                self.sent = []

            async def send_message(self, chat_id, text, parse_mode=None):
                if self.fail:
                    raise RuntimeError("offline")
                self.sent.append((chat_id, text, parse_mode))

        async def run_case():
            fake_bot = FakeBot()
            update_runtime_config({"telegram_user_id": 42})
            bot = TelegramBot(None, None, BatteryTracker())
            bot.app = SimpleNamespace(bot=fake_bot)

            await bot._send_or_queue("断网")
            self.assertEqual(bot._message_queue, ["断网"])

            fake_bot.fail = False
            await bot._flush_message_queue()
            self.assertEqual(bot._message_queue, [])
            self.assertEqual(fake_bot.sent[0][1], "断网")

        asyncio.run(run_case())

    def test_bot_command_menu_uses_valid_commands_with_chinese_descriptions(self):
        commands = dict(bot_command_specs())

        self.assertIn("network", commands)
        self.assertIn("battery", commands)
        self.assertIn("cancel_shutdown", commands)
        self.assertIn("网络", commands["network"])
        self.assertIn("电量", commands["battery"])
        for command in commands:
            self.assertRegex(command, r"^[a-z0-9_]{1,32}$")


if __name__ == "__main__":
    unittest.main()
