#!/usr/bin/env python3
"""
Mavis 知识库动态生成器 v2.0
===========================
- 读 _shared/registry.json 自动发现项目
- 每个项目的 project.html 真正读取该项目的 md 文件内容
- 嵌入 HTML 静态部署
- 轻量级 md→html 转换（无外部依赖）
"""

import json
import sys
import os
import re
import shutil
import zipfile
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path("/workspace/knowledge-base")
SITE_OUTPUT = Path("/workspace/output/pilotdeck-site")
SITE_NAME = "Mavis 多项目知识库"


# ============== Markdown → HTML 转换（轻量级）==============

def md_to_html(md_text: str) -> str:
    """极简 md→html（不依赖外部库）"""
    lines = md_text.split('\n')
    html = []
    in_code = False
    in_list = False
    in_table = False
    list_type = None  # 'ul' or 'ol'
    table_rows = []

    def flush_list():
        nonlocal in_list, list_type
        if in_list:
            html.append(f'</{list_type}>')
            in_list = False
            list_type = None

    def flush_table():
        nonlocal in_table, table_rows
        if in_table and table_rows:
            # table_rows: list of [cells]
            if table_rows:
                html.append('<table>')
                # 第一行是表头
                html.append('<tr>')
                for cell in table_rows[0]:
                    html.append(f'<th>{cell.strip()}</th>')
                html.append('</tr>')
                for row in table_rows[1:]:
                    html.append('<tr>')
                    for cell in row:
                        html.append(f'<td>{cell.strip()}</td>')
                    html.append('</tr>')
                html.append('</table>')
            table_rows = []
            in_table = False

    for line in lines:
        # 代码块
        if line.startswith('```'):
            if in_code:
                html.append('</pre>')
                in_code = False
            else:
                flush_list()
                flush_table()
                html.append('<pre>')
                in_code = True
            continue
        if in_code:
            html.append(line)
            continue

        # 标题
        if line.startswith('#### '):
            flush_list(); flush_table()
            html.append(f'<h4>{line[5:].strip()}</h4>')
            continue
        if line.startswith('### '):
            flush_list(); flush_table()
            html.append(f'<h3>{line[4:].strip()}</h3>')
            continue
        if line.startswith('## '):
            flush_list(); flush_table()
            html.append(f'<h2>{line[3:].strip()}</h2>')
            continue
        if line.startswith('# '):
            flush_list(); flush_table()
            html.append(f'<h1>{line[2:].strip()}</h1>')
            continue

        # 引用
        if line.startswith('> '):
            flush_list(); flush_table()
            html.append(f'<blockquote>{line[2:].strip()}</blockquote>')
            continue
        if line.startswith('>'):
            flush_list(); flush_table()
            html.append(f'<blockquote>{line[1:].strip()}</blockquote>')
            continue

        # 表格
        if line.startswith('|') and '|' in line[1:]:
            cells = [c.strip() for c in line.split('|')[1:-1]]
            # 跳过分隔行 (| --- |)
            if all(re.match(r'^[-:]+$', c) for c in cells if c):
                continue
            in_table = True
            table_rows.append(cells)
            continue
        else:
            if in_table and line.strip() == '':
                flush_table()
                continue
            elif in_table and line.strip():
                flush_table()
            # 继续后面的逻辑

        # 列表
        if re.match(r'^\s*-\s+', line):
            content = re.sub(r'^\s*-\s+', '', line)
            if not in_list or list_type != 'ul':
                flush_list()
                html.append('<ul>')
                in_list = True
                list_type = 'ul'
            # 处理加粗和代码
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'`(.+?)`', r'<code>\1</code>', content)
            content = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', content)
            html.append(f'<li>{content}</li>')
            continue
        if re.match(r'^\s*\d+\.\s+', line):
            content = re.sub(r'^\s*\d+\.\s+', '', line)
            if not in_list or list_type != 'ol':
                flush_list()
                html.append('<ol>')
                in_list = True
                list_type = 'ol'
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'`(.+?)`', r'<code>\1</code>', content)
            html.append(f'<li>{content}</li>')
            continue

        # 普通段落
        if line.strip() == '':
            flush_list()
            flush_table()
            continue

        flush_list()
        flush_table()
        content = line
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        content = re.sub(r'`(.+?)`', r'<code>\1</code>', content)
        content = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', content)
        html.append(f'<p>{content}</p>')

    flush_list()
    flush_table()
    if in_code:
        html.append('</pre>')

    return '\n'.join(html)


# ============== 找文件 ==============

