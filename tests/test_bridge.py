from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from campus_guard.bridge import ApiBridge


class TestApiBridge(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = ApiBridge()

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

    @patch("campus_guard.bridge.campus_login", return_value=(True, "认证成功"))
    def test_quick_connect(self, mock_login) -> None:
        res = self.bridge.quick_connect("20240901001", "password123")
        self.assertTrue(res["success"])
        self.assertIn("认证成功", res["message"])

    @patch("campus_guard.bridge.campus_login", return_value=(True, "一键认证OK"))
    def test_quick_connect_with_real_network_monitor(self, mock_login) -> None:
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

    @patch("campus_guard.bridge.campus_login", side_effect=[(False, "无法连接网关"), (True, "重试自愈成功")])
    @patch("campus_guard.bridge.auto_detect_portal_config", return_value=(True, "嗅探成功", {"campus_auth_url": "http://10.200.84.3:801/login"}))
    def test_quick_connect_auto_heal_retry(self, mock_sniff, mock_login) -> None:
        res = self.bridge.quick_connect("20240901001", "password123")
        self.assertTrue(res["success"])
        self.assertIn("重试自愈成功", res["message"])
        self.assertEqual(mock_login.call_count, 2)
        mock_sniff.assert_called()

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


if __name__ == "__main__":
    unittest.main()


