# PilotDeck 追踪任务运行日志

> 记录每次 cron 触发的执行情况。
> 由 Mavis 自动化写入。

---

## 2026-06-01 17:43 (Asia/Shanghai) — 首次手动跑通

**触发方**: 用户手动要求（绕过 cron 直接执行完整 tracker 流程）

### 采集
- ✅ GitHub REST API: 成功（timeout 内）
- ✅ web_search: 成功
- ⚠️ web_fetch GitHub HTML: timeout（已 fallback 到 API）

### 写入
- ✅ `index.json` (updated, 加入 cron_task_id 和 last_run)
- ✅ `profile.md` (重写，4657 → 7011 bytes，加入 8 个 contributor 数据 + 架构目录)
- ✅ `timeline.md` (重写，834 → 3580 bytes，加入 8 个事件节点)
- ✅ `snapshots/2026-06-01.md` (新建，3451 bytes，完整 baseline)
- ✅ `competitors/tier1-direct-comparison.md` (初版)
- ✅ `competitors/tier2-frameworks-comparison.md` (初版)
- ✅ `templates/weekly-report.md` (新建)
- ✅ `templates/monthly-report.md` (新建)
- ✅ `scripts/feishu_push.py` (新建，3 种退出码 0/2/3)
- ✅ `tracker-prompt.md` (新建)
- ✅ `briefings/weekly/2026-W22.md` (新建，4853 bytes)
- ✅ `briefings/weekly/2026-W22-feishu.txt` (新建，1436 bytes)

### Cron 任务创建
- ✅ `pilotdeck-weekly-report` (task_id: 404484915970695)
  - 调度: `0 8 * * 1` (每周一 08:00 Asia/Shanghai)
  - 活跃窗口: 07:30-09:00
  - 下次执行: 下周一 08:00
- ✅ `pilotdeck-monthly-report` (task_id: 404483081200139)
  - 调度: `0 8 28-31 * *` (每月 28-31 日 08:00 Asia/Shanghai，prompt 内判断是否最后一天)
  - 活跃窗口: 07:30-09:00
  - 下次执行: 6/28 08:00（届时会判断是否月末）

### 推送
- ⏭️ **跳过** — webhook_url 为空（用户飞书移动端未找到自定义机器人配置入口）
- 退出码: 3 (skipped, 正常)

---

## 2026-06-01 17:53 (Asia/Shanghai) — 飞书推送联通验证

**触发方**: 用户提供 Webhook URL + Secret 后手动验证

### 修复
- 🐛 修正 `feishu_push.py`: 签名 timestamp + sign 必须放在 payload **顶层**，不能塞在 card 内
- 测试失败 3 次后定位到问题

### 推送
- ✅ W22 简版周报已成功推送到飞书群
- API 返回: `{"code": 0, "msg": "success"}`
- 退出码: 0

### 后续
- `index.json` 已更新 webhook_url + secret
- `feishu_configured: true`
- cron 任务下次（2026-06-08 周一 08:00）将自动推送

---

## 2026-06-01 18:05 (Asia/Shanghai) — 竞品分析深度化 + 默认规则确立

**触发方**: 用户反馈 + 手动重写

### 用户明说的两条默认规则（已写入 user memory）
1. 所有产出默认同时做两件事：**贴到对话里** + **存到 Drive**
2. 竞品分析不能简陋，必须有数据 + 启示

### 文件更新
- ✅ `competitors/tier1-direct-comparison.md` — 从 3.4KB 重写为 ~16KB
  - 覆盖 7 个产品（Claude Cowork / Skywork / BitFun / OpenClaw / QoderWork / MiniMax / 阶跃）
  - 每个 T1 都有"对 PilotDeck 的启示"
  - 增加 12 维战略对比矩阵
- ✅ `competitors/tier2-frameworks-comparison.md` — 更新
- ✅ `briefings/weekly/2026-W22.md` — 完整版重写，竞品从 4 行扩到 5 大节
- ✅ `briefings/weekly/2026-W22-feishu.txt` — 飞书版重写
- ✅ `templates/weekly-report.md` — 加入"竞品必须详细"硬性要求
- ✅ `tracker-prompt.md` — 加入竞品详细度规则 + 内容产出规范

### 推送
- ✅ 更新版 W22 简版周报重新推送到飞书群
- API 返回: `{"code": 0, "msg": "success"}`

### 用户体验
- 完整版周报 + 飞书简版都贴到对话里
- 用 deliver-assets 包装让用户能下载

---

## 2026-06-02 09:10 (Asia/Shanghai) — 文件管理重构（用户反馈：根目录平铺问题）