def find_latest_weekly(proj_dir: Path) -> Path | None:
    """找最新的 weekly 报告 (按修改时间)"""
    weekly_dir = proj_dir / 'briefings' / 'weekly'
    if not weekly_dir.exists():
        return None
    files = [f for f in weekly_dir.glob('*.md') if not f.name.endswith('-feishu.txt')]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def find_latest_monthly(proj_dir: Path) -> Path | None:
    monthly_dir = proj_dir / 'briefings' / 'monthly'
    if not monthly_dir.exists():
        return None
    files = [f for f in monthly_dir.glob('*.md') if not f.name.endswith('-feishu.txt')]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def list_competitor_files(proj_dir: Path) -> list:
    """列出所有竞品分析 md 文件"""
    competitors_dir = proj_dir / 'competitors'
    if not competitors_dir.exists():
        return []
    return sorted(competitors_dir.glob('*.md'))


# ============== HTML 模板 ==============

INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script>
  (function() {{
    const STORAGE_KEY = "mavis_kb_unlocked_v3";
    if (sessionStorage.getItem(STORAGE_KEY) !== 'yes') {{
      window.location.href = 'gate.html';
    }}
  }})();
</script>
<title>{site_name}</title>
<style>
  :root {{ --bg: #0f1419; --panel: #1a1f29; --panel-2: #232a36; --border: #2d3543; --text: #e6e9ef; --text-dim: #8b95a7; --accent: #4f9eff; --accent-2: #6ee7b7; --warning: #f59e0b; --code-bg: #0a0d12; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ min-height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: var(--bg); color: var(--text); }}
  body {{ display: flex; flex-direction: column; }}
  header {{ background: var(--panel); border-bottom: 1px solid var(--border); padding: 18px 32px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }}
  header h1 {{ font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: 10px; }}
  header h1 .dot {{ width: 10px; height: 10px; border-radius: 50%; background: var(--accent-2); box-shadow: 0 0 14px var(--accent-2); }}
  header .meta {{ font-size: 12px; color: var(--text-dim); display: flex; gap: 18px; flex-wrap: wrap; }}
  header .meta a {{ color: var(--accent); text-decoration: none; }}
  main {{ flex: 1; padding: 32px; max-width: 1400px; margin: 0 auto; width: 100%; }}
  .hero {{ background: linear-gradient(135deg, var(--panel) 0%, var(--panel-2) 100%); border: 1px solid var(--border); border-radius: 12px; padding: 32px 36px; margin-bottom: 28px; }}
  .hero h2 {{ font-size: 22px; margin-bottom: 12px; }}
  .hero p {{ color: var(--text-dim); font-size: 14px; line-height: 1.7; margin-bottom: 8px; }}
  .hero .actions {{ margin-top: 16px; display: flex; gap: 12px; flex-wrap: wrap; }}
  .hero .actions a {{ background: var(--accent); color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 500; }}
  .hero .actions a.secondary {{ background: var(--panel); border: 1px solid var(--border); }}
  h2.section {{ font-size: 16px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; margin: 32px 0 16px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }}
  .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 20px 22px; transition: all 0.15s; cursor: pointer; text-decoration: none; color: var(--text); display: block; }}
  .card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
  .card .head {{ display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 8px; }}
  .card h3 {{ font-size: 16px; font-weight: 600; }}
  .card .badge {{ font-size: 10px; padding: 3px 8px; border-radius: 4px; font-weight: 500; }}
  .card .badge.active {{ background: rgba(110, 231, 183, 0.15); color: var(--accent-2); }}
  .card .tagline {{ color: var(--text-dim); font-size: 13px; margin-bottom: 14px; line-height: 1.5; }}
  .card .stats {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 12px; }}
  .card .stats .stat {{ background: var(--panel-2); padding: 6px 10px; border-radius: 4px; }}
  .card .stats .stat .label {{ color: var(--text-dim); font-size: 10px; }}
  .card .stats .stat .value {{ font-weight: 600; margin-top: 2px; }}
  .card .footer-info {{ margin-top: 12px; font-size: 11px; color: var(--text-dim); display: flex; gap: 12px; flex-wrap: wrap; }}
  .framework-box {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 24px 28px; margin-top: 28px; }}
  .framework-box h3 {{ font-size: 16px; margin-bottom: 12px; }}
  .framework-box pre {{ background: var(--code-bg); padding: 16px; border-radius: 6px; overflow-x: auto; font-size: 12px; line-height: 1.6; margin: 12px 0; }}
  .framework-box table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }}
  .framework-box th, .framework-box td {{ padding: 6px 10px; border: 1px solid var(--border); text-align: left; }}
  .framework-box th {{ background: var(--panel-2); color: var(--text-dim); font-weight: 600; }}
  .competitor-pool {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; margin-top: 12px; }}
  .competitor {{ background: var(--panel-2); padding: 8px 12px; border-radius: 6px; font-size: 12px; }}
  .competitor .name {{ font-weight: 600; }}
  .competitor .vendor {{ color: var(--text-dim); font-size: 11px; }}
  footer {{ background: var(--panel); border-top: 1px solid var(--border); padding: 16px 32px; font-size: 11px; color: var(--text-dim); text-align: center; margin-top: 40px; }}
