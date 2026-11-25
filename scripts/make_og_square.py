"""生成朋友圈用的方形封面（1080×1080）。

朋友圈的链接卡片缩略图是方形，横版 og.png（1200×630）会被裁掉两侧，
标题常常被切。这张方图把文字集中在中部，裁切后仍然完整。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "og-square.png"

S = 1080
SPACE = (6, 6, 15)
INK = (238, 241, 251)
MUTED = (154, 164, 196)
FAINT = (139, 149, 181)
ACCENT = (165, 180, 252)

BOLD = ["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc"]
REG = ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]


def font(cands, size):
    for c in cands:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    raise SystemExit(f"找不到字体：{cands}")


def background() -> Image.Image:
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    img = np.zeros((S, S, 3), np.float32) + np.array(SPACE, np.float32)

    def blob(cx, cy, r, color, k):
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        f = np.clip(1.0 - d / r, 0.0, 1.0) ** 2.3
        img[:] += f[..., None] * np.array(color, np.float32) * k

    blob(0.10 * S, -0.05 * S, 900, (99, 102, 241), 0.55)
    blob(0.95 * S, 0.08 * S, 820, (168, 85, 247), 0.50)
    blob(0.85 * S, 1.02 * S, 860, (236, 72, 153), 0.24)
    blob(0.02 * S, 0.95 * S, 700, (34, 211, 238), 0.14)

    cx = cy = S / 2
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / np.hypot(cx, cy)
    img *= (1.0 - 0.40 * np.clip(d - 0.3, 0, 1) ** 1.6)[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def stars(img: Image.Image) -> Image.Image:
    rng = np.random.default_rng(20261125)
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(300):
        x, y = rng.uniform(0, S), rng.uniform(0, S)
        r = rng.uniform(0.5, 1.7)
        a = int(rng.uniform(26, 150))
        t = rng.random()
        col = (186, 220, 255) if t > 0.88 else ((233, 205, 255) if t > 0.76 else (255, 255, 255))
        d.ellipse([x - r, y - r, x + r, y + r], fill=col + (a,))
    out = img.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


def spaced(draw, xy, text, f, fill, gap):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + gap


def build() -> Path:
    img = stars(background())
    d = ImageDraw.Draw(img)

    f_kick = font(REG, 26)
    f_teci = font(BOLD, 170)
    f_cn = font(REG, 54)
    f_sub = font(REG, 44)
    f_url = font(REG, 30)

    # 顶部小标
    spaced(d, (86, 150), "TOKEN EFFECTIVE COST INDEX", f_kick, ACCENT, 6)

    # 主标题
    d.text((80, 210), "TECI", font=f_teci, fill=(255, 255, 255))
    d.text((86, 420), "词元成本指数", font=f_cn, fill=MUTED)

    # 分隔线
    for i in range(360):
        t = i / 359
        col = (int(139 * (1 - t) + 34 * t), int(92 * (1 - t) + 211 * t), int(246 * (1 - t) + 238 * t))
        d.line([(86 + i, 512), (86 + i, 514)], fill=col)

    # 一句话
    d.text((86, 566), "买到一分 AI 智能，", font=f_sub, fill=INK)
    d.text((86, 626), "要花多少钱？", font=f_sub, fill=INK)

    # 网址（朋友圈发图时，让人知道去哪看）
    d.text((86, 936), "boavec.github.io/teci", font=f_url, fill=FAINT)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)

    # 微信抓取分享缩略图需要页面里有真实的 <img>，且尺寸 ≥300×300。
    # 这里再输出一张小图，供 index.html 里的隐藏图使用。
    thumb = ROOT / "site" / "og-thumb.png"
    img.resize((300, 300), Image.LANCZOS).save(thumb, "PNG", optimize=True)
    print(f"生成：{thumb.relative_to(ROOT)}  {thumb.stat().st_size/1024:.0f} KB  (300×300)")
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"生成：{p.relative_to(ROOT)}  {p.stat().st_size/1024:.0f} KB  ({S}×{S})")
