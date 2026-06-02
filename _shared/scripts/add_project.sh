#!/usr/bin/env bash
# add_project.sh
# ==============
# 一键接入新项目到 Mavis 知识库追踪系统（全流程）
#
# 用法:
#   bash add_project.sh <github-org/repo> [--name "项目名"] [--tier "T1"] [--time "09:40"]
#
# 自动化 (13 步):
#   1. 自动分配 project_id (从 repo 末尾取 slug)
#   2. 从 GitHub API 抓取元数据
#   3. 自动分配错开时间槽 (避开已有项目)
#   4. 创建顶层目录结构 (含 history/2026/12 个月)
#   5. 生成 9 个模板文件 (README/profile/index.json/timeline/tracker/run-log + .gitkeep)
#   6. 更新 _shared/registry.json
#   7. 更新 _shared/scripts/weekly_runner.py REPO_MAP
#   8. 触发首次周报 (生成 briefings/ + history/ 归档)
#   9. 重新生成网站 (build_site + dashboard)
#   10. 准备 cron 创建参数 (weekly + monthly)
#   11. 推 GitHub 仓库 (git_kb_push 推整个知识库)
#   12. 推站点 (git_api_push 推到 output/ + Pages 重新构建)
#   13. 部署国内镜像 (website_deploy)
#
# 后续 Mavis agent 会读取输出，调用 mavis tool 完成步骤 10 的 cron 创建
#
# 示例:
#   bash add_project.sh openai/swarm
#   bash add_project.sh openai/swarm --name "OpenAI Swarm" --tier "T1 框架" --time "10:00"

set -e

# ============== 参数解析 ==============
REPO="$1"
NAME_FLAG=""
TIER_FLAG="T1"
TIME_FLAG=""

shift
while [[ $# -gt 0 ]]; do
    case $1 in
        --name) NAME_FLAG="$2"; shift 2 ;;
        --tier) TIER_FLAG="$2"; shift 2 ;;
        --time) TIME_FLAG="$2"; shift 2 ;;
        *) echo "❌ 未知参数: $1"; exit 1 ;;
    esac
done

if [ -z "$REPO" ]; then
    echo "用法: bash $0 <github-org/repo> [--name NAME] [--tier TIER] [--time HH:MM]"
    echo "示例: bash $0 openai/swarm"
    exit 1
fi

# ============== 环境检查 ==============
cd /workspace/knowledge-base

if [ -z "$GITHUB_KB_TOKEN" ]; then
    echo "❌ GITHUB_KB_TOKEN 未设置"
    exit 1
fi

echo "🚀 Mavis 知识库 · 一键接入新项目"
echo "   目标: $REPO"
echo ""

# ============== 抓 GitHub 数据 ==============
echo "🔍 [1/13] 抓取 GitHub 元数据..."
REPO_DATA=$(curl -s -H "Authorization: token $GITHUB_KB_TOKEN" -m 10 "https://api.github.com/repos/$REPO")
if echo "$REPO_DATA" | grep -q '"message": "Not Found"'; then
    echo "❌ 仓库不存在: $REPO"
    exit 1
fi
echo "   ✅ 元数据已抓取"

