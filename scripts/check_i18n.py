"""检查中英双语文案覆盖率。

两类待译文本：
  1. 静态：site/index.html 里含中文的文本节点（跳过语言选择器、备案号、code）
  2. 动态：JS 里用 tr('...') 或 T('...') 包裹的中文

比较时对键做规范化（空白折叠 + 弯引号转直引号），避免因引号写法不同误报。

要求 100%——差一条就会在英文页露出中文。

用法: python scripts/check_i18n.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from lxml import html as LH

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
EN = ROOT / "site" / "i18n" / "en.json"
CJK = re.compile(r"[\u4e00-\u9fff]")
QUOTES = str.maketrans({"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'"})

# 这些中文在英文里本就没有对应词，允许译文为空
ALLOW_EMPTY = {"个"}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).translate(QUOTES).strip()


src = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

# ---------- 静态 ----------
doc = LH.fromstring(src)
for bad in doc.xpath("//script|//style"):
    bad.getparent().remove(bad)

static: list[str] = []
for el in doc.iter():
    if not isinstance(el.tag, str) or el.tag in ("title", "meta"):
        continue
    if el.tag == "code" or el.get("id") == "lang-select":
        continue
    if el.xpath('ancestor-or-self::*[@id="beian" or contains(@class,"lang-bar")]'):
        continue
    for s in (el.text, el.tail):
        if s and s.strip() and CJK.search(s):
            t = norm(s)
            if t not in static:
                static.append(t)

# ---------- 动态 ----------
js = re.findall(r"<script>([\s\S]*?)</script>", src)[-1]
dyn: list[str] = []
for m in re.finditer(r"tr\('([^']+)'\)|T\('([^']*)'", js):
    s = m.group(1) or m.group(2)
    if s and CJK.search(s):
        t = norm(s)
        if t not in dyn:
            dyn.append(t)

en = json.loads(EN.read_text(encoding="utf-8"))
keys = {norm(k) for k in en}

miss_s = [s for s in static if s not in keys]
miss_d = [s for s in dyn if s not in keys]
total = len(static) + len(dyn)

print(f"待翻译：静态 {len(static)} + 动态 {len(dyn)} = {total} 条")
print(f"en.json 词条：{len(en)}")
print(f"静态覆盖 {100*(len(static)-len(miss_s))/max(len(static),1):.0f}%　"
      f"动态覆盖 {100*(len(dyn)-len(miss_d))/max(len(dyn),1):.0f}%")

bad = False
for label, miss in (("静态", miss_s), ("动态", miss_d)):
    if miss:
        bad = True
        print(f"\n✗ 缺 {len(miss)} 条{label}：")
        for s in miss:
            print("  · " + s[:80])

empties = [k for k, v in en.items() if not str(v).strip() and k not in ALLOW_EMPTY]
if empties:
    bad = True
    print(f"\n✗ {len(empties)} 条空译文：{empties[:5]}")

if not bad:
    print("\n✓ 英文完整覆盖")
sys.exit(1 if bad else 0)
