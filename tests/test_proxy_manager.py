from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from campus_guard import proxy_manager, runtime
from campus_guard.battery import BatteryTracker
from campus_guard.config import update_runtime_config
from campus_guard.models import ConnectivitySnapshot, ConnectivityState
from campus_guard.network import NetworkMonitor


class TestProxyManager(unittest.TestCase):
    def test_parse_proxy_host_port(self) -> None:
        self.assertEqual(proxy_manager.parse_proxy_host_port("127.0.0.1:7897"), ("127.0.0.1", 7897))
        self.assertEqual(proxy_manager.parse_proxy_host_port("http://127.0.0.1:7890"), ("127.0.0.1", 7890))
        self.assertEqual(proxy_manager.parse_proxy_host_port("http=127.0.0.1:8888;https=127.0.0.1:8888"), ("127.0.0.1", 8888))
        self.assertEqual(proxy_manager.parse_proxy_host_port("localhost"), ("localhost", 7897))
        self.assertEqual(proxy_manager.parse_proxy_host_port("bad:999999"), ("127.0.0.1", 7897))

    def test_set_windows_system_proxy_writes_registry_and_refreshes_wininet(self) -> None:
        mock_key = MagicMock()
        mock_key.__enter__ = MagicMock(return_value=mock_key)
        mock_key.__exit__ = MagicMock(return_value=False)

        mock_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER="HKCU",
            KEY_READ=1,
            KEY_SET_VALUE=2,
            REG_DWORD=4,
            REG_SZ=1,
            OpenKey=MagicMock(return_value=mock_key),
            SetValueEx=MagicMock(),
            QueryValueEx=MagicMock(side_effect=OSError("missing")),
        )
        mock_wininet = MagicMock()
        mock_ctypes = types.SimpleNamespace(windll=types.SimpleNamespace(wininet=mock_wininet))

        with (
            patch("campus_guard.proxy_manager.platform.system", return_value="Windows"),
            patch.dict(sys.modules, {"winreg": mock_winreg, "ctypes": mock_ctypes}),
        ):
            ok, msg = proxy_manager.set_windows_system_proxy(True, "http://127.0.0.1:7897")

        self.assertTrue(ok)
        self.assertIn("127.0.0.1:7897", msg)
        set_calls = {call.args[1]: call.args[4] for call in mock_winreg.SetValueEx.call_args_list}
        self.assertEqual(set_calls["ProxyEnable"], 1)
        self.assertEqual(set_calls["ProxyServer"], "127.0.0.1:7897")
        self.assertIn("10.*", set_calls["ProxyOverride"])
        self.assertIn("*.edu.cn", set_calls["ProxyOverride"])
        self.assertEqual(mock_wininet.InternetSetOptionW.call_count, 2)

    def test_detect_clash_client_prefers_running_process(self) -> None:
        fake_proc_core = MagicMock()
        fake_proc_core.info = {"name": "verge-mihomo.exe", "exe": r"D:\Clash Verge\verge-mihomo.exe"}
        fake_proc_gui = MagicMock()
        fake_proc_gui.info = {"name": "clash-verge.exe", "exe": r"D:\Clash Verge\clash-verge.exe"}

        with (
            patch("campus_guard.proxy_manager.psutil.process_iter", return_value=[fake_proc_core, fake_proc_gui]),
            patch("campus_guard.proxy_manager.get_windows_system_proxy", return_value={"enabled": False, "proxy_server": ""}),
            patch("campus_guard.proxy_manager._detect_clash_verge_port", return_value=7897),
        ):
            info = proxy_manager.detect_clash_client()

        self.assertTrue(info["found"])
        self.assertEqual(info["name"], "clash-verge.exe")
        self.assertEqual(info["exe_path"], r"D:\Clash Verge\clash-verge.exe")
        self.assertEqual(info["proxy_server"], "127.0.0.1:7897")
        self.assertTrue(info["running"])

    def test_launch_proxy_skips_when_disabled(self) -> None:
        ok, msg = proxy_manager.launch_proxy_and_enable({"auto_start_proxy": False}, force=False)
        self.assertFalse(ok)
        self.assertIn("未启用", msg)

    def test_launch_proxy_idempotent_when_already_running_and_enabled(self) -> None:
        with (
            patch("campus_guard.proxy_manager.is_proxy_process_running", return_value=True),
            patch("campus_guard.proxy_manager.tcp_check", return_value=True),
            patch("campus_guard.proxy_manager.platform.system", return_value="Windows"),
            patch(
                "campus_guard.proxy_manager.get_windows_system_proxy",
                return_value={"enabled": True, "proxy_server": "127.0.0.1:7897", "proxy_override": ""},
            ),
            patch("campus_guard.proxy_manager.set_windows_system_proxy") as mock_set_sys,
            patch("campus_guard.proxy_manager.subprocess.Popen") as mock_popen,
        ):
            ok, msg = proxy_manager.launch_proxy_and_enable(
                {
                    "auto_start_proxy": True,
                    "proxy_exe_path": r"D:\Clash Verge\clash-verge.exe",
                    "proxy_server": "127.0.0.1:7897",
                    "auto_enable_system_proxy": True,
                }
            )
        self.assertTrue(ok)
        self.assertIn("已处于开启状态", msg)
        mock_popen.assert_not_called()
        mock_set_sys.assert_not_called()

    def test_launch_proxy_starts_process_waits_port_and_enables_system_proxy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_exe = Path(tmpdir) / "clash-verge.exe"
            fake_exe.write_text("dummy", encoding="utf-8")

            with (
                patch("campus_guard.proxy_manager.is_proxy_process_running", return_value=False),
                patch("campus_guard.proxy_manager.tcp_check", return_value=False),
                patch("campus_guard.proxy_manager.wait_for_proxy_port", return_value=True) as mock_wait,
                patch("campus_guard.proxy_manager.platform.system", return_value="Windows"),
                patch(
                    "campus_guard.proxy_manager.get_windows_system_proxy",
                    return_value={"enabled": False, "proxy_server": "", "proxy_override": ""},
                ),
                patch(
                    "campus_guard.proxy_manager.set_windows_system_proxy",
                    return_value=(True, "已开启 Windows 系统代理 (127.0.0.1:7897)"),
                ) as mock_set_sys,
                patch("campus_guard.proxy_manager.subprocess.Popen") as mock_popen,
            ):
                ok, msg = proxy_manager.launch_proxy_and_enable(
                    {
                        "auto_start_proxy": True,
                        "proxy_exe_path": str(fake_exe),
                        "proxy_server": "127.0.0.1:7897",
                        "auto_enable_system_proxy": True,
                        "proxy_wait_timeout_seconds": 10,
                    }
                )

        self.assertTrue(ok)
        self.assertIn("已启动代理", msg)
        mock_popen.assert_called_once()
        mock_wait.assert_called_once()
        mock_set_sys.assert_called_once()

    def test_launch_proxy_fails_when_exe_missing(self) -> None:
        with (
            patch("campus_guard.proxy_manager.is_proxy_process_running", return_value=False),
            patch("campus_guard.proxy_manager.tcp_check", return_value=False),
            patch("campus_guard.proxy_manager.detect_clash_client", return_value={"found": False, "exe_path": ""}),
        ):
            ok, msg = proxy_manager.launch_proxy_and_enable(
                {
                    "auto_start_proxy": True,
                    "proxy_exe_path": "",
                    "proxy_server": "127.0.0.1:7897",
                }
            )
        self.assertFalse(ok)
        self.assertIn("未找到可用", msg)

    def test_network_monitor_triggers_proxy_once_per_online_session(self) -> None:
        update_runtime_config({"auto_start_proxy": True, "campus_wifi_ssids": ["YADX-STU"]})
        monitor = NetworkMonitor(lambda _: None, BatteryTracker())

        online_snap = ConnectivitySnapshot(
            state=ConnectivityState.ONLINE,
            wifi_ok=True,
            gateway_ok=True,
            internet_direct_ok=True,
            internet_proxy_ok=False,
            local_ip="10.211.1.10",
            wifi_info="YADX-STU (90%)",
            clash_tun=False,
            reason="网络在线 (校园网)",
            is_campus_network=True,
            active_interface="WLAN",
        )
        offline_snap = ConnectivitySnapshot(
            state=ConnectivityState.INTERNET_DOWN,
            wifi_ok=True,
            gateway_ok=True,
            internet_direct_ok=False,
            internet_proxy_ok=False,
            local_ip="10.211.1.10",
            wifi_info="YADX-STU (90%)",
            clash_tun=False,
            reason="需要认证",
            is_campus_network=True,
            active_interface="WLAN",
        )

        # 使用同步 Thread mock 避免异步竞争
        with patch("campus_guard.network.launch_proxy_and_enable", return_value=(True, "已启动")) as mock_launch:
            class ImmediateThread:
                def __init__(self, target=None, daemon=None):
                    self._target = target

                def start(self):
                    if self._target:
                        self._target()

            with patch("campus_guard.network.threading.Thread", ImmediateThread):
                with patch.object(monitor, "probe_connectivity", return_value=online_snap):
                    monitor._run_probe_and_handle()
                    monitor._run_probe_and_handle()
                self.assertEqual(mock_launch.call_count, 1)

                # 掉线后再恢复，应再次触发一次
                with patch.object(monitor, "probe_connectivity", return_value=offline_snap), patch.object(
                    monitor, "_trigger_reconnect"
                ):
                    monitor._run_probe_and_handle()
                with patch.object(monitor, "probe_connectivity", return_value=online_snap):
                    monitor._run_probe_and_handle()
                self.assertEqual(mock_launch.call_count, 2)

    def test_unblock_motw_files_clears_ads_and_handles_plain_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            internal_dir = base / "_internal" / "pythonnet" / "runtime"
            internal_dir.mkdir(parents=True)
            dll_path = internal_dir / "Python.Runtime.dll"
            dll_path.write_bytes(b"MZ")
            exe_path = base / "AnLan.exe"
            exe_path.write_bytes(b"MZ")

            # 先在无数据流文件上调用应返回 0 且无异常
            self.assertEqual(runtime.unblock_motw_files(base), 0)

            if sys.platform == "win32":
                # 验证在真实 Windows ADS 上可成功写入并由 unblock_motw_files 清除
                with open(f"{dll_path}:Zone.Identifier", "w", encoding="utf-8") as f:
                    f.write("[ZoneTransfer]\nZoneId=3\n")
                self.assertTrue(os.path.exists(f"{dll_path}:Zone.Identifier"))
                removed = runtime.unblock_motw_files(base)
                self.assertGreaterEqual(removed, 1)
                self.assertFalse(os.path.exists(f"{dll_path}:Zone.Identifier"))


if __name__ == "__main__":
    unittest.main()
