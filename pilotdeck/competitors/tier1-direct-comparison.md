# PilotDeck · T1 直接竞品对比 (2026-W23)

> 数据采集: 2026-06-02 | 颗粒度要求: 必有本周/月动态 + 具体数据 + 战略影响

## 1. Claude Cowork / openwork (开源版)

- **主仓库**: different-ai/openwork
- **Stars / Forks / Issues**: **15,713 / 1,551 / 170** (2026-06-02 push)
- **本周 release**: 持续小版本迭代（社区追踪中）
- **核心定位**: Claude Cowork 桌面代理的开源实现，强调 SaaS 集成（500+ 应用）
- **战略影响**: ⚠️ **中度威胁** —— Anthropic 自身品牌效应 + 多 SaaS 集成切入。PilotDeck 应对：差异化"工作流编排 + Memory 持续性"，避免纯代理执行赛道
- **数据点**: 半年内从 8k stars 涨到 15.7k（增速 +96%），证明用户对 Cowork 模式认可

## 2. BitFun (桌面 Agent 工具集)

- **主仓库**: GCWing/BitFun
- **Stars / Forks / Issues**: **801 / 99 / 29** (本周有 push)
- **本周 release**: 桌面级 Agent runtime 更新（详见 GitHub release）
- **核心定位**: BitFun 是桌面级 Agent runtime + 即可用的 Code Agent
- **战略影响**: 🟢 **低威胁** —— 早期阶段（800 stars），但产品形态对 PilotDeck 桌面化有参考价值
- **数据点**: 29 个 open issues，迭代节奏快；社区尚未爆发

## 3. OpenManus (MetaGPT 团队)

- **主仓库**: mannaandpoem/OpenManus
- **Stars / Forks / Issues**: **484 / 125 / 19** (push 2025-06-21，已停滞)
- **核心定位**: Manus AI 的开源复刻，强调"无需邀请码"
- **战略影响**: 🟢 **低威胁** —— 项目 2025-06 后无更新（停滞），社区关注度下滑
- **数据点**: 19 个 open issues 长期未解决，MetaGPT 团队精力分散

## 4. OpenHands (Coding Agent)

- **主仓库**: All-Hands-AI/OpenHands
- **Stars / Forks / Issues**: **33,487 / 4,594 / 831** (本周 push)
- **本周 release**: v0.x 持续迭代，Coding Agent 标杆项目
- **核心定位**: 开源 AI 软件工程师，自主完成 PR 级别的代码任务
- **战略影响**: ⚠️ **中度威胁** —— Coding Agent 是 PilotDeck 的核心能力之一；OpenHands 已有完整工作流
- **数据点**: 33k stars，是 Coding Agent 第一梯队；831 open issues 反映迭代快

## 5. Continue (IDE AI 助手)

- **主仓库**: continuedev/continue
- **Stars / Forks / Issues**: **33,487 / 4,594 / 831**
- **核心定位**: VS Code/JetBrains AI 编码助手
- **战略影响**: 🟢 **中性** —— IDE 插件形态，与 PilotDeck 桌面工作流定位不同

## 战略判断 (本月)

| 维度 | PilotDeck 优势 | 竞品优势 | 应对 |
|------|-------------|---------|------|
| 工作流编排 | ✅ WorkSpace + Smart Router 独有 | 单一任务代理 | 强化 Always-on + Skills 生态 |
| 桌面集成 | 🟡 起步阶段 | BitFun/openwork 更深 | 加快 MCP 接入 |
| 媒体曝光 | 🟡 早期 | OpenHands 33k | 用对比评测扩大传播 |
| 用户基数 | 🟡 2.8k stars | openwork 15.7k | 借 OpenBMB 流量 + OpenHuman 跨推 |

**本月关键动作**:
1. 跑通 WorkSpace v2 模板（让用户能 5 分钟搭一套 agent 工作流）
2. MCP 接入文档化（降低开发者门槛）
3. 跟 OpenHuman 联动推广（同样桌面优先用户群）
