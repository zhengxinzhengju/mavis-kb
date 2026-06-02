# Mavis 知识库 · 多项目追踪

> 9 个 GitHub 项目的自动追踪系统 · 框架 v3.3

## 仓库结构

```
mavis-kb/                      ← GitHub 仓库根（zhengxinzhengju/mavis-kb）
├── README.md                  ← 本文件
├── .gitignore
├── _shared/                   ← 跨项目共享
│   ├── scripts/               ← 自动化脚本
│   ├── templates/             ← 新项目模板
│   ├── registry.json          ← 项目注册表
│   ├── password.json          ← 站点密码配置
│   ├── dashboard.json         ← Dashboard 原始数据
│   └── _site/                 ← 静态站点（不入 Git）
├── pilotdeck/                 ← 项目 1
├── openclaw/                  ← 项目 2
├── hermes-agent/              ← 项目 3
├── deer-flow/                 ← 项目 4
├── qwenpaw/                   ← 项目 5
├── openhuman/                 ← 项目 6
├── harness/                   ← 项目 7
├── higress/                   ← 项目 8
└── picoclaw/                  ← 项目 9
```

## 每个项目结构

```
<project-id>/
├── README.md
├── profile.md
├── timeline.md
├── index.json
├── run-log.md
├── tracker-prompt.md
├── competitors/               ← 竞品分析
├── snapshots/                 ← 数据快照
├── scripts/                   ← 项目专用脚本（如有）
├── assets/                    ← 静态资源
└── history/                   ← 🆕 长期归档（Git 完整记录所有变更）
    ├── 2026/
    │   ├── 2026-05/
    │   │   ├── 2026-W18-weekly.md
    │   │   ├── 2026-W18-feishu.txt
    │   │   └── 2026-W18-snapshot.md
    │   ├── 2026-06/
    │   │   ├── 2026-W22-weekly.md
    │   │   ├── 2026-W23-weekly.md
    │   │   └── 2026-06-monthly.md
    │   └── 2026-07/
    └── 2027/...
```

## 加新项目（5 分钟）

```bash
# 1. Clone 仓库
git clone https://github.com/zhengxinzhengju/mavis-kb.git
cd mavis-kb

# 2. 复制模板
cp -r _shared/templates/new-project/ my-new-product/

# 3. 编辑配置
vim my-new-product/index.json  # 填项目元数据

# 4. 注册到 registry
vim _shared/registry.json      # 加一个项目对象

# 5. 提交 + 推送
git add . && git commit -m "feat: add my-new-product tracker"
git push

# 6. 触发首次跑（可选）
python3 _shared/scripts/weekly_runner.py --project my-new-product
```

## 自动化

| 任务 | 频率 | 调度 |
|------|------|------|
| 周报 | 每周一 08:00-09:20 | 18 个 cron 错开 10 分钟 |
| 月报 | 每月最后一天 08:00-09:20 | 同上 + `--monthly` 模式 |
| 飞书推送 | 每次周/月报 | 9 条均匀到达 |
| 站点重建 | 每次周/月报 | 自动 build + push GitHub Pages |
| Git 归档 | 每次周/月报 | history/YYYY/YYYY-MM/ |

## 访问

- 🔗 **GitHub Pages**: https://zhengxinzhengju.github.io/mavis-kb/（密码保护）
- 🔗 **国内镜像**: https://xxxx.space.minimaxi.com（密码保护）
- 🔗 **GitHub 仓库**: https://github.com/zhengxinzhengju/mavis-kb
