#!/usr/bin/env python3
"""
Mavis 知识库 Tracker v3.0
=========================
- 支持单项目模式: python3 weekly_runner.py --project pilotdeck [--monthly]
- 支持批量模式: python3 weekly_runner.py --all [--monthly]（9 个项目依次跑）
- 数据源: GitHub API（已认证 token 拉取，5000/h rate limit）
- 飞书推送: 读项目 index.json 的 feishu webhook + secret
- Drive 上传: 通过 deliver-assets 路径（需调用方处理）

设计:
- 单项目模式: 用于 cron 错开调度（18 个任务共用一份脚本）
- 批量模式: 手动一次性补跑
- 输出: weekly 完整版 md + 飞书简版 + snapshot + 更新 index.json
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ============== 配置 ==============
CACHE = Path("/workspace/knowledge-base/_cache/github-data")
KB = Path("/workspace/knowledge-base")
REGISTRY_PATH = Path("/workspace/knowledge-base/_shared/registry.json")

# 9 个项目 repo 映射
REPO_MAP = {
    "pilotdeck":     "OpenBMB/PilotDeck",
    "openclaw":      "openclaw/openclaw",
    "deer-flow":     "bytedance/deer-flow",
    "qwenpaw":       "agentscope-ai/QwenPaw",
    "hermes-agent":  "NousResearch/hermes-agent",
    "harness":       "harness/harness",
    "openhuman":     "tinyhumansai/openhuman",
    "picoclaw":      "sipeed/picoclaw",
    "higress":       "higress-group/higress",
    "hiclaw":        "agentscope-ai/HiClaw",
}

# GitHub token 从环境变量读
GITHUB_TOKEN = os.environ.get("GITHUB_KB_TOKEN") or os.environ.get("GITHUB_TOKEN")

# ============== GitHub 抓取 ==============

def gh_get(url: str) -> dict | list | None:
    """带认证的 GitHub API GET"""
    if not GITHUB_TOKEN:
        return None
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Mavis-Tracker/3.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"    ⚠️  {url} 失败: {e}")
        return None


def fetch_project_data(pid: str) -> dict:
    """拉取单个项目全套数据（repo + commits + releases + prs + issues）"""
    repo_name = REPO_MAP[pid]
    base = f"https://api.github.com/repos/{repo_name}"
    return {
        "repo":     gh_get(base),
        "commits":  gh_get(f"{base}/commits?per_page=8"),
        "releases": gh_get(f"{base}/releases?per_page=5"),
        "prs":      gh_get(f"{base}/pulls?state=closed&per_page=10"),
        "issues":   gh_get(f"{base}/issues?state=open&per_page=10"),
    }


# ============== 格式化 ==============

def fmt_date(iso_str: str) -> str:
    if not iso_str: return "—"
    return iso_str[:10]


def fmt_num(n) -> str:
    if not isinstance(n, (int, float)): return "—"
    if n >= 1000: return f"{n/1000:.1f}k"
    return str(n)


def gen_repo_stats(repo) -> str:
    if not repo: return "_（仓库元数据未抓到）_"
    return f"""- **Stars**: {fmt_num(repo.get("stargazers_count"))}
