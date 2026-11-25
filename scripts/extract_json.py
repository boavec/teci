"""从被截断的抓取结果中回收尽量多的合法 JSON。

用途：web_fetch 有 ~100KB 输出上限，OpenRouter 的 /api/v1/models 完整响应远大于此，
拿回来的文本尾部会被截断。本脚本用括号配平扫描，丢掉最后一个不完整的顶层元素，
把前面的部分还原成合法 JSON。

用法：
    python scripts/extract_json.py <输入文本> <输出json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def find_json_region(text: str) -> str:
    """截掉抓取工具加的头尾说明文字，只保留最外层 {...} 区域。"""
    start = text.find("{")
    if start < 0:
        raise ValueError("输入里找不到 '{'，不是 JSON 载荷")
    return text[start:]


def recover_objects(region: str) -> dict:
    """扫描 '{ "data": [ ... ] }'，在最后一个完整的对象处截断并补齐结构。

    只在字符串字面量之外做括号计数，所以不会被描述文本里的花括号/引号干扰。
    """
    # 定位 data 数组
    key = '"data"'
    kpos = region.find(key)
    if kpos < 0:
        raise ValueError("找不到 \"data\" 字段")
    lb = region.find("[", kpos)
    if lb < 0:
        raise ValueError("找不到 data 数组起始 '['")

    depth = 0          # 相对 data 数组的嵌套深度
    in_str = False
    esc = False
    last_obj_end = -1  # 最后一个顶层对象结束（']' 之前的 '}'）的位置

    i = lb + 1
    while i < len(region):
        ch = region[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch in "[{":
                depth += 1
            elif ch in "]}":
                if depth == 0:
                    # 回到 data 数组的收尾
                    if ch == "]":
                        break
                else:
                    depth -= 1
                    if depth == 0:
                        last_obj_end = i
        i += 1

    if last_obj_end < 0:
        raise ValueError("没有解析到任何完整的顶层对象")

    payload = region[lb : last_obj_end + 1] + "]"
    data = json.loads(payload)
    return {"data": data}


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])

    raw = src.read_text(encoding="utf-8", errors="replace")
    region = find_json_region(raw)
    obj = recover_objects(region)

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    n = len(obj["data"])
    print(f"回收 {n} 个模型 -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
