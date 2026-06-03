from __future__ import annotations

import asyncio
import ctypes
import html as html_mod
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from .auth import campus_login
from .bot_health import register_bot_health_check
from .config import SENSITIVE_FIELDS, get_config_dict, load_config_raw
from .logging_setup import get_logger
from .paths import LOG_PATH
from .security import is_authorized
from .system import check_campus_gateway, check_internet, get_local_ip, get_public_ip, get_wifi_info

if TYPE_CHECKING:
    from .battery import BatteryMonitor, BatteryTracker
    from .network import NetworkMonitor


log = get_logger()


class TelegramBot:
    def __init__(
        self,
        battery_monitor: BatteryMonitor | None,
        network_monitor: NetworkMonitor | None,
        tracker: BatteryTracker,
    ) -> None:
        self.battery = battery_monitor
        self.network = network_monitor
        self.tracker = tracker
        self.app = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self._message_queue: list[str] = []
        self._start_time = time.time()
        self.pending_confirmations: dict[int, dict] = {}
        self._last_update_time = time.time()

    def _config(self) -> dict:
        return get_config_dict()

    def _build_app(self):
        from telegram.ext import Application

        return Application.builder().token(self._config()["telegram_bot_token"]).build()

    async def _health_check(self) -> None:
        if not self.app:
            return
        stale_secs = int(self._config().get("bot_watchdog_stale_seconds", 300))
        elapsed = time.time() - self._last_update_time
        if elapsed < stale_secs:
            log.info("Bot 健康检查通过（%.0fs 前收到消息）", elapsed)
            return
        log.warning(
            "Bot polling 疑似挂掉：已 %.0fs 无消息更新（阈值 %ds），尝试重启",
            elapsed,
            stale_secs,
        )
        await self._restart_polling()

    async def _restart_polling(self) -> None:
        import traceback

        try:
            await self.app.updater.stop()
            log.info("已停止旧 polling")
        except Exception:
            pass
        try:
            await self.app.updater.start_polling(drop_pending_updates=True)
            self._last_update_time = time.time()
            log.info("Bot polling 已重启")
        except Exception:
            log.error("重启 polling 失败:\n%s", traceback.format_exc())

    def _register_handlers(self, app=None) -> None:
        from telegram.ext import CallbackQueryHandler, CommandHandler

        active_app = app or self.app
        active_app.add_handler(CommandHandler("status", self._touch_update(self._cmd_status)))
        active_app.add_handler(CommandHandler("shutdown", self._touch_update(self._cmd_shutdown)))
        active_app.add_handler(CommandHandler("reconnect", self._touch_update(self._cmd_reconnect)))
        active_app.add_handler(CommandHandler("cancel", self._touch_update(self._cmd_cancel_shutdown)))
        active_app.add_handler(CommandHandler("help", self._touch_update(self._cmd_help)))
        active_app.add_handler(CommandHandler("lock", self._touch_update(self._cmd_lock)))
        active_app.add_handler(CommandHandler("screenshot", self._touch_update(self._cmd_screenshot)))
        active_app.add_handler(CommandHandler("ip", self._touch_update(self._cmd_ip)))
        active_app.add_handler(CommandHandler("ping", self._touch_update(self._cmd_ping)))
        active_app.add_handler(CommandHandler("log", self._touch_update(self._cmd_log)))
        active_app.add_handler(CommandHandler("restart", self._touch_update(self._cmd_restart)))
        active_app.add_handler(CommandHandler("config", self._touch_update(self._cmd_config)))
        active_app.add_handler(CommandHandler("yes", self._touch_update(self._cmd_yes)))
        active_app.add_handler(CommandHandler("no", self._touch_update(self._cmd_no)))
        active_app.add_handler(CallbackQueryHandler(self._touch_update(self._handle_callback)))

    async def start(self) -> None:
        from telegram import BotCommand

        self.app = self._build_app()
        self._register_handlers()
        self.loop = asyncio.get_event_loop()
        register_bot_health_check(self.loop, self._health_check)

        log.info("Telegram Bot 启动中...")
        for attempt in range(30):
            try:
                await self.app.initialize()
                await self.app.start()
                await self.app.updater.start_polling(drop_pending_updates=True)
                break
            except Exception as err:
                if attempt < 29:
                    log.warning("Bot 初始化失败（第%d次），10秒后重试: %s", attempt + 1, err)
                    try:
                        await self.app.stop()
                        await self.app.shutdown()
                    except Exception:
                        pass
                    self.app = self._build_app()
                    self._register_handlers(self.app)
                    await asyncio.sleep(10)
                    continue
                log.error("Bot 初始化失败30次，放弃: %s", err)
                return

        await self.app.bot.set_my_commands([
            BotCommand("status", "📊 查看电量·电源·网络状态"),
            BotCommand("shutdown", "⚠️ 远程关机（需确认）"),
            BotCommand("cancel", "✅ 取消关机"),
            BotCommand("reconnect", "🔄 手动重连校园网"),
            BotCommand("lock", "🔒 锁屏"),
            BotCommand("screenshot", "📸 截取屏幕（需确认）"),
            BotCommand("ip", "🌐 查看 IP 地址"),
            BotCommand("ping", "🏓 测试连接"),
            BotCommand("log", "📜 查看最近日志"),
            BotCommand("restart", "🔁 重启程序"),
            BotCommand("config", "⚙️ 查看配置"),
            BotCommand("help", "📖 查看帮助"),
        ])
        log.info("Telegram Bot 已启动，命令菜单已注册")

        for msg in self._message_queue:
            await self._send_message(msg)
        self._message_queue.clear()

        self._schedule_daily_report()
        self._schedule_weekly_report()

        while True:
            await asyncio.sleep(60)
            try:
                await self._health_check()
            except Exception:
                import traceback

                log.error("Bot 健康检查异常:\n%s", traceback.format_exc())

    def _schedule_daily_report(self) -> None:
        async def _send_daily() -> None:
            while True:
                now = datetime.now()
                target = now.replace(hour=0, minute=5, second=0, microsecond=0)
                if now >= target:
                    target += timedelta(days=1)
                await asyncio.sleep((target - now).total_seconds())
                await self._send_message(self.tracker.daily_report())
                log.info("每日报告已发送")

        if self.loop:
            asyncio.run_coroutine_threadsafe(_send_daily(), self.loop)

    def _schedule_weekly_report(self) -> None:
        async def _send_weekly() -> None:
            while True:
                now = datetime.now()
                days_until_sunday = (6 - now.weekday()) % 7
                target = now.replace(hour=20, minute=0, second=0, microsecond=0)
                target += timedelta(days=days_until_sunday)
                if now >= target:
                    target += timedelta(days=7)
                await asyncio.sleep((target - now).total_seconds())
                await self._send_message(self.tracker.weekly_report())
                log.info("每周报告已发送")

        if self.loop:
            asyncio.run_coroutine_threadsafe(_send_weekly(), self.loop)

    def send_notification(self, text: str) -> None:
        if self.loop and self.app:
            asyncio.run_coroutine_threadsafe(self._send_message(text), self.loop)
        else:
            self._message_queue.append(text)
            log.info("消息已排队（Bot 未就绪）: %s", text[:50])

    async def _send_message(self, text: str) -> None:
        try:
            await self.app.bot.send_message(
                chat_id=self._config()["telegram_user_id"],
                text=text,
                parse_mode=None,
            )
        except Exception as err:
            log.error("发送消息失败: %s", err)

    def _is_authorized(self, update) -> bool:
        return is_authorized(update, int(self._config()["telegram_user_id"]))

    def _touch_update(self, handler):
        async def wrapper(update, context):
            self._last_update_time = time.time()
            return await handler(update, context)

        return wrapper

    def _check_pending(self, user_id: int, action: str) -> bool:
        pending = self.pending_confirmations.get(user_id)
        if not pending or pending["action"] != action:
            return False
        if time.time() - pending["time"] > 30:
            del self.pending_confirmations[user_id]
            return False
        return True

    def _clear_pending(self, user_id: int) -> None:
        self.pending_confirmations.pop(user_id, None)

    async def _cmd_status(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        import psutil

        bat = psutil.sensors_battery()
        if bat:
            plug_icon = "🔌 供电中" if bat.power_plugged else "🔋 电池供电"
            bat_text = f"{plug_icon} — {bat.percent}%"
            if bat.power_plugged:
                bat_text += "\n预计剩余: 充电中"
            else:
                bat_text += f"\n预计剩余: {self.battery._format_time(bat.secsleft)}"
        else:
            bat_text = "未检测到电池"

        wifi_info = get_wifi_info()
        local_ip = get_local_ip()
        net_icon = "🟢 在线" if self.network and self.network.is_online else "🔴 离线"
        uptime_secs = time.time() - self._start_time
        uptime_h = int(uptime_secs // 3600)
        uptime_m = int((uptime_secs % 3600) // 60)
        stats = self.tracker.get_today_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = (
            f"📊 系统状态 — {now}\n"
            f"{'─' * 28}\n"
            f"🔋 电池: {bat_text}\n"
            f"📶 WiFi: {wifi_info}\n"
            f"🌐 网络: {net_icon}\n本机 IP: {local_ip}\n"
            f"⏰ 运行时间: {uptime_h}小时{uptime_m}分钟\n"
            f"{'─' * 28}\n"
            f"📋 今日统计 ({today}):\n"
            f"  ⚡ 断电次数: {stats['power_outage_count']}\n"
            f"  🔄 网络重连: {stats['network_reconnect_count']}"
        )
        keyboard = [
            [
                InlineKeyboardButton("🔄 刷新", callback_data="refresh_status"),
                InlineKeyboardButton("⚠️ 关机", callback_data="shutdown"),
            ],
            [
                InlineKeyboardButton("🔌 重连", callback_data="reconnect"),
                InlineKeyboardButton("📸 截屏", callback_data="screenshot"),
            ],
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _handle_callback(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        import psutil

        query = update.callback_query
        data = query.data
        if data == "refresh_status":
            bat = psutil.sensors_battery()
            bat_text = "未检测到电池"
            if bat:
                plug = "🔌 供电中" if bat.power_plugged else "🔋 电池供电"
                bat_text = f"{plug} — {bat.percent}%"
            text = (
                f"📊 系统状态（已刷新） — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"{'─' * 28}\n"
                f"🔋 电池: {bat_text}\n"
                f"📶 WiFi: {get_wifi_info()}\n"
                f"🌐 网络: {'🟢 在线' if self.network and self.network.is_online else '🔴 离线'} — IP: {get_local_ip()}"
            )
            keyboard = [
                [
                    InlineKeyboardButton("🔄 刷新", callback_data="refresh_status"),
                    InlineKeyboardButton("⚠️ 关机", callback_data="shutdown"),
                ],
                [
                    InlineKeyboardButton("🔌 重连", callback_data="reconnect"),
                    InlineKeyboardButton("📸 截屏", callback_data="screenshot"),
                ],
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            await query.answer("已刷新")
        elif data == "shutdown":
            user_id = query.from_user.id
            self.pending_confirmations[user_id] = {"action": "shutdown", "time": time.time()}
            await query.message.reply_text("⚠️ 确认关机？回复 /yes 关机，/no 取消")
            await query.answer()
        elif data == "reconnect":
            await query.message.reply_text("🔄 正在尝试重连校园网...")
            success, msg = campus_login()
            if success:
                time.sleep(3)
                gw_ok = check_campus_gateway()
                inet_ok = check_internet()
                if gw_ok and inet_ok:
                    self.tracker.record_reconnect()
                    await query.message.reply_text(f"✅ {msg}\n网络已恢复")
                else:
                    detail = f"网关={'OK' if gw_ok else '不可达'}, 外网={'OK' if inet_ok else '不通'}"
                    await query.message.reply_text(f"⚠️ 认证已发送，但验证失败 ({detail}): {msg}")
            else:
                await query.message.reply_text(f"❌ 重连失败: {msg}")
            await query.answer()
        elif data == "screenshot":
            user_id = query.from_user.id
            self.pending_confirmations[user_id] = {"action": "screenshot", "time": time.time()}
            await query.message.reply_text("⚠️ 确认截屏？回复 /yes 截屏，/no 取消")
            await query.answer()

    async def _cmd_yes(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        user_id = update.effective_user.id
        pending = self.pending_confirmations.get(user_id)
        if not pending:
            await update.message.reply_text("❌ 没有待确认的操作，或已过期（30秒）")
            return
        if time.time() - pending["time"] > 30:
            del self.pending_confirmations[user_id]
            await update.message.reply_text("❌ 操作已过期（30秒），请重新发起")
            return
        action = pending["action"]
        del self.pending_confirmations[user_id]
        if action == "shutdown":
            await update.message.reply_text("⚠️ 电脑将在 60 秒后关机\n发送 /cancel 取消")
            log.warning("收到远程关机命令！（经用户确认）")
            subprocess.Popen(["shutdown", "/s", "/t", "60"], creationflags=0x08000000)
        elif action == "screenshot":
            await self._do_screenshot(update.message.reply_text)

    async def _cmd_no(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        user_id = update.effective_user.id
        pending = self.pending_confirmations.pop(user_id, None)
        if pending:
            await update.message.reply_text(f"✅ 已取消「{pending['action']}」操作")
        else:
            await update.message.reply_text("没有待确认的操作")

    async def _cmd_shutdown(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        user_id = update.effective_user.id
        self.pending_confirmations[user_id] = {"action": "shutdown", "time": time.time()}
        await update.message.reply_text("⚠️ 确认关机？回复 /yes 关机，/no 取消")

    async def _cmd_cancel_shutdown(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        subprocess.Popen(["shutdown", "/a"], creationflags=0x08000000)
        await update.message.reply_text("✅ 已发送取消关机命令")
        log.info("关机已取消")

    async def _cmd_reconnect(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        await update.message.reply_text("🔄 正在手动重连校园网...")
        success, msg = campus_login()
        await update.message.reply_text(f"{'✅' if success else '❌'} {msg}")

    async def _cmd_lock(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        try:
            ctypes.windll.user32.LockWorkStation()
            await update.message.reply_text("🔒 已锁屏")
            log.info("执行锁屏")
        except Exception as err:
            await update.message.reply_text(f"❌ 锁屏失败: {err}")

    async def _cmd_screenshot(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        user_id = update.effective_user.id
        self.pending_confirmations[user_id] = {"action": "screenshot", "time": time.time()}
        await update.message.reply_text("⚠️ 确认截屏？回复 /yes 截屏，/no 取消")

    async def _do_screenshot(self, reply_text_fn) -> None:
        try:
            from PIL import ImageGrab

            tmp_path = Path(tempfile.gettempdir()) / "campus_guard_screenshot.png"
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            screenshot = ImageGrab.grab()
            screenshot.save(tmp_path, "PNG")
            if self.app:
                with open(tmp_path, "rb") as f:
                    await self.app.bot.send_photo(
                        chat_id=self._config()["telegram_user_id"],
                        photo=f,
                        caption="📸 屏幕截图",
                    )
                log.info("截屏已发送")
        except Exception as err:
            await reply_text_fn(f"❌ 截屏失败: {err}")

    async def _cmd_ip(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        await update.message.reply_text(
            f"🌐 IP 地址\n{'─' * 20}\n局域网 IP: {get_local_ip()}\n公网 IP: {get_public_ip()}"
        )

    async def _cmd_ping(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        await update.message.reply_text("🏓 Pong! 程序运行正常")

    async def _cmd_log(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        n = 20
        if context.args:
            try:
                n = min(int(context.args[0]), 200)
            except ValueError:
                pass
        try:
            if not LOG_PATH.exists():
                await update.message.reply_text("📜 日志文件不存在")
                return
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                recent = f.readlines()[-n:]
            text = "".join(recent)
            if len(text) > 3900:
                text = "...\n" + text[-3900:]
            await update.message.reply_text(
                f"<pre>{html_mod.escape(text)}</pre>",
                parse_mode="HTML",
            )
        except Exception as err:
            await update.message.reply_text(f"❌ 读取日志失败: {err}")

    async def _cmd_restart(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        await update.message.reply_text("🔁 正在重启...")
        log.info("收到远程重启命令")
        await asyncio.sleep(1)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    async def _cmd_config(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        cfg = load_config_raw()
        display = {}
        for key, value in cfg.items():
            if key in SENSITIVE_FIELDS and isinstance(value, str) and len(value) > 4:
                display[key] = value[:2] + "*" * (len(value) - 4) + value[-2:]
            else:
                display[key] = value
        lines = ["⚙️ 当前配置:", "─" * 24]
        for key, value in display.items():
            lines.append(f"  {key}: {value}")
        await update.message.reply_text(
            f"<pre>{html_mod.escape(chr(10).join(lines))}</pre>",
            parse_mode="HTML",
        )

    async def _cmd_help(self, update, context) -> None:
        if not self._is_authorized(update):
            return
        await update.message.reply_text(
            "📖 Campus Guard 命令\n\n"
            "/status — 查看电量、电源、网络状态\n"
            "/shutdown — 远程关机（需确认）\n"
            "/cancel — 取消关机\n"
            "/reconnect — 手动重连校园网\n"
            "/lock — 锁定屏幕\n"
            "/screenshot — 截取屏幕（需确认）\n"
            "/ip — 查看 IP 地址\n"
            "/ping — 测试连接\n"
            "/log [N] — 查看最近 N 行日志（默认20）\n"
            "/restart — 重启程序\n"
            "/config — 查看当前配置\n"
            "/help — 显示帮助"
        )