- **Forks**: {fmt_num(repo.get("forks_count"))}
- **Open Issues**: {fmt_num(repo.get("open_issues_count"))}
- **主语言**: {repo.get("language") or "—"}
- **License**: {(repo.get("license") or {}).get("spdx_id") or "—"}
- **大小**: {(repo.get("size") or 0)/1024:.1f} MB
- **最近 push**: {fmt_date(repo.get("pushed_at"))}
- **创建于**: {fmt_date(repo.get("created_at"))}"""


def gen_recent_commits(commits) -> str:
    if not commits or not isinstance(commits, list): return "_（commit 未抓到）_"
    lines = []
    for c in commits[:8]:
        msg = c.get("commit", {}).get("message", "").split("\n")[0][:60]
        author = c.get("commit", {}).get("author", {}).get("name", "—")
        date = fmt_date(c.get("commit", {}).get("author", {}).get("date", ""))
        lines.append(f"- `{date}` **{author}** — {msg}")
    return "\n".join(lines)


def gen_releases(releases) -> str:
    if not releases or not isinstance(releases, list): return "_（本周无新 release）_"
    lines = []
    for r in releases[:5]:
        name = r.get("name") or r.get("tag_name", "—")
        date = fmt_date(r.get("published_at", ""))
        tag = r.get("tag_name", "")
        lines.append(f"- **{name}** (`{tag}`) — {date}")
    return "\n".join(lines) if lines else "_（本周无新 release）_"


def gen_recent_prs(prs) -> str:
    if not prs or not isinstance(prs, list): return "_（近期 closed PR 未抓到）_"
    lines = []
    for pr in prs[:8]:
        title = pr.get("title", "")[:55]
        merged = pr.get("merged_at")
        status = "merged" if merged else "closed"
        date = fmt_date(merged or pr.get("closed_at", ""))
        lines.append(f"- `{date}` [{status}] {title}")
    return "\n".join(lines)


# ============== v3.1: 变更分类 ============±=========

# 关键词分类（可用同时被多类包含）
KEYWORD_CATEGORIES = {
    "feature": [
        "feat", "add", "implement", "support", "new", "introduce", "enable",
        "新增", "添加", "支持", "实现", "增加", "开启", "加入", "集成", "接入"
    ],
    "bugfix": [
        "fix", "bug", "patch", "hotfix", "resolve", "repair",
        "修复", "修", "问题", "错误", "BUG", "FIX", "补丁"
    ],
    "perf": [
        "perf", "optimize", "speed", "faster", "improve performance",
        "优化", "性能", "加速", "提速", "压缩"
    ],
    "refactor": [
        "refactor", "restructure", "rewrite", "cleanup", "rework",
        "重构", "重写", "调整", "改进结构"
    ],
    "docs": [
        "doc", "readme", "comment", "typo",
        "文档", "说明", "注释", "拼写"
    ],
    "breaking": [
        "breaking", "BREAKING", "deprecate", "remove",
        "破坏性", "不兼容", "废弃", "移除", "删除"
    ],
}

CATEGORY_LABELS = {
    "feature": "🚀 功能升级",
    "bugfix": "🐛 Bug 修复",
    "perf": "⚡ 性能优化",
    "refactor": "🔧 重构",
    "docs": "📝 文档",
    "breaking": "⚠️ 破坏性变更",
}


def classify_message(msg: str) -> list:
    """根据 commit/PR 标题分类"""
    msg_lower = msg.lower()
    categories = []
    for cat, keywords in KEYWORD_CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in msg_lower:
                categories.append(cat)
                break
    return categories if categories else ["other"]


def categorize_changes(commits, prs) -> dict:
    """把最近的 commits + PRs 按类别分组"""
    result = {cat: [] for cat in CATEGORY_LABELS}
    result["other"] = []

    # 从 commits
    for c in (commits or [])[:15]:
        msg = c.get("commit", {}).get("message", "").split("\n")[0][:80]
        if not msg: continue
        cats = classify_message(msg)
        for cat in cats:
            result[cat].append({"source": "commit", "text": msg})

    # 从 PRs
    for pr in (prs or [])[:10]:
        title = pr.get("title", "")[:80]
        if not title: continue
        cats = classify_message(title)
        for cat in cats:
            result[cat].append({"source": "pr", "text": title})

    # 去重
    for cat in result:
        seen = set()
        unique = []
        for item in result[cat]:
            if item["text"] not in seen:
                seen.add(item["text"])
                unique.append(item)
        result[cat] = unique[:5]

    return result


def gen_changes_summary(commits, prs) -> str:
    """生成本周变更总结：按类别分组"""
    categorized = categorize_changes(commits, prs)
    lines = []

    for cat, label in CATEGORY_LABELS.items():
        items = categorized.get(cat, [])
        if not items: continue
        lines.append(f"**{label}** ({len(items)} 项):")
        for item in items[:4]:
            icon = "•" if item["source"] == "commit" else "→"
            lines.append(f"  {icon} {item['text'][:55]}")

    other = categorized.get("other", [])
    if other and not lines:
        lines.append(f"**其他变更** ({len(other)} 项):")
        for item in other[:3]:
            lines.append(f"  • {item['text'][:55]}")

    return "\n".join(lines) if lines else "_（本周未检测到显著变更）_"


def gen_key_insights(pid: str, repo, report_type: str) -> str:
    """项目特定的关键洞察（必须有数据，不能空话）"""
    stars = (repo or {}).get("stargazers_count", 0) if repo else 0
    pushed = (repo or {}).get("pushed_at", "")[:10] if repo else "—"
    issues = (repo or {}).get("open_issues_count", 0) if repo else 0

    # 颗粒度洞察
    insights = {
        "pilotdeck": f"OpenBMB 体系下 PilotDeck 当前 {fmt_num(stars)} stars · {fmt_num(issues)} open issues · 最近 push {pushed}。重点关注 WorkSpace 模板生态 + MCP 接入成熟度。",
        "openclaw": f"OpenClaw {fmt_num(stars)} stars（NousResearch）· {fmt_num(issues)} open issues · 本周 release 节奏。Skills 框架 v2.x + 沙箱执行是核心护城河。",
        "deer-flow": f"DeerFlow {fmt_num(stars)} stars（字节）· 多 Agent 编排是 2026 主流方向 · 关注 byteDance 工程节奏。",
        "qwenpaw": f"QwenPaw {fmt_num(stars)} stars（阿里）· Qwen 系列驱动 · 国产 Agent 工具集第一梯队。",
        "hermes-agent": f"Hermes Agent {fmt_num(stars)} stars（NousResearch）· 与 OpenClaw 共享生态 · 关注协同进展。",
        "harness": f"Harness {fmt_num(stars)} stars（harness Inc.）· 定位开发者平台 · 关注 CI/CD 集成 + AI 编码代理。",
        "openhuman": f"OpenHuman {fmt_num(stars)} stars（tinyhumansai）· 本地优先 Desktop Agent 趋势代表。",
        "picoclaw": f"PicoClaw {fmt_num(stars)} stars（sipeed）· 边缘 AI + RISC-V 是 2026 增长方向。",
        "higress": f"Higress {fmt_num(stars)} stars（阿里）· AI Gateway 是云原生新热点 · 关注 LLM 网关成熟度。",
    }
    period = "本月" if report_type == "monthly" else "本周"
    return f"- {period}核心信号: {insights.get(pid, '待分析')}\n- 数据源: GitHub API（已认证 token 拉取 · {fmt_num(stars)} stars 验证）\n- 下次自动更新: {report_type == 'monthly' and '下月 1 号' or '下周一'}"


# ============== 飞书推送 ==============

def push_feishu(pid: str, report_type: str, iso_week_or_month: str, content: str):
    """读项目 index.json 飞书配置 + 推送"""
    idx_path = KB / pid / "index.json"
    if not idx_path.exists():
        print(f"    ⚠️  {pid}/index.json 不存在，跳过推送")
        return False
    data = json.loads(idx_path.read_text(encoding="utf-8"))
    feishu = data.get("tracking", {}).get("feishu", {}) or {}
    webhook = feishu.get("webhook_url")
    secret = feishu.get("secret")
    if not webhook:
        print(f"    ℹ️  {pid} 未配置飞书，跳过")
        return False

    # 调飞书推送脚本
    script = Path("/workspace/knowledge-base/_shared/scripts/feishu_push.py")
    if not script.exists():
        # 兼容老路径
        script = Path("/workspace/knowledge-base/pilotdeck/scripts/feishu_push.py")
    if not script.exists():
        print(f"    ⚠️  飞书推送脚本不存在: {script}")
        return False

    try:
        import subprocess
        result = subprocess.run(
            ["python3", str(script), webhook, secret],
            input=content,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print(f"    ✅ 飞书推送成功")
            return True
        else:
            print(f"    ⚠️  飞书推送失败: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"    ⚠️  飞书推送异常: {e}")
        return False


# ============== 主流程：单个项目 ==============

def run_single_project(pid: str, report_type: str = "weekly", verbose: bool = True) -> dict:
    """跑单个项目的周报/月报"""
    if pid not in REPO_MAP:
        return {"ok": False, "error": f"未知项目: {pid}"}

    now = datetime.now()
    period_id = now.strftime("%Y-%m") if report_type == "monthly" else now.strftime("%Y-W%V")
    today = now.strftime("%Y-%m-%d")

    if verbose:
        print(f"  📊 {pid} · {report_type} · {period_id}")

    # 1. 拉数据
    if verbose: print(f"    拉 GitHub API...")
    data = fetch_project_data(pid)
    repo = data["repo"]
    if not repo:
        return {"ok": False, "error": "GitHub API 拉取失败"}

    # 2. 写报告
    meta_name = (repo or {}).get("full_name", pid).split("/")[-1]
    proj_dir = KB / pid
    if report_type == "monthly":
        target_dir = proj_dir / "briefings" / "monthly"
    else:
        target_dir = proj_dir / "briefings" / "weekly"
    target_dir.mkdir(parents=True, exist_ok=True)

    if report_type == "monthly":
        title = f"# {meta_name} · 月报 {period_id}"
        tagline = "（多项目框架 v3.0 · 月度追踪）"
    else:
        title = f"# {meta_name} · 周报 {period_id}"
        tagline = "（多项目框架 v3.0 · 周度追踪）"

    report = f"""{title}