</style>
</head>
<body>
<header>
  <h1><span class="dot"></span> {site_name}</h1>
  <div class="meta">
    <span>📦 v{framework_version}</span>
    <span>📁 {active_count} 个项目 active</span>
    <span>🕐 {build_time}</span>
    <a href="knowledge-base.zip">📥 完整下载</a>
  </div>
</header>
<main>
  <div class="hero">
    <h2>🚀 多项目追踪系统</h2>
    <p>支持无限扩展的项目追踪框架。每个项目有独立目录、统一结构；跨项目共享竞品池；本页面由 <code>build_site.py</code> 自动生成。</p>
    <p style="color: var(--text); font-weight: 500;">当前 <span style="color: var(--accent-2);">{active_count} 个 active 项目</span>，{total_branches} 个 Git 分支活跃追踪。</p>
    <div class="actions">
      <a href="#projects">查看项目</a>
      <a href="dashboard.html" class="secondary">📊 Dashboard</a>
      <a href="#add-new" class="secondary">+ 添加新项目</a>
      <a href="knowledge-base.zip" class="secondary">下载 zip</a>
    </div>
  </div>
  <h2 class="section">📊 已注册项目</h2>
  <div class="grid" id="projects">
    {project_cards}
  </div>
  <h2 class="section">🆕 添加新项目</h2>
  <div class="framework-box" id="add-new">
    <h3>3 步添加新项目</h3>
    <p style="color: var(--text-dim); font-size: 13px; margin-bottom: 12px;">零迁移成本，5 分钟接入。</p>
    <pre><code># 1. 复制模板
cp -r /workspace/knowledge-base/projects/_template/ \\
      /workspace/knowledge-base/projects/&lt;new-id&gt;/

# 2. 填入项目元数据
vim /workspace/knowledge-base/projects/&lt;new-id&gt;/index.json

# 3. 在全局注册表登记 + 重新生成 + 部署
vim _shared/registry.json
python3 /workspace/knowledge-base/_index/scripts/build_site.py</code></pre>
  </div>
  <h2 class="section">🏗 框架结构</h2>
  <div class="framework-box">
    <h3>目录布局</h3>
    <pre><code>mavis-kb/                         ← GitHub 仓库根
├── README.md                    ← 仓库入口
├── _shared/                     ← 跨项目共享
│   ├── scripts/                 ← 所有可执行脚本
│   ├── templates/new-project/   ← 新项目模板
│   ├── registry.json            ← 项目注册表
│   ├── password.json
│   └── dashboard.json
├── pilotdeck/                   ← 项目 1（顶层平铺）
│   ├── README.md
│   ├── profile.md
│   ├── index.json
│   ├── competitors/
│   ├── snapshots/
│   └── history/                 ← 🆕 长期归档
│       └── 2026/2026-06/
├── openclaw/                    ← 项目 2
├── ... (9 个项目顶层)
└── &lt;new-project&gt;/             ← 加新项目 = 复制模板 + 改 index.json + push</code></pre>
  </div>
  <h2 class="section">🥊 共享竞品池</h2>
  <div class="framework-box">
    <h3>跨项目共享的竞品信息（{competitor_count} 个）</h3>
    <div class="competitor-pool">{competitor_cards}</div>
  </div>
  <h2 class="section">📅 Cron 任务（v1.3 错开调度）</h2>
  <div class="framework-box">
    <h3>错开调度：每周一 08:00-09:20 + 月末同时间窗口</h3>
    <p style="color: var(--text-dim); font-size: 13px; margin-bottom: 12px;">
      避免 18 个 cron 同时触发的资源争抢 + 飞书刷屏 + GitHub API 撞车。10 分钟错开，按用户关注度 + 类别排序。
    </p>
    <table>
      <tr><th>时间</th><th>项目</th><th>分组</th><th>调度</th></tr>
      {cron_rows}
    </table>
    <p style="color: var(--text-dim); font-size: 12px; margin-top: 12px;">
      ⏱ 总跨度 1h20m · 9 个项目 · 月末月报同节奏
    </p>
  </div>
</main>
<footer>
  {site_name} · 由 Mavis 维护 · 自动生成于 {build_time}