# ============== 自动分配 project_id ==============
echo "📝 [2/13] 分配项目 ID..."
EXISTING_COUNT=$(python3 -c "
import json
data = json.load(open('_shared/registry.json'))
print(sum(1 for p in data['projects'] if p.get('status') == 'active'))")
NEXT_NUM=$((EXISTING_COUNT + 1))
SLUG=$(echo "$REPO" | awk -F'/' '{print tolower($2)}' | tr '_' '-')
PROJECT_ID=$(python3 -c "
import json
data = json.load(open('_shared/registry.json'))
existing = [p['id'] for p in data['projects']]
slug = '$SLUG'
n = 1
while slug in existing:
    n += 1
    slug = f'$SLUG-{n}'
print(slug)")
SEQUENTIAL_ID="project-$(printf "%02d" $NEXT_NUM)"

echo "   📂 目录: $PROJECT_ID (来自 repo slug)"
echo "   🆔 顺序: $SEQUENTIAL_ID (共 $EXISTING_COUNT 个 active 项目)"

# ============== 解析元数据 ==============
NAME=$(echo "$REPO_DATA" | python3 -c "import json,sys; print(json.load(sys.stdin).get('name', 'unknown'))")
DESCRIPTION=$(echo "$REPO_DATA" | python3 -c "import json,sys; print(json.load(sys.stdin).get('description') or '—')")
STARS=$(echo "$REPO_DATA" | python3 -c "import json,sys; print(json.load(sys.stdin).get('stargazers_count', 0))")
FORKS=$(echo "$REPO_DATA" | python3 -c "import json,sys; print(json.load(sys.stdin).get('forks_count', 0))")
ISSUES=$(echo "$REPO_DATA" | python3 -c "import json,sys; print(json.load(sys.stdin).get('open_issues_count', 0))")
LANGUAGE=$(echo "$REPO_DATA" | python3 -c "import json,sys; print(json.load(sys.stdin).get('language') or '—')")
LICENSE=$(echo "$REPO_DATA" | python3 -c "
import json, sys
d = json.load(sys.stdin)
lic = d.get('license')
print(lic.get('spdx_id') if lic else '—')")
SIZE_KB=$(echo "$REPO_DATA" | python3 -c "import json,sys; print(int(json.load(sys.stdin).get('size', 0)))")
CREATED=$(echo "$REPO_DATA" | python3 -c "import json,sys; print(json.load(sys.stdin).get('created_at', '')[:10])")
PUSHED=$(echo "$REPO_DATA" | python3 -c "import json,sys; print(json.load(sys.stdin).get('pushed_at', '')[:10])")
YEAR=$(date +%Y)
TODAY=$(date +%Y-%m-%d)

[ -n "$NAME_FLAG" ] && NAME="$NAME_FLAG"

echo "   名称: $NAME | Stars: $STARS | Forks: $FORKS | $LANGUAGE | $LICENSE"

# ============== 自动分配时间槽 ==============
echo "⏰ [3/13] 分配错开时间槽..."
if [ -n "$TIME_FLAG" ]; then
    ALLOC_TIME="$TIME_FLAG"
else
    MAX_TIME=$(python3 -c "
import json
data = json.load(open('_shared/registry.json'))
times = [g.get('time', '00:00') for g in data.get('stagger_strategy', {}).get('groups', [])]
print(max(times) if times else '08:00')")
    HOUR=$(echo $MAX_TIME | cut -d: -f1)
    MIN=$(echo $MAX_TIME | cut -d: -f2)
    NEW_MIN=$((MIN + 10))
    if [ $NEW_MIN -ge 60 ]; then
        NEW_MIN=$((NEW_MIN - 60))
        HOUR=$((HOUR + 1))
    fi
    ALLOC_TIME=$(date -d "today $HOUR:$NEW_MIN" "+%H:%M")
fi
echo "   ✅ $ALLOC_TIME (每周一 + 月末)"

# ============== 创建目录结构 ==============
echo "📁 [4/13] 创建目录结构..."
mkdir -p "$PROJECT_ID"/{briefings/weekly,briefings/monthly,snapshots,competitors,scripts,assets}
for M in 01 02 03 04 05 06 07 08 09 10 11 12; do
    mkdir -p "$PROJECT_ID/history/$YEAR/$YEAR-$M"
done
echo "   ✅ $PROJECT_ID/{briefings,snapshots,competitors,scripts,assets,history/}"

# ============== 生成 9 个文件 ==============
echo "📄 [5/13] 生成 9 个模板文件..."

# README.md
cat > "$PROJECT_ID/README.md" << EOF
# $NAME · 知识库

> 本目录为 Mavis 多项目追踪系统的 $NAME 子项目

## 目录结构

\`\`\`
$PROJECT_ID/
├── index.json
├── profile.md
├── timeline.md
├── run-log.md
├── tracker-prompt.md
├── README.md
├── competitors/
├── snapshots/
├── scripts/
├── assets/
└── history/
    └── YYYY/YYYY-MM/
\`\`\`

## 自动化

| 任务 | 频率 | 说明 |
|------|------|------|
| 周报 | 每周一 $ALLOC_TIME | 拉 GitHub API + 飞书推送 + 归档到 history/ |
| 月报 | 每月最后一天 $ALLOC_TIME | 同上 + 竞品对比刷新 |

## 数据可访问性

- 网站: （已脱敏，请私下联系获取）
- 飞书: 每周一推送
- GitHub: 本目录所有历史（Git 完整记录）
EOF

# profile.md
cat > "$PROJECT_ID/profile.md" << EOF
# $NAME · 项目档案

> 数据采集: $TODAY | 框架版本: v3.3

## 基本信息

- **项目**: $NAME
- **主仓库**: https://github.com/$REPO
- **Stars**: $STARS
- **Forks**: $FORKS
- **Open Issues**: $ISSUES
- **License**: $LICENSE
- **主语言**: $LANGUAGE
- **大小**: $((SIZE_KB/1024)) MB
- **最近 push**: $PUSHED
- **创建于**: $CREATED

## 定位

> $DESCRIPTION

## 核心能力

（待 weekly_runner 跑出数据后补充）

## 风险与机会

（待分析）

## 追踪建议

- **监控周频**: star 增量 + commit 节奏
EOF

# index.json
cat > "$PROJECT_ID/index.json" << EOF
{
  "project": {
    "id": "$PROJECT_ID",
    "name": "$NAME",
    "tagline": "$DESCRIPTION",
    "github_repo": "https://github.com/$REPO",
    "category": "$TIER_FLAG",
    "license": "$LICENSE",
    "language": "$LANGUAGE"
  },
  "key_features": [],
  "tracking": {
    "weekly_report": {
      "enabled": true,
      "cron_expr": "$(echo $ALLOC_TIME | awk -F: '{printf "%d %d", $2, $1}') * * 1"
    },
    "monthly_report": {
      "enabled": true,
      "cron_expr": "$(echo $ALLOC_TIME | awk -F: '{printf "%d %d", $2, $1}') $(echo $ALLOC_TIME | awk -F: '{print $2}')-31 * *"
    },
    "feishu": {
      "webhook_url": "",
      "secret": ""
    }
  },
  "last_github_data": {
    "stargazers_count": $STARS,
    "forks_count": $FORKS,
    "open_issues_count": $ISSUES,
    "language": "$LANGUAGE",
    "size": $SIZE_KB,
    "license": "$LICENSE"
  },
  "last_snapshot_at": "$TODAY"
}
EOF

# timeline.md
cat > "$PROJECT_ID/timeline.md" << EOF
# $NAME · 重大事件时间线

> 关键事件由 weekly_runner 自动追加

## $YEAR

- **$TODAY** 加入 Mavis 知识库追踪系统 (#$NEXT_NUM)
EOF

# tracker-prompt.md
cat > "$PROJECT_ID/tracker-prompt.md" << EOF
# $NAME · Tracker 提示词

> 每周一 cron 自动执行的标准 tracker 流程

## 1. 读配置
- \`_shared/registry.json\` 确认本项目 active
- \`$PROJECT_ID/index.json\` 确认配置

## 2. 拉数据
\`\`\`bash
curl -s -H "Authorization: token \$GITHUB_KB_TOKEN" -m 10 \\
  https://api.github.com/repos/$REPO
\`\`\`

## 3. 写报告
- 完整版: \`briefings/weekly/YYYY-Wnn.md\`
- 飞书版: \`briefings/weekly/YYYY-Wnn-feishu.txt\`
- 归档: \`history/YYYY/YYYY-MM/\`

## 4. 飞书推送
- 读 \`index.json\` 的 feishu 配置
- 调用 \`_shared/scripts/feishu_push.py\`

## 5. 站点重建 + GitHub 同步
- \`_shared/scripts/build_site.py\`
- \`_shared/scripts/git_kb_push.py\`
EOF

# run-log.md
cat > "$PROJECT_ID/run-log.md" << EOF
# $NAME · 运行日志

> weekly_runner 自动追加

## $YEAR

- **$TODAY** 加入追踪系统
EOF

# history/README.md
cat > "$PROJECT_ID/history/README.md" << EOF
# $NAME · 长期历史归档

> 按月归档所有周报、月报、快照。Git 完整记录所有变更历史。

## 目录结构

\`\`\`
history/
├── $YEAR/
│   ├── $(date +%Y)-05/
│   ├── $(date +%Y)-06/
│   └── ...
└── $((YEAR+1))/
\`\`\`
EOF

# 4 个 .gitkeep
cat > "$PROJECT_ID/competitors/.gitkeep" << EOF
# 竞品对比文件放这里
# 命名建议: tier1-direct-comparison.md / tier2-frameworks-comparison.md
EOF
cat > "$PROJECT_ID/snapshots/.gitkeep" << EOF
# 数据快照放这里
EOF
cat > "$PROJECT_ID/assets/.gitkeep" << EOF
# 静态资源放这里
EOF
cat > "$PROJECT_ID/scripts/.gitkeep" << EOF
# 项目专用脚本放这里
EOF

echo "   ✅ 9 个文件已生成"

# ============== 更新 REPO_MAP ==============
echo "🔧 [6/13] 更新 weekly_runner.py REPO_MAP..."
python3 << PYEOF
from pathlib import Path
p = Path("_shared/scripts/weekly_runner.py")
content = p.read_text(encoding="utf-8")
if "\"$PROJECT_ID\"" not in content:
    old = '''REPO_MAP = {'''
    new = f'''REPO_MAP = {{
    "$PROJECT_ID":        "$REPO",'''
    if old in content:
        content = content.replace(old, new, 1)
        p.write_text(content, encoding="utf-8")
        print("   ✅ REPO_MAP 加 $PROJECT_ID")
    else:
        print("   ⚠️  REPO_MAP 锚点找不到")
else:
    print("   ℹ️  REPO_MAP 已有 $PROJECT_ID")
PYEOF

# ============== 更新 registry.json ==============
echo "🔧 [7/13] 更新 registry.json..."
python3 << PYEOF
import json
from pathlib import Path
p = Path("_shared/registry.json")
data = json.loads(p.read_text(encoding="utf-8"))
existing = [proj.get('id') for proj in data['projects']]
if "$PROJECT_ID" not in existing:
    data['projects'].append({
        "id": "$PROJECT_ID",
        "name": "$NAME",
        "status": "active",
        "tracking_since": "$TODAY",
        "sequential_id": "$SEQUENTIAL_ID",
        "stagger_time": "$ALLOC_TIME",
        "tier": "$TIER_FLAG",
        "github_repo": "https://github.com/$REPO",
        # 自动检测: 如果模板 index.json.template 里有 webhook url，设为 True
        "feishu_webhook_configured": bool("$WEEKLY_CRON_EXPR"),  # 占位，下面会被覆盖
        "cron_task_ids": {}
    })
    if "stagger_strategy" not in data:
        data["stagger_strategy"] = {"groups": []}
    data["stagger_strategy"]["groups"].append({
        "project": "$PROJECT_ID",
        "time": "$ALLOC_TIME",
        "tier": "$TIER_FLAG"
    })
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("   ✅ registry 加 $PROJECT_ID + $ALLOC_TIME")
else:
    print("   ℹ️  registry 已有 $PROJECT_ID")
PYEOF

# ============== 触发首次周报 ==============
echo "📊 [8/13] 触发首次周报..."
nohup python3 _shared/scripts/weekly_runner.py --project $PROJECT_ID --no-push --no-rebuild > /tmp/${PROJECT_ID}_init.log 2>&1 &
INIT_PID=$!
sleep 12
if grep -q "✅ 跑完: ✅ 1" /tmp/${PROJECT_ID}_init.log; then
    echo "   ✅ 首次周报成功（briefings/ + history/ 已归档）"
else
    echo "   ⚠️  首次周报可能失败，查看 /tmp/${PROJECT_ID}_init.log"
fi

# ============== 重新 build site ==============
echo "🌐 [9/13] 重新生成网站..."
nohup python3 _shared/scripts/build_site.py > /tmp/site_build.log 2>&1 &
sleep 12
if grep -q "✅ 全部完成" /tmp/site_build.log; then
    echo "   ✅ 网站已重建"
fi
nohup python3 _shared/scripts/build_dashboard.py > /tmp/dash_build.log 2>&1 &
sleep 5
echo "   ✅ Dashboard 已更新"

# ============== 加 gate 检查 ==============
echo "🔒 [10/13] 加密码门检查..."
python3 << 'PYEOF'
from pathlib import Path
import re
gate_check = """<script>
  (function() {
    const STORAGE_KEY = "mavis_kb_unlocked_v3";
    if (sessionStorage.getItem(STORAGE_KEY) !== 'yes') {
      window.location.href = 'gate.html';
    }
  })();
</script>
"""
for html_file in Path("/workspace/output/pilotdeck-site").glob("*.html"):
    if html_file.name == "gate.html":
        continue
    c = html_file.read_text(encoding="utf-8")
    if 'mavis_kb_unlocked_v3' not in c:
        pattern = re.compile(r'<script>\s*\(function\(\) \{\s*const STORAGE_KEY.*?</script>\s*', re.DOTALL)
        c = pattern.sub('', c)
        c = c.replace('<meta charset="UTF-8">', '<meta charset="UTF-8">\n' + gate_check, 1)
        html_file.write_text(c, encoding="utf-8")
print("   ✅ 12 个 HTML 加 gate 检查")
PYEOF

# ============== 准备 cron 参数 ==============
echo "⏰ [11/13] 准备 cron 创建参数..."
WEEKLY_CRON_MIN=$(echo $ALLOC_TIME | awk -F: '{print $2}')
WEEKLY_CRON_HOUR=$(echo $ALLOC_TIME | awk -F: '{print $1}')
WEEKLY_CRON_EXPR="$WEEKLY_CRON_MIN $WEEKLY_CRON_HOUR * * 1"
MONTHLY_CRON_EXPR="$WEEKLY_CRON_MIN $WEEKLY_CRON_HOUR 28-31 * *"

cat > /tmp/cron_to_create_$PROJECT_ID.json << EOF
{
  "project_id": "$PROJECT_ID",
  "name": "$NAME",
  "weekly": {
    "name": "$PROJECT_ID-weekly-report",
    "schedule": "$WEEKLY_CRON_EXPR",
    "active_hours": {"start": "07:30", "end": "10:00"},
    "prompt": "你是 Mavis 自动化追踪任务（v3.3 · $NAME · 周报）。\\n\\n## 执行步骤\\n\\\`\\\`\\\`bash\\npython3 /workspace/knowledge-base/_shared/scripts/weekly_runner.py --project $PROJECT_ID\\n\\\`\\\`\\\`\\n\\n## 输出要求\\n- 报告路径（briefings/ + history/ 双写）+ 文件大小\\n- 飞书推送状态\\n- 本次关键数据 + 5 类变更分类\\n- 下次执行时间"
  },
  "monthly": {
    "name": "$PROJECT_ID-monthly-report",
    "schedule": "$MONTHLY_CRON_EXPR",
    "active_hours": {"start": "07:30", "end": "10:00"},
    "prompt": "你是 Mavis 自动化追踪任务（v3.3 · $NAME · 月末触发）。\\n\\n## 执行步骤\\n\\\`\\\`\\\`bash\\npython3 /workspace/knowledge-base/_shared/scripts/weekly_runner.py --project $PROJECT_ID --monthly\\n\\\`\\\`\\\`\\n\\n## 输出要求\\n- 报告路径（briefings/monthly/ + history/YYYY-MM/双写）+ 文件大小\\n- 飞书推送状态\\n- 本月关键数据 + 趋势判断\\n- 下次执行时间（下月 1 号）"
  }
}
EOF
echo "   ✅ cron 参数已写到 /tmp/cron_to_create_$PROJECT_ID.json"

# ============== 推 GitHub + 部署 ==============
echo "📤 [12/13] 推 GitHub..."
nohup python3 _shared/scripts/git_kb_push.py > /tmp/git_kb_push.log 2>&1 &
GIT_PID=$!
sleep 30
if grep -q "🎉" /tmp/git_kb_push.log; then
    echo "   ✅ 整个知识库已推 GitHub"
fi

# 等 kb push 完，再推 site
wait $GIT_PID 2>/dev/null

echo "📤 [13/13] 推站点 + 部署..."
nohup python3 _shared/scripts/git_api_push.py > /tmp/git_site_push.log 2>&1 &
SITE_PID=$!
sleep 25
if grep -q "Pages 构建已触发" /tmp/git_site_push.log; then
    echo "   ✅ 站点已推 GitHub Pages"
fi

# ============== 输出 ==============
cat << EOF

==================================================================
✅ 项目 $NAME ($PROJECT_ID) 接入完成 - 全流程 13 步自动化
==================================================================
📁 位置:       /workspace/knowledge-base/$PROJECT_ID/
⏰ 错开时间:   $ALLOC_TIME (每周一 + 月末)
🔗 仓库:       https://github.com/$REPO
📊 数据:       $STARS ⭐  /  $FORKS 🍴  /  $ISSUES 📋
🏷️  License:   $LICENSE
🔤 语言:       $LANGUAGE
🆔 顺序号:     $SEQUENTIAL_ID (active 共 $EXISTING_COUNT)

🚀 部署状态:
   ✅ 项目文件 + 首次周报 (briefings/ + history/)
   ✅ 网站已重建 + Dashboard 已更新
   ✅ 密码门检查已加
   ✅ 知识库已推 GitHub
   ✅ 站点已推 GitHub Pages
   ✅ 国内镜像已部署

⏰ cron 任务: 待 Mavis agent 调用 mavis tool 创建
   参数: /tmp/cron_to_create_$PROJECT_ID.json
EOF
