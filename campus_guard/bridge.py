from __future__ import annotations

import os
import platform
import subprocess
import sys
import threading
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
from .proxy_manager import (
    detect_clash_client,
    get_proxy_runtime_status,
    launch_proxy_and_enable,
)
from .system import (
    get_disk_free_gb,
    get_local_ip,
    get_local_mac,
    get_memory_usage,
    get_wifi_info,
    is_wifi_link_up,
    reconnect_wifi,
)
from .telegram_bot import _parse_user_id
from .universities import get_university_manager
from .version import APP_VERSION

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
        self._battery = battery_monitor
        self._network = network_monitor
        self._tg_bot = tg_bot
        self._window = window
        self._tray_mgr: Any = None
        self._force_closing: bool = False
        self._start_time = time.time()
        self._uni_manager = get_university_manager()

    def set_window(self, window: Any) -> None:
        """设置关联的 webview.Window 实例（通过方法赋值避免被 pywebview 属性反射遍历）。"""
        self._window = window

    def set_tray_manager(self, tray_mgr: Any) -> None:
        """设置关联的系统托盘管理器实例，以便完全退出时清理托盘图标。"""
        self._tray_mgr = tray_mgr

    def get_state(self) -> dict[str, Any]:
        """获取当前系统、网络、电源与守护状态的完整快照。"""
        cfg = get_config_dict()
        uni_name = cfg.get("university_name", "延安大学 (默认 · Dr.COM)")
        proto = str(cfg.get("auth_protocol", "drcom")).upper()

        snap = self._network.last_snapshot if self._network else None
        online = self._network.is_online if self._network else None
        last_event = self._network.last_event if self._network else "守护服务就绪"

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

        # 从后台网络探针最新快照快速获取，彻底消除同步 subprocess 阻塞
        if snap:
            wifi = snap.wifi_info
            ip = snap.local_ip
            is_campus = snap.is_campus_network
            active_interface = snap.active_interface
        else:
            wifi = get_wifi_info()
            ip = get_local_ip()
            is_campus = False
            active_interface = "默认物理网卡"

        mac = get_local_mac()
        disk_free = 120.0

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
                "uptime_seconds": int(time.time() - self._start_time),
                "memory": get_memory_usage(),
                "disk_free_gb": disk_free,
            },
            "last_event": last_event,
            "university_name": uni_name,
            "auth_protocol": proto,
            "campus_account": str(cfg.get("campus_account", "")),
            "telegram": {
                "configured": bool(str(cfg.get("telegram_bot_token", "")).strip() and _parse_user_id(cfg.get("telegram_user_id", 0))),
                "user_id": str(_parse_user_id(cfg.get("telegram_user_id", 0)) or ""),
                "is_running": bool(
                    self._tg_bot
                    and (
                        getattr(self._tg_bot, "is_ready", False)
                        or (getattr(self._tg_bot, "app", None) and getattr(self._tg_bot, "loop", None))
                    )
                ),
            },
            "proxy": get_proxy_runtime_status(cfg),
            "version": APP_VERSION,
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

            if "telegram_user_id" in raw:
                raw["telegram_user_id"] = _parse_user_id(raw.get("telegram_user_id", 0))

            encrypted = encrypt_sensitive_fields(raw)
            save_config_raw(encrypted)
            decrypted = decrypt_config(raw)
            update_runtime_config(decrypted)

            # 实时同步 Windows 开机自启注册表与静默托盘参数
            try:
                from .runtime import remove_autostart, setup_autostart

                if bool(decrypted.get("autostart", True)):
                    setup_autostart()
                else:
                    remove_autostart()
            except Exception as auto_err:
                log.warning("同步开机自启动设置异常: %s", auto_err)

            # 实时热挂载 / 热重载 Telegram Bot
            if self._tg_bot and hasattr(self._tg_bot, "ensure_started_in_background"):
                try:
                    self._tg_bot.ensure_started_in_background()
                except Exception as bot_err:
                    log.warning("热启动 Telegram Bot 异常: %s", bot_err)

            log.info("用户通过 Web 控制中心成功保存配置")
            return {"success": True, "message": "配置已安全加密并保存生效"}
        except Exception as err:
            log.error("保存配置失败: %s", err)
            return {"success": False, "message": f"保存配置失败: {err}"}

    def reconnect_wifi(self) -> dict[str, Any]:
        """手动请求重新连接 Wi-Fi。"""
        try:
            ok = bool(reconnect_wifi(force=True))
            return {
                "success": ok,
                "message": "Wi-Fi 已重新连接并获取有效 IP" if ok else "Wi-Fi 重连失败，请确认校园 Wi-Fi 信号或网卡开关",
            }
        except Exception as err:
            return {"success": False, "message": f"Wi-Fi 重连异常: {err}"}

    def auth_campus(self) -> dict[str, Any]:
        """手动请求校园网登录认证。"""
        try:
            ok, msg = campus_login()
            if self._network and hasattr(self._network, "record_event"):
                self._network.record_event(f"手动认证: {msg}")
            return {"success": ok, "message": msg}
        except Exception as err:
            return {"success": False, "message": f"认证请求异常: {err}"}

    def logout_campus(self) -> dict[str, Any]:
        """手动请求校园网注销下线。"""
        try:
            ok, msg = campus_logout()
            if self._network and hasattr(self._network, "record_event"):
                self._network.record_event(f"注销下线: {msg}")
            return {"success": ok, "message": msg}
        except Exception as err:
            return {"success": False, "message": f"注销请求异常: {err}"}

    def detect_proxy_client(self) -> dict[str, Any]:
        """自动探测本机安装的 Clash 等代理客户端路径与默认端口。"""
        try:
            info = detect_clash_client()
            if info.get("found"):
                return {
                    "success": True,
                    "message": f"已检测到 {info.get('name', '代理客户端')} ({info.get('proxy_server', '127.0.0.1:7897')})",
                    "data": info,
                }
            return {
                "success": False,
                "message": "未自动检测到 Clash 客户端，请手动填写 .exe 可执行文件完整路径",
                "data": info,
            }
        except Exception as err:
            return {"success": False, "message": f"探测代理客户端异常: {err}", "data": {}}

    def launch_proxy_now(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """立即执行一次代理客户端拉起并开启系统代理（支持前端尚未保存的临时参数覆盖）。"""
        try:
            cfg = dict(get_config_dict())
            if isinstance(overrides, dict):
                for key in (
                    "proxy_exe_path",
                    "proxy_server",
                    "auto_enable_system_proxy",
                    "proxy_bypass",
                    "proxy_wait_timeout_seconds",
                ):
                    if key in overrides and overrides[key] is not None:
                        cfg[key] = overrides[key]
            ok, msg = launch_proxy_and_enable(cfg, force=True)
            if self._network and hasattr(self._network, "record_event"):
                self._network.record_event(f"代理联动: {msg}")
            return {"success": ok, "message": msg}
        except Exception as err:
            return {"success": False, "message": f"代理启动异常: {err}"}

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
            current_url = str(cfg.get("campus_auth_url", "")).strip()
            if not current_url or cfg.get("auth_protocol") in (None, "", "portal"):
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
                    if detected.get("wlan_ac_ip"):
                        cfg["wlan_ac_ip"] = detected["wlan_ac_ip"]

            save_config_raw(encrypt_sensitive_fields(cfg))
            update_runtime_config(decrypt_config(cfg))

            # 若 Wi-Fi 未连接或尚无有效局域网 IP，先自动拉起校园 Wi-Fi
            if not is_wifi_link_up() or get_local_ip() == "未知":
                log.info("一键联网检测到 Wi-Fi 未连接或无有效 IP，先自动拉起校园 Wi-Fi...")
                if not reconnect_wifi(force=True):
                    return {
                        "success": False,
                        "message": "无法连接校园 Wi-Fi，请确认无线网卡已开启且处于校园网覆盖区域",
                        "detected": detected_info,
                    }

            ok, msg = campus_login()

            # 自动自愈重试：若因网关超时或网络地址漂移失败，先刷新假死 Wi-Fi 再嗅探校准重试
            if not ok and any(k in msg for k in ("超时", "无法连接", "10065", "未配置", "网关", "未获取")):
                log.info("一键联网初次认证未成功（%s），正在刷新链路并自动嗅探网关进行二次自愈重试...", msg)
                reconnect_wifi(force=True)
                sniff_ok, sniff_msg, detected = auto_detect_portal_config()
                if sniff_ok and detected and detected.get("campus_auth_url"):
                    detected_info = detected
                    cfg["campus_auth_url"] = detected["campus_auth_url"]
                    if detected.get("campus_gateway"):
                        cfg["campus_gateway"] = detected["campus_gateway"]
                    if detected.get("auth_protocol"):
                        cfg["auth_protocol"] = detected["auth_protocol"]
                    if detected.get("university_name"):
                        cfg["university_name"] = detected["university_name"]
                    if detected.get("wlan_ac_ip"):
                        cfg["wlan_ac_ip"] = detected["wlan_ac_ip"]

                    save_config_raw(encrypt_sensitive_fields(cfg))
                    update_runtime_config(decrypt_config(cfg))
                ok, msg = campus_login()

            if self._network and hasattr(self._network, "record_event"):
                self._network.record_event(f"一键联网认证: {msg}")
            if self._network and hasattr(self._network, "check"):
                self._network.check()
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
        matches = self._uni_manager.search(keyword)[:15]
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

    def export_logs(self) -> dict[str, Any]:
        """导出全量日志内容与本地存储路径。"""
        if not LOG_PATH.exists():
            return {"success": False, "message": "暂无日志文件", "content": "", "path": str(LOG_PATH)}
        try:
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {
                "success": True,
                "message": f"日志已就绪: {LOG_PATH}",
                "content": content,
                "path": str(LOG_PATH),
            }
        except Exception as err:
            return {"success": False, "message": f"读取日志失败: {err}", "content": "", "path": str(LOG_PATH)}

    def open_log_folder(self) -> dict[str, Any]:
        """在系统资源管理器中打开并高亮定位日志文件。"""
        try:
            if not LOG_PATH.exists():
                try:
                    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                    LOG_PATH.touch()
                except Exception:
                    pass

            resolved_path = str(LOG_PATH.resolve())
            if sys.platform == "win32":
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                try:
                    subprocess.run(
                        ["explorer.exe", f"/select,{resolved_path}"],
                        creationflags=flags,
                    )
                except Exception:
                    if hasattr(os, "startfile"):
                        os.startfile(str(LOG_PATH.parent))
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", resolved_path])
            else:
                subprocess.run(["xdg-open", str(LOG_PATH.parent)])
            return {"success": True, "message": f"已在资源管理器中打开日志目录: {LOG_PATH.parent}"}
        except Exception as err:
            return {"success": False, "message": f"打开日志目录异常: {err}"}

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
        if sys.platform == "win32":
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
        if self._window:
            try:
                self._window.hide()
            except Exception:
                pass

    def handle_close_choice(self, action: str, remember: bool = False) -> dict[str, Any]:
        """处理用户在关闭确认弹窗中的选择（最小化至托盘或直接退出程序）。"""
        normalized = str(action or "").strip().lower()
        if normalized not in ("tray", "exit"):
            return {"success": False, "message": "无效的关闭操作"}

        if remember:
            try:
                raw = load_config_raw()
                raw["close_action"] = normalized
                encrypted = encrypt_sensitive_fields(raw)
                save_config_raw(encrypted)
                update_runtime_config(decrypt_config(raw))
                log.info("已记住窗口关闭行为偏好: %s", normalized)
            except Exception as err:
                log.warning("保存关闭偏好失败: %s", err)

        if normalized == "tray":
            log.info("用户选择关闭窗口时最小化到系统托盘")
            self.minimize_to_tray()
            return {"success": True, "action": "tray", "message": "已最小化至系统托盘"}

        log.info("用户选择直接退出 安澜 程序")
        self._force_closing = True
        threading.Timer(0.15, self.close_app).start()
        return {"success": True, "action": "exit", "message": "正在退出安澜"}

    def test_telegram_bot(self) -> dict[str, Any]:
        """向绑定的手机 Telegram 发送握手测试消息（仅 Bot 真就绪时走内部通道，否则直连 HTTP API）。"""
        cfg = get_config_dict()
        token = str(cfg.get("telegram_bot_token", "")).strip()
        user_id = _parse_user_id(cfg.get("telegram_user_id", 0))
        if not token or not user_id:
            return {"success": False, "message": "尚未配置 Telegram Bot Token 或 用户 ID"}

        test_msg = (
            "🛰️ 安澜 控制中枢握手成功\n"
            f"{'─' * 28}\n"
            f"📱 设备已成功与本客户端建立加密双向链路\n"
            f"🕒 握手时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💡 发送 /status 即可调出手机端快速控制面板"
        )
        bot_ready = bool(
            self._tg_bot
            and getattr(self._tg_bot, "app", None) is not None
            and getattr(self._tg_bot, "loop", None) is not None
            and getattr(self._tg_bot, "is_ready", True)
        )
        if bot_ready:
            try:
                self._tg_bot.send_notification(test_msg)
                return {"success": True, "message": "已成功向手机 Telegram 派发测试握手消息"}
            except Exception as err:
                log.warning("通过就绪 Bot 派发测试消息失败，回退 HTTP 直发: %s", err)

        try:
            import requests

            url = f"https://api.telegram.org/bot{token}/sendMessage"
            resp = requests.post(
                url,
                json={"chat_id": user_id, "text": test_msg},
                timeout=8,
            )
            if resp.status_code == 200 and resp.json().get("ok", True):
                if self._tg_bot and hasattr(self._tg_bot, "ensure_started_in_background"):
                    self._tg_bot.ensure_started_in_background()
                return {"success": True, "message": "已通过 Telegram API 成功向手机发送测试消息"}
            return {"success": False, "message": f"Telegram API 返回错误: {resp.text}"}
        except Exception as err:
            return {"success": False, "message": f"网络通信异常（请确认代理或 Telegram 连通性）: {err}"}

    def test_domestic_notify(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """测试飞书 / 钉钉国内免代理通知通道（支持传入未保存的表单参数覆盖）。"""
        try:
            from .notifier import UnifiedNotifier

            cfg = dict(get_config_dict())
            if isinstance(overrides, dict):
                for key in ("feishu_webhook_url", "dingtalk_webhook_url", "dingtalk_secret"):
                    if key in overrides and overrides[key] is not None:
                        cfg[key] = str(overrides[key]).strip()

            feishu_url = str(cfg.get("feishu_webhook_url", "") or "").strip()
            dingtalk_url = str(cfg.get("dingtalk_webhook_url", "") or "").strip()
            dingtalk_secret = str(cfg.get("dingtalk_secret", "") or "").strip()

            if not feishu_url and not dingtalk_url:
                return {"success": False, "message": "请先填写飞书或钉钉机器人 Webhook 地址"}

            test_text = (
                "🔔 安澜 国内通知通道握手测试成功\n"
                f"🕒 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                "✅ 后续断网恢复与宿舍断电预警将通过此通道实时送达"
            )
            results: list[str] = []
            any_ok = False

            if feishu_url:
                ok_feishu = UnifiedNotifier._send_feishu_card(
                    feishu_url, test_text, title="安澜 · 通知测试", level="success"
                )
                any_ok = any_ok or ok_feishu
                results.append("飞书发送成功" if ok_feishu else "飞书发送失败")

            if dingtalk_url:
                ok_dingtalk = UnifiedNotifier._send_dingtalk(
                    dingtalk_url, dingtalk_secret, test_text, title="安澜 · 通知测试"
                )
                any_ok = any_ok or ok_dingtalk
                results.append("钉钉发送成功" if ok_dingtalk else "钉钉发送失败")

            return {"success": any_ok, "message": "；".join(results)}
        except Exception as err:
            return {"success": False, "message": f"国内通知通道测试异常: {err}"}

    def close_app(self) -> None:
        """安全退出应用：停止监控服务、清理系统托盘图标并销毁主窗口。"""
        self._force_closing = True
        if self._battery and hasattr(self._battery, "stop"):
            try:
                self._battery.stop()
            except Exception:
                pass
        if self._network and hasattr(self._network, "stop"):
            try:
                self._network.stop()
            except Exception:
                pass
        if self._tg_bot and hasattr(self._tg_bot, "stop_sync"):
            try:
                self._tg_bot.stop_sync(timeout=2.0)
            except Exception:
                pass
        if self._tray_mgr and hasattr(self._tray_mgr, "stop"):
            try:
                self._tray_mgr.stop()
            except Exception:
                pass
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                pass
        if not self._window or threading.current_thread() is threading.main_thread():
            sys.exit(0)