</footer>
</body>
</html>
"""

PROJECT_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script>
  (function() {{
    const STORAGE_KEY = "mavis_kb_unlocked_" + new Date().toISOString().slice(0, 10).replace(/-/g, '');
    if (sessionStorage.getItem(STORAGE_KEY) !== 'yes') {{
      window.location.href = 'gate.html';
    }}
  }})();
</script>
<title>{name} · 项目详情</title>
<style>
  :root {{ --bg: #0f1419; --panel: #1a1f29; --panel-2: #232a36; --border: #2d3543; --text: #e6e9ef; --text-dim: #8b95a7; --accent: #4f9eff; --accent-2: #6ee7b7; --warning: #f59e0b; --danger: #ef4444; --code-bg: #0a0d12; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }}
  header {{ background: var(--panel); border-bottom: 1px solid var(--border); padding: 16px 32px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }}
  header h1 {{ font-size: 16px; display: flex; align-items: center; gap: 10px; }}
  header h1 a {{ color: var(--accent); text-decoration: none; }}
  header h1 a:hover {{ text-decoration: underline; }}
  header .meta {{ font-size: 12px; color: var(--text-dim); }}
  header .meta a {{ color: var(--accent); text-decoration: none; margin-left: 12px; }}
  .layout {{ display: flex; flex: 1; }}
  nav {{ width: 280px; background: var(--panel); border-right: 1px solid var(--border); padding: 20px 0; overflow-y: auto; flex-shrink: 0; max-height: calc(100vh - 70px); }}
  nav .group {{ margin-bottom: 18px; }}
  nav .group-title {{ font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-dim); padding: 0 20px 8px; letter-spacing: 0.5px; }}
  nav a {{ display: block; padding: 8px 20px; color: var(--text); text-decoration: none; font-size: 13px; border-left: 3px solid transparent; word-break: break-all; }}
  nav a:hover {{ background: var(--panel-2); border-left-color: var(--accent); }}
  nav a.active {{ background: var(--panel-2); border-left-color: var(--accent); color: var(--accent); }}
  nav .file-hint {{ font-size: 10px; color: var(--text-dim); margin-left: 4px; }}
  main {{ flex: 1; padding: 32px 40px; overflow-y: auto; max-height: calc(100vh - 70px); }}
  article.doc {{ max-width: 1000px; margin: 0 auto; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 28px 36px; }}
  article.doc h1 {{ font-size: 24px; padding-bottom: 12px; border-bottom: 1px solid var(--border); margin-bottom: 16px; }}
  article.doc h2 {{ font-size: 18px; margin: 28px 0 12px; color: var(--accent); }}
  article.doc h3 {{ font-size: 15px; margin: 20px 0 10px; color: var(--accent-2); }}
  article.doc h4 {{ font-size: 13px; margin: 16px 0 8px; color: var(--text); font-weight: 600; }}
  article.doc p, article.doc li {{ font-size: 14px; line-height: 1.7; margin-bottom: 8px; }}
  article.doc ul, article.doc ol {{ margin: 8px 0 8px 24px; }}
  article.doc table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }}
  article.doc th, article.doc td {{ padding: 8px 12px; border: 1px solid var(--border); text-align: left; }}
  article.doc th {{ background: var(--panel-2); color: var(--text-dim); font-weight: 600; }}
  article.doc pre {{ background: var(--code-bg); padding: 14px; border-radius: 6px; overflow-x: auto; margin: 12px 0; font-size: 12px; line-height: 1.5; }}
  article.doc code {{ background: var(--code-bg); padding: 2px 6px; border-radius: 3px; font-size: 12px; color: var(--accent-2); }}
  article.doc pre code {{ background: transparent; padding: 0; }}
  article.doc .meta {{ font-size: 12px; color: var(--text-dim); margin-bottom: 20px; }}
  article.doc a {{ color: var(--accent); text-decoration: none; }}
  article.doc a:hover {{ text-decoration: underline; }}
  article.doc blockquote {{ border-left: 3px solid var(--accent); padding: 8px 16px; background: var(--panel-2); margin: 12px 0; color: var(--text-dim); }}
  article.doc strong {{ color: var(--accent-2); }}
  .badge {{ display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 10px; margin-right: 6px; }}
  .badge-ok {{ background: rgba(110, 231, 183, 0.15); color: var(--accent-2); }}
  .badge-warn {{ background: rgba(245, 158, 11, 0.15); color: var(--warning); }}
  .empty {{ padding: 60px 20px; text-align: center; color: var(--text-dim); }}
  .empty h2 {{ color: var(--text); margin-bottom: 12px; font-size: 18px; }}
  .empty p {{ font-size: 13px; margin-bottom: 16px; }}
  .empty code {{ background: var(--code-bg); padding: 4px 8px; border-radius: 3px; color: var(--accent-2); font-size: 12px; display: inline-block; margin: 4px 0; }}
  footer {{ background: var(--panel); border-top: 1px solid var(--border); padding: 12px; text-align: center; font-size: 11px; color: var(--text-dim); }}
</style>
</head>
<body>
<header>
  <h1>🚀 {name} · <a href="index.html">← 返回知识库</a></h1>
  <div class="meta">
    {tagline}
    <a href="{github_repo}" target="_blank">GitHub ↗</a>
  </div>
</header>
<div class="layout">
  <nav id="nav">
    {nav_html}
  </nav>
  <main>
    {articles_html}
  </main>
</div>
<footer>{name} 追踪项目 · Mavis 维护 · 自动生成于 {build_time}</footer>
<script>
  const articles = document.querySelectorAll('article.doc');
  const links = document.querySelectorAll('nav a');
  function show(id) {{
    articles.forEach(a => a.style.display = (a.id === id) ? 'block' : 'none');
    links.forEach(l => l.classList.toggle('active', l.getAttribute('href') === '#' + id));
    document.querySelector('main').scrollTop = 0;
  }}
  function handleHash() {{
    const id = (location.hash || '#welcome').slice(1);
    show(Array.from(articles).some(a => a.id === id) ? id : 'welcome');
  }}
  links.forEach(l => l.addEventListener('click', e => {{
    const href = l.getAttribute('href');
    if (href && href.startsWith('#')) {{ e.preventDefault(); history.pushState(null, '', href); handleHash(); }}
  }}));
  window.addEventListener('popstate', handleHash);
  handleHash();
</script>
</body>
</html>
"""


