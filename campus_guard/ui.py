from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

from .battery import BatteryMonitor
from .bridge import ApiBridge
from .config import SETTINGS_SCHEMA as _SETTINGS_SCHEMA, get_config_dict
from .logging_setup import get_logger
from .models import GuardState
from .network import NetworkMonitor
from .paths import APP_DIR, WEB_DIST_PATH
from .telegram_bot import TelegramBot
from .tray import PystrayTrayManager, create_tray_icon, get_tray_color, pil_image_to_qicon
from .version import APP_VERSION

log = get_logger()

# 导出兼容旧代码引用的变量与组件
_COLORS = {
    "window_bg": "#111216",
    "sidebar_bg": "#16171d",
    "card_bg": "#1c1e26",
    "card_hover": "#232630",
    "text_primary": "#f3f4f6",
    "text_secondary": "#9ca3af",
    "accent": "#0a84ff",
    "success": "#32d74b",
    "warning": "#ff9f0a",
    "danger": "#ff453a",
}
_STYLESHEET = ""

# 尝试导入历史 PyQt6 模块以保持旧代码无缝兼容；在无 GUI 或无 PyQt6 环境下优雅回退
try:
    from .ui_modules.dashboard_page import _DashboardPage
    from .ui_modules.log_page import _LogPage
    from .ui_modules.settings_page import _SettingsPage
    from .ui_modules.styles import _STYLESHEET as _OLD_STYLESHEET
    from .ui_modules.widgets import _SideBar, _Worker
    _STYLESHEET = _OLD_STYLESHEET

    from PyQt6.QtWidgets import QMainWindow

    class MainWindow(QMainWindow):
        """兼容保留的 PyQt6 历史主窗口基类。"""
        def __init__(self, battery: BatteryMonitor, network: NetworkMonitor, tg_bot: TelegramBot) -> None:
            super().__init__()
            self.battery = battery
            self.network = network
            self.tg_bot = tg_bot
except ImportError:
    class MainWindow:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            pass

    class _DashboardPage:  # type: ignore
        pass

    class _LogPage:  # type: ignore
        pass

    class _SettingsPage:  # type: ignore
        pass

    class _SideBar:  # type: ignore
        pass

    class _Worker:  # type: ignore
        pass


