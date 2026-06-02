#!/usr/bin/env bash
# add_project.sh
# ==============
# 一键接入新项目到 Mavis 知识库追踪系统
#
# 用法:
#   bash add_project.sh <github-org/repo> [--name "项目名"] [--tier "T1"] [--monthly "09:30"]
#
# 自动化:
#   1. 自动分配 project_id (从 11 开始顺序编号: project-11, project-12, ...)
#   2. 从 GitHub API 抓取元数据
#   3. 创建顶层目录结构 (含 history/)
#   4. 生成 README / profile / index.json
#   5. 更新 _shared/registry.json
#   6. 更新 _shared/scripts/weekly_runner.py REPO_MAP
#   7. 创建 2 个 cron 任务 (weekly + monthly)
#   8. 触发首次周报
#   9. 重建网站 + 推 GitHub
#
# 示例:
#   bash add_project.sh openai/swarm
#   bash add_project.sh openai/swarm --name "OpenAI Swarm" --tier "T1 框架"

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
        *) echo "未知参数: $1"; exit 1 ;;
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

# ============== 抓 GitHub 数据 ==============
echo "🔍 抓取 GitHub 元数据: $REPO"
REPO_DATA=$(curl -s -H "Authorization: token $GITHUB_KB_TOKEN" -m 10 "https://api.github.com/repos/$REPO")

# 检查是否 404
if echo "$REPO_DATA" | grep -q '"message": "Not Found"'; then
    echo "❌ 仓库不存在: $REPO"
    exit 1
fi