# ============== 数据加载 ==============

def load_projects_registry():
    with open(ROOT / "_shared" / "registry.json") as f:
        return json.load(f)


def load_project_index(project_id):
    path = ROOT / project_id / "index.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


# ============== HTML 生成 ==============

def format_stars(n):
    if not n:
        return "—"
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def build_project_card(project):
    pid = project["id"]
    proj_index = load_project_index(pid) or {}
    proj = proj_index.get("project", {})
    gh = proj_index.get("last_github_data", {}) or {}

    stars = format_stars(gh.get("stargazers_count"))
    forks = format_stars(gh.get("forks_count"))
    issues = gh.get("open_issues_count", "—")

    # 找到是否有 weekly 报告
    has_weekly = find_latest_weekly(ROOT / pid) is not None
    has_monthly = find_latest_monthly(ROOT / pid) is not None
    files_count = list(ROOT.glob(f"projects/{pid}/**/*.md"))

    return f'''
    <a href="project-{pid}.html" class="card">
      <div class="head">
        <h3>{proj.get("name", pid)}</h3>
        <span class="badge active">{project.get("status", "active").upper()}</span>
      </div>
      <p class="tagline">{proj.get("tagline", "")}</p>
      <div class="stats">
        <div class="stat"><div class="label">GitHub Stars</div><div class="value">{stars}</div></div>
        <div class="stat"><div class="label">Forks</div><div class="value">{forks}</div></div>
        <div class="stat"><div class="label">Open Issues</div><div class="value">{issues}</div></div>
        <div class="stat"><div class="label">追踪起始</div><div class="value">{project.get("tracking_since", "—")}</div></div>
      </div>
      <div class="footer-info">
        {"<span style='color: var(--accent-2);'>✅ 有周报</span>" if has_weekly else "<span style='color: var(--warning);'>⏳ 等待首次周报</span>"}
        {"<span style='color: var(--accent-2);'>✅ 有月报</span>" if has_monthly else "<span style='color: var(--text-dim);'>⏳ 等待首次月报</span>"}
        {"<span style='color: var(--accent-2);'>✅ 飞书已配</span>" if project.get("feishu_webhook_configured") else "<span style='color: var(--warning);'>⚠️ 飞书未配</span>"}
      </div>
    </a>
    '''


def build_competitor_cards(registry):
    comps = registry.get("competitors_shared", {}).get("competitors", {})
    cards = []
    for cid, c in comps.items():
        cards.append(f'<div class="competitor"><div class="name">{c.get("name", cid)}</div><div class="vendor">{c.get("vendor", "")} · {c.get("category", "")}</div></div>')
    return "\n".join(cards)


def build_cron_rows(registry):
    rows = []
    stagger = registry.get("stagger_strategy", {})
    groups = stagger.get("groups", [])
    for group in groups:
        pid = group["project"]
        time_str = group["time"]
        tier = group.get("tier", "")
        sched = f"{time_str} 周一 / {time_str} 月末"
        rows.append(f'<tr><td><strong>{time_str}</strong></td><td>{pid}</td><td>{tier}</td><td>{sched}</td></tr>')
    return "\n".join(rows) if rows else '<tr><td colspan="4" style="text-align:center;color:var(--text-dim)">暂无</td></tr>'


