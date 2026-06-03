from __future__ import annotations

from .models import GuardState


def get_tray_color(state: GuardState) -> str:
    if state.network_ok is False:
        return "red"
    if state.power_plugged is False:
        return "yellow"
    if state.network_ok is True:
        return "green"
    return "gray"


def create_tray_icon(color: str, size: int = 64):
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    colors = {
        "green": (76, 175, 80),
        "yellow": (255, 193, 7),
        "red": (244, 67, 54),
        "gray": (158, 158, 158),
    }
    draw.ellipse([4, 4, size - 4, size - 4], fill=colors.get(color, colors["gray"]))
    return img


def pil_image_to_qicon(pil_img):
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
