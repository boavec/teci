"""生成社交分享封面图（1200×630），配色与网页一致。

输出 site/og.png；构建脚本会把它复制到 publish/ 一起部署。

设计上刻意**不写日期和模型数量**——这张图是一次性生成、长期复用的，
写死数字的话过几天就变成了假信息。

用法: python scripts/make_og.py
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
OUT = ROOT / "site" / "og.png"

W, H = 1200, 630

# 与网页一致的深空配色
SPACE = (6, 6, 15)
INK = (238, 241, 251)
MUTED = (154, 164, 196)
FAINT = (139, 149, 181)
ACCENT = (165, 180, 252)

FONT_BOLD = ["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc"]
FONT_REG = ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]


def pick_font(cands: list[str], size: int) -> ImageFont.FreeTypeFont:
    for c in cands:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except OSError:
                continue
    raise SystemExit(f"找不到可用字体：{cands}")


def nebula_background() -> Image.Image:
    """四团径向辉光，对应网页 body 上的四层 radial-gradient。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.zeros((H, W, 3), np.float32)
    img += np.array(SPACE, np.float32)

    def blob(cx, cy, radius, color, strength):
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        f = np.clip(1.0 - d / radius, 0.0, 1.0) ** 2.3
        img[:] += f[..., None] * np.array(color, np.float32) * strength

    blob(0.12 * W, -0.10 * H, 980, (99, 102, 241), 0.62)    # 靛蓝
    blob(0.92 * W, -0.06 * H, 820, (168, 85, 247), 0.55)    # 紫罗兰
    blob(0.86 * W, 0.96 * H, 900, (236, 72, 153), 0.24)     # 品红
    blob(0.02 * W, 0.92 * H, 720, (34, 211, 238), 0.15)     # 青

    # 四周压暗，让文字更清楚
    cx, cy = W / 2, H / 2
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / np.hypot(cx, cy)
    img *= (1.0 - 0.42 * np.clip(d - 0.35, 0, 1) ** 1.6)[..., None]

    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def add_stars(img: Image.Image) -> Image.Image:
    rng = np.random.default_rng(20261124)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    for _ in range(300):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(0.4, 1.4)
        a = int(rng.uniform(26, 150))
        t = rng.random()
        col = (186, 220, 255) if t > 0.88 else ((233, 205, 255) if t > 0.76 else (255, 255, 255))
        d.ellipse([x - r, y - r, x + r, y + r], fill=col + (a,))

    # 少量略大略亮的星，不做光晕（光晕缩到这个尺寸只会变成灰斑）
    for _ in range(9):
        x, y = rng.uniform(40, W - 40), rng.uniform(30, H - 30)
        r = rng.uniform(1.5, 2.1)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 215))

    img = img.convert("RGBA")
    img.alpha_composite(layer)
    return img.convert("RGB")


def gradient_text(base: Image.Image, xy: tuple[int, int], text: str,
                  font: ImageFont.FreeTypeFont,
                  c1: tuple[int, int, int], c2: tuple[int, int, int]) -> int:
    """把文字画成横向渐变，返回文字宽度。"""
    bbox = font.getbbox(text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 6
    mask = Image.new("L", (tw + pad * 2, th + pad * 2), 0)
    ImageDraw.Draw(mask).text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=255)

    grad = Image.new("RGB", mask.size)
    gd = ImageDraw.Draw(grad)
    n = max(mask.size[0] - 1, 1)
    for x in range(mask.size[0]):
        t = x / n
        gd.line([(x, 0), (x, mask.size[1])],
                fill=tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3)))

    base.paste(grad, (xy[0] - pad, xy[1] - pad), mask)
    return tw


def spaced_text(draw, xy, text: str, font, fill, spacing: int):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + spacing


def build() -> Path:
    img = nebula_background()
    img = add_stars(img)
    draw = ImageDraw.Draw(img)

    f_kicker = pick_font(FONT_REG, 19)
    f_title = pick_font(FONT_BOLD, 116)
    f_cn = pick_font(FONT_REG, 40)
    f_sub = pick_font(FONT_REG, 37)
    f_foot = pick_font(FONT_REG, 22)

    x = 84

    # 顶部小标
    spaced_text(draw, (x, 110), "TOKEN EFFECTIVE COST INDEX", f_kicker, ACCENT, 5)

    # 主标题 TECI（渐变）+ 中文
    tw = gradient_text(img, (x, 156), "TECI", f_title, (255, 255, 255), (196, 181, 253))
    draw = ImageDraw.Draw(img)
    cn_bbox = f_cn.getbbox("· 词元成本指数")
    cn_h = cn_bbox[3] - cn_bbox[1]
    title_bbox = f_title.getbbox("TECI")
    title_h = title_bbox[3] - title_bbox[1]
    draw.text((x + tw + 26, 156 + title_bbox[1] + (title_h - cn_h) // 2 - cn_bbox[1]),
              "· 词元成本指数", font=f_cn, fill=MUTED)

    # 一句话
    draw.text((x, 336), "买到一分 AI 智能，", font=f_sub, fill=INK)
    draw.text((x, 390), "要花多少钱？", font=f_sub, fill=INK)

    # 渐变分隔线
    line_y = 470
    for i in range(300):
        t = i / 299
        col = (int(139 * (1 - t) + 34 * t), int(92 * (1 - t) + 211 * t), int(246 * (1 - t) + 238 * t))
        draw.line([(x + i, line_y), (x + i, line_y + 2)], fill=col)

    # 底部说明
    draw.text((x, 504), "公开数据 · 公开方法论 · 每日更新", font=f_foot, fill=MUTED)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"生成：{p.relative_to(ROOT)}  {p.stat().st_size/1024:.0f} KB  ({W}×{H})")
