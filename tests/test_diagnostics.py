from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from campus_guard import diagnostics


class TestDiagnostics(unittest.TestCase):
    def test_sanitize_config_for_diagnostics_masks_secrets(self):
        raw_cfg = {
            "campus_username": "20230001",
            "campus_password": "plain_password_123",
            "telegram_bot_token": "12345678:ABCdefGHI",
            "feishu_webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/secret-hook",
            "dingtalk_webhook": "",
            "dingtalk_secret": "SEC_super_secret",
            "network_mode": "campus",
            "proxy_port": 7897,
        }
        sanitized = diagnostics.sanitize_config_for_diagnostics(raw_cfg)

        self.assertEqual(sanitized["campus_password"], "***已配置***")
        self.assertEqual(sanitized["telegram_bot_token"], "***已配置***")
        self.assertEqual(sanitized["feishu_webhook"], "***已配置***")
        self.assertEqual(sanitized["dingtalk_webhook"], "")
        self.assertEqual(sanitized["dingtalk_secret"], "***已配置***")
        self.assertEqual(sanitized["network_mode"], "campus")
        self.assertEqual(sanitized["proxy_port"], 7897)
        self.assertNotIn("plain_password_123", json.dumps(sanitized, ensure_ascii=False))
        self.assertNotIn("ABCdefGHI", json.dumps(sanitized, ensure_ascii=False))
        self.assertNotIn("SEC_super_secret", json.dumps(sanitized, ensure_ascii=False))

    def test_collect_diagnostics_returns_expected_structure(self):
        mock_cfg = {
            "campus_password": "secret_password",
            "telegram_bot_token": "999999:XYZ",
            "network_mode": "auto",
            "university_id": "yau",
            "auth_protocol": "drcom",
            "campus_auth_url": "http://10.200.84.3/eportal/index.jsp",
            "campus_gateway": "10.200.84.3",
            "auto_start_proxy": True,
            "proxy_port": 7897,
            "autostart": True,
            "start_minimized_on_boot": True,
            "close_action": "ask",
        }
        with (
            patch("campus_guard.diagnostics.get_config_dict", return_value=mock_cfg),
            patch("campus_guard.diagnostics.get_wifi_info", return_value="Campus-WiFi"),
            patch("campus_guard.diagnostics.get_local_ip", return_value="10.200.1.10"),
            patch("campus_guard.diagnostics.check_campus_gateway", return_value=True),
            patch("campus_guard.diagnostics.check_internet", return_value=True),
            patch(
                "campus_guard.diagnostics.detect_clash_client",
                return_value={"found": True, "client_name": "Clash Verge", "running": True, "port": 7897},
            ),
        ):
            report = diagnostics.collect_diagnostics()

        self.assertEqual(report["wifi"], "Campus-WiFi")
        self.assertEqual(report["local_ip"], "10.200.1.10")
        self.assertTrue(report["gateway_ok"])
        self.assertTrue(report["internet_ok"])
        self.assertTrue(report["proxy_client"]["found"])
        self.assertEqual(report["config_summary"]["campus_password"], "***已配置***")
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("secret_password", serialized)
        self.assertNotIn("999999:XYZ", serialized)

        text = diagnostics.format_diagnostics_text(report)
        self.assertIn("Campus-WiFi", text)
        self.assertIn("Clash Verge", text)

    def test_export_diagnostic_bundle_creates_sanitized_zip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            fake_log = tmp_path / "campus_guard.log"
            fake_log.write_text(
                "2026-11-23 10:00:00 [INFO] login url=http://10.200.84.3/login?user_account=123&user_password=MySecretPwd123\n"
                "2026-11-23 10:00:01 [INFO] tg https://api.telegram.org/bot12345678:SecretBotTokenXYZ/getMe\n",
                encoding="utf-8",
            )
            out_dir = tmp_path / "out"

            with (
                patch("campus_guard.diagnostics.LOG_PATH", fake_log),
                patch(
                    "campus_guard.diagnostics.collect_diagnostics",
                    return_value={
                        "app_version": "2.3.2",
                        "generated_at": "2026-11-23T10:00:00",
                        "platform": "Windows-11",
                        "python_version": "3.12.14",
                        "wifi": "Campus-WiFi",
                        "local_ip": "10.200.1.10",
                        "gateway_ok": True,
                        "internet_ok": True,
                        "proxy_client": {"found": False},
                        "config_summary": {"campus_password": "***已配置***"},
                    },
                ),
            ):
                bundle_path = diagnostics.export_diagnostic_bundle(output_dir=out_dir)

            self.assertTrue(bundle_path.exists())
            self.assertTrue(bundle_path.name.startswith("autocampusnet_diagnostic_"))
            with zipfile.ZipFile(bundle_path, "r") as zf:
                names = set(zf.namelist())
                self.assertEqual(names, {"diagnostics.json", "diagnostics.txt", "campus_guard.log"})
                log_content = zf.read("campus_guard.log").decode("utf-8")
                self.assertNotIn("MySecretPwd123", log_content)
                self.assertNotIn("SecretBotTokenXYZ", log_content)
                self.assertIn("user_password=******", log_content)
                self.assertIn("bot12345678:******", log_content)


if __name__ == "__main__":
    unittest.main()
