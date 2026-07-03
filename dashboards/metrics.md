# OpenClaw 自进化 Agent 监控指标

## 核心指标
- pass_rate: 评测通过率（目标 ≥ 0.88）
- success_delta: 相比基线的成功率提升（目标 ≥ +2%）
- latency_p95_ms: P95 延迟（目标 ≤ 9000ms）
- crash_rate: 崩溃率（目标 ≤ 0.5%）
- login_redirect_rate: 闪退到登录页比率（目标 ≤ 0.3%）
- 401_rate: 401 认证失败比率（目标 ≤ 0.3%）

## 成本指标
- daily_token_usage: 日 Token 用量
- daily_cost_usd: 日费用（美元）
- remaining_tokens: 剩余预算 Token

## 护栏指标
- gate_pass: 门禁是否通过
- rollback_count: 回滚次数
- canary_duration: 灰度持续时间
