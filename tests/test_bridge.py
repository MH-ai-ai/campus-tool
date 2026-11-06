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


if __name__ == "__main__":
    unittest.main()