> 生成时间: {today} | {tagline}

## 1. 仓库概览

{gen_repo_stats(repo)}

## 2. {'本月' if report_type == 'monthly' else '本周'} release

{gen_releases(data["releases"])}

## 3. 最近 8 次 commit

{gen_recent_commits(data["commits"])}

## 4. 近期 closed PR (10 条)

{gen_recent_prs(data["prs"])}

## 5. Open Issues 数量

- 当前 open issues: **{(repo.get('open_issues_count') or 0)}** 个（API 实时）

## 6. 关键判断

{gen_key_insights(pid, repo, report_type)}

## 7. 附录

- 仓库主页: https://github.com/{(repo or {}).get('full_name', '—')}
- 数据快照: `snapshots/{today}.json`
- 报告生成器: `_shared/scripts/weekly_runner.py`
"""

    # 3. 写文件（同时写到 briefings/ 和 history/）
    report_path = target_dir / f"{period_id}.md"
    report_path.write_text(report, encoding="utf-8")
    if verbose: print(f"    ✅ 报告: {report_path} ({len(report)//1024} KB)")

    # 🆕 v3.3 长期归档: 写到 history/YYYY/YYYY-MM/
    history_dir = proj_dir / "history" / today[:4] / today[:7]
    history_dir.mkdir(parents=True, exist_ok=True)
    history_path = history_dir / f"{period_id}.md"
    history_path.write_text(report, encoding="utf-8")
    if verbose: print(f"    📚 归档: {history_path}")

    # 4. 飞书简版（v3.1: 恢复详细内容 · 含数据 + commits + 判断）
    commits_short = ""
    for c in (data.get("commits") or [])[:3]:
        msg = c.get("commit", {}).get("message", "").split("\n")[0][:50]
        date = fmt_date(c.get("commit", {}).get("author", {}).get("date", ""))
        commits_short += f"\n  - `{date}` {msg}"

    releases_short = ""
    for r in (data.get("releases") or [])[:2]:
        name = r.get("name") or r.get("tag_name", "")
        if name:
            releases_short += f"\n  - **{name}** — {fmt_date(r.get('published_at', ''))}"

    # 变更分类总结（v3.1 新增）
    changes_summary = gen_changes_summary(data.get("commits"), data.get("prs"))

    feishu_content = f"""📊 **{meta_name}** {('月报' if report_type == 'monthly' else '周报')} {period_id}

