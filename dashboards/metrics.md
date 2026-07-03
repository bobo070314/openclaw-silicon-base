# 📊 硅基体集团 · 部门成本看板

## 今日消耗（评测报告自动更新）

| 部门 | Token 消耗 | 占比 | 预算状态 |
|------|-----------|------|----------|
| 🧑‍💻 Coding | `{{cost_by_role.coder}}` | `{{pct_coder}}%` | ✅ |
| 🔧 Fixer | `{{cost_by_role.fixer}}` | `{{pct_fixer}}%` | ✅ |
| 💬 Chat | `{{cost_by_role.chat}}` | `{{pct_chat}}%` | ✅ |
| 🗂 Other | `{{cost_by_role.other}}` | `{{pct_other}}%` | ✅ |
| **合计** | **`{{total_tokens}}`** | **100%** | **`{{usage_pct}}%` 已用** |

## 预算配置

| 部门 | 日预算（Token） | 月估算（USD） | 告警阈值 |
|------|----------------|--------------|-----------|
| Coding | 50,000 | $3.00 | 80% |
| Fixer | 30,000 | $1.80 | 80% |
| Chat | 10,000 | $0.60 | 90% |
| **总预算** | **50,000** | **$3.00** | **80%** |

## 核心门禁指标

| 指标 | 当前值 | 阈值 | 状态 |
|------|--------|------|------|
| pass_rate | `{{pass_rate}}` | >= 0.88 | - |
| login_redirect_rate | `{{login_redirect_rate}}` | <= 0.003 | - |
| crash_rate | `{{crash_rate}}` | <= 0.005 | - |
| p95_latency_ms | `{{p95_latency_ms}}` | <= 9000ms | - |

## 说明
- Token 数据来自 `data/runs/latest_eval.json` 的 `cost_breakdown` 字段
- 预算从环境变量 `COST_BUDGET_DAILY` 读取（默认 50000）
- 当前为模拟数据，对接真实 OpenClaw API 后自动替换
