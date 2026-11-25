"""对 GitHub Actions 工作流做基础结构检查。

没有 PyYAML 时，用逐行校验覆盖最容易出错的几类问题：
  * 制表符（YAML 里绝对不能用）
  * 缩进不是 2 的倍数
  * steps 下的每一项必须以 "- " 开头，且带了 name 或 uses
  * uses: 的值不能为空
  * 顶层必备键是否齐全

用法: python scripts/check_workflow.py [路径]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DEFAULT = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "deploy.yml"


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not path.exists():
        print(f"FAIL 找不到 {path}")
        return 1

    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    errs: list[str] = []

    if "\t" in raw:
        errs.append("含有制表符（YAML 不允许，请统一用空格）")

    for i, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2 != 0:
            errs.append(f"第 {i} 行缩进 {indent} 不是 2 的倍数：{line.strip()[:40]}")
        if line.rstrip() != line:
            errs.append(f"第 {i} 行有行尾空白")

    # 顶层键
    top = set()
    for line in lines:
        if line and not line.startswith((" ", "#", "-")) and ":" in line:
            top.add(line.split(":", 1)[0].strip())
    for need in ("name", "on", "permissions", "jobs"):
        if need not in top:
            errs.append(f"缺少顶层键：{need}")

    # steps 列表项
    steps = [ln for ln in lines if re.match(r"^\s*-\s+(name|uses):", ln)]
    if not steps:
        errs.append("没有解析到任何 step（- name: / - uses:）")

    bad_uses = [ln.strip() for ln in lines
                if re.match(r"^\s*uses:\s*$", ln) or re.match(r"^\s*-\s*uses:\s*$", ln)]
    if bad_uses:
        errs.append(f"uses 值为空：{bad_uses}")

    # 常见的 action 版本号丢失
    for ln in lines:
        m = re.match(r"^\s*-?\s*uses:\s*(\S+)", ln)
        if m and "@" not in m.group(1):
            errs.append(f"uses 缺少版本号：{m.group(1)}")

    print(f"文件：{path}")
    print(f"行数：{len(lines)}　step 数：{len(steps)}")
    print(f"顶层键：{', '.join(sorted(top))}")

    if errs:
        print("\n发现问题：")
        for e in errs:
            print("  ✗ " + e)
        return 1

    print("\n结构检查通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
