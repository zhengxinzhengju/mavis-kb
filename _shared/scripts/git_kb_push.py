#!/usr/bin/env python3
"""
git_kb_push.py
==============
把整个 /workspace/knowledge-base 推到 GitHub 仓库 zhengxinzhengju/mavis-kb
- 用 Contents API（不用 git 协议，国内网络也能通）
- 自动跳过 _cache/ / _site/ / __pycache__ / .pyc
- 进度可见
"""
import os
import sys
import time
import base64
import json
import urllib.request
import urllib.error
from pathlib import Path

REPO = "zhengxinzhengju/mavis-kb"
BRANCH = "main"
SOURCE = Path("/workspace/knowledge-base")
TOKEN = os.environ.get("GITHUB_KB_TOKEN")

# 排除规则
EXCLUDE_DIRS = {"_cache", "_site", "__pycache__", ".git"}
EXCLUDE_EXTS = {".pyc", ".pyo", ".swp"}


def gh_api(method: str, path: str, data: dict | None = None) -> dict:
    url = f"https://api.github.com{path}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Mavis-KBPush/1.0",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()) if resp.length else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="ignore")[:300]
        return {"error": True, "status": e.code, "body": body_text}
    except Exception as e:
        return {"error": True, "exception": str(e)}


def get_file_sha(path: str) -> str | None:
    r = gh_api("GET", f"/repos/{REPO}/contents/{path}?ref={BRANCH}")
    return r.get("sha") if not r.get("error") else None


def upload_file(rel_path: str, content: bytes, msg: str) -> tuple[bool, str]:
    """上传单文件，返回 (ok, info)。409 冲突时重试 1 次。"""
    for attempt in range(2):
        sha = get_file_sha(rel_path)
        payload = {
            "message": msg,
            "content": base64.b64encode(content).decode("ascii"),
            "branch": BRANCH,
        }
        if sha:
            payload["sha"] = sha
        r = gh_api("PUT", f"/repos/{REPO}/contents/{rel_path}", payload)
        if r.get("error"):
            if r.get("status") == 409 and attempt == 0:
                # SHA 冲突，重试
                time.sleep(1)
                continue
            return False, f"{r.get('status', '?')} {r.get('body', r.get('exception', ''))[:200]}"
        return True, "ok"
    return False, "重试仍失败"


def collect_files():
    """收集所有要推的文件"""
    files = []
    for p in SOURCE.rglob("*"):
        if p.is_file():
            # 排除规则
            if any(ex in p.parts for ex in EXCLUDE_DIRS):
                continue
            if p.suffix in EXCLUDE_EXTS:
                continue
            rel = p.relative_to(SOURCE).as_posix()
            files.append((p, rel))
    return sorted(files, key=lambda x: x[1])


def main():
    if not TOKEN:
        print("❌ GITHUB_KB_TOKEN 未设置")
        sys.exit(1)

    print(f"🚀 GitHub KB Push → {REPO}:{BRANCH}")
    print(f"   源: {SOURCE}")
    print()

    files = collect_files()
    total = len(files)
    total_size = sum(f.stat().st_size for f, _ in files)
    print(f"📁 找到 {total} 个文件, 总大小 {total_size//1024} KB")
    print()

    ok, fail = 0, 0
    failed = []
    for i, (fp, rel) in enumerate(files, 1):
        try:
            content = fp.read_bytes()
            msg = f"chore: update {rel}"
            success, info = upload_file(rel, content, msg)
            if success:
                ok += 1
                if i % 20 == 0 or i == total:
                    print(f"  [{i:3d}/{total}] ✅ {rel}")
            else:
                fail += 1
                failed.append((rel, info))
                print(f"  [{i:3d}/{total}] ❌ {rel}: {info[:80]}")
        except Exception as e:
            fail += 1
            failed.append((rel, str(e)))
            print(f"  [{i:3d}/{total}] ❌ {rel}: {e}")
        time.sleep(0.2)  # rate limit

    print()
    print(f"{'🎉' if fail == 0 else '⚠️ '}  完成: ✅ {ok} / ❌ {fail}")

    if failed:
        print()
        print("失败文件:")
        for rel, info in failed[:10]:
            print(f"  - {rel}: {info[:80]}")


if __name__ == "__main__":
    main()