def build_index_html(registry):
    projects = [p for p in registry.get("projects", []) if p.get("status") == "active"]
    cards = "\n".join(build_project_card(p) for p in projects)
    comp_cards = build_competitor_cards(registry)
    cron_rows = build_cron_rows(registry)
    cron_count = sum(2 for p in projects if p.get("cron_task_ids"))
    comp_count = len(registry.get("competitors_shared", {}).get("competitors", {}))

    return INDEX_HTML.format(
        site_name=SITE_NAME,
        framework_version=registry.get("framework_version", "1.3"),
        active_count=len(projects),
        total_branches=0,
        build_time=datetime.now().strftime("%Y-%m-%d %H:%M CST"),
        project_cards=cards,
        competitor_cards=comp_cards,
        competitor_count=comp_count,
        cron_rows=cron_rows,
        cron_count=cron_count,
    )


def safe_id(s):
    """生成可作为 HTML id 的字符串"""
    return re.sub(r'[^a-zA-Z0-9_-]', '-', s).strip('-')


def build_project_articles_html(proj_dir: Path, project_id: str):
    """扫描项目目录，生成所有 article + 对应 nav 链接"""
    nav_groups = []  # list of (group_title, list of (display_name, anchor_id))
    articles_html = []  # list of article HTML strings

    # 1. 欢迎页（基础元数据）
    proj_index_path = proj_dir / "index.json"
    if proj_index_path.exists():
        with open(proj_index_path) as f:
            data = json.load(f)
        proj_meta = data.get("project", {})
        gh = data.get("last_github_data", {}) or {}
        tracking = data.get("tracking", {})

        gh_table = ""
        for k, v in [
            ("GitHub Stars", format_stars(gh.get("stargazers_count"))),
            ("Forks", format_stars(gh.get("forks_count"))),
            ("Watchers", format_stars(gh.get("watchers_count"))),
            ("Open Issues", gh.get("open_issues_count", "—")),
            ("License", (gh.get("license", {}).get("spdx_id") if isinstance(gh.get("license"), dict) else None) or proj_meta.get("license", "—")),
            ("主语言", gh.get("language") or "—"),
            ("Size", f"{gh.get('size', 0) / 1024:.1f} MB" if gh.get('size') else "—"),
            ("最近 push", (gh.get('pushed_at', '') or '')[:10] or "—"),
        ]:
            gh_table += f"<tr><td>{k}</td><td>{v}</td></tr>"

        sched_html = ""
        if tracking.get("weekly_report", {}).get("enabled"):
            sched = tracking["weekly_report"].get("cron_expr", "0 8 * * 1")
            sched_html += f'<p><span class="badge badge-ok">周报 cron</span> <code>{sched}</code></p>'
        if tracking.get("monthly_report", {}).get("enabled"):
            sched = tracking["monthly_report"].get("cron_expr", "0 8 28-31 * *")
            sched_html += f'<p><span class="badge badge-ok">月报 cron</span> <code>{sched}</code></p>'
        if data.get("tracking", {}).get("feishu", {}).get("webhook_url"):
            sched_html += '<p><span class="badge badge-ok">飞书推送</span> 已配置</p>'

        # 关键能力
        features_html = ""
        for f in data.get("key_features", []):
            features_html += f"<li>{f}</li>"

        article = f"""
    <article class="doc" id="welcome">
      <h1>🚀 {proj_meta.get('name', project_id)}</h1>
      <p class="meta">{proj_meta.get('tagline', '')}</p>
      <p><strong>追踪起始:</strong> {data.get('framework_v1_compliance', {}).get('created_at', '—')[:10] or '—'}</p>
      <p><strong>主仓库:</strong> <a href="{proj_meta.get('github_repo', '#')}">{proj_meta.get('github_repo', '—')}</a></p>
      <h2>关键数据 (GitHub API 实时)</h2>
      <table>{gh_table}</table>
      <h2>运行状态</h2>
      {sched_html}
      <h2>核心能力</h2>
      <ul>{features_html}</ul>
    </article>
"""
        articles_html.append(article)
        nav_groups.append(("概览", [("欢迎页", "welcome")]))

    # 2. profile.md
    profile_path = proj_dir / "profile.md"
    if profile_path.exists():
        content = profile_path.read_text(encoding="utf-8")
        # 截掉第一个 # 标题（避免重复）
        lines = content.split('\n')
        if lines and lines[0].startswith('# '):
            lines = lines[1:]
        content = '\n'.join(lines).strip()
        body_html = md_to_html(content)
        aid = "profile"
        article = f"""
    <article class="doc" id="{aid}" style="display:none">
      <h1>📋 项目档案</h1>
      <p class="meta">文件: <code>profile.md</code></p>
      {body_html}
    </article>
"""
        articles_html.append(article)
        nav_groups.append(("档案", [(f"档案 ({profile_path.stat().st_size//1024}KB)", aid)]))

    # 3. timeline.md
    timeline_path = proj_dir / "timeline.md"
    if timeline_path.exists():
        content = timeline_path.read_text(encoding="utf-8")
        lines = content.split('\n')
        if lines and lines[0].startswith('# '):
            lines = lines[1:]
        content = '\n'.join(lines).strip()
        body_html = md_to_html(content)
        aid = "timeline"
        article = f"""
    <article class="doc" id="{aid}" style="display:none">
      <h1>📅 重大事件时间线</h1>
      <p class="meta">文件: <code>timeline.md</code></p>
      {body_html}
    </article>
"""
        articles_html.append(article)
        nav_groups.append(("事件", [(f"时间线 ({timeline_path.stat().st_size//1024}KB)", aid)]))

    # 4. 最新周报
    latest_weekly = find_latest_weekly(proj_dir)
    if latest_weekly:
        content = latest_weekly.read_text(encoding="utf-8")
        lines = content.split('\n')
        if lines and lines[0].startswith('# '):
            lines = lines[1:]
        content = '\n'.join(lines).strip()
        body_html = md_to_html(content)
        aid = "weekly-latest"
        article = f"""
    <article class="doc" id="{aid}" style="display:none">
      <h1>📊 最新周报</h1>
      <p class="meta">文件: <code>{latest_weekly.name}</code> · 大小 {latest_weekly.stat().st_size//1024}KB</p>
      {body_html}
    </article>
"""
        articles_html.append(article)
        nav_groups.append(("简报", [(f"最新周报 ({latest_weekly.stem})", aid)]))

    # 5. 最新月报
    latest_monthly = find_latest_monthly(proj_dir)
    if latest_monthly:
        content = latest_monthly.read_text(encoding="utf-8")
        lines = content.split('\n')
        if lines and lines[0].startswith('# '):
            lines = lines[1:]
        content = '\n'.join(lines).strip()
        body_html = md_to_html(content)
        aid = "monthly-latest"
        article = f"""
    <article class="doc" id="{aid}" style="display:none">
      <h1>📊 最新月报</h1>
      <p class="meta">文件: <code>{latest_monthly.name}</code> · 大小 {latest_monthly.stat().st_size//1024}KB</p>
      {body_html}
    </article>
"""
        articles_html.append(article)
        nav_groups.append(("简报", [(f"最新月报 ({latest_monthly.stem})", aid)]))

    # 6. 竞品分析
    competitor_files = list_competitor_files(proj_dir)
    for cf in competitor_files:
        content = cf.read_text(encoding="utf-8")
        lines = content.split('\n')
        if lines and lines[0].startswith('# '):
            lines = lines[1:]
        content = '\n'.join(lines).strip()
        body_html = md_to_html(content)
        aid = safe_id(f"comp-{cf.stem}")
        article = f"""
    <article class="doc" id="{aid}" style="display:none">
      <h1>🥊 {cf.stem}</h1>
      <p class="meta">文件: <code>{cf.name}</code> · 大小 {cf.stat().st_size//1024}KB</p>
      {body_html}
    </article>
"""
        articles_html.append(article)
        nav_groups.append(("竞品分析", [(f"{cf.stem} ({cf.stat().st_size//1024}KB)", aid)]))

    # 7. snapshot
    snapshots_dir = proj_dir / "snapshots"
    if snapshots_dir.exists():
        snapshot_files = sorted(snapshots_dir.glob("*.md"), key=lambda p: p.name, reverse=True)
        for sf in snapshot_files[:3]:  # 最多显示 3 个最新 snapshot
            content = sf.read_text(encoding="utf-8")
            lines = content.split('\n')
            if lines and lines[0].startswith('# '):
                lines = lines[1:]
            content = '\n'.join(lines).strip()
            body_html = md_to_html(content)
            aid = safe_id(f"snap-{sf.stem}")
            article = f"""
    <article class="doc" id="{aid}" style="display:none">
      <h1>📸 数据快照 {sf.stem}</h1>
      <p class="meta">文件: <code>{sf.name}</code></p>
      {body_html}
    </article>
"""
            articles_html.append(article)
            nav_groups.append(("快照", [(f"{sf.stem}", aid)]))

    return nav_groups, articles_html


