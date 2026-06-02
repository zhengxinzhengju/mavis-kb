# 快速接入 {PROJECT_NAME}

## 1. 改 index.json

填入项目元数据（id / name / github_repo / key_features / tracking.feishu）

## 2. 改 profile.md

一句话定位 + 核心能力列表

## 3. 注册到 _shared/registry.json

加一个项目对象到 projects 数组

## 4. 提交 + 推送

```bash
git add .
git commit -m "feat: add {project_id} tracker"
git push
```

## 5. 触发首次跑

```bash
python3 _shared/scripts/weekly_runner.py --project {project_id}
```

## 6. 验证

- 网站: https://zhengxinzhengju.github.io/mavis-kb/project-{project_id}.html
- 飞书: 收到 1 条推送
- Git: history/2026/2026-06/2026-Wxx-weekly.md 出现
