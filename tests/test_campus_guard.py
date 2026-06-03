import importlib
import unittest
from types import SimpleNamespace

from campus_guard import Config, GuardState, build_auth_params, get_tray_color, is_authorized


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


if __name__ == "__main__":
    unittest.main()