**触发方**: 用户反馈"文件管理有问题，应建立文件夹分门别类存储"

### 问题诊断
- Drive 工具**没有 create_folder 命令**（系统限制）
- 之前用 `<deliver-assets>` 上传的文件全部平铺在 `session_404453968618295/` 根目录
- 8 个文件没有业务分类、名称相似（`profile.md`, `weekly-report.md` 等都是通用名）

### 采取的措施
1. **重命名 8 个现有 Drive 文件**——采用 `[PilotDeck] NN-类别_名称.ext` 约定
   - 01-档案_profile.md
   - 02-周报_2026-W22.md / 02-周报_2026-W22-feishu.txt
   - 03-竞品_T1直接对标.md / 03-竞品_T2框架层.md
   - 04-模板_周报.md
   - 05-配置_追踪prompt.md
   - 06-日志_运行.md
2. **打包 zip** — `pilotdeck-knowledge-base.zip` (36KB, 22 文件) 在工作空间
3. **部署 HTML 索引页** — https://v8its98x502v.space.minimaxi.com
   - 左侧 6 大分类导航
   - 右侧文档预览
   - 嵌入 zip 下载链接
   - 自包含 CSS（无外部依赖）

### 未来文件命名规范
- `<项目名>_<文档类别>_<日期>_<版本>.ext`
- 例：`PilotDeck_weekly-report_2026-W23_v1.md`、`PilotDeck_competitor_tier1_2026-06.md`
- 所有文件带 `PilotDeck_` 前缀，跟其他项目区分

### 待优化（下次处理）
- 如果 mavis 系统未来提供 create_folder 命令，立刻迁移到「项目文件夹/类别文件夹/文件」三层结构
- 手动 cron 任务生成的快照/月报也要按新规范命名
- 考虑为多个项目（不只是 PilotDeck）采用统一的命名空间

### 下次执行
- **周报**: 2026-06-08 08:00 (周一)
- **月报**: 2026-06-28 08:00 (判断是否 6/30 触发)

### 待用户确认
1. 飞书自定义机器人 Webhook URL（PC 端配置后回填）
2. 是否切换其他渠道（Server酱 / PushPlus / 企业微信 / 邮件）
3. 月报首次执行：6/30 当天跑（届时会生成 6 月完整月报）

---

（后续 cron 自动触发记录会追加到此文件）


---

## 2026-06-02 09:30 (Asia/Shanghai) — 多项目框架升级 v1.0

**触发方**: 用户反馈"还有别的产品和github项目需要追踪，要整体设计健壮"

### 升级动机
- 单项目结构不适多项目追踪
- 需要共享竞品池、模板
- 需要零迁移成本加新项目
- 现有 session 文件夹平铺问题需从根本上解决

### 新架构 v1.0
```
/workspace/knowledge-base/
├── _index/                  # 跨项目共享层
│   ├── projects.json       # 项目注册表（cron 读这个）
│   └── README.md
├── projects/
│   ├── _template/          # 新项目模板
│   ├── pilotdeck/          # 迁移后的项目 1
│   └── <future>/
└── _site/                  # 浏览器端多项目聚合页
```

### 实施动作
- ✅ 创建 _index/、projects/_template/ 目录
- ✅ PilotDeck 从 `knowledge-base/pilotdeck/` 迁移到 `knowledge-base/projects/pilotdeck/`
- ✅ index.json 更新加 $schema、framework_v1_compliance 字段
- ✅ tracker-prompt.md 重写为 v1.1，适配新路径
- ✅ 两个 cron 任务的 prompt 字段全部更新（用 cron update）
- ✅ Drive 根文件夹 rename 为「📚 Mavis 知识库根目录」
- ✅ 重新打包知识库 zip（44KB, 18 文件）
- ✅ 重新部署知识库浏览器（新 URL: https://gwaz3sc1qrnw.space.minimaxi.com）

### Drive 命名约定
```
[<project-id>] {NN}-{category}_{name}_{date}_{version}.{ext}
例: [PilotDeck] 02-周报_2026-W22.md
例: [PilotDeck] 02-周报_2026-W22-feishu.txt
例: [NewProject] 01-档案_2026-07-01.md
```

### 加新项目工作流
1. `cp -r projects/_template/ projects/<new-id>/`
2. 填 projects/<new-id>/index.json
3. 在 _index/projects.json 注册
4. (可选) 创建 cron 任务
5. 重新部署 _site/ 浏览器

### 下次 cron 触发预期
- **2026-06-08 08:00**: W23 周报自动生成、推送飞书、上传 Drive（按新命名约定）


---

