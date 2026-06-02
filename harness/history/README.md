# Harness · 长期历史归档

> 这部分按月归档所有周报、月报、快照、关键事件。Git 完整记录所有变更历史。

## 目录结构

```
history/
├── 2026/                          ← 年
│   ├── 2026-05/                   ← 月
│   │   ├── 2026-W18-weekly.md
│   │   ├── 2026-W18-feishu.txt
│   │   └── 2026-W18-snapshot.md
│   ├── 2026-06/
│   │   ├── 2026-W22-weekly.md
│   │   ├── 2026-W22-feishu.txt
│   │   └── 2026-06-monthly.md
│   └── 2026-07/
└── 2027/
```

## 文件命名规范

- `<YYYY-Wnn>-weekly.md` - 周报完整版
- `<YYYY-Wnn>-feishu.txt` - 飞书推送版
- `<YYYY-Wnn>-snapshot.md` - 数据快照
- `<YYYY-MM>-monthly.md` - 月报完整版（仅月末生成）

## 自动化

weekly_runner.py 每次跑周报/月报时自动归档到对应月份目录。

```bash
python3 _shared/scripts/weekly_runner.py --project harness
```