def launch_gui(
    battery: BatteryMonitor,
    network: NetworkMonitor,
    tg_bot: TelegramBot | None = None,
    start_minimized: bool = False,
) -> None:
    """启动现代 Webview 桌面控制中心（由 Edge WebView2 驱动）。
    具备浅色微透磨砂玻璃质感、系统托盘常驻与无缝显隐；支持 start_minimized 静默启动到托盘。
    """
    from .runtime import unblock_motw_files

    unblock_motw_files()
    import webview

    bridge = ApiBridge(battery, network, tg_bot)

    # 确定前端静态资源入口路径
    html_file = WEB_DIST_PATH / "index.html"
    alt_file = APP_DIR / "web_dist" / "index.html"
    internal_file = APP_DIR / "_internal" / "campus_guard" / "web_dist" / "index.html"

    target_url: str
    if html_file.exists():
        target_url = str(html_file.resolve().as_uri())
    elif alt_file.exists():
        target_url = str(alt_file.resolve().as_uri())
    elif internal_file.exists():
        target_url = str(internal_file.resolve().as_uri())
    else:
        # 开发模式或产物缺失时的后备内置简易页面
        target_url = "data:text/html;charset=utf-8," + (
            "<!DOCTYPE html><html><body style='background:#eef2f7;color:#18202c;font-family:sans-serif;padding:40px;'>"
            "<h2>安澜 控制中心载入中...</h2>"
            "<p style='color:#526075;'>前端资源正在构建中，请在 frontend/ 目录下运行 npm run build 生成静态包。</p>"
            "</body></html>"
        )

    log.info("启动 Webview 窗口，加载资源: %s", target_url)

    window = webview.create_window(
        title="安澜",
        url=target_url,
        js_api=bridge,
        width=960,
        height=640,
        min_size=(840, 560),
        background_color="#eef2f7",
        hidden=start_minimized,
        frameless=False,
        easy_drag=True,
    )

    bridge.set_window(window)

    # 启动 pystray 系统托盘常驻
    tray_mgr = PystrayTrayManager(bridge, window)
    bridge.set_tray_manager(tray_mgr)
    tray_mgr.start()

    # 监听关闭事件：根据 close_action 配置决定直接退出、隐藏托盘，或弹出前端确认弹窗让用户选择
    _last_close_time = 0.0

    def _notify_frontend_close_prompt() -> None:
        try:
            window.evaluate_js("window.dispatchEvent(new CustomEvent('anlan:close-requested'))")
        except Exception as err:
            log.debug("派发前端关闭确认弹窗失败，回退最小化至托盘: %s", err)
            try:
                window.hide()
            except Exception:
                pass

    def on_closing():
        nonlocal _last_close_time
        if getattr(bridge, "_force_closing", False):
            return True

        now = time.time()
        if now - _last_close_time < 0.35:
            return False
        _last_close_time = now

        close_action = str(get_config_dict().get("close_action", "ask")).strip().lower()
        if close_action == "tray":
            log.info("根据配置将窗口隐藏至系统托盘")
            try:
                window.hide()
            except Exception:
                pass
            return False

        if close_action == "exit":
            log.info("根据配置直接退出 安澜")
            bridge._force_closing = True
            try:
                battery.stop()
                network.stop()
                tray_mgr.stop()
            except Exception:
                pass
            return True

        log.info("捕获窗口关闭事件，弹出关闭方式选择弹窗")
        threading.Thread(target=_notify_frontend_close_prompt, daemon=True).start()
        return False  # 拦截原生销毁，交由用户弹窗选择

    window.events.closing += on_closing

    # 查找「安澜」专属图标文件
    icon_file = APP_DIR / "assets" / "app_icon.ico"
    if not icon_file.exists():
        icon_file = APP_DIR / "_internal" / "assets" / "app_icon.ico"
    if not icon_file.exists():
        icon_file = Path(__file__).resolve().parent.parent / "assets" / "app_icon.ico"

    if sys.platform == "win32":
        try:
            import ctypes

            # 注册独立 Windows AppUserModelID，彻底剥离 Python 任务栏标识
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"MH.AnLan.Desktop.{APP_VERSION}")
        except Exception as e:
            log.debug("注册 AppUserModelID 异常: %s", e)

        # 注入 Edge WebView2 原生硬件加速与零拷贝平滑滚轮指令
        current_args = os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "")
        gpu_args = (
            "--enable-gpu-rasterization "
            "--enable-zero-copy "
            "--ignore-gpu-blocklist "
            "--enable-smooth-scrolling "
            "--disable-features=msWebOOUI,msPdfOOUI"
        )
        if gpu_args not in current_args:
            os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = f"{current_args} {gpu_args}".strip()

    # 启动 Webview 事件循环（显式优先调用 edgechromium / WebView2 硬件加速渲染内核）
    try:
        icon_arg = str(icon_file.resolve()) if icon_file.exists() else None
        gui_target = "edgechromium" if sys.platform == "win32" else None
        webview.start(debug=False, icon=icon_arg, gui=gui_target)
    except Exception as err:
        log.error("Webview 运行时异常: %s", err)
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"安澜 启动异常: {err}\n\n可能原因：缺失 pythonnet 或 Edge WebView2 运行时。\n请尝试在终端执行: pip install pythonnet",
                    "安澜 错误",
                    0x10,
                )
            except Exception:
                pass
        raise
    finally:
        try:
            battery.stop()
            network.stop()
            tray_mgr.stop()
        except Exception:
            pass


__all__ = [
    "MainWindow",
    "_SETTINGS_SCHEMA",
    "_DashboardPage",
    "_LogPage",
    "_SettingsPage",
    "_SideBar",
    "_Worker",
    "_COLORS",
    "_STYLESHEET",
    "launch_gui",
]
