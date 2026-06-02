#!/usr/bin/env python3
"""
用 GitHub API 直接 push 知识库到 mavis-kb 仓库
=============================================
绕开 git 协议（国内网络可能限制），用 Contents API 一文件一文件写
"""
import os
import sys
import json
import base64
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO = "zhengxinzhengju/mavis-kb"
BRANCH = "main"
SOURCE_DIR = Path("/workspace/output/pilotdeck-site")
TOKEN = os.environ.get("GITHUB_KB_TOKEN")

if not TOKEN:
    print("❌ GITHUB_KB_TOKEN 未设置")
    sys.exit(1)


def gh_api(method: str, path: str, data: dict | None = None) -> dict:
    """统一 GitHub API 调用"""
    url = f"https://api.github.com{path}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Mavis-GitApiPush/1.0",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read()) if resp.length else {}
    except urllib.error.HTTPError as e:
        return {"error": True, "status": e.code, "body": e.read().decode("utf-8", errors="ignore")[:500]}
    except Exception as e:
        return {"error": True, "exception": str(e)}


def get_file_sha(path: str) -> str | None:
    """获取文件当前 SHA（更新需要）"""
    r = gh_api("GET", f"/repos/{REPO}/contents/{path}?ref={BRANCH}")
    return r.get("sha") if not r.get("error") else None


def upload_file(rel_path: str, content: bytes, msg: str) -> bool:
    """上传单文件"""
    path = f"{BRANCH}/{rel_path}" if False else rel_path
    # 1. 查 SHA
    sha = get_file_sha(rel_path)
    # 2. PUT 创建/更新
    payload = {
        "message": msg,
        "content": base64.b64encode(content).decode("ascii"),
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha
    r = gh_api("PUT", f"/repos/{REPO}/contents/{rel_path}", payload)
    if r.get("error"):
        print(f"  ❌ {rel_path}: {r.get('status', '?')} {r.get('body', r.get('exception', ''))[:200]}")
        return False
    print(f"  ✅ {rel_path}")
    return True


def main():
    print(f"🚀 GitHub API Push → {REPO}:{BRANCH}")
    print(f"   源: {SOURCE_DIR}")
    print()

    # 收集所有文件
    files = []
    for f in sorted(SOURCE_DIR.iterdir()):
        if f.is_file():
            files.append(f)

    print(f"📁 找到 {len(files)} 个文件待推送:")
    for f in files:
        print(f"   - {f.name} ({f.stat().st_size//1024} KB)")
    print()

    # 推送
    ok = 0
    fail = 0
    for f in files:
        try:
            content = f.read_bytes()
            msg = f"chore: update {f.name} via Mavis tracker"
            if upload_file(f.name, content, msg):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  ❌ {f.name}: {e}")
            fail += 1
        time.sleep(0.3)  # 避免 rate limit

    print()
    print(f"{'🎉' if fail == 0 else '⚠️ '}  完成: ✅ {ok} / ❌ {fail}")

    # 触发 GitHub Pages
    print("\n📡 触发 GitHub Pages 重新构建...")
    pages_r = gh_api("POST", f"/repos/{REPO}/pages/builds")
    if pages_r.get("error"):
        # Pages 可能是 disabled 状态，先 enable
        print(f"   第一次失败，尝试启用 Pages...")
        enable_r = gh_api("POST", f"/repos/{REPO}/pages", {"source": {"branch": BRANCH, "path": "/"}})
        if enable_r.get("error"):
            print(f"   ⚠️ 启用 Pages 失败: {enable_r.get('body', enable_r.get('exception', ''))[:200]}")
        else:
            print(f"   ✅ Pages 启用: {enable_r.get('html_url')}")
    else:
        print(f"   ✅ Pages 构建已触发")

    # 获取 Pages URL
    pages_info = gh_api("GET", f"/repos/{REPO}/pages")
    if pages_info.get("html_url"):
        print(f"\n🔗 GitHub Pages URL: {pages_info['html_url']}")
    elif pages_info.get("error"):
        print(f"\n⚠️  Pages 信息获取失败: {pages_info.get('body', '')[:200]}")


if __name__ == "__main__":
    main()
