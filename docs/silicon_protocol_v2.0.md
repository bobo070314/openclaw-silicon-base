# 硅基体协议 v2.0

**版本**: v2.0  
**起草时间**: 2026-07-04  
**状态**: 已定稿  
**代码实现**: `src/protocol/normalizer.py` (v10.0 升级版)  
**设计基础**: v6.0 协议草案 + v1.0 实践经验 + 50 条真实工业故障模板

---

## 1. 与 v1.0 变更摘要

| 维度 | v1.0 | v2.0 | 理由 |
|---|---|---|---|
| 字段 | 8 MUST + 5 SHOULD | 8 MUST + 7 SHOULD | 产业隔离/来源追踪 |
| 新增 `industry_type` | — | enum: general/lithium/pv/energy_storage | 跨产业模板隔离 |
| 新增 `fault_source` | — | enum: infrastructure/security/system/application/sensor | 故障根因分类 |
| 新增 `rbac_level` | — | enum: L1/L2/L3 (从 severity 自动映射) | 权限隔离 |
| 新增 `sensor_type` | — | str | 传感器跟踪 |
| `is_v2_format()` | 宽松检测 | 严格检测（排除归一化后结果） | 精度提升 |
| `is_v10_format()` | — | 新增 | v2.0 合规检测 |

## 2. 完整字段定义

### 8 个必选字段 (MUST)

| # | 字段 | 类型 | 示例 | v2.0 变更 |
|---|---|---|---|---|
| 1 | `fault_id` | str | `F-021` | — |
| 2 | `name` | str | `sintering_temp_exceeded` | — |
| 3 | `description` | str | `正极材料烧结温度超上限` | — |
| 4 | `severity` | enum | `P1`, `P2`, `P3` | — |
| 5 | `category` | enum | `process_anomaly` | — |
| 6 | `repair_strategy` | enum | `S1`, `S2`, `S3` | — |
| 7 | `signals` | list | `[temperature > 980°C]` | — |
| 8 | `affects` | list | `[cathode_batch]` | — |

### 7 个建议字段 (SHOULD)

| # | 字段 | 类型 | 说明 | v2.0 新增 |
|---|---|---|---|---|
| 9 | `industry_type` | enum | 所属产业 | ✅ |
| 10 | `fault_source` | enum | 故障来源分类 | ✅ |
| 11 | `rbac_level` | enum | 修复所需权限 | ✅ |
| 12 | `sensor_type` | str | 触发信号的传感器 | ✅ |
| 13 | `industry` | str | v6.0 draft 兼容字段 | — |
| 14 | `threshold` | str | 触发阈值表达式 | — |
| 15 | `parameters` | dict | 旧格式兼容 (v2.0 原始) | — |

## 3. 新增枚举

### industry_type

| 枚举值 | 前缀范围 | 模板数 |
|---|---|---|
| `general` | F-005~F-020 | 16 |
| `lithium` | F-021~F-030 | 10 |
| `pv` | F-031~F-040 | 10 |
| `energy_storage` | F-041~F-050 | 10 |

### fault_source

| 枚举值 | 说明 | 示例 |
|---|---|---|
| `infrastructure` | 基础设施故障 | 磁盘/网络/依赖 |
| `security` | 安全相关 | 权限/证书 |
| `system` | 系统配置 | 配置损坏/日志 |
| `application` | 应用层 | 队列/限流 |
| `sensor` | 传感器层 | 温度探头 |

### rbac_level

| 等级 | 说明 | 对应 Severity |
|---|---|---|
| L3 | System Admin (系统管理员) | P1 |
| L2 | Line Supervisor (产线主管) | P2 |
| L1 | Operator (操作员) | P3 |

## 4. normalize_v2() 补齐行为

| 缺失字段 | 补齐来源 | v2.0 升级 |
|---|---|---|
| `industry_type` | fault_type → Industry Map | ✅ 新增 |
| `fault_source` | fault_type → Source Map | ✅ 新增 |
| `rbac_level` | severity → RBAC Map | ✅ 新增 |
| `sensor_type` | fault_type → Sensor Map | ✅ 新增 |

## 5. 验证结果

| 测试 | 通过数 |
|---|---|
| normalizer v2.0 升级 | 18/18 ✅ |
| 锂电策略类 | 7/7 ✅ |
| 光伏策略类 | 4/4 ✅ |
| 储能策略类 | 4/4 ✅ |
| 并行调度器 | 8/8 ✅ |
| mes_adapter gate | 3/3 ✅ |
| **总计** | **44/44 ✅** |

## 6. 协议演进路线

```
v1.0 ──→ v2.0 ──→ v3.0 (规划)
  |          |
  标准化     产业隔离    v3.0: 连续信号支持
  字段       权限模型    v3.0: 多产业策略链
  8 MUST     4 个新字段  v3.0: 协议版本协商
```
