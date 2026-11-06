from __future__ import annotations

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
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "app_icon.png"

    colors = {
        "green": (50, 215, 75),    # Apple Mint Green
        "yellow": (255, 159, 10),   # Apple Amber
        "red": (255, 69, 58),       # Apple Coral Red
        "gray": (142, 142, 147),    # Apple Neutral Gray
    }
    fill_color = colors.get(color, colors["gray"])

    if icon_path.exists():
        try:
            base_img = Image.open(icon_path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
            draw = ImageDraw.Draw(base_img)
            dot_r = max(4, int(size * 0.16))
            dot_cx = int(size * 0.78)
            dot_cy = int(size * 0.78)
            draw.ellipse([dot_cx - dot_r - 2, dot_cy - dot_r - 2, dot_cx + dot_r + 2, dot_cy + dot_r + 2], fill=(15, 17, 24, 240))
            draw.ellipse([dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r], fill=fill_color)
            return base_img
        except Exception:
            pass

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill=fill_color)
    draw.ellipse([size // 4, size // 4, size * 3 // 4, size * 3 // 4], fill=(255, 255, 255, 90))
    return img


def pil_image_to_qicon(pil_img):
    try:
        from PyQt6.QtGui import QIcon, QImage, QPixmap

        raw = pil_img.tobytes("raw", "RGBA")
        qimg = QImage(
            raw,
            pil_img.width,
            pil_img.height,
            pil_img.width * 4,
            QImage.Format.Format_RGBA8888,
        )
        return QIcon(QPixmap.fromImage(qimg))
    except ImportError:
        return None


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
                Menu.SEPARATOR,
                MenuItem("退出 Campus Guard", self._on_exit),
            )

            initial_icon = create_tray_icon("green")
            self.icon = pystray.Icon("CampusGuard", initial_icon, "Campus Guard 校园网守护", menu=menu)
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
