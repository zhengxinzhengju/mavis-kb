# OpenHuman · 知识库

> 本目录为 Mavis 多项目追踪系统的 OpenHuman 子项目结构

## 目录结构

```
openhuman/
├── index.json         # 项目元数据 (id, name, github_repo, key_features, ...)
├── profile.md         # 项目档案（核心能力、本周信号、竞品位置）
├── timeline.md        # 重大事件时间线
├── run-log.md         # 运行日志（tracker 执行历史）
├── tracker-prompt.md  # tracker 提示词（cron 任务用的标准 prompt）
├── README.md          # 本文件
├── briefings/
│   ├── weekly/        # 周报（每周一生成）
│   └── monthly/       # 月报（每月最后一天生成）
├── snapshots/         # 每日数据快照
├── competitors/       # 竞品分析（T1/T2 对比）
├── templates/         # 项目专用模板（如有）
├── scripts/           # 项目专用脚本（如有）
└── assets/            # 静态资源（图片、PDF 等）
```

## 自动化

| 任务 | 频率 | 时间（Asia/Shanghai） | 说明 |
|------|------|---------------------|------|
| 周报 | 每周一 | 错开调度 | 拉 GitHub API + 飞书推送 + 网站重建 |
| 月报 | 每月最后一天 | 错开调度 | 同上 + 竞品对比刷新 |
| 快照 | 每次周报/月报 | - | 写入 `snapshots/YYYY-MM-DD.md` |

## 数据来源

- GitHub API（已认证 token，rate limit 5000/h）
- web_search（媒体提及）
- 人工录入（重要事件、战略判断）

## 如何手动跑

```bash
# 单项目
python3 /workspace/knowledge-base/_index/scripts/weekly_runner.py --project openhuman

# 批量跑全部
python3 /workspace/knowledge-base/_index/scripts/weekly_runner.py --all

# 重新生成网站
python3 /workspace/knowledge-base/_index/scripts/build_site.py

# 推送到 GitHub
python3 /workspace/knowledge-base/_index/scripts/git_api_push.py
```

## 数据可访问性

- 本地: `/workspace/knowledge-base/projects/openhuman/`
- Drive: 通过 weekly_runner 上传 deliver-assets
- 飞书: 每周一推送（项目配置 feishu.webhook_url 后）
- 网站: https://zhengxinzhengju.github.io/mavis-kb/（需密码 chinaunicom10010）

## 最近一次更新

2026-06-02 06:49 CST (Mavis 自动追踪 v3.1)
