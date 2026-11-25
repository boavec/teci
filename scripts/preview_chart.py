"""把 dump_svg.js 导出的散点图 SVG 重新画成 PNG，用来肉眼检查标签有没有互相压。

沙箱里开不了 headless 浏览器，所以这里只实现我们图表实际用到的那几种图元：
line / circle / polyline / text。不是通用 SVG 渲染器，够看布局就行。

用法: python scripts/preview_chart.py
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "build" / "scatter.svg"
OUT = ROOT / "build" / "scatter_preview.png"

SCALE = 1.5
W, H = 1000, 470

BG = (10, 10, 22)
GRID = (26, 26, 44)
INK = (195, 205, 236)
INK_CN = (167, 243, 208)
AXIS = (139, 149, 181)

FONT = "C:/Windows/Fonts/msyh.ttc"


def font(size: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, max(8, int(round(size * SCALE))))


def local(tag: str) -> str:
    return tag.split("}")[-1]


def parse_color(v: str | None, default=(255, 255, 255)) -> tuple[int, int, int]:
    if not v or not v.startswith("#"):
        return default
    v = v.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    try:
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return default


def main() -> int:
    if not SVG.exists():
        print(f"找不到 {SVG}，先跑 node scripts/dump_svg.js")
        return 1

    tree = ET.parse(SVG)
    root = tree.getroot()

    # 元素是分图层嵌在 <g> 里的，必须遍历全部后代，否则会漏掉坐标轴文字
    buckets: dict[str, list] = {"line": [], "polyline": [], "circle": [], "text": []}
    for el in root.iter():
        t = local(el.tag)
        if t in buckets:
            buckets[t].append(el)

    img = Image.new("RGB", (int(W * SCALE), int(H * SCALE)), BG)
    d = ImageDraw.Draw(img, "RGBA")

    # 先画网格线
    for el in buckets["line"]:
        d.line(
            [
                (float(el.get("x1", 0)) * SCALE, float(el.get("y1", 0)) * SCALE),
                (float(el.get("x2", 0)) * SCALE, float(el.get("y2", 0)) * SCALE),
            ],
            fill=GRID,
            width=1,
        )

    # 折线（前沿）
    for el in buckets["polyline"]:
        cls = el.get("class", "")
        pts = [
            (float(p.split(",")[0]) * SCALE, float(p.split(",")[1]) * SCALE)
            for p in el.get("points", "").split()
            if "," in p
        ]
        if len(pts) < 2:
            continue
        color = (45, 212, 191) if "cn" in cls else (150, 140, 250)
        d.line(pts, fill=color, width=2)

    # 圆点
    for el in buckets["circle"]:
        cx = float(el.get("cx", 0)) * SCALE
        cy = float(el.get("cy", 0)) * SCALE
        r = float(el.get("r", 3)) * SCALE
        fill = parse_color(el.get("fill"))
        op = float(el.get("fill-opacity", el.get("opacity", 1)) or 1)
        alpha = int(255 * op)
        stroke = el.get("stroke")
        sw = float(el.get("stroke-width", 0) or 0) * SCALE
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill + (alpha,))
        if stroke and sw:
            d.ellipse([cx - r, cy - r, cx + r, cy + r],
                      outline=parse_color(stroke) + (255,), width=max(1, int(sw)))

    # 文字（带浅色描边模拟 halo）
    for el in buckets["text"]:
        txt = "".join(el.itertext())
        if not txt.strip():
            continue
        cls = el.get("class", "")
        size = 10 if "plabel-cn" in cls else (10.5 if "plabel" in cls else 11.5)
        f = font(size)
        x = float(el.get("x", 0)) * SCALE
        y = float(el.get("y", 0)) * SCALE
        anchor = el.get("text-anchor", "start")
        w = d.textlength(txt, font=f)
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        if "plabel" in cls:
            color = (110, 231, 183) if "plabel-cn" in cls else INK
            d.text((x, y), txt, font=f, fill=color + (255,), anchor="ls",
                   stroke_width=2, stroke_fill=(10, 10, 22, 235))
        else:
            d.text((x, y), txt, font=f, fill=AXIS + (255,), anchor="ls")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"预览：{OUT.relative_to(ROOT)}  {img.size[0]}×{img.size[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