def build_project_html(project, default_article_id="welcome"):
    """生成单个项目详情页（v2.0: 真正读 md 文件）"""
    pid = project["id"]
    proj_index = load_project_index(pid) or {}
    proj = proj_index.get("project", {})
    proj_dir = ROOT / pid

    nav_groups, articles_html = build_project_articles_html(proj_dir, pid)

    # 生成 nav HTML
    nav_html_parts = []
    for group_title, items in nav_groups:
        nav_html_parts.append(f'<div class="group"><div class="group-title">{group_title}</div>')
        for display, anchor in items:
            nav_html_parts.append(f'<a href="#{anchor}">{display}</a>')
        nav_html_parts.append('</div>')
    nav_html = '\n      '.join(nav_html_parts)

    # 生成 articles HTML
    articles_block = '\n'.join(articles_html)

    return PROJECT_HTML.format(
        name=proj.get("name", pid),
        tagline=proj.get("tagline", "")[:200] + ("..." if len(proj.get("tagline", "")) > 200 else ""),
        github_repo=proj.get("github_repo", "#"),
        nav_html=nav_html,
        articles_html=articles_block,
        build_time=datetime.now().strftime("%Y-%m-%d %H:%M CST"),
    )


# ============== 主流程 ==============

def zip_knowledge_base(output_path):
    if output_path.exists():
        output_path.unlink()
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if file.endswith(".pyc"):
                    continue
                full_path = Path(root) / file
                rel_path = full_path.relative_to(ROOT.parent)
                zf.write(full_path, rel_path)


