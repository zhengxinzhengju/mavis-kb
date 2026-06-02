# HiClaw · 项目档案

> 数据采集: 2026-06-02 | 框架版本: v3.3

## 基本信息

- **项目**: HiClaw
- **主仓库**: https://github.com/agentscope-ai/HiClaw
- **所属组织**: AgentScope（阿里）
- **Stars**: 4,716
- **Forks**: 567
- **Open Issues**: 255
- **License**: Apache-2.0
- **主语言**: Go
- **大小**: 15.0 MB
- **最近 push**: 2026-06-02
- **创建于**: 2026-02-21

## 定位

> "An open-source Collaborative Multi-Agent OS for transparent, human-in-the-loop task coordination via Matrix rooms."

HiClaw 是阿里 AgentScope 团队 2026-02 推出的**协作多 Agent 操作系统**，核心是基于 **Matrix 协议**（去中心化即时通讯协议）实现：

- **透明的多 Agent 协作** — 所有 Agent 通信经 Matrix rooms 路由
- **Human-in-the-loop** — 人类可观察、介入、调整 Agent 协作
- **任务协调** — 多个 Agent 共同完成复杂工作流

## 与 QwenPaw 的关系

| 维度 | QwenPaw | HiClaw |
|------|---------|--------|
| 形态 | 桌面 Agent 平台 | 多 Agent 操作系统 |
| 模型 | Qwen 系列 | 任意 LLM |
| 协作 | 单 Agent + Skills | 多 Agent + Matrix 协议 |
| 协议 | 自有 IM | Matrix（开放） |
| 交互 | GUI | Rooms + 人机协作 |

## 核心能力

- Matrix 协议集成（rooms / events / E2EE）
- 多 Agent 任务分发与协调
- 透明审计（人可观察 Agent 通信）
- Go 编写的高性能 runtime
- Apache-2.0 友好开源协议

## 风险与机会

- **机会**: Matrix 协议 = 跨平台 Agent 互操作基础
- **风险**: 4716 stars 早期阶段
- **协同**: 与 QwenPaw 共享 AgentScope 生态

## 追踪建议

- **监控周频**: star 增量 + commit 节奏 + Matrix 集成深度
- **关键事件**: v1.0 / 跨项目互操作 demo / QwenPaw 联动
