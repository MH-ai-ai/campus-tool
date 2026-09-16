import importlib
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import campus_guard.config as config_module
import campus_guard.runtime as runtime
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

    def test_missing_config_is_created_from_example(self):
        with TemporaryDirectory() as tmp:
            app_dir = Path(tmp)
            config_path = app_dir / "config.json"
            example_path = app_dir / "config.example.json"
            example_path.write_text(
                '{"telegram_user_id": 0, "network_check_interval_seconds": 2}',
                encoding="utf-8",
            )

            with (
                patch.object(config_module, "APP_DIR", app_dir),
                patch.object(config_module, "CONFIG_PATH", config_path),
            ):
                data = config_module.load_config_raw()

            self.assertTrue(config_path.exists())
            self.assertEqual(data["telegram_user_id"], 0)
            self.assertEqual(data["network_check_interval_seconds"], 2)

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
        self.assertEqual(popen.call_args.args[0], ["shutdown", "/s", "/f", "/t", "60"])

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

    def test_telegram_start_skips_when_token_is_missing(self):
        async def run_case():
            update_runtime_config({"telegram_bot_token": "", "telegram_user_id": 42})
            bot = TelegramBot(None, None, BatteryTracker())
            with patch.object(bot, "_build_app") as build_app:
                await bot.start()
            build_app.assert_not_called()

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

    def test_autostart_command_uses_exe_when_frozen(self):
        with (
            patch.object(
                runtime.sys,
                "executable",
                r"C:\Apps\CampusGuard\CampusGuard.exe",
            ),
            patch.object(runtime.sys, "frozen", True, create=True),
        ):
            command = runtime.build_autostart_command()

        self.assertEqual(command, r'"C:\Apps\CampusGuard\CampusGuard.exe"')

    def test_autostart_command_uses_pythonw_launcher_in_source_mode(self):
        with (
            patch.object(runtime.sys, "executable", r"C:\Python312\python.exe"),
            patch.object(runtime.sys, "frozen", False, create=True),
            patch("campus_guard.runtime.os.path.exists", return_value=True),
        ):
            command = runtime.build_autostart_command()

        self.assertIn(r'"C:\Python312\pythonw.exe"', command)
        self.assertIn("campus_guard.pyw", command)

    def test_ui_settings_schema_matches_config(self):
        from dataclasses import fields
        from campus_guard.models import Config
        from campus_guard.ui import _SETTINGS_SCHEMA

        config_fields = {f.name for f in fields(Config)}
        for key, _label, _group, _wtype, _extra in _SETTINGS_SCHEMA:
            self.assertIn(
                key,
                config_fields,
                f"UI 设置项 {key} 在 Config 数据类中未找到定义",
            )

    def test_network_mode_detection_campus_vs_home(self):
        from campus_guard.network import detect_is_campus_network

        # 1. 校园网 SSID 匹配
        update_runtime_config({
            "campus_wifi_ssids": ["Campus-WiFi", "EDUROAM"],
            "trusted_home_ssids": ["Home_5G", "Pixel_Hotspot"],
            "forced_network_mode": "auto",
        })
        self.assertTrue(detect_is_campus_network("Campus-WiFi (90%)", gateway_ok=False))
        self.assertTrue(detect_is_campus_network("eduroam", gateway_ok=False))

        # 2. 家庭网络 SSID 匹配
        self.assertFalse(detect_is_campus_network("Home_5G (85%)", gateway_ok=True))
        self.assertFalse(detect_is_campus_network("Pixel_Hotspot", gateway_ok=True))

        # 3. 强制模式覆盖
        update_runtime_config({"forced_network_mode": "home"})
        self.assertFalse(detect_is_campus_network("Campus-WiFi", gateway_ok=True))
        update_runtime_config({"forced_network_mode": "campus"})
        self.assertTrue(detect_is_campus_network("Home_5G", gateway_ok=False))

    def test_home_network_probe_skips_gateway_failure(self):
        update_runtime_config({
            "campus_wifi_ssids": ["Campus"],
            "trusted_home_ssids": ["MyHome"],
            "forced_network_mode": "auto",
        })
        monitor = NetworkMonitor(lambda _: None, BatteryTracker())

        with (
            patch("campus_guard.network.is_wifi_link_up", return_value=True),
            patch("campus_guard.network.check_campus_gateway", return_value=False),
            patch("campus_guard.network.check_internet", return_value=True),
            patch("campus_guard.network.check_proxy_internet", return_value=True),
            patch("campus_guard.network.get_local_ip", return_value="192.168.1.100"),
            patch("campus_guard.network.get_wifi_info", return_value="MyHome (95%)"),
        ):
            snapshot = monitor.probe_connectivity()

        # 在家庭网络下，即便校园网关不通，只要外网连通，状态仍是在线，且不判定为校园网
        self.assertEqual(snapshot.state, ConnectivityState.ONLINE)
        self.assertFalse(snapshot.is_campus_network)
        self.assertIn("家庭/免认证网络", snapshot.reason)

    def test_drcom_error_translation_and_logout_params(self):
        from campus_guard.auth import build_logout_params, parse_drcom_response

        # 验证常见 Dr.COM 错误代码映射
        ok, msg = parse_drcom_response('dr1003({"result":0,"msg":"ldap auth error"})')
        self.assertFalse(ok)
        self.assertIn("账号或密码错误", msg)

        ok, msg = parse_drcom_response('dr1003({"result":0,"msg":"balance error"})')
        self.assertFalse(ok)
        self.assertIn("账号已欠费停机", msg)

        # 验证注销参数
        config = Config(
            telegram_bot_token="token",
            telegram_user_id=12345,
            campus_auth_url="http://10.200.84.3:801/eportal/portal/login",
            campus_account="user1",
            campus_password="pwd",
            wlan_ac_ip="10.255.250.74",
        )
        params = build_logout_params(config, "10.0.0.1", "112233445566")
        self.assertEqual(params["callback"], "dr1004")
        self.assertEqual(params["user_account"], ",0,user1")
        self.assertEqual(params["wlan_user_ip"], "10.0.0.1")

    def test_bot_new_commands_in_specs(self):
        commands = dict(bot_command_specs())
        self.assertIn("logout", commands)
        self.assertIn("mode", commands)
        self.assertIn("wifi", commands)
        self.assertIn("注销", commands["logout"])
        self.assertIn("模式", commands["mode"])
        self.assertIn("Wi-Fi", commands["wifi"])

    def test_auto_detect_portal_config_success(self):
        from campus_guard.auth import auto_detect_portal_config

        mock_resp = Mock()
        mock_resp.status_code = 302
        mock_resp.headers = {
            "Location": "http://10.200.84.3:801/eportal/portal/login?wlanuserip=10.1.2.3&wlanacip=10.255.250.74"
        }
        mock_resp.text = ""

        with (
            patch("requests.Session.get", return_value=mock_resp),
            patch("campus_guard.auth.get_wifi_info", return_value="Campus-5G (95%)"),
            patch("campus_guard.auth.get_local_ip", return_value="10.1.2.3"),
        ):
            ok, msg, extracted = auto_detect_portal_config()

        self.assertTrue(ok)
        self.assertIn("成功捕获", msg)
        self.assertEqual(extracted.get("campus_wifi_ssid"), "Campus-5G")
        self.assertEqual(extracted.get("campus_auth_url"), "http://10.200.84.3:801/eportal/portal/login")
        self.assertEqual(extracted.get("campus_gateway"), "10.200.84.3")
        self.assertEqual(extracted.get("wlan_ac_ip"), "10.255.250.74")
        self.assertEqual(extracted.get("wlan_user_ip"), "10.1.2.3")

    def test_auto_detect_portal_config_when_no_redirect(self):
        from campus_guard.auth import auto_detect_portal_config

        mock_resp = Mock()
        mock_resp.status_code = 204
        mock_resp.headers = {}
        mock_resp.text = ""

        with (
            patch("requests.Session.get", return_value=mock_resp),
            patch("campus_guard.auth.get_wifi_info", return_value="HomeWiFi"),
            patch("campus_guard.auth.get_local_ip", return_value="192.168.1.5"),
        ):
            ok, msg, extracted = auto_detect_portal_config()

        self.assertFalse(ok)
        self.assertIn("未捕获到校园网重定向", msg)

    def test_unified_notifier_feishu_and_dingtalk(self):
        from campus_guard.notifier import UnifiedNotifier

        # 1. 飞书卡片自适应色彩与内容测试
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"code": 0}
            success = UnifiedNotifier._send_feishu_card(
                "https://open.feishu.cn/webhook/mock",
                "⚠️ 网络连接异常断开，准备重连",
                "网络告警",
                "error",
            )
            self.assertTrue(success)
            payload = mock_post.call_args[1]["json"]
            self.assertEqual(payload["msg_type"], "interactive")
            self.assertEqual(payload["card"]["header"]["template"], "red")

        # 2. 钉钉加签与 Markdown 测试
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"errcode": 0}
            success = UnifiedNotifier._send_dingtalk(
                "https://oapi.dingtalk.com/robot/send?access_token=test",
                "my_secret_token",
                "校园网已自动重新认证成功",
                "状态通报",
            )
            self.assertTrue(success)
            called_url = mock_post.call_args[0][0]
            self.assertIn("timestamp=", called_url)
            self.assertIn("sign=", called_url)
            payload = mock_post.call_args[1]["json"]
            self.assertEqual(payload["msgtype"], "markdown")

    def test_wifi_cache_prevents_frequent_location_polling(self):
        import campus_guard.system as sys_mod

        # 清除缓存
        sys_mod._wlan_cache = (0.0, "未知", -1)

        mock_stat = SimpleNamespace(isup=True)
        mock_stats = {"Wi-Fi": mock_stat}
        mock_proc = SimpleNamespace(
            returncode=0,
            stdout="    SSID                   : Campus-WiFi\n    信号                   : 88%\n".encode("gbk"),
            stderr=b"",
        )

        with (
            patch("campus_guard.system.psutil.net_if_stats", return_value=mock_stats),
            patch("campus_guard.system.subprocess.run", return_value=mock_proc) as mock_subproc,
        ):
            # 第一次调用：应该执行 netsh
            info1 = sys_mod.get_wifi_info(force=False)
            self.assertIn("Campus-WiFi", info1)
            self.assertEqual(mock_subproc.call_count, 1)

            # 紧接着第二次调用：命中 120s 缓存，不应该重复调用 netsh（避免触发 Windows 定位提示）
            info2 = sys_mod.get_wifi_info(force=False)
            self.assertEqual(info2, info1)
            self.assertEqual(mock_subproc.call_count, 1)

            # 强制刷新：应该再次执行 netsh
            info3 = sys_mod.get_wifi_info(force=True)
            self.assertEqual(info3, info1)
            self.assertEqual(mock_subproc.call_count, 2)

    def test_trim_process_memory(self):
        from campus_guard.system import trim_process_memory

        result = trim_process_memory()
        self.assertTrue(result)

    def test_network_monitor_effective_interval(self):
        from campus_guard.network import NetworkMonitor
        from campus_guard.battery import BatteryTracker

        monitor = NetworkMonitor(lambda _: None, BatteryTracker())

        # 1. 稳定在线状态：自动拉长心跳至至少10秒节电
        monitor.is_online = True
        self.assertEqual(monitor.effective_check_interval(2), 10)
        self.assertEqual(monitor.effective_check_interval(15), 15)

        # 2. 掉线状态：瞬间切入急速模式（默认2秒）
        monitor.is_online = False
        self.assertEqual(monitor.effective_check_interval(10), 2)

        # 3. 正在重连中：急速冲刺
        monitor.is_online = True
        monitor._reconnecting = True
        self.assertEqual(monitor.effective_check_interval(10), 2)


if __name__ == "__main__":
    unittest.main()

