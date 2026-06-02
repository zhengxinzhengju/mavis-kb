# HiClaw · Tracker 提示词

> 每周一 cron 自动执行的标准 tracker 流程

## 1. 读配置
- `_shared/registry.json` 确认本项目 active
- `hiclaw/index.json` 确认配置

## 2. 拉数据
```bash
curl -s -H "Authorization: token $GITHUB_KB_TOKEN" -m 10 \
  https://api.github.com/repos/agentscope-ai/HiClaw
```

## 3. 写报告
- 完整版: `briefings/weekly/YYYY-Wnn.md`
- 飞书版: `briefings/weekly/YYYY-Wnn-feishu.txt`
- 归档: `history/YYYY/YYYY-MM/`

## 4. 飞书推送
- 读 `index.json` 的 feishu 配置
- 调用 `_shared/scripts/feishu_push.py`

## 5. 站点重建 + GitHub 同步
- `_shared/scripts/build_site.py`
- `_shared/scripts/git_kb_push.py`
