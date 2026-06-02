# _shared · 跨项目共享

> 这部分是跨项目共享的脚本、模板、配置。新项目不要在这里建文件，建在根目录的 `<project-id>/` 下。

## 子目录

- `scripts/` — 跨项目可执行脚本（weekly_runner / build_dashboard / feishu_push / git_api_push / build_password_gate）
- `templates/new-project/` — 新项目模板（README + profile + index.json + tracker-prompt + history 目录结构）
- `_site/` — 生成的静态站点（**不入 Git**，仅本地预览用，部署走 `_site/` → GitHub Pages）
- `password.json` — 站点访问密码
- `registry.json` — 项目注册表（v3.3 升级版）
- `dashboard.json` — Dashboard 统计原始数据