def main():
    no_zip = "--no-zip" in sys.argv
    no_deploy = "--no-deploy" in sys.argv

    print(f"🏗  Mavis 知识库动态生成器 v2.0")
    print(f"   源: {ROOT}")
    print(f"   输出: {SITE_OUTPUT}")
    print()

    print("📋 加载项目注册表...")
    registry = load_projects_registry()
    projects = [p for p in registry.get("projects", []) if p.get("status") == "active"]
    print(f"   找到 {len(projects)} 个 active 项目")

    SITE_OUTPUT.mkdir(parents=True, exist_ok=True)
    for f in SITE_OUTPUT.iterdir():
        if f.is_file():
            f.unlink()

    print("\n🌐 生成 index.html...")
    index_html = build_index_html(registry)
    (SITE_OUTPUT / "index.html").write_text(index_html, encoding="utf-8")
    print(f"   ✓ index.html ({len(index_html):,} bytes)")

    print("\n🚀 生成项目详情页（v2.0 - 真正读 md 文件）...")
    for project in projects:
        pid = project["id"]
        proj_dir = ROOT / pid
        # 统计该项目的文件数
        md_files = list(proj_dir.rglob("*.md"))
        project_html = build_project_html(project)
        (SITE_OUTPUT / f"project-{pid}.html").write_text(project_html, encoding="utf-8")
        print(f"   ✓ project-{pid}.html ({pid}) — {len(md_files)} 个 md 文件")

    # 兼容的 project.html 重定向到第一个项目
    if projects:
        (SITE_OUTPUT / "project.html").write_text(
            f'<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url=project-{projects[0]["id"]}.html"></head><body></body></html>',
            encoding="utf-8"
        )

    print("\n🔒 生成密码保护页...")
    gate_script = Path(__file__).parent / "build_password_gate.py"
    if gate_script.exists():
        import subprocess
        r = subprocess.run(["python3", str(gate_script)], capture_output=True, text=True, timeout=15)
        for line in r.stdout.strip().split("\n"):
            print(f"   {line}")
    else:
        print("   ⚠️  build_password_gate.py 不存在，跳过")

    print("\n📊 生成 dashboard.html...")
    dash_script = Path(__file__).parent / "build_dashboard.py"
    if dash_script.exists():
        import subprocess
        r = subprocess.run(["python3", str(dash_script)], capture_output=True, text=True, timeout=15)
        for line in r.stdout.strip().split("\n"):
            print(f"   {line}")
    else:
        print("   ⚠️  build_dashboard.py 不存在")

    if not no_zip:
        print("\n📦 打包知识库 zip...")
        zip_path = SITE_OUTPUT / "knowledge-base.zip"
        zip_knowledge_base(zip_path)
        size_kb = zip_path.stat().st_size / 1024
        print(f"   ✓ knowledge-base.zip ({size_kb:.1f} KB)")

    print(f"\n✅ 全部完成！输出目录: {SITE_OUTPUT}, 文件数: {len(list(SITE_OUTPUT.iterdir()))}")


if __name__ == "__main__":
    main()
