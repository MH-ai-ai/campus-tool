"""生成「AutoCampusNet」应用图标（iOS 风连续圆角黛蓝底板 + 三道平缓水波）。

输出：assets/app_icon.png（512px）与多尺寸 assets/app_icon.ico。
运行：.venv\\Scripts\\python.exe scripts/generate_icon.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

SIZE = 512
SS = 4  # 超采样倍数，保证边缘平滑
S = SIZE * SS

# 黛蓝渐变（顶部略亮，底部沉稳）
SLATE_TOP = (74, 123, 184)
SLATE_BOT = (30, 66, 116)


def squircle_mask(n: float = 5.0, radius: float = 0.46) -> Image.Image:
    """iOS 风格连续圆角（超椭圆）遮罩。"""
    mask = Image.new("L", (S, S), 0)
    pts = []
    steps = 720
    for i in range(steps):
        t = 2 * math.pi * i / steps
        c, s = math.cos(t), math.sin(t)
        x = math.copysign(abs(c) ** (2 / n), c)
        y = math.copysign(abs(s) ** (2 / n), s)
        pts.append((S / 2 + x * radius * S, S / 2 + y * radius * S))
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    return mask


def vgradient(top: tuple[int, int, int], bot: tuple[int, int, int]) -> Image.Image:
    grad = Image.linear_gradient("L").resize((S, S))
    return Image.composite(
        Image.new("RGB", (S, S), bot), Image.new("RGB", (S, S), top), grad
    ).convert("RGBA")


def base_tile() -> Image.Image:
    """渐变底板 + 顶部柔和高光 + 极细内描边。"""
    tile = vgradient(SLATE_TOP, SLATE_BOT)
    grad = Image.linear_gradient("L").rotate(180).resize((S, int(S * 0.55)))
    gloss = Image.new("RGBA", (S, int(S * 0.55)), (255, 255, 255, 0))
    gloss.putalpha(grad.point(lambda v: int(v * 0.16)))
    tile.alpha_composite(gloss, (0, 0))

    mask = squircle_mask()
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(tile, (0, 0), mask)
    ring = ImageChops.subtract(mask, squircle_mask(radius=0.455))
    out.paste(Image.new("RGBA", (S, S), (255, 255, 255, 60)), (0, 0), ring)
    return out


def stroke(img: Image.Image, pts, width: float, rgb, alpha: int = 255) -> None:
    """沿路径用圆章叠加成平滑圆头描边（单次合成，避免 alpha 叠加出现断点）。"""
    mask = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mask)
    r = width / 2
    step = max(1.0, r / 3)
    dense = [pts[0]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        for k in range(1, n + 1):
            dense.append((x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n))
    for x, y in dense:
        d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    if alpha < 255:
        mask = mask.point(lambda v: v * alpha // 255)
    img.paste(Image.new("RGBA", (S, S), tuple(rgb) + (255,)), (0, 0), mask)


def draw_autocampusnet(size: int = SIZE) -> Image.Image:
    """绘制「AutoCampusNet」图标：三道自上而下渐淡的平缓水波，寓意网络稳如平波。"""
    img = base_tile()
    x0, x1 = S * 0.25, S * 0.75
    amp = S * 0.04
    for row, (y, alpha) in enumerate(((0.37, 255), (0.5, 210), (0.63, 160))):
        phase = row * 0.8
        pts = []
        for i in range(241):
            t = i / 240
            pts.append((x0 + (x1 - x0) * t, S * y + amp * math.sin(t * 2 * math.pi * 1.5 + phase)))
        stroke(img, pts, S * 0.052, (255, 255, 255), alpha)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    assets_dir = root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    img = draw_autocampusnet(SIZE)
    png_path = assets_dir / "app_icon.png"
    ico_path = assets_dir / "app_icon.ico"

    img.save(png_path, "PNG")
    print(f"Saved PNG icon to: {png_path}")

    # 多尺寸 ICO：覆盖 Windows 任务栏、托盘、资源管理器全部标准尺寸
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
    img.save(ico_path, format="ICO", sizes=sizes)
    print(f"Saved multi-resolution ICO icon to: {ico_path}")


if __name__ == "__main__":
    main()
