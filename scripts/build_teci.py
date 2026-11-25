"""TECI v0.1 构建管道：原始模型快照 -> 清洗 -> 计算指数 -> 产出网页数据。

口径：
  L1  挂牌价指数   = 混合价（按典型对话负载 输入:输出 = 4:1 加权）的中位数
  L2  单位智能成本 = 混合价 / 智能分，衡量"买到一分智能要花多少钱"
  L3  有效成本指数 = 未启用，需实测吞吐/重试率，等有算力预算再开

输入：data/raw/openrouter_models_*.json（取最新一份）
输出：data/teci_snapshot.csv
      data/teci_history.csv      （每运行一次追加/更新一行，用来长成时间序列）
      site/data/teci.js          （网页数据，挂到 window.TECI_DATA）
"""

from __future__ import annotations

import csv
import json
import shutil
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# Windows 控制台默认 GBK，中文输出会乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"

# 典型对话负载的 token 结构。改这里等于改口径，必须同时改方法论文档并升版本号。
W_IN = 4
W_OUT = 1

# 档位切分（按 Artificial Analysis 智能分）
TIER_FLAGSHIP_MIN = 55.0
TIER_MID_MIN = 40.0

# 上市窗口：只统计最近 N 个月上架/发布的模型。
# 理由：本指数的用途是"现在买哪家最实惠"，混入 2023 年的退役型号会让"最便宜"
# 变成一个没人用的选项，也会让不同时期的可比性变差。
LISTING_WINDOW_MONTHS = 12

# 部署地址。og:image / og:url 必须是绝对地址，否则微信、Twitter 等抓不到封面图。
# 上线后把这里改成你的实际域名（不带结尾斜杠），再跑一次 run.cmd。
SITE_URL = "https://boavec.github.io/teci"

# 判定为国内厂商的模型作者
CN_AUTHORS = {
    "deepseek", "moonshotai", "moonshot", "qwen", "tencent", "minimax",
    "z-ai", "baidu", "inclusionai", "stepfun", "01-ai", "baichuan",
    "bytedance", "bytedance-seed", "xiaomi", "sensetime",
}

AUTHOR_LABEL = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "google": "Google",
    "deepseek": "DeepSeek",
    "moonshotai": "Moonshot",
    "qwen": "阿里 Qwen",
    "tencent": "腾讯",
    "minimax": "MiniMax",
    "z-ai": "智谱",
    "baidu": "百度",
    "meta": "Meta",
    "mistralai": "Mistral",
    "thinkingmachines": "Thinking Machines",
    "liquid": "Liquid AI",
    "nvidia": "NVIDIA",
    "microsoft": "Microsoft",
    "x-ai": "xAI",
    "amazon": "Amazon",
    "cohere": "Cohere",
    "ai21": "AI21",
    "nousresearch": "Nous",
    "reflection": "Reflection",
    "prism-ml": "PrismML",
    "moondream": "Moondream",
    "elorian": "Elorian",
    "particle-ai": "Particle",
    "radixark": "RadixArk",
    "nex-agi": "Nex AGI",
    "kt": "KT",
    "recursive": "Recursive",
    "ricursiveai": "Ricursive",
    "motif-technologies": "Motif",
    "inclusionai": "InclusionAI",
    "bytedance": "字节",
    "bytedance-seed": "字节 Seed",
    "meta-models": "Meta",
}


def author_of(model_id: str) -> str:
    return model_id.split("/", 1)[0]


def age_months(ts: float) -> float:
    """距今天数换算成月（按 30.44 天/月）。"""
    dt = datetime.fromtimestamp(ts, timezone.utc)
    return (datetime.now(timezone.utc) - dt).days / 30.44


def tier_of(score: float | None) -> str:
    if score is None:
        return "未评级"
    if score >= TIER_FLAGSHIP_MIN:
        return "旗舰"
    if score >= TIER_MID_MIN:
        return "中端"
    return "轻量"


def median(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 4) if xs else None


def load_latest_raw() -> tuple[dict, Path]:
    cands = sorted(RAW_DIR.glob("openrouter_models_*.json"))
    if not cands:
        raise SystemExit(f"{RAW_DIR} 下没有 openrouter_models_*.json，先跑 scripts/fetch_models.py")
    path = cands[-1]
    return json.loads(path.read_text(encoding="utf-8")), path


