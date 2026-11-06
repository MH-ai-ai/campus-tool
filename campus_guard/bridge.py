from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
from typing import Any

from .auth import auto_detect_portal_config, campus_login, campus_logout
from .battery import BatteryMonitor
from .config import (
    SENSITIVE_FIELDS,
    decrypt_config,
    encrypt_sensitive_fields,
    get_config_dict,
    load_config_raw,
    save_config_raw,
    update_runtime_config,
)
from .logging_setup import get_logger
from .network import NetworkMonitor
from .paths import APP_DIR, LOG_PATH
from .system import (
    get_disk_free_gb,
    get_local_ip,
    get_local_mac,
    get_memory_usage,
    get_wifi_info,
    reconnect_wifi,
)
from .universities import get_university_manager

log = get_logger()


class ApiBridge:
    """JS-Python 双向绑定桥接类，供 pywebview 前端调用。"""

    def __init__(
        self,
        battery_monitor: BatteryMonitor | None = None,
        network_monitor: NetworkMonitor | None = None,
        tg_bot: Any = None,
        window: Any = None,
    ) -> None:
        self.battery = battery_monitor
        self.network = network_monitor
        self.tg_bot = tg_bot
        self.window = window
        self.start_time = time.time()
        self.uni_manager = get_university_manager()

    def get_state(self) -> dict[str, Any]:
        """获取当前系统、网络、电源与守护状态的完整快照。"""
        cfg = get_config_dict()
        uni_name = cfg.get("university_name", "延安大学 (默认 · Dr.COM)")
        proto = str(cfg.get("auth_protocol", "drcom")).upper()

        snap = self.network.last_snapshot if self.network else None
        online = self.network.is_online if self.network else None
        last_event = self.network.last_event if self.network else "守护服务就绪"

        # 电池与电源信息
        has_battery = False
        percent = 100
        plugged = True
        status_text = "交流供电中"

        try:
            import psutil

            bat = psutil.sensors_battery()
            if bat is not None:
                has_battery = True
                percent = int(bat.percent)
                plugged = bool(bat.power_plugged)
                if plugged:
                    status_text = "正在充电" if percent < 100 else "已充满 (交流供电)"
                else:
                    status_text = f"预计可用 {BatteryMonitor._format_time(bat.secsleft)}"
            else:
                status_text = "台式机持续交流供电"
        except Exception:
            pass

        wifi = get_wifi_info()
        ip = get_local_ip()
        mac = get_local_mac()

        try:
            disk_free = round(get_disk_free_gb(), 1)
        except Exception:
            disk_free = 0.0

        is_campus = snap.is_campus_network if snap else False

        return {
            "online": online,
            "is_campus": is_campus,
            "wifi": wifi,
            "ip": ip,
            "mac": mac,
            "gateway": str(cfg.get("campus_gateway", "10.212.0.1")),
            "gateway_ok": snap.gateway_ok if snap else False,
            "clash_tun": snap.clash_tun if snap else False,
            "active_interface": snap.active_interface if snap else "以太网 / Wi-Fi",
            "battery": {
                "has_battery": has_battery,
                "percent": percent,
                "plugged": plugged,
                "charging": plugged and (percent < 100),
                "status_text": status_text,
            },
            "system": {
                "uptime_seconds": int(time.time() - self.start_time),
                "memory": get_memory_usage(),
                "disk_free_gb": disk_free,
            },
            "last_event": last_event,
            "university_name": uni_name,
            "auth_protocol": proto,
            "campus_account": str(cfg.get("campus_account", "")),
            "telegram": {
                "configured": bool(str(cfg.get("telegram_bot_token", "")).strip() and int(cfg.get("telegram_user_id", 0))),
                "user_id": str(cfg.get("telegram_user_id", "")),
                "is_running": bool(self.tg_bot and getattr(self.tg_bot, "app", None)),
            },
        }

    def get_config(self) -> dict[str, Any]:
        """获取解密后的配置数据供设置页面展示。"""
        raw = load_config_raw()
        decrypted = decrypt_config(raw)
        return decrypted

    def save_config(self, new_config: dict[str, Any]) -> dict[str, Any]:
        """保存前端提交的配置字典，自动执行本地敏感字段加密与原子持久化。"""
        try:
            raw = load_config_raw()
            # 过滤只保留字典键值
            for k, v in new_config.items():
                raw[k] = v

            encrypted = encrypt_sensitive_fields(raw)
            save_config_raw(encrypted)
            update_runtime_config(decrypt_config(raw))
            log.info("用户通过 Web 控制中心成功保存配置")
            return {"success": True, "message": "配置已安全加密并保存生效"}
        except Exception as err:
            log.error("保存配置失败: %s", err)
            return {"success": False, "message": f"保存配置失败: {err}"}

    def reconnect_wifi(self) -> dict[str, Any]:
        """手动请求重新连接 Wi-Fi。"""
        try:
            ok, msg = reconnect_wifi()
            return {"success": ok, "message": msg}
        except Exception as err:
            return {"success": False, "message": f"Wi-Fi 重连异常: {err}"}

    def auth_campus(self) -> dict[str, Any]:
        """手动请求校园网登录认证。"""
        try:
            ok, msg = campus_login()
            if self.network:
                self.network.record_event(f"手动认证: {msg}")
            return {"success": ok, "message": msg}
        except Exception as err:
            return {"success": False, "message": f"认证请求异常: {err}"}

    def logout_campus(self) -> dict[str, Any]:
        """手动请求校园网注销下线。"""
        try:
            ok, msg = campus_logout()
            if self.network:
                self.network.record_event(f"注销下线: {msg}")
            return {"success": ok, "message": msg}
        except Exception as err:
            return {"success": False, "message": f"注销请求异常: {err}"}

    def auto_sniff(self) -> dict[str, Any]:
        """触发未加密 HTTP Captive Portal 探针智能识别高校参数。"""
        try:
            ok, msg, detected = auto_detect_portal_config()
            return {
                "success": ok,
                "message": msg,
                "detected": detected,
            }
        except Exception as err:
            return {"success": False, "message": f"智能嗅探发生异常: {err}", "detected": {}}

    def quick_setup(self, payload: dict[str, Any]) -> dict[str, Any]:
        """小白 10 秒一键打通向导提交。"""
        try:
            account = str(payload.get("account", "")).strip()
            password = str(payload.get("password", "")).strip()
            protocol = str(payload.get("protocol", "drcom")).strip().lower()
            university_name = str(payload.get("university_name", "")).strip()
            auth_url = str(payload.get("auth_url", "")).strip()
            gateway = str(payload.get("gateway", "")).strip()
            ssid = str(payload.get("ssid", "")).strip()

            if not account or not password:
                return {"success": False, "message": "学号/账号与密码不能为空"}

            cfg = load_config_raw()
            cfg["campus_account"] = account
            cfg["campus_password"] = password
            cfg["auth_protocol"] = protocol
            if university_name:
                cfg["university_name"] = university_name
            if auth_url:
                cfg["campus_auth_url"] = auth_url
            if gateway:
                cfg["campus_gateway"] = gateway
            if ssid:
                ssids = cfg.get("campus_wifi_ssids", [])
                if isinstance(ssids, list) and ssid not in ssids:
                    ssids.append(ssid)
                    cfg["campus_wifi_ssids"] = ssids

            save_config_raw(encrypt_sensitive_fields(cfg))
            update_runtime_config(decrypt_config(cfg))

            # 立即触发一次认证
            ok, msg = campus_login()
            return {
                "success": ok,
                "message": f"配置已保存！认证结果: {msg}",
            }
        except Exception as err:
            return {"success": False, "message": f"一键打通执行失败: {err}"}

    def quick_connect(self, account: str = "", password: str = "") -> dict[str, Any]:
        """首屏一键极速联网：首次输入自动探测并持久化加密保存，已配置时一键强制认证自愈。"""
        try:
            cfg = load_config_raw()
            if account.strip():
                cfg["campus_account"] = account.strip()
            if password.strip():
                cfg["campus_password"] = password.strip()

            final_account = str(cfg.get("campus_account", "")).strip()
            final_password = str(cfg.get("campus_password", "")).strip()
            if not final_account or not final_password:
                return {"success": False, "message": "请先输入校园网学号/账号与认证密码"}

            detected_info = {}
            if not cfg.get("campus_auth_url") or cfg.get("auth_protocol") in (None, "", "portal"):
                sniff_ok, sniff_msg, detected = auto_detect_portal_config()
                if sniff_ok and detected:
                    detected_info = detected
                    if detected.get("campus_auth_url"):
                        cfg["campus_auth_url"] = detected["campus_auth_url"]
                    if detected.get("campus_gateway"):
                        cfg["campus_gateway"] = detected["campus_gateway"]
                    if detected.get("auth_protocol"):
                        cfg["auth_protocol"] = detected["auth_protocol"]
                    if detected.get("university_name"):
                        cfg["university_name"] = detected["university_name"]

            save_config_raw(encrypt_sensitive_fields(cfg))
            update_runtime_config(decrypt_config(cfg))

            ok, msg = campus_login()
            if self.network:
                self.network.record_event(f"一键联网认证: {msg}")
            return {
                "success": ok,
                "message": msg,
                "detected": detected_info,
            }
        except Exception as err:
            log.error("一键联网异常: %s", err)
            return {"success": False, "message": f"一键联网异常: {err}"}

    def search_universities(self, keyword: str) -> list[dict[str, Any]]:
        """全拼/首字母/汉字高校库模糊检索。"""
        matches = self.uni_manager.search(keyword)[:15]
        return [
            {
                "id": u.id,
                "name": u.name,
                "protocol": u.protocol,
                "auth_url": u.auth_url,
                "gateway": u.gateway,
                "wifi_ssids": u.wifi_ssids,
            }
            for u in matches
        ]

    def get_logs(self, max_lines: int = 120) -> list[str]:
        """获取实时日志切片。"""
        if not LOG_PATH.exists():
            return ["暂无日志记录"]
        try:
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            return [line.rstrip() for line in lines[-max_lines:]]
        except Exception as err:
            return [f"读取日志文件失败: {err}"]

    def clear_logs(self) -> dict[str, Any]:
        """清除运行日志文件。"""
        try:
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 日志已手动清空\n")
            return {"success": True, "message": "日志已清空"}
        except Exception as err:
            return {"success": False, "message": f"清空日志失败: {err}"}

    def lock_screen(self) -> dict[str, Any]:
        """快速锁定屏幕。"""
        if platform.system() == "Windows":
            try:
                import ctypes

                ctypes.windll.user32.LockWorkStation()
                return {"success": True, "message": "已执行 Windows 锁屏"}
            except Exception as err:
                return {"success": False, "message": f"锁屏失败: {err}"}
        return {"success": False, "message": "非 Windows 平台不支持该操作"}

    def take_screenshot(self) -> dict[str, Any]:
        """截取桌面并保存至应用目录。"""
        try:
            from PIL import ImageGrab

            img = ImageGrab.grab()
            save_path = APP_DIR / f"screenshot_{int(time.time())}.png"
            img.save(str(save_path))
            return {"success": True, "message": f"截图已保存至: {save_path.name}"}
        except Exception as err:
            return {"success": False, "message": f"截图失败: {err}"}

    def minimize_to_tray(self) -> None:
        """隐藏窗口至系统托盘。"""
        if self.window:
            try:
                self.window.hide()
            except Exception:
                pass

    def test_telegram_bot(self) -> dict[str, Any]:
        """向绑定的手机 Telegram 发送握手测试消息。"""
        cfg = get_config_dict()
        token = str(cfg.get("telegram_bot_token", "")).strip()
        user_id = cfg.get("telegram_user_id")
        if not token or not user_id:
            return {"success": False, "message": "尚未配置 Telegram Bot Token 或 用户 ID"}

        test_msg = (
            "🛰️ Campus Guard 控制中枢握手成功\n"
            f"{'─' * 28}\n"
            f"📱 设备已成功与本客户端建立加密双向链路\n"
            f"🕒 握手时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💡 发送 /status 即可调出手机端快速控制面板"
        )
        if self.tg_bot:
            try:
                self.tg_bot.send_notification(test_msg)
                return {"success": True, "message": "已成功向手机 Telegram 派发测试握手消息"}
            except Exception as err:
                return {"success": False, "message": f"发送测试失败: {err}"}

        try:
            import requests

            url = f"https://api.telegram.org/bot{token}/sendMessage"
            resp = requests.post(
                url,
                json={"chat_id": user_id, "text": test_msg},
                timeout=6,
            )
            if resp.status_code == 200:
                return {"success": True, "message": "已成功向手机 Telegram 派发测试握手消息"}
            return {"success": False, "message": f"Telegram API 返回: {resp.text}"}
        except Exception as err:
            return {"success": False, "message": f"网络通信异常: {err}"}

    def close_app(self) -> None:
        """退出应用。"""
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
        sys.exit(0)

