# 7.15 合规证据包 — 硅基体自修复 + 日志压缩

**打包时间**: 2026-07-04 17:10 UTC  
**git HEAD**: `d3aeb48` (silicon-body-fixer) / `21318e1` (workspace)  
**仓库地址**: `github.com/bobo070314/openclaw-silicon-base`

---

## 1. 核心协议 — 自修复规范

| 文件 | 说明 |
|---|---|
| `docs/specs/AUTO_FIXER_PROTOCOL_v1.md` | 修复协议 v1 — fault input spec / repair strategy / rollback contract |
| `docs/specs/v2.0_fault_request_template_hoshine.yaml` | 合盛产线故障格式示例 |

## 2. 日志压缩 — Headroom 集成

| 文件 | 说明 |
|---|---|
| `external/headroom` (submodule) | Headroom v0.5.20-1395 — 开源 LLM 优化层 |
| `src/integrations/headroom_adapter.py` | 适配器 — `USE_HEADROOM=true` 环境变量控制 |
| `src/core/apply_repair.py` | 修复引擎（输入消毒 + 路径隔离） |
| `docs/hoshine_mes_poc_report.md` | 合盛 MES POC 对接报告 |

**压缩能力说明**
- Headroom Proxy (`port 8787`, lossless mode) 已验证存活
- 真实 Kompress ML 压缩需上游 LLM API key（可选，不影响现有系统）
- 未激活时以 `SmartCrusher` lossless 压缩（~10-20% 结构压缩）
- 默认 `USE_HEADROOM=false`，零风险

## 3. 产线对接 — 合盛 MES POC

| 文件 | 说明 |
|---|---|
| `scripts/hoshine_mes_poc_with_compression.py` | 5 fault types × 5x burst 模拟测试 |
| `data/poc/received/*.json` | 模拟接收端压缩后记录 |
| `docs/hoshine_mes_poc_report.md` | 合规报告 |

## 4. 多产线并行监控

| 文件 | 说明 |
|---|---|
| `scripts/parallel_report.py` | 3 条产线（退火炉/涂布线/质检站）并行事件模拟 |
| `reports/parallel/` | 自动生成的并行报告 |
| `data/parallel/` | 原始事件 JSONL |

## 5. 集中观察流程

| 文件 | 说明 |
|---|---|
| `scripts/centralized_observation_v2_v3.py` | 7 天观察窗模拟（基线/压力/恢复/低负载/裁决） |
| `reports/observation/` | 7 天观察报告 |
| `data/observation/` | 观察原始数据 |

## 6. 回滚与安全

| 文件 | 说明 |
|---|---|
| `scripts/rollback_test_all.py` | 5/5 commit 回滚验证 ✅ |
| `src/core/mes_adapter.py` | MES 适配器（dry-run/inject/status） |
| `fault_templates/F-005_to_F-020.yaml` | 16 种生产故障模板 |

## 7. 架构文档

| 文件 | 说明 |
|---|---|
| `README.md` | 项目总纲领 |
| `docs/roadmap/VERSION_EVOLUTION.md` | v1.8 → v5.0+ 路线图 + 工业合作伙伴 |
| `docs/roadmap/DECEPTION_RESISTANCE.md` | 反欺骗防御原则 |
| `docs/hoshine_onboarding_faq.md` | 合盛入驻 FAQ（5 Q&A） |

---

## 合规检查表

| # | 检查项 | 状态 | 证据 |
|---|---|---|---|
| 1 | 自修复协议 | ✅ | AUTO_FIXER_PROTOCOL_v1.md |
| 2 | Headroom 集成方案 | ✅ | submodule + 适配器 |
| 3 | 日志压缩能力 | ✅ | MES POC 验证 |
| 4 | 多产线并行 | ✅ | parallel_report.py |
| 5 | 集中观察流程 | ✅ | observation 7-day |
| 6 | 回滚能力 | ✅ | 5/5 通过 |
| 7 | 反欺骗防御 | ✅ | input sanitization + entropy |
| 8 | 产线故障模板 | ✅ | F-005~F-020 |
| 9 | 合盛 FAQ | ✅ | hoshine_onboarding_faq.md |
| 10 | 架构文档 | ✅ | README + roadmap |

---

## 标记

```bash
git tag v3.0-compliant
git push origin v3.0-compliant
```
