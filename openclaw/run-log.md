# OpenClaw 追踪项目运行日志

> 由 Mavis 维护

---

## 2026-06-02 10:05 (Asia/Shanghai) — 初始化

**触发方**: 用户添加新项目请求

### 实施
- ✅ 创建项目目录 `/workspace/knowledge-base/projects/openclaw/`
- ✅ 写 `index.json` 注册到 `_index/projects.json`（active 状态）
- ✅ 写 `profile.md` (3.8KB) + `timeline.md` (1.6KB) + `tracker-prompt.md` (3.3KB)
- ✅ 实时拉取 GitHub API 写入 `last_github_data`
- ✅ 创建 2 个 cron 任务
  - `openclaw-weekly-report` (404572285354876) · `0 8 * * 1`
  - `openclaw-monthly-report` (404574797529385) · `0 8 28-31 * *`
- ✅ 复用 PilotDeck 的飞书推送脚本（未来提取到 `_index/scripts/`）

### OpenClaw 关键数据（首次入库）
| 指标 | 数值 |
|------|------|
| Stars | 376,081 |
| Forks | 78,545 |
| Open Issues | 7,064 |
| License | Other (NOASSERTION) |
| 语言 | TypeScript |
| Size | 1.49 GB |
| 创建 | 2025-11-24 |
| Contributors (Top 1) | steipete — 31,495 commits (70% 占比) |

### 监控重点
- 🔴 高: 安全漏洞 (CVE/ClawJacked)、release 节奏 (日均 4+)、maintainer steipete 动态
- 🟡 中: Skills 生态、新模型集成、QClaw 衍生版本
- 🟢 低: Issues 关闭率、新 contributors 增长

### 下次 cron 触发
- **2026-06-08 08:00**: 首次 W23 周报（同时为 OpenClaw 和 PilotDeck 出）
- **2026-06-28 08:00**: 首次 M06 月报窗口

### 框架升级
- ✅ 抽出 `feishu_push.py` 到共享层 `_index/scripts/`
- ✅ 创建动态生成器 `_index/scripts/build_site.py`
- ✅ 重写 `build_site.py` 为 v1.0（读 _index/projects.json 自动产出 HTML）
- ✅ 重新部署 https://esp64unzgswn.space.minimaxi.com （v1.1 双项目版）
