"""通过 GitHub REST API 上传项目（不需要 git）。

用途：本机没有 git，也不方便在网页里拖整个文件夹时，用这个脚本把文件逐个推上去。

用法：
    # 先看会传哪些文件，不实际发送
    python scripts/upload_github.py --repo 用户名/仓库名 --dry-run

    # 真正上传（令牌也可以放在环境变量 GITHUB_TOKEN 里）
    python scripts/upload_github.py --repo 用户名/仓库名 --token ghp_xxx

令牌要求：
    细粒度（Fine-grained）个人访问令牌，只勾这一个仓库，
    Repository permissions → Contents: Read and write
    有效期建议设为 1 天，用完立刻撤销。

注意：
    * 仓库必须先在网页上建好（空仓库即可），本脚本不负责创建仓库。
    * 会跳过 .gitignore 里那些不该入库的目录（原始快照、构建产物、日志）。
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

# 不入库的路径（与 .gitignore 保持一致）
EXCLUDE_DIRS = {"logs", "publish", "__pycache__", ".git", ".idea", ".vscode", "node_modules", "business", "build"}
EXCLUDE_FILES = {"render.png"}
EXCLUDE_RELS = {
    "site/data/teci.js",          # 构建产物，CI 重新生成
    "site/data/i18n.js",          # 构建产物
    "site/teci-standalone.html",  # 构建产物
    "scripts/upload_github.py",   # 本地上传工具，不入库
    "render.png",
}
EXCLUDE_PREFIXES = ("data/raw/",)

API = "https://api.github.com"


def should_skip(rel: str) -> bool:
    parts = rel.split("/")
    if any(p in EXCLUDE_DIRS for p in parts[:-1]):
        return True
    if rel in EXCLUDE_FILES or rel in EXCLUDE_RELS:
        return True
    if rel.startswith(EXCLUDE_PREFIXES):
        return True
    if rel.endswith(".pyc"):
        return True
    return False


def collect() -> list[Path]:
    files: list[Path] = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if should_skip(rel):
            continue
        files.append(p)
    return files


def api(method: str, url: str, token: str, payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "teci-uploader")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"message": body[:300]}


def get_sha(repo: str, rel: str, token: str, branch: str) -> str | None:
    url = f"{API}/repos/{repo}/contents/{rel}?ref={branch}"
    code, body = api("GET", url, token)
    if code == 200 and isinstance(body, dict):
        return body.get("sha")
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/repo")
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    ap.add_argument("--branch", default="main")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--message", default="chore: 上传 TECI 项目")
    ap.add_argument("--only", default="", help="只上传这些文件，逗号分隔的相对路径")
    args = ap.parse_args()

    files = collect()
    if args.only.strip():
        want = {x.strip().replace("\\", "/") for x in args.only.split(",") if x.strip()}
        files = [f for f in files if f.relative_to(ROOT).as_posix() in want]
        missing = want - {f.relative_to(ROOT).as_posix() for f in files}
        if missing:
            print("未匹配到:", missing, file=sys.stderr)
            return 2
    total = sum(f.stat().st_size for f in files)

    print(f"仓库    : {args.repo}")
    print(f"分支    : {args.branch}")
    print(f"文件数  : {len(files)}")
    print(f"总大小  : {total/1024:.0f} KB\n")

    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        print(f"  {rel:<44}{f.stat().st_size/1024:>8.1f} KB")

    skipped = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
               if p.is_file() and should_skip(p.relative_to(ROOT).as_posix())]
    if skipped:
        print(f"\n已跳过 {len(skipped)} 个（按 .gitignore）：")
        for s in sorted(skipped)[:12]:
            print(f"  {s}")
        if len(skipped) > 12:
            print(f"  …… 以及另外 {len(skipped)-12} 个")

    if args.dry_run:
        print("\n[dry-run] 没有发送任何请求。")
        return 0

    if not args.token:
        print("\n错误：没有令牌。请用 --token 传入，或设置环境变量 GITHUB_TOKEN。", file=sys.stderr)
        return 2

    print("\n开始上传……")
    ok, failed = 0, []
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        content = base64.b64encode(f.read_bytes()).decode()
        payload = {"message": f"{args.message} [{rel}]", "content": content, "branch": args.branch}
        sha = get_sha(args.repo, rel, args.token, args.branch)
        if sha:
            payload["sha"] = sha
        code, body = api("PUT", f"{API}/repos/{args.repo}/contents/{rel}", args.token, payload)
        if code in (200, 201):
            ok += 1
            print(f"  ✅ {rel}")
        else:
            failed.append((rel, code, body.get("message", "")))
            print(f"  ❌ {rel}  HTTP {code}  {body.get('message','')[:120]}")

    print(f"\n成功 {ok} / {len(files)}")
    if failed:
        print("失败列表：")
        for rel, code, msg in failed:
            print(f"  {rel}  HTTP {code}  {msg[:160]}")
        return 1

    owner, name = args.repo.split("/", 1)
    print(f"\n仓库地址：https://github.com/{owner}/{name}")
    print("下一步：Settings → Pages → Source 选 “GitHub Actions”")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
