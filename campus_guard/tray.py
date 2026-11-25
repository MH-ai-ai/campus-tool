from __future__ import annotations

import sys
import threading
import time
from typing import Any

from .logging_setup import get_logger
from .models import GuardState

log = get_logger()


def get_tray_color(state: GuardState) -> str:
    if state.network_ok is False:
        return "red"
    if state.power_plugged is False:
        return "yellow"
    if state.network_ok is True:
        return "green"
    return "gray"


def create_tray_icon(color: str, size: int = 64):
    from pathlib import Path
    from PIL import Image, ImageDraw
    from .paths import APP_DIR

    icon_path = APP_DIR / "assets" / "app_icon.png"
    if not icon_path.exists():
        icon_path = APP_DIR / "_internal" / "assets" / "app_icon.png"
    if not icon_path.exists():
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "app_icon.png"

    colors = {
        "green": (42, 157, 108),    # 低饱和松绿（在线）
        "yellow": (207, 138, 39),   # 柔珀（警告）
        "red": (207, 77, 84),       # 绛红（断网）
        "gray": (142, 150, 164),    # 冷灰（未知）
    }
    fill_color = colors.get(color, colors["gray"])

    if icon_path.exists():
        try:
            base_img = Image.open(icon_path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
            draw = ImageDraw.Draw(base_img)
            dot_r = max(4, int(size * 0.17))
            dot_cx = int(size * 0.77)
            dot_cy = int(size * 0.77)
            ring = max(2, int(size * 0.04))
            # 白色描边环，使状态点在黛蓝底板与深浅任务栏上均清晰可辨
            draw.ellipse([dot_cx - dot_r - ring, dot_cy - dot_r - ring, dot_cx + dot_r + ring, dot_cy + dot_r + ring], fill=(255, 255, 255, 245))
            draw.ellipse([dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r], fill=fill_color)
            return base_img
        except Exception:
            pass

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill=fill_color)
    draw.ellipse([size // 4, size // 4, size * 3 // 4, size * 3 // 4], fill=(255, 255, 255, 90))
    return img


class PystrayTrayManager:
    """基于 pystray 的现代化轻量系统托盘管理器，支持与 Webview 窗口协同。"""

    def __init__(self, bridge: Any, window: Any = None) -> None:
        self.bridge = bridge
        self.window = window
        self.icon = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        try:
            import pystray
            from pystray import Menu, MenuItem

            menu = Menu(
                MenuItem("打开控制中心", self._on_open, default=True),
                MenuItem("重新连接 Wi-Fi", self._on_reconnect_wifi),
                MenuItem("立即认证校园网", self._on_auth_campus),
                MenuItem("启动代理并开系统代理", self._on_launch_proxy),
                Menu.SEPARATOR,
                MenuItem("退出 AutoCampusNet", self._on_exit),
            )

            initial_icon = create_tray_icon("green")
            self.icon = pystray.Icon("AutoCampusNet", initial_icon, "AutoCampusNet · 校园网守护", menu=menu)
            self._running = True

            def _run():
                try:
                    self.icon.run()
                except Exception as err:
                    log.debug("托盘运行退出: %s", err)

            self._thread = threading.Thread(target=_run, daemon=True)
            self._thread.start()
            log.info("pystray 系统托盘常驻守护已启动")
        except Exception as err:
            log.warning("启动 pystray 系统托盘失败: %s", err)

    def update_icon(self, color: str, tooltip: str = "") -> None:
        if self.icon and self._running:
            try:
                self.icon.icon = create_tray_icon(color)
                if tooltip:
                    self.icon.title = tooltip
            except Exception:
                pass

    def stop(self) -> None:
        """优雅停止托盘图标循环，确保完全退出时不残留任务栏托盘图标。"""
        self._running = False
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass

    def _on_open(self, icon, item) -> None:
        if self.window:
            try:
                self.window.show()
                self.window.restore()
            except Exception:
                pass

    def _on_reconnect_wifi(self, icon, item) -> None:
        if self.bridge:
            threading.Thread(target=self.bridge.reconnect_wifi, daemon=True).start()

    def _on_auth_campus(self, icon, item) -> None:
        if self.bridge:
            threading.Thread(target=self.bridge.auth_campus, daemon=True).start()

    def _on_launch_proxy(self, icon, item) -> None:
        if self.bridge:
            threading.Thread(target=self.bridge.launch_proxy_now, daemon=True).start()

    def _on_exit(self, icon, item) -> None:
        self._running = False
        try:
            icon.stop()
        except Exception:
            pass
        if self.bridge:
            self.bridge.close_app()
        else:
            sys.exit(0)
