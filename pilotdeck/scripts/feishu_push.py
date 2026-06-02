#!/usr/bin/env python3
"""
飞书自定义机器人 Webhook 推送脚本 v2.0
======================================
支持两种调用方式：

方式 1 (推荐, 新版):
  python3 feishu_push.py <project_id> [--title "标题"] < content_file
  - 自动从 /workspace/knowledge-base/projects/<id>/index.json 读 webhook/secret
  - 不需要 shell 变量, cron 任务调用更安全

方式 2 (兼容, 旧版):
  python3 feishu_push.py <webhook_url> [secret] [--title "标题"] < content_file

支持参数:
  --test    dry-run 模式, 只打印 payload 不真推送
  --title   自定义卡片标题 (默认从 project.name 生成)
"""

import sys
import json
import time
import hmac
import hashlib
import base64
import argparse
import urllib.request
import urllib.error

WORKSPACE = "/workspace/knowledge-base"


def make_sign(secret: str, timestamp: int) -> str:
    """飞书签名校验：HMAC-SHA256"""
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def load_project_config(project_id: str) -> dict:
    """从 index.json 读 webhook/secret/title"""
    index_path = f"{WORKSPACE}/projects/{project_id}/index.json"
    try:
        with open(index_path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"ok": False, "error": f"项目配置文件不存在: {index_path}"}

    feishu = data.get("tracking", {}).get("feishu", {})
    proj = data.get("project", {})

    return {
        "ok": True,
        "webhook_url": feishu.get("webhook_url", ""),
        "secret": feishu.get("secret", ""),
        "title": f"📊 {proj.get('name', project_id)} 追踪简报",
        "project_id": project_id,
        "project_name": proj.get("name", project_id),
    }


def push_to_feishu(webhook_url: str, content: str, secret: str = "", title: str = "📊 追踪简报", dry_run: bool = False) -> dict:
    """
    推送消息到飞书自定义机器人
    content: 纯文本（飞书会原样显示）或 Markdown
    secret: 飞书签名校验密钥（可选）
    title: 卡片标题（仅签名模式生效）
    dry_run: True 则不真推送, 只返回 payload
    """
    if not webhook_url or not webhook_url.strip():
        return {"ok": False, "skipped": True, "error": "webhook_url 为空，跳过推送"}

    headers = {"Content-Type": "application/json; charset=utf-8"}

    if not secret:
        # 简单 text 模式
        payload = {
            "msg_type": "text",
            "content": {"text": content},
        }
    else:
        # interactive 卡片模式（带签名）
        timestamp = str(round(time.time()))
        sign = make_sign(secret, timestamp)
        payload = {
            "timestamp": timestamp,
            "sign": sign,
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title[:60],  # 飞书卡片标题上限
                    },
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content,
                    },
                ],
            },
        }

    if dry_run:
        return {"ok": True, "dry_run": True, "payload": payload}

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(webhook_url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("code") == 0 or result.get("StatusCode") == 0:
                return {"ok": True, "response": result}
            return {"ok": False, "error": result}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode('utf-8')}"}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"URL Error: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def parse_args():
    parser = argparse.ArgumentParser(
        description="飞书自定义机器人推送 (Mavis 知识库 v2.0)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  echo "hello" | python3 feishu_push.py pilotdeck
  cat weekly.txt | python3 feishu_push.py openclaw --title "OpenClaw W23"
  python3 feishu_push.py pilotdeck --test < weekly.txt
        """,
    )
    parser.add_argument(
        "target",
        help="项目 ID (pilotdeck/openclaw/...) 或 webhook_url",
    )
    parser.add_argument(
        "secret_positional",
        nargs="?",
        default="",
        help="(兼容旧版) 飞书签名密钥, 紧跟在 webhook_url 之后",
    )
    parser.add_argument(
        "--title",
        default="",
        help="自定义卡片标题 (默认从项目名生成)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="dry-run 模式: 只打印 payload 不真推送",
    )
    return parser.parse_args()


def detect_mode(args) -> dict:
    """判断是新版 (project_id) 还是旧版 (webhook_url) 调用"""
    target = args.target

    # 旧版: webhook_url 一般以 http 开头
    if target.startswith("http://") or target.startswith("https://"):
        return {
            "mode": "legacy",
            "webhook_url": target,
            "secret": args.secret_positional,
            "title": args.title or "📊 追踪简报",
        }

    # 新版: project_id
    config = load_project_config(target)
    if not config.get("ok"):
        return {"mode": "new", "error": config.get("error", "未知错误")}

    return {
        "mode": "new",
        "webhook_url": config["webhook_url"],
        "secret": config["secret"],
        "title": args.title or config["title"],
        "project_id": target,
        "project_name": config["project_name"],
    }


def main():
    args = parse_args()
    mode_info = detect_mode(args)

    if "error" in mode_info:
        print(json.dumps({"ok": False, "error": mode_info["error"]}, ensure_ascii=False))
        sys.exit(1)

    # 从 stdin 读内容
    content = sys.stdin.read().strip()
    if not content:
        print(json.dumps({"ok": False, "error": "内容为空"}, ensure_ascii=False))
        sys.exit(1)

    # 推送
    result = push_to_feishu(
        webhook_url=mode_info["webhook_url"],
        content=content,
        secret=mode_info["secret"],
        title=mode_info["title"],
        dry_run=args.test,
    )

    # 在结果里附上元信息
    if mode_info["mode"] == "new":
        result["project_id"] = mode_info["project_id"]
        result["project_name"] = mode_info["project_name"]
    result["title_used"] = mode_info["title"]

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("ok"):
        if args.test:
            print("\n[DRY-RUN] 未真实推送，仅展示 payload")
        sys.exit(0)
    elif result.get("skipped"):
        sys.exit(3)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
