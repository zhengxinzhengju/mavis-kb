# Hermes Agent 重大事件时间线

> 按时间倒序。最后更新：2026-06-02
> 初次入库：Mavis bulk_init

---

### 2026-06-02 | 首次入库
**摘要**: 项目加入多项目追踪框架
**影响**: 关键
**详情**:
- 由用户手动添加
- 创建 index.json + profile.md + timeline.md + tracker-prompt.md
- 实时拉取 GitHub API 数据
- 已注册到 _index/projects.json
- 飞书推送配置完毕（复用 PilotDeck 的 webhook）
- 创建 2 个 cron 任务（周报 + 月报）
**来源**: Mavis + GitHub API

（更多事件由后续 cron 任务自动追加）