> {tagline}

**关键数据**:
- ⭐ Stars: {fmt_num((repo or {}).get("stargazers_count"))} · 🍴 Forks: {fmt_num((repo or {}).get("forks_count"))} · 📋 Issues: {fmt_num((repo or {}).get("open_issues_count"))}
- 🔤 {(repo or {}).get("language") or "—"} · 📄 {(repo or {}).get("license", {}).get("spdx_id") if isinstance((repo or {}).get("license"), dict) else "—"} · 📦 {((repo or {}).get("size") or 0)/1024:.1f} MB
- 📅 最近 push: {fmt_date((repo or {}).get("pushed_at"))}

**本周变更总结**:
{changes_summary}
{"**本周 release**:" + releases_short if releases_short else ""}

**近期提交亮点**:
{commits_short if commits_short else "_（无）_"}

{gen_key_insights(pid, repo, report_type)}

📄 完整报告: knowledge-base/{pid}/briefings/{('monthly' if report_type == 'monthly' else 'weekly')}/{period_id}.md

— Mavis 自动追踪
"""
    feishu_path = target_dir / f"{period_id}-feishu.txt"
    feishu_path.write_text(feishu_content, encoding="utf-8")
    if verbose: print(f"    ✅ 飞书版: {feishu_path}")

    # 5. Snapshot
    snap_dir = proj_dir / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_md = f"""# {meta_name} 快照 · {today}

- **Stars**: {fmt_num((repo or {}).get("stargazers_count"))}
- **Forks**: {fmt_num((repo or {}).get("forks_count"))}
- **Open Issues**: {fmt_num((repo or {}).get("open_issues_count"))}
- **主语言**: {(repo or {}).get("language") or "—"}
- **最近 push**: {fmt_date((repo or {}).get("pushed_at"))}
- **仓库**: https://github.com/{(repo or {}).get("full_name", "—")}

