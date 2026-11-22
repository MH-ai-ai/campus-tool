from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from campus_guard.bridge import ApiBridge


class TestApiBridge(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = ApiBridge()
        self._save_patcher = patch("campus_guard.bridge.save_config_raw")
        self._mock_save = self._save_patcher.start()

    def tearDown(self) -> None:
        self._save_patcher.stop()

    def test_get_state_structure(self) -> None:
        state = self.bridge.get_state()
        self.assertIn("online", state)
        self.assertIn("wifi", state)
        self.assertIn("ip", state)
        self.assertIn("battery", state)
        self.assertIn("percent", state["battery"])
        self.assertIn("system", state)
        self.assertIn("uptime_seconds", state["system"])
        self.assertIn("university_name", state)

    def test_search_universities_returns_matches(self) -> None:
        results = self.bridge.search_universities("延安")
        self.assertTrue(len(results) > 0)
        first = results[0]
        self.assertIn("延安大学", first["name"])

    def test_get_logs_returns_list(self) -> None:
        logs = self.bridge.get_logs(max_lines=10)
        self.assertIsInstance(logs, list)

    @patch("campus_guard.bridge.campus_login", return_value=(True, "模拟登录成功"))
    def test_auth_campus(self, mock_login) -> None:
        res = self.bridge.auth_campus()
        self.assertTrue(res["success"])
        self.assertEqual(res["message"], "模拟登录成功")

    def test_telegram_in_state(self) -> None:
        state = self.bridge.get_state()
        self.assertIn("telegram", state)
        self.assertIn("configured", state["telegram"])
        self.assertIn("user_id", state["telegram"])
        self.assertIn("is_running", state["telegram"])

    def test_test_telegram_bot_when_unconfigured(self) -> None:
        with patch("campus_guard.bridge.get_config_dict", return_value={"telegram_bot_token": ""}):
            res = self.bridge.test_telegram_bot()
            self.assertFalse(res["success"])
            self.assertIn("尚未配置", res["message"])

    @patch("campus_guard.bridge.reconnect_wifi", return_value=True)
    @patch("campus_guard.bridge.get_local_ip", return_value="10.211.0.100")
    @patch("campus_guard.bridge.is_wifi_link_up", return_value=True)
    @patch("campus_guard.bridge.campus_login", return_value=(True, "认证成功"))
    def test_quick_connect(self, mock_login, mock_wifi_up, mock_ip, mock_reconn) -> None:
        res = self.bridge.quick_connect("20240901001", "password123")
        self.assertTrue(res["success"])
        self.assertIn("认证成功", res["message"])

    @patch("campus_guard.bridge.reconnect_wifi", return_value=True)
    @patch("campus_guard.bridge.get_local_ip", return_value="10.211.0.100")
    @patch("campus_guard.bridge.is_wifi_link_up", return_value=True)
    @patch("campus_guard.bridge.campus_login", return_value=(True, "一键认证OK"))
    def test_quick_connect_with_real_network_monitor(self, mock_login, mock_wifi_up, mock_ip, mock_reconn) -> None:
        from campus_guard.battery import BatteryTracker
        from campus_guard.network import NetworkMonitor

        tracker = BatteryTracker()
        net_mon = NetworkMonitor(notify_callback=lambda x: None, tracker=tracker)
        bridge = ApiBridge(network_monitor=net_mon)

        res = bridge.quick_connect("20240901001", "password123")
        self.assertTrue(res["success"])
    @patch("campus_guard.bridge.auto_detect_portal_config", return_value=(True, "捕获成功", {"campus_auth_url": "http://10.211.0.1/login"}))
    def test_auto_sniff(self, mock_sniff) -> None:
        res = self.bridge.auto_sniff()
        self.assertTrue(res["success"])
        self.assertEqual(res["message"], "捕获成功")
        self.assertEqual(res["detected"]["campus_auth_url"], "http://10.211.0.1/login")

    @patch("campus_guard.bridge.reconnect_wifi", return_value=True)
    @patch("campus_guard.bridge.get_local_ip", return_value="10.211.0.100")
    @patch("campus_guard.bridge.is_wifi_link_up", return_value=True)
    @patch("campus_guard.bridge.campus_login", side_effect=[(False, "无法连接网关"), (True, "重试自愈成功")])
    @patch("campus_guard.bridge.auto_detect_portal_config", return_value=(True, "嗅探成功", {"campus_auth_url": "http://10.200.84.3:801/eportal/portal/login"}))
    def test_quick_connect_auto_heal_retry(self, mock_sniff, mock_login, mock_wifi_up, mock_ip, mock_reconn) -> None:
        res = self.bridge.quick_connect("20240901001", "password123")
        self.assertTrue(res["success"])
        self.assertIn("重试自愈成功", res["message"])
        self.assertEqual(mock_login.call_count, 2)
        mock_sniff.assert_called()
        mock_reconn.assert_called_with(force=True)

    def test_bridge_reconnect_wifi_handles_bool_return(self) -> None:
        """验证 ApiBridge.reconnect_wifi 正确处理 bool 返回值，不会因元组解包抛出 TypeError。"""
        with patch("campus_guard.bridge.reconnect_wifi", return_value=True) as mock_reconn:
            res = self.bridge.reconnect_wifi()
            self.assertTrue(res["success"])
            self.assertIn("已重新连接", res["message"])
            mock_reconn.assert_called_once_with(force=True)

        with patch("campus_guard.bridge.reconnect_wifi", return_value=False):
            res_fail = self.bridge.reconnect_wifi()
            self.assertFalse(res_fail["success"])
            self.assertIn("失败", res_fail["message"])

    @patch("campus_guard.bridge.campus_login", return_value=(True, "认证成功"))
    @patch("campus_guard.bridge.reconnect_wifi", return_value=True)
    @patch("campus_guard.bridge.get_local_ip", return_value="未知")
    @patch("campus_guard.bridge.is_wifi_link_up", return_value=False)
    def test_quick_connect_reconnects_wifi_when_disconnected(self, mock_wifi_up, mock_ip, mock_reconn, mock_login) -> None:
        """验证 Wi-Fi 断开时调用 quick_connect 会先强力拉起 Wi-Fi，再执行校园网登录。"""
        call_order = []
        mock_reconn.side_effect = lambda **kw: (call_order.append("reconnect"), True)[1]
        mock_login.side_effect = lambda: (call_order.append("login"), (True, "认证成功"))[1]

        res = self.bridge.quick_connect("20240901001", "password123")
        self.assertTrue(res["success"])
        self.assertEqual(call_order, ["reconnect", "login"])
        mock_reconn.assert_called_once_with(force=True)

    def test_export_logs_returns_dict(self) -> None:
        res = self.bridge.export_logs()
        self.assertIn("success", res)
        self.assertIn("path", res)
        self.assertIn("content", res)

    @patch("campus_guard.bridge.subprocess.run")
    def test_open_log_folder(self, mock_subproc) -> None:
        mock_subproc.return_value = MagicMock(returncode=0)
        res = self.bridge.open_log_folder()
        self.assertTrue(res["success"], res.get("message"))

    @patch("campus_guard.bridge.sys.platform", "win32")
    @patch("campus_guard.bridge.subprocess.run")
    def test_open_log_folder_windows(self, mock_subproc) -> None:
        mock_subproc.return_value = MagicMock(returncode=0)
        res = self.bridge.open_log_folder()
        self.assertTrue(res["success"], res.get("message"))
        mock_subproc.assert_called_once()
        args = mock_subproc.call_args[0][0]
        self.assertEqual(args[0], "explorer.exe")

    @patch("campus_guard.bridge.sys.platform", "linux")
    @patch("campus_guard.bridge.subprocess.run")
    def test_open_log_folder_linux(self, mock_subproc) -> None:
        mock_subproc.return_value = MagicMock(returncode=0)
        res = self.bridge.open_log_folder()
        self.assertTrue(res["success"], res.get("message"))
        mock_subproc.assert_called_once()
        args = mock_subproc.call_args[0][0]
        self.assertEqual(args[0], "xdg-open")

    def test_bridge_exposes_only_callable_methods(self) -> None:
        """验证 ApiBridge 公开属性全为 callable 方法，杜绝 pywebview 反射引发无限递归与 COM 死锁。"""
        bridge = ApiBridge(window=MagicMock(), tg_bot=MagicMock())
        public_attrs = [attr for attr in dir(bridge) if not attr.startswith("_")]
        for attr in public_attrs:
            val = getattr(bridge, attr)
            self.assertTrue(
                callable(val),
                f"Attribute '{attr}' on ApiBridge is not callable! It will be traversed by pywebview reflection and risk deadlock.",
            )

    def test_set_window(self) -> None:
        win = MagicMock()
        self.bridge.set_window(win)
        self.assertEqual(self.bridge._window, win)

    @patch(
        "campus_guard.bridge.detect_clash_client",
        return_value={"found": True, "name": "clash-verge.exe", "exe_path": r"D:\Clash Verge\clash-verge.exe", "proxy_server": "127.0.0.1:7897"},
    )
    def test_detect_proxy_client(self, mock_detect) -> None:
        res = self.bridge.detect_proxy_client()
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["name"], "clash-verge.exe")
        mock_detect.assert_called_once()

    @patch("campus_guard.bridge.launch_proxy_and_enable", return_value=(True, "已启动代理并开启系统代理"))
    def test_launch_proxy_now_applies_overrides(self, mock_launch) -> None:
        res = self.bridge.launch_proxy_now({"proxy_exe_path": r"D:\Clash\clash-verge.exe", "proxy_server": "127.0.0.1:7898"})
        self.assertTrue(res["success"])
        passed_cfg = mock_launch.call_args[0][0]
        self.assertEqual(passed_cfg["proxy_exe_path"], r"D:\Clash\clash-verge.exe")
        self.assertEqual(passed_cfg["proxy_server"], "127.0.0.1:7898")
        self.assertTrue(mock_launch.call_args.kwargs.get("force"))

    @patch("campus_guard.runtime.remove_autostart")
    @patch("campus_guard.runtime.setup_autostart")
    @patch("campus_guard.bridge.update_runtime_config")
    @patch("campus_guard.bridge.load_config_raw", return_value={"autostart": True})
    def test_save_config_syncs_autostart(self, mock_load, mock_update, mock_setup, mock_remove) -> None:
        res_on = self.bridge.save_config({"autostart": True, "start_minimized_on_boot": True})
        self.assertTrue(res_on["success"])
        mock_setup.assert_called_once()
        mock_remove.assert_not_called()

        mock_setup.reset_mock()
        res_off = self.bridge.save_config({"autostart": False})
        self.assertTrue(res_off["success"])
        mock_remove.assert_called_once()
        mock_setup.assert_not_called()

    def test_get_state_includes_app_version(self) -> None:
        from campus_guard.version import APP_VERSION

        state = self.bridge.get_state()
        self.assertEqual(state.get("version"), APP_VERSION)

    @patch("campus_guard.bridge.update_runtime_config")
    @patch("campus_guard.bridge.load_config_raw", return_value={"close_action": "ask"})
    def test_handle_close_choice_tray_and_remember(self, mock_load, mock_update) -> None:
        mock_win = MagicMock()
        self.bridge.set_window(mock_win)

        res = self.bridge.handle_close_choice("tray", remember=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "tray")
        mock_win.hide.assert_called_once()
        self._mock_save.assert_called_once()
        saved_dict = self._mock_save.call_args[0][0]
        self.assertEqual(saved_dict.get("close_action"), "tray")

    @patch("campus_guard.bridge.threading.Timer")
    def test_handle_close_choice_exit_sets_force_closing(self, mock_timer) -> None:
        res = self.bridge.handle_close_choice("exit", remember=False)
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "exit")
        self.assertTrue(self.bridge._force_closing)
        mock_timer.assert_called_once()
        mock_timer.return_value.start.assert_called_once()

    @patch("campus_guard.runtime.setup_autostart")
    @patch("campus_guard.bridge.update_runtime_config")
    @patch("campus_guard.bridge.load_config_raw", return_value={"autostart": True})
    def test_save_config_hot_starts_telegram_bot(self, mock_load, mock_update, mock_setup) -> None:
        mock_bot = MagicMock()
        bridge = ApiBridge(tg_bot=mock_bot)

        res = bridge.save_config({"telegram_bot_token": "123:abc", "telegram_user_id": "987654321"})
        self.assertTrue(res["success"])
        mock_bot.ensure_started_in_background.assert_called_once()
        saved_dict = self._mock_save.call_args[0][0]
        self.assertEqual(saved_dict.get("telegram_user_id"), 987654321)

    @patch("requests.post")
    def test_test_telegram_bot_uses_http_fallback_when_bot_not_ready(self, mock_post) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_post.return_value = mock_resp

        mock_bot = MagicMock()
        mock_bot.is_ready = False
        mock_bot.app = None
        mock_bot.loop = None
        bridge = ApiBridge(tg_bot=mock_bot)

        with patch(
            "campus_guard.bridge.get_config_dict",
            return_value={"telegram_bot_token": "123:abc", "telegram_user_id": 987654321},
        ):
            res = bridge.test_telegram_bot()

        self.assertTrue(res["success"])
        mock_bot.send_notification.assert_not_called()
        mock_post.assert_called_once()
        mock_bot.ensure_started_in_background.assert_called_once()


if __name__ == "__main__":
    unittest.main()