def clean(models: list[dict]) -> list[dict]:
    out: list[dict] = []
    for m in models:
        mid = m.get("id", "")
        # 促销免费档和批量档不是同一件商品，剔除，否则指数会失真
        if ":free" in mid or ":batch" in mid:
            continue

        # 上市窗口：太老的型号不进篮子
        created = m.get("created")
        if not created or age_months(created) > LISTING_WINDOW_MONTHS:
            continue

        # 已过厂商设定的下线日期（有的条目带时区、有的不带，统一按 UTC 处理）
        exp = m.get("expiration_date")
        if exp:
            try:
                d = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
                if d.tzinfo is None:
                    d = d.replace(tzinfo=timezone.utc)
                if d <= datetime.now(timezone.utc):
                    continue
            except ValueError:
                pass

        pr = m.get("pricing") or {}
        try:
            p_in = float(pr.get("prompt", 0))
            p_out = float(pr.get("completion", 0))
        except (TypeError, ValueError):
            continue
        if p_in <= 0 or p_out <= 0:
            continue

        usd_in = p_in * 1_000_000
        usd_out = p_out * 1_000_000
        blended = (W_IN * usd_in + W_OUT * usd_out) / (W_IN + W_OUT)

        benchmarks = m.get("benchmarks") or {}
        aa = (benchmarks.get("artificial_analysis") or {}).get("intelligence_index")
        score = float(aa) if isinstance(aa, (int, float)) else None

        author = author_of(mid)
        out.append(
            {
                "id": mid,
                "name": m.get("name", mid),
                "author": author,
                "vendor": AUTHOR_LABEL.get(author, author),
                "region": "国内" if author in CN_AUTHORS else "海外",
                "usd_in": round(usd_in, 4),
                "usd_out": round(usd_out, 4),
                "blended": round(blended, 4),
                "score": score,
                "tier": tier_of(score),
                "cost_per_point": round(blended / score, 4) if score else None,
                "context": m.get("context_length"),
                "listed": datetime.fromtimestamp(created, timezone.utc).date().isoformat(),
            }
        )
    return out


def pareto_front(rows: list[dict]) -> list[str]:
    """性价比前沿：便宜且聪明。按价格升序扫描，智能分不断创新高即入选。"""
    scored = [r for r in rows if r["score"] is not None]
    scored.sort(key=lambda r: (r["blended"], -(r["score"] or 0)))
    front: list[str] = []
    best = -1.0
    for r in scored:
        if (r["score"] or 0) > best:
            best = r["score"]
            front.append(r["id"])
    return front


# 能力门槛：机构买家真正的问题是"我至少要 X 分，最便宜的在哪"
CAPABILITY_THRESHOLDS = [30, 40, 50, 55, 60]


def picks(rows: list[dict]) -> dict:
    """直接给答案的三个选择。"""
    scored = [r for r in rows if r["score"] is not None]
    cheapest = min(rows, key=lambda r: r["blended"])
    best_value = min(scored, key=lambda r: r["cost_per_point"]) if scored else None
    strongest = max(scored, key=lambda r: r["score"]) if scored else None
    return {"cheapest": cheapest, "best_value": best_value, "strongest": strongest}


def capability_table(rows: list[dict]) -> list[dict]:
    """对每个能力门槛，给出最便宜的达标模型。"""
    scored = [r for r in rows if r["score"] is not None]
    out: list[dict] = []
    for t in CAPABILITY_THRESHOLDS:
        cand = [r for r in scored if (r["score"] or 0) >= t]
        if not cand:
            out.append({"threshold": t, "n": 0})
            continue
        best = min(cand, key=lambda r: r["blended"])
        out.append(
            {
                "threshold": t,
                "n": len(cand),
                "id": best["id"],
                "name": best["name"],
                "vendor": best["vendor"],
                "region": best["region"],
                "blended": best["blended"],
                "score": best["score"],
                "cost_per_point": best["cost_per_point"],
            }
        )
    return out


def vendor_table(rows: list[dict]) -> list[dict]:
    """按厂商聚合：机构做供应商短名单时看这张。"""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["vendor"], []).append(r)

    out: list[dict] = []
    for vendor, sub in groups.items():
        scored = [r for r in sub if r["score"] is not None]
        cheapest = min(sub, key=lambda r: r["blended"])
        out.append(
            {
                "vendor": vendor,
                "region": sub[0]["region"],
                "n": len(sub),
                "n_scored": len(scored),
                "median_blended": median([r["blended"] for r in sub]),
                "median_score": median([r["score"] for r in scored]),
                "median_cost_per_point": median([r["cost_per_point"] for r in scored]),
                "cheapest_name": cheapest["name"],
                "cheapest_blended": cheapest["blended"],
            }
        )
    # 有单位智能成本的排前面，按该值升序
    out.sort(key=lambda x: (x["median_cost_per_point"] is None,
                            x["median_cost_per_point"] or 9e9))
    return out