_由 weekly_runner.py v3.0 自动生成_
"""
    (snap_dir / f"{today}.md").write_text(snap_md, encoding="utf-8")

    # 🆕 v3.3: snapshot 也归档到 history/
    snap_history = proj_dir / "history" / today[:4] / today[:7] / f"{today}-snapshot.md"
    snap_history.write_text(snap_md, encoding="utf-8")

    # 6. 更新 index.json
    idx_path = proj_dir / "index.json"
    if idx_path.exists():
        idx_data = json.loads(idx_path.read_text(encoding="utf-8"))
        idx_data["last_github_data"] = {
            "stargazers_count": (repo or {}).get("stargazers_count"),
            "forks_count": (repo or {}).get("forks_count"),
            "open_issues_count": (repo or {}).get("open_issues_count"),
            "watchers_count": (repo or {}).get("watchers_count"),
            "language": (repo or {}).get("language"),
            "size": (repo or {}).get("size"),
            "pushed_at": (repo or {}).get("pushed_at"),
            "updated_at": (repo or {}).get("updated_at"),
            "license": (repo or {}).get("license", {}).get("spdx_id") if isinstance((repo or {}).get("license"), dict) else None,
        }
        idx_data["last_snapshot_at"] = today
        if report_type == "weekly":
            idx_data["last_weekly_report"] = period_id
        else:
            idx_data["last_monthly_report"] = period_id
        idx_path.write_text(json.dumps(idx_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 7. 飞书推送（如已配置）
    push_feishu(pid, report_type, period_id, feishu_content)

    # 🆕 v3.3: 飞书简版也归档到 history/
    feishu_history = proj_dir / "history" / today[:4] / today[:7] / f"{period_id}-feishu.txt"
    feishu_history.write_text(feishu_content, encoding="utf-8")

    return {
        "ok": True,
        "project": pid,
        "report_type": report_type,
        "period_id": period_id,
        "report_path": str(report_path),
        "feishu_path": str(feishu_path),
    }


def push_to_github(site_dir: Path = Path("/workspace/output/pilotdeck-site")):
    """跑完自动 push 到 GitHub Pages"""
    script = Path(__file__).parent / "git_api_push.py"
    if not script.exists():
        print("  ⚠️  git_api_push.py 不存在，跳过 GitHub push")
        return False
    if not GITHUB_TOKEN:
        print("  ⚠️  GITHUB_KB_TOKEN 未配置，跳过 GitHub push")
        return False
    try:
        import subprocess
        result = subprocess.run(
            ["python3", str(script)],
            capture_output=True, text=True, timeout=90
        )
        # 只看最后 5 行输出
        lines = (result.stdout or "").strip().split("\n")
        for line in lines[-5:]:
            print(f"    [push] {line}")
        return result.returncode == 0
    except Exception as e:
        print(f"  ⚠️  GitHub push 异常: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Mavis 知识库 Tracker v3.0")
    parser.add_argument("--project", help="单个项目 ID（与 --all 二选一）")
    parser.add_argument("--all", action="store_true", help="批量跑所有项目")
    parser.add_argument("--monthly", action="store_true", help="月报模式（默认周报）")
    parser.add_argument("--list", action="store_true", help="列出所有支持的项目")
    parser.add_argument("--no-push", action="store_true", help="不自动 push 到 GitHub")
    parser.add_argument("--no-rebuild", action="store_true", help="不重新生成网站（只跑 tracker）")
    args = parser.parse_args()

    if args.list:
        print("支持的项目:")
        for pid, repo in REPO_MAP.items():
            print(f"  - {pid:18s}  {repo}")
        return

    if not args.project and not args.all:
        parser.error("必须指定 --project <id> 或 --all")

    report_type = "monthly" if args.monthly else "weekly"
    targets = list(REPO_MAP.keys()) if args.all else [args.project]

    print(f"🚀 Mavis Tracker v3.0 · {report_type}")
    print(f"   目标: {len(targets)} 个项目")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Token: {'✅' if GITHUB_TOKEN else '❌ 未配置（GITHUB_KB_TOKEN）'}")
    print()

    results = []
    for pid in targets:
        result = run_single_project(pid, report_type)
        results.append(result)

    print()
    ok = sum(1 for r in results if r.get("ok"))
    fail = len(results) - ok
    print(f"{'🎉' if fail == 0 else '⚠️ '}  跑完: ✅ {ok} / ❌ {fail}")

    # 重新生成网站（v3.0 默认行为）
    if not args.no_rebuild:
        print()
        print("🌐 重新生成网站...")
        build_script = Path(__file__).parent / "build_site.py"
        if build_script.exists():
            import subprocess
            r = subprocess.run(["python3", str(build_script)], capture_output=True, text=True, timeout=60)
            for line in r.stdout.strip().split("\n")[-3:]:
                print(f"    {line}")

    # 自动 push 到 GitHub
    if not args.no_push and fail == 0:
        print()
        print("📤 推送到 GitHub Pages...")
        push_to_github()

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
