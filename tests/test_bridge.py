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
        self.assertIn("一键认证OK", net_mon.last_event)

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

    @patch("campus_guard.bridge.platform.system", return_value="Windows")
    @patch("campus_guard.bridge.subprocess.run")
    def test_open_log_folder_windows(self, mock_subproc, mock_sys) -> None:
        mock_subproc.return_value = MagicMock(returncode=0)
        res = self.bridge.open_log_folder()
        self.assertTrue(res["success"], res.get("message"))
        mock_subproc.assert_called_once()

    @patch("campus_guard.bridge.platform.system", return_value="Linux")
    @patch("campus_guard.bridge.subprocess.run")
    def test_open_log_folder_linux(self, mock_subproc, mock_sys) -> None:
        mock_subproc.return_value = MagicMock(returncode=0)
        res = self.bridge.open_log_folder()
        self.assertTrue(res["success"], res.get("message"))
        mock_subproc.assert_called_once()


if __name__ == "__main__":
    unittest.main()


