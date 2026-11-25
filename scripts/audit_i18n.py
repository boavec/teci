"""审计：英文模式下，页面上还有哪些中文没被翻译。

做两件事：
  1. 静态文本——模拟 translateDom 的替换逻辑，找出替换后仍含中文的文本节点
  2. 动态文本——由 audit_i18n.js 负责（跑真实脚本）

用法: python scripts/audit_i18n.py
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
norm = lambda s: re.sub(r"\s+", " ", s).strip()
QUOTE = str.maketrans({"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'"})
def norm_q(s):
    return norm(s).translate(QUOTE)

CJK = re.compile(r"[\u4e00-\u9fff]")

en = json.loads((ROOT / "site" / "i18n" / "en.json").read_text(encoding="utf-8"))
html_text = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

doc = LH.fromstring(html_text)
for bad in doc.xpath("//script|//style"):
    bad.getparent().remove(bad)

SKIP_TAGS = {"script", "style", "code", "canvas", "textarea"}
missing: list[str] = []

for el in doc.iter():
    if not isinstance(el.tag, str):
        continue
    # 跳过语言选择器和备案号（这两处本就该保持原样）
    if el.get("id") == "lang-select" or el.get("id") == "beian":
        continue
    if el.xpath('ancestor-or-self::*[@id="beian" or contains(@class,"lang-bar")]'):
        continue
    if el.tag in SKIP_TAGS:
        continue

    for s in (el.text, el.tail):
        if not s or not s.strip() or not CJK.search(s):
            continue
        k = norm(s)
        if norm_q(k) in {norm_q(x) for x in en}:
            continue  # 有译文，会被替换
        missing.append(k)

seen, uniq = set(), []
for m in missing:
    if m not in seen:
        seen.add(m)
        uniq.append(m)

print(f"静态文本：英文模式下仍会显示中文的有 {len(uniq)} 条\n")
for m in uniq:
    print(f"  · {m[:90]}{'…' if len(m) > 90 else ''}")

if not uniq:
    print("  （无）")