def domestic_front(rows: list[dict]) -> list[str]:
    """国内厂商自己的性价比前沿，用来和全球前沿对照。"""
    return pareto_front([r for r in rows if r["region"] == "国内"])


def top_domestic(rows: list[dict], n: int = 10) -> list[str]:
    """国内智能分最高的 n 个模型，按分数从高到低。"""
    scored = [r for r in rows if r["region"] == "国内" and r["score"] is not None]
    scored.sort(key=lambda r: (-(r["score"] or 0), r["blended"]))
    return [r["id"] for r in scored[:n]]


def region_tier_matrix(rows: list[dict]) -> dict:
    """国内/海外 × 档位 的交叉明细。空单元保留，让缺口可见。"""
    matrix: dict[str, dict] = {}
    for reg in ["国内", "海外"]:
        for tier in ["旗舰", "中端", "轻量", "未评级"]:
            sub = [r for r in rows if r["region"] == reg and r["tier"] == tier]
            matrix[f"{reg}|{tier}"] = {
                "n": len(sub),
                "median_blended": median([r["blended"] for r in sub]),
                "median_score": median([r["score"] for r in sub if r["score"] is not None]),
                "median_cost_per_point": median([r["cost_per_point"] for r in sub]),
            }
    return matrix


def build() -> None:
    raw, raw_path = load_latest_raw()
    rows = clean(raw["data"])
    if not rows:
        raise SystemExit("清洗后没有可用模型，检查原始快照")

    scored = [r for r in rows if r["score"] is not None]
    front = set(pareto_front(rows))

    tiers = ["旗舰", "中端", "轻量", "未评级"]
    tier_stats = {}
    for t in tiers:
        sub = [r for r in rows if r["tier"] == t]
        tier_stats[t] = {
            "n": len(sub),
            "n_scored": sum(1 for r in sub if r["score"] is not None),
            "median_blended": median([r["blended"] for r in sub]),
            "median_cost_per_point": median([r["cost_per_point"] for r in sub]),
            "min_blended": round(min([r["blended"] for r in sub]), 4) if sub else None,
        }

    region_stats = {}
    for reg in ["国内", "海外"]:
        sub = [r for r in rows if r["region"] == reg]
        region_stats[reg] = {
            "n": len(sub),
            "median_blended": median([r["blended"] for r in sub]),
            "median_score": median([r["score"] for r in sub if r["score"] is not None]),
            "median_cost_per_point": median([r["cost_per_point"] for r in sub]),
        }

    summary = {
        "as_of": date.today().isoformat(),
        "n_models": len(rows),
        "n_scored": len(scored),
        "median_blended_all": median([r["blended"] for r in rows]),
        "median_cost_per_point_all": median([r["cost_per_point"] for r in rows]),
        "best_value": min(
            (r for r in scored), key=lambda r: r["cost_per_point"] or 9e9
        )["id"]
        if scored
        else None,
    }

    payload = {
        "meta": {
            "index": "TECI",
            "version": "0.1",
            "as_of": summary["as_of"],
            "weights": {"input": W_IN, "output": W_OUT},
            "tiers": {"flagship_min": TIER_FLAGSHIP_MIN, "mid_min": TIER_MID_MIN},
            "source": "OpenRouter /api/v1/models",
            "raw_file": raw_path.name,
            "raw_total": len(raw["data"]),
            "listing_window_months": LISTING_WINDOW_MONTHS,
            "levels_enabled": ["L1", "L2"],
            "levels_disabled": ["L3"],
        },
        "summary": summary,
        "tiers": tier_stats,
        "regions": region_stats,
        "region_tier": region_tier_matrix(rows),
        "picks": picks(rows),
        "capability": capability_table(rows),
        "vendors": vendor_table(rows),
        "models": sorted(rows, key=lambda r: r["blended"]),
        "frontier": sorted(front),
        "frontier_cn": sorted(domestic_front(rows)),
        "top_cn": top_domestic(rows, 10),
    }

    # 1) 截面明细
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    snap = DATA_DIR / "teci_snapshot.csv"
    cols = ["id", "name", "vendor", "region", "tier", "usd_in", "usd_out",
            "blended", "score", "cost_per_point", "context", "listed"]
    with snap.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in payload["models"]:
            w.writerow(r)

    # 2) 历史序列（同日重跑则覆盖当天行）
    hist = DATA_DIR / "teci_history.csv"
    hcols = ["as_of", "n_models", "n_scored", "median_blended_all",
             "median_cost_per_point_all", "median_blended_flagship",
             "median_blended_mid", "median_blended_light",
             "median_cpp_domestic", "median_cpp_overseas"]
    existing: list[dict] = []
    if hist.exists():
        with hist.open(encoding="utf-8-sig") as f:
            existing = [r for r in csv.DictReader(f) if r["as_of"] != summary["as_of"]]
    existing.append(
        {
            "as_of": summary["as_of"],
            "n_models": summary["n_models"],
            "n_scored": summary["n_scored"],
            "median_blended_all": summary["median_blended_all"],
            "median_cost_per_point_all": summary["median_cost_per_point_all"],
            "median_blended_flagship": tier_stats["旗舰"]["median_blended"],
            "median_blended_mid": tier_stats["中端"]["median_blended"],
            "median_blended_light": tier_stats["轻量"]["median_blended"],
            "median_cpp_domestic": region_stats["国内"]["median_cost_per_point"],
            "median_cpp_overseas": region_stats["海外"]["median_cost_per_point"],
        }
    )
    existing.sort(key=lambda r: r["as_of"])
    with hist.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=hcols, extrasaction="ignore")
        w.writeheader()
        w.writerows(existing)

    # 3) 网页数据（写成 js 而非 json，file:// 直接双击也能用，不需要起服务器）
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "data").mkdir(parents=True, exist_ok=True)

    # 多语言词典：site/i18n/*.json 合并成 window.TECI_I18N
    i18n: dict[str, dict] = {}
    i18n_dir = SITE_DIR / "i18n"
    if i18n_dir.is_dir():
        for f in sorted(i18n_dir.glob("*.json")):
            try:
                i18n[f.stem] = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                print(f"警告：{f.name} 解析失败（{e}），该语言将被跳过")
    i18n_js = "window.TECI_I18N = " + json.dumps(i18n, ensure_ascii=False) + ";\n"
    (SITE_DIR / "data" / "i18n.js").write_text(i18n_js, encoding="utf-8")

    js = "window.TECI_DATA = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n"
    (SITE_DIR / "data" / "teci.js").write_text(js, encoding="utf-8")

    # 4) 单文件版 + 发布目录
    #    GitHub Pages 要求入口必须叫 index.html，所以同时产出一份可直接上传的。
    tpl = (SITE_DIR / "index.html").read_text(encoding="utf-8")
    marker = '<script src="data/teci.js"></script>'
    i18n_marker = '<script src="data/i18n.js"></script>'
    if marker in tpl:
        inlined = (tpl.replace(i18n_marker, "<script>\n" + i18n_js + "</script>")
                      .replace(marker, "<script>\n" + js + "</script>")
                      .replace("__SITE_URL__", SITE_URL.rstrip("/")))
        (SITE_DIR / "teci-standalone.html").write_text(inlined, encoding="utf-8")
        publish_dir = ROOT / "publish"
        publish_dir.mkdir(parents=True, exist_ok=True)
        (publish_dir / "index.html").write_text(inlined, encoding="utf-8")

        # 分享封面图（由 scripts/make_og.py 生成）一起部署
        og_src = SITE_DIR / "og.png"
        og_note = "，但缺少 og.png（跑一次 scripts/make_og.py）"
        if og_src.exists():
            shutil.copy2(og_src, publish_dir / "og.png")
            og_note = "，已带 og.png"
        standalone_note = "teci-standalone.html + publish/index.html 已生成" + og_note
    else:
        standalone_note = "警告：index.html 里没找到数据脚本占位，单文件版未生成"

    print(f"原始快照 : {raw_path.name}（{payload['meta']['raw_total']} 个模型）")
    print(f"纳入口径 : 最近 {LISTING_WINDOW_MONTHS} 个月上市 · 剔除免费档/批量档/已下线")
    print(f"清洗后   : {len(rows)} 个模型，其中 {len(scored)} 个有智能分")
    print(f"L1 全样本中位混合价 : ${summary['median_blended_all']}/百万 token")
    print(f"L2 全样本每智能点   : ${summary['median_cost_per_point_all']}")
    print(f"性价比最优          : {summary['best_value']}")
    print(f"前沿模型            : {len(front)} 个")
    print(f"产出 : {snap.name}, {hist.name}, site/data/teci.js")
    print(f"       {standalone_note}")


if __name__ == "__main__":
    build()
