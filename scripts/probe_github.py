"""探测本机到 GitHub 各域名的连通性，决定走哪条上传路径。"""

from __future__ import annotations

import socket
import ssl
import sys
import time
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TARGETS = [
    ("github.com 主站", "https://github.com"),
    ("api.github.com（API）", "https://api.github.com/rate_limit"),
    ("objects.githubusercontent.com（下载资源）",
     "https://objects.githubusercontent.com"),
    ("desktop.github.com（Desktop 官网）", "https://desktop.github.com"),
    ("raw.githubusercontent.com", "https://raw.githubusercontent.com"),
    ("github.io", "https://pages.github.com"),
]

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TECI-probe"}


def probe(name: str, url: str, timeout: int = 12) -> None:
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code = r.status
        print(f"  ✅ {name:<42} HTTP {code}  {time.time()-t0:.1f}s")
        return
    except urllib.error.HTTPError as e:
        print(f"  ⚠️ {name:<42} HTTP {e.code}（能连通，只是拒绝了请求）  {time.time()-t0:.1f}s")
        return
    except Exception as e:
        print(f"  ❌ {name:<42} {type(e).__name__}: {str(e)[:60]}  {time.time()-t0:.1f}s")


print("=== DNS 解析 ===")
for host in ["github.com", "api.github.com", "desktop.github.com",
             "objects.githubusercontent.com"]:
    try:
        ip = socket.gethostbyname(host)
        print(f"  {host:<36} -> {ip}")
    except Exception as e:
        print(f"  {host:<36} -> 解析失败：{e}")

print("\n=== HTTPS 连通性 ===")
for name, url in TARGETS:
    probe(name, url)

print("\n=== 结论提示 ===")
print("  github.com 与 api.github.com 都通 → 不用装 Desktop，直接在网页建仓库 + 用 API 上传")
print("  只有 desktop.github.com 不通 → 正常，它是 Pages 托管，被墙不影响主站")
print("  github.com 也不通 → 这台机器上不了 GitHub，需要换方案或挂代理")
