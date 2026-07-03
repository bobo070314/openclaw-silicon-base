# OpenClaw 自进化 Agent MVP

让 Agent 形成闭环：收集失败样本 → 自动生成候选策略 → 离线评测 → 灰度发布 → 监控 → 自动回滚。

## 目录结构

```
openclaw-self-evolve/
├─ configs/           # 策略配置（基线/候选/活跃/护栏）
├─ data/              # 数据集（冒烟/回归/难例/标注/评测结果）
├─ prompts/           # 提示词模板（system/tools）
├─ scripts/           # 脚本（Python + PowerShell，零 bash 依赖）
├─ policies/          # 路由/预算/安全策略
├─ dashboards/        # 监控指标
├─ ci/                # CI 流水线
└─ README.md
```

## 运行流程

1. `python scripts/collect_failures.py` — 从日志抓失败样本
2. `python scripts/propose_candidate.py` — 生成候选策略
3. `python scripts/run_eval.py` — 跑评测（mock_agent 模拟 Agent 行为）
4. `python scripts/gate_check.py` — 门禁检查（对比 guardrails.yaml 阈值）
5. `powershell scripts/deploy_canary.ps1` — 灰度发布
6. `powershell scripts/promote.ps1` — 正式发布 / `rollback.ps1` — 回滚

## 一键全链路

```powershell
# 从当前目录执行
.\scripts\run_all.ps1

# 会依次执行：
# 备份配置 → 故障注入(401/超时/工具失败) → 故障演练 → 评测 → 门禁检查
```

## 首次全链路验证结果（2026-07-03）

```
Run ID: 2026-07-03T21:06:09Z
Tag:    mvp-v1-gate-verified

Steps:
  [1/5] Backup config          → OK
  [2/5] Fault injection (3)    → OK
  [3/5] Fault drill + accept   → OK
  [4/5] Evaluation             → OK (3/3 failed under injected faults)
  [5/5] Gate check             → FAIL (expected - protection active)

Key metrics:
  pass_rate:          0.0       (threshold >= 0.88)   → BLOCKED
  login_redirect_rate: 0.3333   (threshold <= 0.003)  → BLOCKED
  crash_rate:         1.0       (threshold <= 0.005)  → BLOCKED
  p95_latency_ms:     0.0       (threshold <= 9000)   → PASSED

Verdict: MVP functional. Gate FAIL = protection wall is working.
         Without injected faults, normal config passes all gates.
```

## 环境要求

- Windows PowerShell 5.1+
- Python 3.11+
- pyyaml (`pip install pyyaml`)
- 无需 bash / WSL
