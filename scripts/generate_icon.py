from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter


def draw_cyber_shield(size: int = 512) -> Image.Image:
    # 4x 超采样绘制以获得顶级超采样抗锯齿
    scale = 4
    canvas_size = size * scale
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx = canvas_size / 2
    cy = canvas_size / 2

    # 1. 外部环境光晕 (Glow layer)
    glow_img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    glow_box = [cx - canvas_size * 0.38, cy - canvas_size * 0.40, cx + canvas_size * 0.38, cy + canvas_size * 0.42]
    glow_draw.ellipse(glow_box, fill=(10, 132, 255, 60))
    glow_draw.ellipse([cx - canvas_size * 0.28, cy - canvas_size * 0.28, cx + canvas_size * 0.28, cy + canvas_size * 0.35], fill=(50, 215, 75, 45))
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=30 * scale))
    img.alpha_composite(glow_img)

    # 2. 盾牌外部轮廓多边形
    # 顶部平滑微弧、侧边向下微收、底部尖角圆润
    pad_x = canvas_size * 0.16
    pad_y = canvas_size * 0.12
    bot_y = canvas_size * 0.88
    mid_y = canvas_size * 0.58

    shield_pts = [
        (cx, pad_y + canvas_size * 0.02),
        (canvas_size - pad_x, pad_y + canvas_size * 0.06),
        (canvas_size - pad_x * 1.08, mid_y),
        (cx, bot_y),
        (pad_x * 1.08, mid_y),
        (pad_x, pad_y + canvas_size * 0.06),
    ]

    # 外圈深色金属微反光边缘
    draw.polygon(shield_pts, fill=(28, 30, 42, 255), outline=(10, 132, 255, 230), width=int(5 * scale))

    # 3. 盾牌主体内部渐变底色
    inner_pad = canvas_size * 0.03
    inner_pts = [
        (cx, pad_y + canvas_size * 0.02 + inner_pad),
        (canvas_size - pad_x - inner_pad, pad_y + canvas_size * 0.06 + inner_pad),
        (canvas_size - pad_x * 1.08 - inner_pad, mid_y - inner_pad * 0.5),
        (cx, bot_y - inner_pad * 1.2),
        (pad_x * 1.08 + inner_pad, mid_y - inner_pad * 0.5),
        (pad_x + inner_pad, pad_y + canvas_size * 0.06 + inner_pad),
    ]
    draw.polygon(inner_pts, fill=(17, 18, 25, 255))

    # 4. 核心符号：翡翠绿脉冲雷达 / 守护锁环
    # 绘制同心圆自愈波纹弧
    arc_center = (cx, cy + canvas_size * 0.02)
    # 外波纹
    r1 = canvas_size * 0.22
    draw.arc(
        [arc_center[0] - r1, arc_center[1] - r1, arc_center[0] + r1, arc_center[1] + r1],
        start=210,
        end=330,
        fill=(50, 215, 75, 180),
        width=int(6 * scale),
    )
    # 内波纹
    r2 = canvas_size * 0.15
    draw.arc(
        [arc_center[0] - r2, arc_center[1] - r2, arc_center[0] + r2, arc_center[1] + r2],
        start=205,
        end=335,
        fill=(50, 215, 75, 240),
        width=int(7 * scale),
    )

    # 5. 核心脉冲发光微球 (Pulse Core)
    r_core = canvas_size * 0.065
    draw.ellipse(
        [arc_center[0] - r_core, arc_center[1] - r_core * 0.8, arc_center[0] + r_core, arc_center[1] + r_core * 1.2],
        fill=(50, 215, 75, 255),
    )
    # 核心高光点
    draw.ellipse(
        [arc_center[0] - r_core * 0.45, arc_center[1] - r_core * 0.45, arc_center[0] + r_core * 0.45, arc_center[1] + r_core * 0.45],
        fill=(255, 255, 255, 220),
    )

    # 下采样至目标分辨率（顶级抗锯齿）
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_img


def main():
    root = Path(__file__).resolve().parent.parent
    assets_dir = root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    img = draw_cyber_shield(512)
    png_path = assets_dir / "app_icon.png"
    ico_path = assets_dir / "app_icon.ico"

    img.save(png_path, "PNG")
    print(f"Saved PNG icon to: {png_path}")

    # 生成包含全部 Windows 标准尺寸的多层 ICO 文件
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(ico_path, format="ICO", sizes=sizes)
    print(f"Saved multi-resolution ICO icon to: {ico_path}")


if __name__ == "__main__":
    main()
