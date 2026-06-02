# PilotDeck · T2 框架层竞品对比 (2026-W23)

## 1. LangChain (138k stars, T2 龙头)

- **主仓库**: langchain-ai/langchain
- **Stars / Forks / Issues**: **138,270 / 22,917 / 606** (本周 push)
- **本周 release**: LangChain v0.3+ 持续，LCEL (LangChain Expression Language) 成熟
- **核心定位**: LLM 应用编排框架，Python + TypeScript 双栈
- **战略影响**: 🟡 **中性偏威胁** —— LangChain 已是事实标准，PilotDeck 不在编排赛道正面竞争
- **机会**: 把 LangChain 作为 PilotDeck 的 Skill 后端（兼容 LCEL）
- **数据点**: 22.9k forks，生态规模最大；606 open issues 质量高

## 2. AutoGen (Microsoft 58k stars)

- **主仓库**: microsoft/autogen
- **Stars / Forks / Issues**: **58,623 / 8,855 / 876** (push 2026-04-15)
- **本周 release**: AutoGen v0.4+ 推 Actor Model 架构
- **核心定位**: 多 Agent 编排（微软背书）
- **战略影响**: 🟡 **中度威胁** —— AutoGen 正在主推 v0.4 重构
- **数据点**: push 时间 2026-04-15（**近 1.5 个月无新 push**），可能 v0.4 仍在内部打磨

## 3. CrewAI (52k stars)

- **主仓库**: crewAIInc/crewAI
- **Stars / Forks / Issues**: **52,635 / 7,340 / 383** (本周 push)
- **本周 release**: CrewAI v0.80+ 持续小步快跑
- **核心定位**: Role-based Multi-Agent 框架，定位"团队"概念
- **战略影响**: ⚠️ **中度威胁** —— 增长快（半年 +60%），营销强
- **机会**: PilotDeck 借 Smart Router 强调"动态角色"区别于 CrewAI 静态 Role

## 4. smolagents (HuggingFace 27k stars)

- **主仓库**: huggingface/smolagents
- **Stars / Forks / Issues**: **27,657 / 2,632 / 570** (push 2026-05-29)
- **核心定位**: HF 出品的极简 Agent 框架
- **战略影响**: 🟢 **低威胁** —— 学术/极客圈为主，定位轻量

## 5. Aider (45k stars, Coding Agent)

- **主仓库**: Aider-AI/aider
- **Stars / Forks / Issues**: **45,659 / 4,528 / 1,590** (push 2026-05-22)
- **本周 release**: 持续更新
- **核心定位**: 命令行 Coding Agent，对标 Cursor / Copilot
- **战略影响**: 🟡 **中性** —— Coding Agent 赛道细分

## T2 战略判断

| 维度 | PilotDeck 战略 | 建议 |
|------|-------------|------|
| 不与 LangChain/AutoGen 正面竞争 | ✅ 已在做 | 持续 |
| 借 CrewAI 增长推动市场教育 | ✅ 关注中 | 持续 |
| 兼容主流框架 | 🟡 待规划 | **Q3 推出 LangChain Skill 桥接** |
| Coding Agent 能力 | 🟡 自研 | 评估集成 Continue/Aider |
