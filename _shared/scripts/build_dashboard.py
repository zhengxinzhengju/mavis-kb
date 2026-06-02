#!/usr/bin/env python3
"""Dashboard 独立页生成器 - 统计 + 排序 + 可视化"""
import json
from pathlib import Path
from datetime import datetime

DASH = Path("/workspace/knowledge-base/_shared/dashboard.json")
SITE = Path("/workspace/output/pilotdeck-site")
SITE_NAME = "Mavis 知识库 Dashboard"


def build_dashboard_html(dash: dict) -> str:
    totals = dash["totals"]
    projects = dash["projects"]
    max_stars = max(p["stars"] for p in projects) or 1

    # 排名卡片
    rank_cards = []
    for i, p in enumerate(projects, 1):
        width_pct = (p["stars"] / max_stars) * 100
        bar_color = ["#4f9eff", "#6ee7b7", "#f59e0b", "#a78bfa", "#f472b6"][i % 5] if i <= 5 else "#8b95a7"
        rank_cards.append(f"""
        <a href="project-{p['id']}.html" class="rank-card">
          <div class="rank-num">#{i}</div>
          <div class="rank-info">
            <div class="rank-name">{p['name']} <span class="rank-tagline">{p['tagline']}</span></div>
            <div class="rank-bar-wrap">
              <div class="rank-bar" style="width:{width_pct:.1f}%; background:{bar_color}"></div>
            </div>
            <div class="rank-stats">
              <span class="stat">⭐ {p['stars']:,}</span>
              <span class="stat">🍴 {p['forks']:,}</span>
              <span class="stat">📋 {p['issues']:,}</span>
              <span class="stat">🔤 {p['language']}</span>
            </div>
          </div>
        </a>""")

    # 类别分布
    by_lang = {}
    for p in projects:
        lang = p["language"] or "Other"
        by_lang[lang] = by_lang.get(lang, 0) + p["stars"]
    by_lang = sorted(by_lang.items(), key=lambda x: -x[1])
    lang_total = sum(v for _, v in by_lang) or 1
    lang_bars = []
    lang_colors = {
        "TypeScript": "#3178c6",
        "Python": "#3776ab",
        "Go": "#00add8",
        "C": "#555",
        "Rust": "#dea584",
        "Other": "#888",
    }
    for lang, stars in by_lang:
        pct = (stars / lang_total) * 100
        color = lang_colors.get(lang, "#888")
        lang_bars.append(f"""
        <tr>
          <td><span class="lang-dot" style="background:{color}"></span> {lang}</td>
          <td class="num">{stars:,}</td>
          <td class="num">{pct:.1f}%</td>
          <td>
            <div class="bar-wrap"><div class="bar" style="width:{pct:.1f}%; background:{color}"></div></div>
          </td>
        </tr>""")

    # Issues 排行
    by_issues = sorted(projects, key=lambda p: -p["issues"])
    issue_rows = []
    for p in by_issues:
        issue_rows.append(f"""
        <tr>
          <td><a href="project-{p['id']}.html">{p['name']}</a></td>
          <td class="num">{p['issues']:,}</td>
          <td class="num">{p['stars']:,}</td>
          <td class="num">{(p['issues']/p['stars']*100 if p['stars'] else 0):.2f}%</td>
        </tr>""")

    # 活跃度（最近 push）
    by_pushed = sorted(projects, key=lambda p: p['pushed'], reverse=True)
    activity_rows = []
    for p in by_pushed:
        pushed = p['pushed'] or "—"
        days_ago = "—"
        if pushed and pushed != "—":
            try:
                d = datetime.strptime(pushed, "%Y-%m-%d")
                days_ago = (datetime.now() - d).days
                days_ago = f"{days_ago} 天前"
            except: pass
        activity_rows.append(f"""
        <tr>
          <td><a href="project-{p['id']}.html">{p['name']}</a></td>
          <td>{pushed}</td>
          <td>{days_ago}</td>
          <td><span class="badge {'active' if '今天' in days_ago or '1 天' in days_ago or '0 天' in days_ago else 'dim'}">{days_ago}</span></td>
        </tr>""")

    html = f"""<!DOCTYPE html>
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
<title>{SITE_NAME}</title>
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
  .section-title {{ font-size: 14px; text-transform: uppercase; color: var(--text-dim); letter-spacing: 1px; margin: 32px 0 14px; font-weight: 600; }}
  .totals {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 24px; }}
  .total-card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 20px 24px; }}
  .total-card .label {{ font-size: 12px; color: var(--text-dim); margin-bottom: 6px; }}
  .total-card .value {{ font-size: 28px; font-weight: 700; color: var(--text); }}
  .total-card .sub {{ font-size: 11px; color: var(--text-dim); margin-top: 4px; }}
  .rank-list {{ display: flex; flex-direction: column; gap: 10px; }}
  .rank-card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; display: flex; align-items: center; gap: 18px; text-decoration: none; color: var(--text); transition: all 0.15s; }}
  .rank-card:hover {{ border-color: var(--accent); transform: translateX(4px); }}
  .rank-num {{ font-size: 24px; font-weight: 800; color: var(--text-dim); width: 40px; text-align: center; }}
  .rank-card:nth-child(1) .rank-num {{ color: #ffd700; }}
  .rank-card:nth-child(2) .rank-num {{ color: #c0c0c0; }}
  .rank-card:nth-child(3) .rank-num {{ color: #cd7f32; }}
  .rank-info {{ flex: 1; }}
  .rank-name {{ font-size: 15px; font-weight: 600; margin-bottom: 8px; }}
  .rank-tagline {{ font-weight: 400; color: var(--text-dim); font-size: 12px; margin-left: 8px; }}
  .rank-bar-wrap {{ height: 6px; background: var(--panel-2); border-radius: 3px; margin-bottom: 8px; overflow: hidden; }}
  .rank-bar {{ height: 100%; border-radius: 3px; transition: width 0.3s; }}
  .rank-stats {{ display: flex; gap: 16px; font-size: 12px; color: var(--text-dim); }}
  .rank-stats .stat {{ color: var(--text); font-weight: 500; }}
  .data-panel {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 20px 24px; margin-bottom: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 8px 10px; border-bottom: 1px solid var(--border); text-align: left; }}
  th {{ color: var(--text-dim); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }}
  td.num {{ font-family: 'SF Mono', Monaco, monospace; text-align: right; }}
  td a {{ color: var(--text); text-decoration: none; }}
  td a:hover {{ color: var(--accent); }}
  .lang-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }}
  .bar-wrap {{ background: var(--panel-2); border-radius: 3px; height: 8px; overflow: hidden; }}
  .bar {{ height: 100%; border-radius: 3px; transition: width 0.3s; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }}
  .badge.active {{ background: rgba(110, 231, 183, 0.15); color: var(--accent-2); }}
  .badge.dim {{ background: var(--panel-2); color: var(--text-dim); }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media (max-width: 900px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
  footer {{ background: var(--panel); border-top: 1px solid var(--border); padding: 16px 32px; font-size: 11px; color: var(--text-dim); text-align: center; margin-top: 40px; }}
</style>
</head>
<body>
<header>
  <h1><span class="dot"></span> {SITE_NAME}</h1>
  <div class="meta">
    <span>📊 {totals['projects']} 个项目</span>
    <span>🕐 {dash['generated_at']}</span>
    <a href="index.html">← 返回主页</a>
  </div>
</header>
<main>
  <div class="totals">
    <div class="total-card">
      <div class="label">⭐ 总 Stars</div>
      <div class="value">{totals['stars']:,}</div>
      <div class="sub">{totals['projects']} 个项目合计</div>
    </div>
    <div class="total-card">
      <div class="label">🍴 总 Forks</div>
      <div class="value">{totals['forks']:,}</div>
      <div class="sub">社区贡献指标</div>
    </div>
    <div class="total-card">
      <div class="label">📋 总 Open Issues</div>
      <div class="value">{totals['issues']:,}</div>
      <div class="sub">需要关注的工作量</div>
    </div>
    <div class="total-card">
      <div class="label">💾 总代码量</div>
      <div class="value">{totals['size_mb']:,.1f} MB</div>
      <div class="sub">不含依赖 / vendor</div>
    </div>
  </div>

  <div class="section-title">🏆 Stars 排行（按规模）</div>
  <div class="rank-list">{''.join(rank_cards)}
  </div>

  <div class="grid-2">
    <div>
      <div class="section-title">🎨 按语言分布</div>
      <div class="data-panel">
        <table>
          <tr><th>语言</th><th class="num">Stars</th><th class="num">占比</th><th>分布</th></tr>
          {''.join(lang_bars)}
        </table>
      </div>
    </div>
    <div>
      <div class="section-title">🔥 Issues 排行（压力榜）</div>
      <div class="data-panel">
        <table>
          <tr><th>项目</th><th class="num">Issues</th><th class="num">Stars</th><th class="num">I/S 比</th></tr>
          {''.join(issue_rows)}
        </table>
      </div>
    </div>
  </div>

  <div class="section-title">⚡ 活跃度排行（最近 push）</div>
  <div class="data-panel">
    <table>
      <tr><th>项目</th><th>最近 push</th><th>距今</th><th>状态</th></tr>
      {''.join(activity_rows)}
    </table>
  </div>
</main>
<footer>{SITE_NAME} · Mavis 自动生成 · 数据来自 GitHub API（已认证 token）</footer>
</body>
</html>"""
    return html


def main():
    if not DASH.exists():
        print("❌ dashboard.json 不存在，先跑 weekly_runner")
        return 1
    dash = json.loads(DASH.read_text(encoding="utf-8"))
    html = build_dashboard_html(dash)
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "dashboard.html").write_text(html, encoding="utf-8")
    print(f"✅ dashboard.html 生成 ({len(html)//1024} KB)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
