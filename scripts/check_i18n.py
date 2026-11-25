"""检查中英双语文案的覆盖率：页面里还有哪些中文没被翻译。

做法：把页面里所有中文字符串抽出来，逐条去 en.json 里找。
查不到的会在英文模式下回退成中文，所以要求 100%。

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
I18N = ROOT / "site" / "i18n"
norm = lambda s: re.sub(r"\s+", " ", s).strip()
CJK = re.compile(r"[\u4e00-\u9fff]")

# 这些中文在英文里本就没有对应词，允许译文为空
ALLOW_EMPTY = {"个"}

src = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

# 静态文本（跳过语言选择器本身和 code 片段）
doc = LH.fromstring(src)
for bad in doc.xpath("//script|//style"):
    bad.getparent().remove(bad)
static: list[str] = []
for el in doc.iter():
    if not isinstance(el.tag, str) or el.tag in ("title", "meta"):
        continue
    cls = el.get("class") or ""
    if "lang-bar" in cls or el.tag == "code":
        continue
    # 备案号是行政编号，不翻译；连它的子元素一起跳过
    if el.xpath('ancestor-or-self::*[@id="beian"]'):
        continue
    for s in (el.text, el.tail):
        if s and s.strip() and CJK.search(s):
            t = norm(s)
            if t not in static:
                static.append(t)

# JS 里走 tr()/T() 的中文（含 {占位符} 的句子）
js = re.findall(r"<script>([\s\S]*?)</script>", src)[-1]
dyn: list[str] = []
for m in re.finditer(r"tr\('([^']+)'\)|T\('([^']*)'", js):
    s = m.group(1) or m.group(2)
    if s and CJK.search(s):
        t = norm(s)
        if t not in dyn:
            dyn.append(t)

total = len(static) + len(dyn)
print(f"待翻译：静态 {len(static)} 条 + 动态 {len(dyn)} 条 = {total} 条\n")

en_path = I18N / "en.json"
if not en_path.exists():
    print("FAIL 找不到 site/i18n/en.json")
    sys.exit(1)

d = json.loads(en_path.read_text(encoding="utf-8"))
miss_s = [s for s in static if s not in d]
miss_d = [s for s in dyn if s not in d]
cov_s = 100 * (len(static) - len(miss_s)) / len(static) if static else 100
cov_d = 100 * (len(dyn) - len(miss_d)) / len(dyn) if dyn else 100

print(f"en.json 词条：{len(d)}")
print(f"静态覆盖：{cov_s:.0f}%   动态覆盖：{cov_d:.0f}%")

bad = False
for label, miss in (("静态", miss_s), ("动态", miss_d)):
    if miss:
        bad = True
        print(f"\n✗ 还缺 {len(miss)} 条{label}：")
        for s in miss:
            print("  · " + s[:80] + ("…" if len(s) > 80 else ""))

empties = [k for k, v in d.items() if not str(v).strip() and k not in ALLOW_EMPTY]
if empties:
    bad = True
    print(f"\n✗ 有 {len(empties)} 条空译文：{empties[:5]}")

if not bad:
    print("\n✓ 英文完整覆盖，切换到 English 后不会残留中文")
sys.exit(1 if bad else 0)
