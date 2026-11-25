"""检查发布用的单文件页面是否真的自包含（不依赖任何外部资源）。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "publish" / "index.html"

html = PAGE.read_text(encoding="utf-8")
size = PAGE.stat().st_size

print(f"文件：{PAGE.relative_to(ROOT)}")
print(f"大小：{size:,} 字节（约 {size/1024:.0f} KB）\n")

checks = [
    ("外部脚本 src", r'<script[^>]+src='),
    ("外部样式 link", r'<link[^>]+rel=["\']stylesheet'),
    ("外部图片 img", r'<img[^>]+src=["\']https?:'),
    ("@font-face", r'@font-face'),
    ("CSS 里 url(http…)", r'url\(\s*[\'"]?https?:'),
    ("iframe", r'<iframe'),
]

blocking = 0
for name, pat in checks:
    n = len(re.findall(pat, html, re.I))
    if n and name not in ("外部图片 img",):
        blocking += n
    print(f"{name:<20}{n:>3}  {'← 会阻断离线' if n and 'img' not in name else ''}")

print(f"\n外部资源引用合计：{blocking} 处", "（自包含 ✅）" if blocking == 0 else "（需要处理 ⚠️）")

links = sorted(set(re.findall(r'href=["\'](https?://[^"\']+)["\']', html)))
print("\n普通超链接（点击才跳转，不影响加载）：")
for u in links:
    print("  " + u)

print("\n基础标签：")
for name, pat in [
    ("charset", r'charset=["\']utf-8["\']'),
    ("viewport", r'name=["\']viewport["\']'),
    ("title", r"<title>([^<]*)</title>"),
    ("description", r'name=["\']description["\']'),
    ("og:title", r'property=["\']og:title["\']'),
    ("og:description", r'property=["\']og:description["\']'),
    ("theme-color", r'name=["\']theme-color["\']'),
]:
    m = re.search(pat, html, re.I)
    print(f"  {name:<14}{'✅' if m else '❌'}" + (f"  {m.group(1)[:40]}" if m and m.groups() else ""))

# ---- 分享卡片 ----
print("\n分享卡片：")
og_image = re.search(r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html, re.I)
og_url = re.search(r'property=["\']og:url["\']\s+content=["\']([^"\']+)["\']', html, re.I)
og_png = PAGE.parent / "og.png"

ok = True
if og_image:
    url = og_image.group(1)
    absolute = url.startswith(("http://", "https://"))
    placeholder = "YOUR-DOMAIN" in url
    print(f"  og:image       {url}")
    print(f"  绝对地址       {'✅' if absolute else '❌ 平台不会去抓相对路径'}")
    if placeholder:
        print("  ⚠️ 域名还是占位符：部署后改 build_teci.py 里的 SITE_URL 再重新构建")
    ok = ok and absolute
else:
    print("  og:image       ❌ 未设置")
    ok = False

if og_url:
    print(f"  og:url         {og_url.group(1)}")
else:
    print("  og:url         ❌ 未设置")

if og_png.exists():
    print(f"  publish/og.png ✅ {og_png.stat().st_size/1024:.0f} KB")
else:
    print("  publish/og.png ❌ 缺失（跑 scripts/make_og.py 后重新构建）")
    ok = False

print("\n" + ("分享卡片配置完整" if ok else "分享卡片还有问题，见上面 ⚠️/❌"))