## 2026-06-02 10:05 (Asia/Shanghai) — 框架升级 v1.1：OpenClaw 加入 + 动态生成器

**触发方**: 用户添加新项目 + 动态生成器需求

### OpenClaw 加入
- ✅ 真实数据：376,081 stars (史上最高 Star 软件项目，超越 React)
- ✅ 完整项目目录 + 2 个 cron 任务
- ✅ 复用 PilotDeck 飞书推送脚本

### 动态生成器 v1.0
- ✅ 创建 `_index/scripts/build_site.py` (25KB)
- ✅ 读 `_index/projects.json` 自动产出 HTML
- ✅ 项目卡显示实时 GitHub 数据（last_github_data 字段）
- ✅ 共享竞品池从 `_index/projects.json#competitors_shared` 读
- ✅ 命令: `python3 _index/scripts/build_site.py [--no-zip] [--no-deploy]`

### 共享层整理
- ✅ `_index/scripts/feishu_push.py` 共享版（所有项目可调用）
- ✅ 原始 `projects/pilotdeck/scripts/feishu_push.py` 保留（向后兼容）

### 部署
- 新 URL: https://esp64unzgswn.space.minimaxi.com
- 包含 5 个文件：
  - index.html (10.9KB) - 多项目总览
  - project-pilotdeck.html (9.2KB) - PilotDeck 详情
  - project-openclaw.html (9.3KB) - OpenClaw 详情
  - knowledge-base.zip (60KB) - 完整下载

### Cron 任务（共 4 个）
- pilotdeck-weekly-report · pilotdeck-monthly-report
- openclaw-weekly-report · openclaw-monthly-report
- 下次触发: 2026-06-08 08:00 (周一) — 4 个项目同时跑（实际是 2 个周报 + 2 个检查）


---

## 2026-06-02 10:30 (Asia/Shanghai) — 框架升级 v1.2：批量 7 个项目加入

**触发方**: 用户一次性给 7 个 GitHub 仓库

### 新增项目（7 个）
1. **deer-flow** (bytedance) - 70k stars - SuperAgent Framework
2. **qwenpaw** (agentscope-ai) - 17k stars - 阿里 CoPaw 改名
3. **hermes-agent** (NousResearch) - 176k stars - 自我进化 Agent
4. **harness** (harness) - 36k stars - DevOps 平台
5. **openhuman** (tinyhumansai) - 30k stars - 桌面 AI 助手
6. **picoclaw** (sipeed) - 29k stars - 10 美元 RISC-V Agent
7. **higress** (higress-group) - 8.5k stars - 云原生网关

### 总计
- 9 个 active 项目
- 18 个 cron 任务
- 60 个知识库文件
- 360K 总数据

### Cron 任务（18 个）
- 9 × weekly (`0 8 * * 1`)
- 9 × monthly (`0 8 28-31 * *`)

### 下次触发
- **2026-06-08 08:00 (周一)**: 9 个项目同时出 W23 周报
- **2026-06-28 08:00**: 9 个项目月报窗口

### 部署
- 新 URL: https://qtychket9ykx.space.minimaxi.com
- 12 个文件（含 9 个 project-*.html）



---

## 2026-06-02 10:40 (Asia/Shanghai) — 框架 v1.3：错开调度

**触发方**: 用户反馈"18 个 cron 同时执行有问题"

### 修复
- 16 个 cron 任务 schedule 错开（保留 PilotDeck 2 个 8:00 起点）
- 18 个 cron 任务 active_hours 扩到 07:30-10:00
- `_index/projects.json` 升级 v1.3，加 `stagger_strategy` 段
- `build_site.py` 升级，HTML 显示新时间表
- 重新部署 https://qff9zpg1roxn.space.minimaxi.com

### 新时间表（错开 10 分钟）

| 时间 | 项目 | 分组 |
|------|------|------|
| 08:00 | PilotDeck | T0 主项目 |
| 08:10 | OpenClaw | T1 媒体焦点 |
| 08:20 | Hermes Agent | T1 对标 |
| 08:30 | DeerFlow | T1 字节 |
| 08:40 | QwenPaw | T1 阿里 |
| 08:50 | OpenHuman | T1 Desktop |
| 09:00 | Harness | T2 DevOps |
| 09:10 | Higress | T2 AI Gateway |
| 09:20 | PicoClaw | T2 Edge AI |

### 收益
- ✅ 资源不再争抢（每时刻最多 1 个 session）
- ✅ GitHub API 不再撞 rate limit
- ✅ 飞书消息按时间均匀到达（10 分钟 1 条）
- ✅ 早上一杯咖啡 + 通勤 全看完（08:00-09:20）
- ✅ 月末月报不拖到中午
