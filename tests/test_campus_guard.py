import importlib
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

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
            telegram_user_id=12345678,
            campus_auth_url="http://10.200.84.3:801/eportal/portal/login",
            campus_account="test_student_2024",
            campus_password="secret",
            wlan_ac_ip="10.255.250.74",
            check_interval_seconds=5,
            network_check_interval_seconds=30,
            low_battery_threshold=30,
            autostart=True,
        )

        params = build_auth_params(config, "10.1.2.3", "aabbccddeeff")

        self.assertEqual(params["login_method"], "1")
        self.assertEqual(params["user_account"], ",0,test_student_2024")
        self.assertEqual(params["user_password"], "secret")
        self.assertEqual(params["wlan_user_ip"], "10.1.2.3")
        self.assertEqual(params["wlan_user_mac"], "aabbccddeeff")
        self.assertEqual(params["wlan_ac_ip"], "10.255.250.74")
        self.assertIn("v", params)

    def test_authorized_only_rejects_other_users(self):
        update = SimpleNamespace(effective_user=SimpleNamespace(id=123))

        self.assertFalse(is_authorized(update, 12345678))

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

    def test_network_probe_online_when_direct_internet_ok_even_if_gateway_fails(self):
        update_runtime_config({"campus_wifi_ssids": ["Campus"]})
        monitor = NetworkMonitor(lambda _: None, BatteryTracker())

        with (
            patch("campus_guard.network.is_wifi_link_up", return_value=True),
            patch("campus_guard.network.check_campus_gateway", return_value=False),
            patch("campus_guard.network.check_internet", return_value=True),
            patch("campus_guard.network.check_proxy_internet", return_value=False),
            patch("campus_guard.network.get_local_ip", return_value="10.211.89.86"),
            patch("campus_guard.network.get_wifi_info", return_value="Campus (90%)"),
        ):
            snapshot = monitor.probe_connectivity()

        self.assertEqual(snapshot.state, ConnectivityState.ONLINE)
        self.assertTrue(snapshot.gateway_ok)
        self.assertTrue(snapshot.internet_direct_ok)

    def test_ping_check_fallback(self):
        from campus_guard.system import ping_check

        self.assertFalse(ping_check("0.0.0.0"))
        self.assertFalse(ping_check(""))

    def test_telegram_bot_health_check_keeps_running(self):
        import asyncio
        from campus_guard.telegram_bot import TelegramBot
        from unittest.mock import AsyncMock

        bot = TelegramBot(None, None, BatteryTracker())
        mock_app = MagicMock()
        mock_app.updater.running = True
        mock_app.bot.get_me = AsyncMock(return_value=SimpleNamespace(username="test_bot"))
        bot.app = mock_app

        asyncio.run(bot._health_check())
        self.assertEqual(bot._consecutive_probe_failures, 0)

    def test_telegram_bot_health_check_skips_when_network_offline(self):
        import asyncio
        from campus_guard.telegram_bot import TelegramBot
        from unittest.mock import AsyncMock

        mock_network = MagicMock()
        mock_network.is_online = False

        bot = TelegramBot(None, mock_network, BatteryTracker())
        mock_app = MagicMock()
        mock_app.updater.running = False  # updater not running
        mock_app.updater.start_polling = AsyncMock()
        bot.app = mock_app

        # Because network.is_online is False, _health_check should return immediately without restarting polling
        asyncio.run(bot._health_check())
        mock_app.updater.start_polling.assert_not_called()

    def test_sensitive_data_filter(self):
        import logging
        from campus_guard.logging_setup import SensitiveDataFilter

        sanitized = SensitiveDataFilter.sanitize(
            "Request failed: url=http://10.200.84.3:801/login?user_account=123&user_password=SecretPass123&v=10"
        )
        self.assertNotIn("SecretPass123", sanitized)
        self.assertIn("user_password=******", sanitized)

        token_sanitized = SensitiveDataFilter.sanitize(
            "Connecting to https://api.telegram.org/bot12345678:ABCdefGHIjkLMNopQRsTuVwXyz/getUpdates"
        )
        self.assertNotIn("ABCdefGHIjkLMNopQRsTuVwXyz", token_sanitized)
        self.assertIn("bot12345678:******", token_sanitized)


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

        # 验证数字错误代码 512 映射 (密码错误)
        ok, msg = parse_drcom_response('dr1003({"result":0,"msg":"512"})')
        self.assertFalse(ok)
        self.assertIn("密码错误", msg)

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
            patch("campus_guard.auth.get_default_gateway", return_value=""),
        ):
            ok, msg, extracted = auto_detect_portal_config()

        self.assertTrue(ok)
        self.assertIn("成功捕获", msg)
        self.assertEqual(extracted.get("campus_wifi_ssid"), "Campus-5G")
        self.assertEqual(extracted.get("campus_auth_url"), "http://10.200.84.3:801/eportal/portal/login")
        self.assertEqual(extracted.get("campus_gateway"), "10.200.84.3")
        self.assertEqual(extracted.get("wlan_ac_ip"), "10.255.250.74")
        self.assertEqual(extracted.get("wlan_user_ip"), "10.1.2.3")

        # 验证当跳转主机为公共 IP (如 1.1.1.1) 时，被安全过滤器拦截排除，杜绝误识别
        mock_resp_1111 = Mock()
        mock_resp_1111.status_code = 302
        mock_resp_1111.headers = {"Location": "http://1.1.1.1/login"}
        mock_resp_1111.text = ""
        with (
            patch("requests.Session.get", return_value=mock_resp_1111),
            patch("campus_guard.auth.get_wifi_info", return_value="Campus-5G"),
            patch("campus_guard.auth.get_local_ip", return_value="10.1.2.3"),
            patch("campus_guard.auth.get_default_gateway", return_value="10.211.0.1"),
        ):
            ok, msg, extracted = auto_detect_portal_config()
        self.assertFalse(ok)

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

    def test_continuous_offline_self_healing_reconnect(self):
        """验证网络持续处于离线状态时，掉线探针具备持续自愈重试调度能力，不会在首轮失败后停滞。"""
        import time
        from campus_guard.models import ConnectivitySnapshot
        reconnect_calls = []

        monitor = NetworkMonitor(lambda _: None, BatteryTracker())
        monitor._trigger_reconnect = lambda: reconnect_calls.append(time.time())

        # 模拟快照持续处于离线断网状态
        offline_snap = ConnectivitySnapshot(
            state=ConnectivityState.INTERNET_DOWN,
            wifi_ok=True,
            gateway_ok=True,
            internet_direct_ok=False,
            internet_proxy_ok=False,
            local_ip="10.211.110.229",
            wifi_info="YADX-STU (90%)",
            clash_tun=False,
            reason="直连外网不通",
            is_campus_network=True,
        )

        with patch.object(monitor, "probe_connectivity", return_value=offline_snap):
            # 1. 首次在线转离线：触发边缘自愈
            monitor.is_online = True
            monitor._run_probe_and_handle()
            self.assertEqual(len(reconnect_calls), 1)
            self.assertFalse(monitor.is_online)

            # 2. 持续离线但处于冷却中：不重复轰炸
            monitor._last_reconnect_attempt = time.time()  # 刚刚重试过
            monitor._run_probe_and_handle()
            self.assertEqual(len(reconnect_calls), 1)

            # 3. 冷却时间过去后，持续离线探针再次调度自愈重连
            monitor._last_reconnect_attempt = time.time() - 20  # 已过冷却时间
            monitor._run_probe_and_handle()
            self.assertEqual(len(reconnect_calls), 2)

    def test_gateway_check_prioritizes_auth_server_port(self):
        """验证网关探活优先探测 campus_auth_url 中的认证端点与端口，解决默认网关禁 ping 导致的误判。"""
        from campus_guard.system import check_campus_gateway

        update_runtime_config({
            "campus_auth_url": "http://10.200.84.3:801/eportal/portal/login",
            "campus_gateway": "10.211.0.1",
        })

        # 模拟：默认物理网关 10.211.0.1 不通，但认证网关 10.200.84.3:801 通
        def fake_tcp_check(host, port, timeout=0.8):
            if host == "10.200.84.3" and port == 801:
                return True
            return False

        with (
            patch("campus_guard.system.tcp_check", side_effect=fake_tcp_check),
            patch("campus_guard.system.ping_check", return_value=False),
            patch("campus_guard.system.get_default_gateway", return_value="10.211.0.1"),
        ):
            ok = check_campus_gateway()
            self.assertTrue(ok, "当认证网关 10.200.84.3:801 可达时，即使物理网关未开放端口，也必须判定网关可达")

    def test_auto_detect_portal_js_replace_redirect(self):
        """验证智能嗅探支持 HTML 中各种复杂 JS 跳转语法 (如 location.replace 与 top.self.location.href)。"""
        from campus_guard.auth import auto_detect_portal_config

        # 模拟深澜/Dr.COM 常见的 location.replace 页面
        js_replace_html = """
        <html><head><script type="text/javascript">
            location.replace("http://10.200.84.3:801/eportal/portal/login?wlanuserip=10.211.110.229&wlanacip=10.255.250.74");
        </script></head><body></body></html>
        """
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.headers = {}
        mock_resp.text = js_replace_html
        mock_resp.url = "http://1.2.3.4/"

        with (
            patch("requests.Session.get", return_value=mock_resp),
            patch("campus_guard.auth.get_wifi_info", return_value="YADX-STU (88%)"),
            patch("campus_guard.auth.get_local_ip", return_value="10.211.110.229"),
            patch("campus_guard.auth.get_default_gateway", return_value="10.211.0.1"),
        ):
            ok, msg, extracted = auto_detect_portal_config()
            self.assertTrue(ok)
            self.assertEqual(extracted.get("wlan_user_ip"), "10.211.110.229")
            self.assertEqual(extracted.get("wlan_ac_ip"), "10.255.250.74")
            self.assertEqual(extracted.get("auth_protocol"), "drcom")

    def test_auto_detect_portal_smart_fallback_when_already_online(self):
        """验证当 Captive 探针未被 302 劫持时，通过 SSID 与认证服务器主动探活智能回退识别延安大学。"""
        from campus_guard.auth import auto_detect_portal_config

        # 探针均返回 204（未劫持）
        mock_resp = Mock()
        mock_resp.status_code = 204
        mock_resp.headers = {}
        mock_resp.text = ""

        with (
            patch("requests.Session.get", return_value=mock_resp),
            patch("campus_guard.auth.get_wifi_info", return_value="YADX-STU (92%)"),
            patch("campus_guard.auth.get_local_ip", return_value="10.211.110.229"),
            patch("campus_guard.auth.get_default_gateway", return_value="10.211.0.1"),
            patch("campus_guard.system.tcp_check", return_value=True),
        ):
            ok, msg, extracted = auto_detect_portal_config()
            self.assertTrue(ok)
            self.assertIn("延安大学", msg)
            self.assertEqual(extracted.get("university_id"), "yau")
            self.assertEqual(extracted.get("auth_protocol"), "drcom")
            self.assertEqual(extracted.get("campus_auth_url"), "http://10.200.84.3:801/eportal/portal/login")


    def test_yau_new_campus_ip_recognition(self):
        """验证延安大学新校区 172.30.x.x IP 网段可精准反推归属高校。"""
        from campus_guard.universities import get_university_manager

        mgr = get_university_manager()
        prof = mgr.infer_by_ssid_and_ip("未知", "172.30.212.26")
        self.assertIsNotNone(prof)
        self.assertEqual(prof.id, "yau")
        self.assertIn("延安大学", prof.name)

    def test_try_reconnect_forces_wifi_refresh_on_gateway_unreachable(self):
        """验证在网络离线且网关不可达（网卡假死）时，自愈重连强制触发 Wi-Fi 重连刷新链路。"""
        from campus_guard.battery import BatteryTracker
        from campus_guard.models import ConnectivitySnapshot, ConnectivityState
        from campus_guard.network import NetworkMonitor

        tracker = BatteryTracker()
        monitor = NetworkMonitor(lambda msg: None, tracker)
        monitor.retry_count = 1  # 已有连续失败记录

        offline_snap = ConnectivitySnapshot(
            state=ConnectivityState.GATEWAY_DOWN,
            wifi_ok=True,
            gateway_ok=False,
            internet_direct_ok=False,
            internet_proxy_ok=False,
            local_ip="10.211.110.229",
            wifi_info="YADX-STU (85%)",
            clash_tun=False,
            reason="校园网网关不可达",
            is_campus_network=True,
            active_interface="WLAN",
        )
        monitor.last_snapshot = offline_snap

        with (
            patch("campus_guard.network.reconnect_wifi") as mock_reconn,
            patch("campus_guard.network.campus_login", return_value=(True, "认证成功")),
            patch.object(monitor, "probe_connectivity", return_value=offline_snap),
        ):
            monitor._try_reconnect()
            # 确认调用了 reconnect_wifi 且 force=True
            self.assertTrue(mock_reconn.called)
            _args, kwargs = mock_reconn.call_args
            self.assertTrue(kwargs.get("force", False))

    def test_bot_boost_command_registered_and_executable(self):
        """验证 Telegram Bot 注册了 /boost 与 /sniff 指令且 _cmd_boost 正常执行。"""
        import asyncio
        from campus_guard.telegram_bot import TelegramBot, bot_command_specs

        specs = dict(bot_command_specs())
        self.assertIn("boost", specs)

        bot = TelegramBot(None, None, Mock())
        mock_update = Mock()
        mock_update.effective_user.id = 8512030855
        mock_update.message.reply_text = Mock(return_value=asyncio.Future())
        mock_update.message.reply_text.return_value.set_result(None)

        with (
            patch.object(bot, "_is_authorized", return_value=True),
            patch("campus_guard.auth.auto_detect_portal_config", return_value=(True, "成功", {"university_name": "延安大学", "auth_protocol": "drcom"})),
            patch("campus_guard.auth.campus_login", return_value=(True, "登录成功")),
            patch("campus_guard.system.check_campus_gateway", return_value=True),
            patch("campus_guard.system.check_internet", return_value=True),
            patch("campus_guard.system.get_wifi_info", return_value="YADX-STU (90%)"),
            patch("campus_guard.system.get_local_ip", return_value="10.211.110.229"),
        ):
            asyncio.run(bot._cmd_boost(mock_update, Mock()))
            self.assertTrue(mock_update.message.reply_text.called)
            # 校验回复中包含自愈完成与延安大学
            calls = [c[0][0] for c in mock_update.message.reply_text.call_args_list]
            self.assertTrue(any("延安大学" in c for c in calls))

    def test_reconnect_wifi_force_parameter(self):
        """验证 reconnect_wifi 在 force=True 时绕过短路直接执行系统无线连接。"""
        from campus_guard.system import reconnect_wifi

        with (
            patch("campus_guard.system.get_wifi_info", return_value="YADX-STU (85%)"),
            patch("campus_guard.system.get_local_ip", return_value="10.211.110.229"),
            patch("campus_guard.system.get_saved_wifi_profiles", return_value=["YADX-STU", "Home"]),
            patch("campus_guard.system.is_wifi_link_up", return_value=False),
            patch("time.sleep"),
            patch("subprocess.run") as mock_run,
        ):
            mock_proc = Mock()
            mock_proc.returncode = 0
            mock_proc.stdout = b"Connection request was completed successfully."
            mock_proc.stderr = b""
            mock_run.return_value = mock_proc

            # force=False 时应短路
            res_no_force = reconnect_wifi("YADX-STU", force=False)
            self.assertTrue(res_no_force)
            self.assertFalse(mock_run.called)

            # force=True 时应真正执行 subprocess netsh connect
            res_forced = reconnect_wifi("YADX-STU", force=True)
            self.assertTrue(res_forced)
            self.assertTrue(mock_run.called)

    def test_probe_and_handle_initial_offline_triggers_reconnect_without_deadlock(self):
        """验证初始离线状态下 _run_probe_and_handle 不会自死锁，并能完整触发 Wi-Fi 重连与认证。"""
        import threading
        from campus_guard.battery import BatteryTracker
        from campus_guard.models import ConnectivitySnapshot, ConnectivityState
        from campus_guard.network import NetworkMonitor

        notifications = []
        monitor = NetworkMonitor(notifications.append, BatteryTracker())
        monitor._is_probing = True

        offline_snap = ConnectivitySnapshot(
            state=ConnectivityState.WIFI_DOWN,
            wifi_ok=False,
            gateway_ok=False,
            internet_direct_ok=False,
            internet_proxy_ok=False,
            local_ip="未知",
            wifi_info="未连接",
            clash_tun=False,
            reason="WiFi 链路断开",
            is_campus_network=True,
            active_interface="未知网卡",
        )
        online_snap = ConnectivitySnapshot(
            state=ConnectivityState.ONLINE,
            wifi_ok=True,
            gateway_ok=True,
            internet_direct_ok=True,
            internet_proxy_ok=False,
            local_ip="10.211.110.229",
            wifi_info="YADX-STU (90%)",
            clash_tun=False,
            reason="网络在线 (校园网)",
            is_campus_network=True,
            active_interface="WLAN",
        )

        reconnect_done = threading.Event()

        def fake_login():
            reconnect_done.set()
            return True, "认证成功"

        with (
            patch.object(monitor, "probe_connectivity", side_effect=[offline_snap, offline_snap, online_snap]),
            patch("campus_guard.network.reconnect_wifi", return_value=True) as mock_reconn,
            patch("campus_guard.network.campus_login", side_effect=fake_login) as mock_login,
            patch.object(monitor, "_wait", return_value=False),
        ):
            t = threading.Thread(target=monitor._run_probe_and_handle, daemon=True)
            t.start()
            t.join(timeout=3.0)
            self.assertFalse(t.is_alive(), "检测到 _run_probe_and_handle 发生线程死锁！")
            self.assertFalse(monitor._is_probing)
            self.assertTrue(reconnect_done.wait(timeout=3.0), "未触发异步重连认证流程！")
            mock_reconn.assert_called()
            mock_login.assert_called()

    def test_probe_and_handle_online_to_offline_and_retry_without_deadlock(self):
        """验证在线→断网边缘触发以及冷却后持续离线周期调度均不死锁，且最终能恢复在线。"""
        import threading
        from campus_guard.battery import BatteryTracker
        from campus_guard.models import ConnectivitySnapshot, ConnectivityState
        from campus_guard.network import NetworkMonitor

        monitor = NetworkMonitor(lambda _msg: None, BatteryTracker())
        monitor.is_online = True

        offline_snap = ConnectivitySnapshot(
            state=ConnectivityState.GATEWAY_DOWN,
            wifi_ok=True,
            gateway_ok=False,
            internet_direct_ok=False,
            internet_proxy_ok=False,
            local_ip="10.211.110.229",
            wifi_info="YADX-STU (88%)",
            clash_tun=False,
            reason="校园网网关不可达",
            is_campus_network=True,
            active_interface="WLAN",
        )
        online_snap = ConnectivitySnapshot(
            state=ConnectivityState.ONLINE,
            wifi_ok=True,
            gateway_ok=True,
            internet_direct_ok=True,
            internet_proxy_ok=False,
            local_ip="10.211.110.229",
            wifi_info="YADX-STU (90%)",
            clash_tun=False,
            reason="网络在线 (校园网)",
            is_campus_network=True,
            active_interface="WLAN",
        )

        # 第一次边缘触发：先让重连线程同步占位完成（模拟首次重连仍未成功）
        with (
            patch.object(monitor, "probe_connectivity", return_value=offline_snap),
            patch.object(monitor, "_trigger_reconnect") as mock_trig1,
        ):
            monitor._is_probing = True
            t1 = threading.Thread(target=monitor._run_probe_and_handle, daemon=True)
            t1.start()
            t1.join(timeout=3.0)
            self.assertFalse(t1.is_alive())
            self.assertFalse(monitor.is_online)
            self.assertFalse(monitor._is_probing)
            mock_trig1.assert_called_once()

        # 第二次持续离线冷却到期：再次自动调度自愈重连，并恢复在线
        monitor._reconnecting = False
        monitor._last_reconnect_attempt = 0.0
        with (
            patch.object(monitor, "probe_connectivity", side_effect=[offline_snap, online_snap]),
            patch.object(monitor, "_trigger_reconnect") as mock_trig2,
        ):
            monitor._is_probing = True
            t2 = threading.Thread(target=monitor._run_probe_and_handle, daemon=True)
            t2.start()
            t2.join(timeout=3.0)
            self.assertFalse(t2.is_alive())
            self.assertFalse(monitor._is_probing)
            mock_trig2.assert_called_once()

            monitor._is_probing = True
            t3 = threading.Thread(target=monitor._run_probe_and_handle, daemon=True)
            t3.start()
            t3.join(timeout=3.0)
            self.assertTrue(monitor.is_online)

    def test_get_local_mac_does_not_cache_fallback_bluetooth_mac(self):
        """验证断网回退的蓝牙 MAC 不会永久污染 _cached_mac，连上 WLAN 后能拿到真实 MAC。"""
        from campus_guard import system as sys_mod

        old_cache = sys_mod._cached_mac
        try:
            sys_mod._cached_mac = None
            with patch(
                "campus_guard.system.get_primary_interface_info",
                side_effect=[
                    ("未知网卡", "未知", "c85ea9797308"),
                    ("WLAN", "10.211.110.229", "c85ea9797304"),
                ],
            ):
                mac_offline = sys_mod.get_local_mac()
                self.assertIsNone(sys_mod._cached_mac)
                self.assertEqual(len(mac_offline), 12)

                mac_online = sys_mod.get_local_mac()
                self.assertEqual(mac_online, "c85ea9797304")
                self.assertEqual(sys_mod._cached_mac, "c85ea9797304")
        finally:
            sys_mod._cached_mac = old_cache

    def test_reconnect_wifi_returns_false_and_tries_next_ssid_on_no_ip(self):
        """验证第一个 SSID 未获取到有效 IP 时不会假返回 True，而是继续尝试下一个；全失败返回 False。"""
        from campus_guard.system import reconnect_wifi

        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_proc.stdout = b"Connection request was completed successfully."
        mock_proc.stderr = b""

        # 前 16 次检查（第一个 SSID）无有效 IP，第 17 次（第二个 SSID）获取到有效 IP
        ip_seq = ["未知"] * 16 + ["10.211.110.229"]
        with (
            patch("campus_guard.system.get_config_dict", return_value={"campus_wifi_ssid": "YADX-TEA", "campus_wifi_ssids": ["YADX-STU"]}),
            patch("campus_guard.system.get_saved_wifi_profiles", return_value=["YADX-TEA", "YADX-STU"]),
            patch("campus_guard.system.is_wifi_link_up", return_value=False),
            patch("campus_guard.system.get_local_ip", side_effect=ip_seq),
            patch("time.sleep"),
            patch("subprocess.run", return_value=mock_proc) as mock_run,
        ):
            ok = reconnect_wifi(force=True)
            self.assertTrue(ok)
            self.assertEqual(mock_run.call_count, 2)
            self.assertIn("name=YADX-TEA", mock_run.call_args_list[0][0][0])
            self.assertIn("name=YADX-STU", mock_run.call_args_list[1][0][0])

        # 所有候选均拿不到有效 IP 时，应返回 False
        with (
            patch("campus_guard.system.get_config_dict", return_value={"campus_wifi_ssid": "YADX-STU", "campus_wifi_ssids": []}),
            patch("campus_guard.system.get_saved_wifi_profiles", return_value=["YADX-STU"]),
            patch("campus_guard.system.is_wifi_link_up", return_value=False),
            patch("campus_guard.system.get_local_ip", return_value="未知"),
            patch("time.sleep"),
            patch("subprocess.run", return_value=mock_proc),
        ):
            self.assertFalse(reconnect_wifi(force=True))

    def test_wifi_signature_prevents_polling_after_ttl_when_unchanged(self):
        """验证即使超过 120s TTL，只要 WLAN 状态与 IP 签名未变，就不再调外部进程（彻底消除定位闪烁）。"""
        import campus_guard.system as sys_mod

        old_cache = sys_mod._wlan_cache
        old_sig = sys_mod._wlan_sig_cache
        try:
            sys_mod._wlan_cache = (0.0, "未知", -1)
            sys_mod._wlan_sig_cache = None

            mock_stats = {"WLAN": SimpleNamespace(isup=True)}
            sig_seq = [
                (True, "WLAN", "10.211.130.38"),
                (True, "WLAN", "10.211.130.38"),  # 签名未变
                (True, "WLAN", "10.211.130.99"),  # IP 发生改变，自动刷新
            ]
            proc1 = SimpleNamespace(returncode=0, stdout=b"YADX-STU 6\r\n", stderr=b"")
            proc2 = SimpleNamespace(returncode=0, stdout=b"Home_5G\r\n", stderr=b"")

            with (
                patch("campus_guard.system._get_wlan_signature", side_effect=sig_seq),
                patch("campus_guard.system.sys.platform", "win32"),
                patch("campus_guard.system.get_config_dict", return_value={"campus_wifi_ssid": "YADX-STU"}),
                patch("campus_guard.system.subprocess.run", side_effect=[proc1, proc2]) as mock_run,
            ):
                info1 = sys_mod.get_wifi_info(force=False)
                self.assertIn("YADX-STU", info1)
                self.assertNotIn("6", info1)
                self.assertEqual(mock_run.call_count, 1)

                # 模拟时间过去 1 小时（远超 120s），但签名未变 -> 不得再次触发查询
                sys_mod._wlan_cache = (1.0, info1, 100)
                info2 = sys_mod.get_wifi_info(force=False)
                self.assertEqual(info2, info1)
                self.assertEqual(mock_run.call_count, 1)

                # 签名改变（IP 变更）-> 立即走无定位 NLA 刷新，且命令不是 netsh wlan
                info3 = sys_mod.get_wifi_info(force=False)
                self.assertIn("Home_5G", info3)
                self.assertEqual(mock_run.call_count, 2)
                for call_item in mock_run.call_args_list:
                    cmd_list = call_item[0][0]
                    self.assertNotEqual(cmd_list[0], "netsh")
        finally:
            sys_mod._wlan_cache = old_cache
            sys_mod._wlan_sig_cache = old_sig

    def test_setup_autostart_migrates_legacy_campusguard_entry(self):
        """验证 setup_autostart 写入新 AnLan 自启项并清理旧 CampusGuard 残留项。"""
        import sys
        import types
        from campus_guard import runtime

        mock_key = MagicMock()
        mock_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER="HKCU",
            KEY_SET_VALUE=2,
            REG_SZ=1,
            OpenKey=MagicMock(return_value=mock_key),
            SetValueEx=MagicMock(),
            DeleteValue=MagicMock(),
            CloseKey=MagicMock(),
        )
        with (
            patch("campus_guard.runtime.platform.system", return_value="Windows"),
            patch.dict(sys.modules, {"winreg": mock_winreg}),
            patch("campus_guard.runtime.subprocess.run") as mock_subproc,
        ):
            runtime.setup_autostart()
            mock_winreg.SetValueEx.assert_called_once()
            self.assertEqual(mock_winreg.SetValueEx.call_args[0][1], "AnLan")
            mock_winreg.DeleteValue.assert_called_with(mock_key, "CampusGuard")
            # 确认调用过清理旧计划任务
            schtasks_cmds = [c[0][0] for c in mock_subproc.call_args_list]
            self.assertTrue(any("/delete" in cmd and "CampusGuard" in cmd for cmd in schtasks_cmds))


if __name__ == "__main__":
    unittest.main()

