"""检查网页配色在深空背景上的对比度是否达标。

深色主题最常见的问题是"看着高级但读不清"。这里按 WCAG 2.1 公式算实际对比度：
  * 正文小字（≤18px）要求 ≥ 4.5:1
  * 大号标题 / 次要装饰文字 要求 ≥ 3.0:1

调色板直接从 site/index.html 的 CSS 变量里读，避免脚本和样式各说各话。

用法: python scripts/check_contrast.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "site" / "index.html"


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def lin(c: int) -> float:
    s = c / 255
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = luminance(hex_rgb(a)), luminance(hex_rgb(b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def blend(fg: tuple[int, int, int], alpha: float, bg: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg))


def to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def main() -> int:
    css = HTML.read_text(encoding="utf-8")

    def var(name: str) -> str:
        m = re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{6}})", css)
        if not m:
            raise SystemExit(f"CSS 变量 --{name} 没找到，index.html 结构可能变了")
        return m.group(1)

    space = var("space")
    ink, muted, faint = var("ink"), var("muted"), var("faint")
    cn, ov = var("cn"), var("ov")

    # 卡片是 rgba(255,255,255,.062)→.018 的渐变，取偏暗的 3% 作为最坏情况
    card = to_hex(blend((255, 255, 255), 0.03, hex_rgb(space)))

    # 从样式表里抓取硬编码的次要色
    def grab(pat: str, fallback: str) -> str:
        m = re.search(pat, css)
        return m.group(1) if m else fallback

    axis = grab(r"\.axis text\{fill:(#[0-9a-fA-F]{6})", "#8b95b5")
    plabel = grab(r"\.plabel\{font-size:10\.5px;fill:(#[0-9a-fA-F]{6})", "#c3cdec")
    kicker = grab(r"color:(#[0-9a-fA-F]{6});font-weight:600;\n  \}", "#a5b4fc")
    body_txt = grab(r"font-size:13\.5px;color:(#[0-9a-fA-F]{6})", "#c2cbe6")

    checks = [
        ("正文 ink / 深空底", ink, space, 4.5),
        ("正文 ink / 卡片", ink, card, 4.5),
        ("次要 muted / 卡片", muted, card, 4.5),
        ("次要 muted / 深空底", muted, space, 4.5),
        ("辅助 faint / 卡片", faint, card, 4.5),
        ("辅助 faint / 深空底", faint, space, 4.5),
        ("国内色 cn / 卡片", cn, card, 4.5),
        ("海外色 ov / 卡片", ov, card, 4.5),
        ("坐标轴文字 / 深空底", axis, space, 4.5),
        ("图内标签 / 深空底", plabel, space, 4.5),
        ("大写小标题 / 深空底", kicker, space, 4.5),
        ("方法论正文 / 卡片", body_txt, card, 4.5),
    ]

    print(f"深空底色 {space} · 卡片底色 {card}\n")
    print(f"{'项目':<22}{'前景':<10}{'对比度':>8}  {'要求':>5}  结果")
    print("-" * 62)

    failed = 0
    for name, fg, bg, need in checks:
        r = contrast(fg, bg)
        ok = r >= need
        if not ok:
            failed += 1
        print(f"{name:<22}{fg:<10}{r:>7.2f}:1  {need:>5.1f}  {'PASS' if ok else 'FAIL'}")

    print("-" * 62)
    print(f"{len(checks) - failed}/{len(checks)} 达标")
    if failed:
        print("\n有未达标项：小字低于 4.5:1 的话，在实际屏幕上会发灰、难读。请调亮对应变量。")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
