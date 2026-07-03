# OpenClaw 自进化 Agent MVP

让 Agent 形成闭环：收集失败样本 → 自动生成候选策略 → 离线评测 → 灰度发布 → 监控 → 自动回滚。

## 目录结构

```
openclaw-self-evolve/
├─ configs/           # 策略配置（基线/候选/活跃/护栏）
├─ data/              # 数据集（冒烟/回归/难例/标注/评测结果）
├─ prompts/           # 提示词模板（system/tools）
├─ scripts/           # 脚本（Python + PowerShell）
├─ policies/          # 路由/预算/安全策略
├─ dashboards/        # 监控指标
├─ ci/                # CI 流水线
└─ README.md
```

## 运行流程

1. `python scripts/collect_failures.py` — 从日志抓失败样本
2. `python scripts/propose_candidate.py` — 生成候选策略
3. `python scripts/run_eval.py` — 跑评测
4. `python scripts/gate_check.py` — 门禁检查
5. `powershell scripts/deploy_canary.ps1` — 灰度发布
6. `powershell scripts/promote.ps1` — 正式发布 / `rollback.ps1` — 回滚
