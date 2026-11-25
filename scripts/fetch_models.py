"""抓取 OpenRouter 公开模型目录，落盘为带日期的原始快照。

用法：
    python scripts/fetch_models.py
    python scripts/fetch_models.py --from-spill <被截断的抓取文本>   # 从截断结果里回收

说明：
  * 本脚本只写 data/raw/，不改动任何已有快照，保证原始数据可追溯。
  * 国内网络访问 openrouter.ai 可能不通，可先设置代理：
        $env:HTTPS_PROXY="http://127.0.0.1:7890"   (PowerShell)
  * 抓取失败时脚本会明确报错退出，不会静默写一个空文件。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
URL = "https://openrouter.ai/api/v1/models"


def fetch(url: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TECI/0.1 (+research index; contact: you@example.com)",
            "Accept": "application/json",
        },
    )
    # urllib 会自动读取 HTTPS_PROXY / HTTP_PROXY 环境变量
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    obj = json.loads(raw)
    if "data" not in obj or not isinstance(obj["data"], list):
        raise ValueError("响应里没有 data 数组，接口可能已变更")
    return obj


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=URL)
    ap.add_argument("--from-spill", help="从被截断的抓取文本中回收 JSON，而不是联网抓取")
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f"openrouter_models_{date.today():%Y%m%d}.json"

    if args.from_spill:
        sys.path.insert(0, str(Path(__file__).parent))
        from extract_json import find_json_region, recover_objects  # noqa: PLC0415

        text = Path(args.from_spill).read_text(encoding="utf-8", errors="replace")
        obj = recover_objects(find_json_region(text))
        print(f"[回收] 从 {args.from_spill} 解析出 {len(obj['data'])} 个模型（可能不完整）")
    else:
        if os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"):
            print(f"[网络] 使用代理 {os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')}")
        else:
            print("[网络] 未检测到代理环境变量，直连")
        try:
            obj = fetch(args.url, timeout=args.timeout)
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as e:
            print(f"[失败] 抓取失败：{type(e).__name__}: {e}", file=sys.stderr)
            print("       如果是网络问题，请设置 HTTPS_PROXY 后重试；", file=sys.stderr)
            print("       如果拿到的是被截断的文本，可用 --from-spill 回收。", file=sys.stderr)
            return 1
        print(f"[抓取] 拿到 {len(obj['data'])} 个模型")

    out.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    print(f"[落盘] {out.relative_to(ROOT)}  ({out.stat().st_size/1024:.0f} KB)")
    print("下一步： python scripts/build_teci.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