# ============== 自动分配 project_id ==============
# 读 registry 现有 active 项目数
EXISTING_COUNT=$(python3 -c "
import json
data = json.load(open('_shared/registry.json'))
print(sum(1 for p in data['projects'] if p.get('status') == 'active'))
")
NEXT_NUM=$((EXISTING_COUNT + 1))

# 自动从 repo 末尾取 slug（人类可读的名字）
SLUG=$(echo "$REPO" | awk -F'/' '{print tolower($2)}' | tr '_' '-')
# 去重检查：如果 slug 已存在，加 -2 / -3 后缀
python3 << PYEOF
import json
data = json.load(open('_shared/registry.json'))
existing = [p['id'] for p in data['projects']]
slug = "$SLUG"
n = 1
while slug in existing:
    n += 1
    slug = f"$SLUG-{n}"
print(slug)
PYEOF
FINAL_SLUG=$(python3 -c "
import json
data = json.load(open('_shared/registry.json'))
existing = [p['id'] for p in data['projects']]
slug = '$SLUG'
n = 1
while slug in existing:
    n += 1
    slug = f'$SLUG-{n}'
print(slug)
")
PROJECT_ID="$FINAL_SLUG"

echo "📝 项目顺序: #$NEXT_NUM (共 $EXISTING_COUNT 个 active 项目)"
echo "📂 分配目录: $PROJECT_ID (来自 repo 末尾自动推)"

# ============== 注册表内的顺序号 ==============
SEQUENTIAL_ID="project-$(printf "%02d" $NEXT_NUM)"
echo "🆔 顺序号: $SEQUENTIAL_ID (供参考)"

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
print(lic.get('spdx_id') if lic else '—')
")
SIZE_KB=$(echo "$REPO_DATA" | python3 -c "import json,sys; print(int(json.load(sys.stdin).get('size', 0)))")
CREATED=$(echo "$REPO_DATA" | python3 -c "import json,sys; print(json.load(sys.stdin).get('created_at', '')[:10])")
PUSHED=$(echo "$REPO_DATA" | python3 -c "import json,sys; print(json.load(sys.stdin).get('pushed_at', '')[:10])")

# 优先级名称覆盖
if [ -n "$NAME_FLAG" ]; then
    NAME="$NAME_FLAG"
fi

echo "   名称: $NAME"
echo "   描述: $DESCRIPTION"
echo "   Stars: $STARS | Forks: $FORKS | Issues: $ISSUES"
echo "   语言: $LANGUAGE | License: $LICENSE"
echo "   Size: $((SIZE_KB/1024)) MB | 创建: $CREATED | 最近 push: $PUSHED"
echo ""

# ============== 自动分配时间槽 ==============
# 读现有 stagger_strategy 找最大时间
MAX_TIME=$(python3 -c "
import json
data = json.load(open('_shared/registry.json'))
times = [g.get('time', '00:00') for g in data.get('stagger_strategy', {}).get('groups', [])]
if times:
    print(max(times))
else:
    print('08:00')
")
if [ -n "$TIME_FLAG" ]; then
    ALLOC_TIME="$TIME_FLAG"
else:
    # 解析 +10 分钟
    HOUR=$(echo $MAX_TIME | cut -d: -f1)
    MIN=$(echo $MAX_TIME | cut -d: -f2)
    NEW_MIN=$((MIN + 10))
    if [ $NEW_MIN -ge 60 ]; then
        NEW_MIN=$((NEW_MIN - 60))
        HOUR=$((HOUR + 1))
    fi
    ALLOC_TIME=$(printf "%02d:%02d" $HOUR $NEW_MIN)
fi
echo "⏰ 分配时间: $ALLOC_TIME"
echo ""

# ============== 创建目录结构 ==============
echo "📁 创建目录结构"
mkdir -p "$PROJECT_ID"/{briefings/weekly,briefings/monthly,snapshots,competitors,scripts,assets,history/2026/2026-05,history/2026/2026-06,history/2026/2026-07,history/2026/2026-08,history/2026/2026-09,history/2026/2026-10,history/2026/2026-11,history/2026/2026-12}

# ============== 生成文件 ==============
echo "📄 生成 README.md / profile.md / index.json / timeline.md / tracker-prompt.md / run-log.md"

TODAY=$(date +%Y-%m-%d)

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
| 周报 | 每周一 | 拉 GitHub API + 飞书推送 + 归档到 history/ |
| 月报 | 每月最后一天 | 同上 + 竞品对比刷新 |

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
EOF
YEAR=$(date +%Y)
sed -i "s/\$YEAR/$YEAR/g" "$PROJECT_ID/timeline.md"
cat >> "$PROJECT_ID/timeline.md" << EOF

- **$TODAY** 加入 Mavis 知识库追踪系统
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
mkdir -p "$PROJECT_ID/history"
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

# competitors/.gitkeep
cat > "$PROJECT_ID/competitors/.gitkeep" << EOF
# 竞品对比文件放这里
# 命名建议: tier1-direct-comparison.md / tier2-frameworks-comparison.md
EOF

# snapshots/.gitkeep
cat > "$PROJECT_ID/snapshots/.gitkeep" << EOF
# 数据快照放这里
EOF

# assets/.gitkeep
cat > "$PROJECT_ID/assets/.gitkeep" << EOF
# 静态资源放这里
EOF

# scripts/.gitkeep
cat > "$PROJECT_ID/scripts/.gitkeep" << EOF
# 项目专用脚本放这里
EOF

echo "✅ 9 个文件已生成"
echo ""

# ============== 更新 REPO_MAP ==============
echo "🔧 更新 _shared/scripts/weekly_runner.py REPO_MAP"
python3 << PYEOF
from pathlib import Path
p = Path("_shared/scripts/weekly_runner.py")
content = p.read_text(encoding="utf-8")
old = '''REPO_MAP = {'''
new = f'''REPO_MAP = {{
    "$PROJECT_ID":        "$REPO",'''
if old in content and "\"$PROJECT_ID\"" not in content:
    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")
    print("   ✅ REPO_MAP 加 $PROJECT_ID")
else:
    print("   ℹ️  REPO_MAP 已存在或找不到锚点")
PYEOF

# ============== 更新 registry.json ==============
echo "🔧 更新 _shared/registry.json"
python3 << PYEOF
import json
from pathlib import Path
p = Path("_shared/registry.json")
data = json.loads(p.read_text(encoding="utf-8"))

# 防重复
existing_ids = [proj.get('id') for proj in data['projects']]
if "$PROJECT_ID" not in existing_ids:
    data['projects'].append({
        "id": "$PROJECT_ID",
        "name": "$NAME",
        "status": "active",
        "tracking_since": "$TODAY",
        "stagger_time": "$ALLOC_TIME",
        "tier": "$TIER_FLAG",
        "github_repo": "https://github.com/$REPO",
        "feishu_webhook_configured": False,
        "cron_task_ids": {}
    })
    # stagger
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

# ============== 创建 2 个 cron ==============
echo "⏰ 创建 cron 任务 (weekly + monthly)"
WEEKLY_CRON_MIN=$(echo $ALLOC_TIME | awk -F: '{print $2}')
WEEKLY_CRON_HOUR=$(echo $ALLOC_TIME | awk -F: '{print $1}')
WEEKLY_CRON_EXPR="$WEEKLY_CRON_MIN $WEEKLY_CRON_HOUR * * 1"
MONTHLY_CRON_EXPR="$WEEKLY_CRON_MIN $WEEKLY_CRON_HOUR 28-31 * *"

WEEKLY_PROMPT="你是 Mavis 自动化追踪任务（v3.3 新路径 · $NAME）。

## 执行步骤
\`\`\`bash
python3 /workspace/knowledge-base/_shared/scripts/weekly_runner.py --project $PROJECT_ID
\`\`\`

## 输出要求
- 报告路径（briefings/ + history/ 双写）+ 文件大小
- 飞书推送状态
- 本次关键数据 + 5 类变更分类
- 下次执行时间"

MONTHLY_PROMPT="你是 Mavis 自动化追踪任务（v3.3 · $NAME · 月末触发）。

## 执行步骤
\`\`\`bash
python3 /workspace/knowledge-base/_shared/scripts/weekly_runner.py --project $PROJECT_ID --monthly
\`\`\`

## 输出要求
- 报告路径（briefings/monthly/ + history/YYYY-MM/双写）+ 文件大小
- 飞书推送状态
- 本月关键数据 + 趋势判断
- 下次执行时间（下月 1 号）"

# 用 mavis 工具
echo "   调用 mavis cron create..."
echo "   (需要 mavis 工具支持，请人工执行)"

# 改为写到 cron_prompts 让用户后续处理
cat > /tmp/cron_to_create.json << EOF
{
  "weekly": {
    "name": "$PROJECT_ID-weekly-report",
    "schedule": "$WEEKLY_CRON_EXPR",
    "prompt": $(echo "$WEEKLY_PROMPT" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))")
  },
  "monthly": {
    "name": "$PROJECT_ID-monthly-report",
    "schedule": "$MONTHLY_CRON_EXPR",
    "prompt": $(echo "$MONTHLY_PROMPT" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))")
  }
}
EOF
cat /tmp/cron_to_create.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'   准备创建: {data[\"weekly\"][\"name\"]} ({data[\"weekly\"][\"schedule\"]})')
print(f'   准备创建: {data[\"monthly\"][\"name\"]} ({data[\"monthly\"][\"schedule\"]})')
"

# ============== 跑首次周报 ==============
echo ""
echo "📊 触发首次周报..."
nohup python3 _shared/scripts/weekly_runner.py --project $PROJECT_ID --no-push --no-rebuild > /tmp/${PROJECT_ID}_init.log 2>&1 &
sleep 10
tail -10 /tmp/${PROJECT_ID}_init.log

# ============== 重新 build site ==============
echo ""
echo "🌐 重新生成网站..."
nohup python3 _shared/scripts/build_site.py > /tmp/site_build.log 2>&1 &
sleep 12
tail -3 /tmp/site_build.log

# ============== 完成 ==============
echo ""
echo "=========================================="
echo "✅ 项目 $NAME ($PROJECT_ID) 接入完成"
echo "=========================================="
echo "📁 位置: /workspace/knowledge-base/$PROJECT_ID/"
echo "⏰ 错开时间: $ALLOC_TIME (每周一)"
echo "🔗 仓库: https://github.com/$REPO"
echo "📊 Stars: $STARS | Forks: $FORKS"
echo ""
echo "⚠️  待人工完成:"
echo "  1. mavis 工具调用创建 2 个 cron 任务 (见 /tmp/cron_to_create.json)"
echo "  2. (可选) 编辑 $PROJECT_ID/profile.md 加更详细介绍"
echo "  3. (可选) 在 $PROJECT_ID/competitors/ 加竞品分析"
echo "  4. (可选) git add . && git commit && git push"
echo "  5. 部署新站点: website_deploy /workspace/output/pilotdeck-site"
