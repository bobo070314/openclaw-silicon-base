# 硅基体协议 v1.0 — Silicon Protocol

**版本**: v1.0  
**起草时间**: 2026-07-04  
**状态**: 已定稿  
**代码实现**: `src/protocol/normalizer.py`  
**设计基础**: v6.0 协议兼容性评估 + 36 条真实工业故障模板

---

## 1. 目标

定义硅基体自修复系统的统一故障描述协议，确保：

1. **跨产业兼容** — 通用/锂电/光伏模板字段一致
2. **向下兼容** — v2.0 旧格式 (F-005~F-020) 运行时可补齐
3. **扩展预留** — v10.0 标准化路径清晰

## 2. 核心数据结构

### 2.1 单故障模板字段 (8 MUST + 5 SHOULD)

**8 个必选字段 (MUST)**:

| # | 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|---|
| 1 | `fault_id` | str | `F-021` | 全局唯一 ID |
| 2 | `name` | str | `sintering_temp_exceeded` | 机器可读名称 (snake_case) |
| 3 | `description` | str | `正极材料烧结温度超上限` | 人类可读描述 |
| 4 | `severity` | enum | `P1`, `P2`, `P3` | 严重等级 |
| 5 | `category` | enum | `process_anomaly` | 故障分类 |
| 6 | `repair_strategy` | enum | `S1`, `S2`, `S3` | 修复策略 |
| 7 | `signals` | list | `[temperature > 980°C, duration > 30min]` | 可观测信号 (≥2) |
| 8 | `affects` | list | `[cathode_batch, crystal_grain_size]` | 受影响组件 |

**5 个建议字段 (SHOULD)**:

| # | 字段 | 类型 | 说明 |
|---|---|---|---|
| 9 | `industry` | enum | `general`, `lithium`, `pv` (v10.0 扩展) |
| 10 | `sensor_type` | str | 触发信号的传感器类型 |
| 11 | `threshold` | str | 触发阈值表达式 |
| 12 | `rbac_level` | enum | `L1`, `L2`, `L3` (修复所需权限) |
| 13 | `parameters` | dict | 旧格式兼容 (v2.0) |

### 2.2 Category 枚举

| Enum | 说明 | 模板数 |
|---|---|---|
| `process_anomaly` | 工艺参数偏差 | 7 (锂电) + 3 (光伏) + 5 (通用) |
| `equipment_fault` | 设备故障/停机 | 1 (锂电) + 2 (光伏) + 9 (通用) |
| `material_quality` | 原材料品质问题 | 2 (锂电) + 1 (光伏) |
| `quality_defect` | 产品缺陷 | 0 (锂电) + 4 (光伏) |
| `general` | 通用 (v2.0 缺 field 时 fallback) | — |

### 2.3 修复策略枚举

| 策略 | 说明 | 适用场景 | 典型延迟 |
|---|---|---|---|
| S1 | 文件补全 / 参数调整 | 参数超限、配置缺失 | ~1.2s |
| S2 | 配置修复 / 质检判定 | 物料批号替换、等级降级 | ~3.5s |
| S3 | 权限恢复 / escalation | 产线停机、安全风险 | ~8.0s |

## 3. v2.0 兼容性

### 3.1 normalize_v2() 补齐规则

v2.0 模板 (F-005~F-020 格式) 缺少 `signals/category/name/affects` 字段，
通过 `src/protocol/normalizer.py` 的 `normalize_v2()` 函数补齐：

```python
result = normalize_v2(v2_fault)  # 输入单对象 dict → 输出统一格式 dict
```

### 3.2 补齐逻辑

| 缺失字段 | 补齐来源 | 示例 |
|---|---|---|
| `fault_id` | 从 `fault_type` 推断 | `disk_full` → `F-DISK-FULL` |
| `name` | 预定义名称映射表 | `disk_full` → `disk_space_exceeded` |
| `category` | `fault_type` → category 映射 | `disk_full` → `equipment_fault` |
| `signals` | 从 `parameters` 键值对推导 | `{mount_point: /data, usage: 95}` → `[mount_point: /data, usage > 85]` |
| `affects` | 按 `fault_type` 推理 | `disk_full` → `[disk_monitor, data_persistence]` |

### 3.3 验证结果

输入: `fault_templates/F-005_to_F-020.yaml` (16 条 v2.0 模板)
测试: **144/144 通过 ✅**
- 16/16 正确识别为 v2.0 格式
- 16/16 正确补齐 5 个缺失字段
- 16/16 保留 severity/repair_strategy/description 原值

## 4. 完整示例

### v2.0 原始格式 (F-005)

```yaml
fault_type: disk_full
description: 日志/数据分区磁盘空间超过阈值
severity: P1
source: filesystem_monitor
parameters:
  mount_point: /data
  usage_percent: 95
  threshold: 85
repair_strategy: S2
```

### 补齐后 (v1.0 兼容格式)

```yaml
fault_id: F-DISK-FULL
name: disk_space_exceeded
description: 日志/数据分区磁盘空间超过阈值
severity: P1
category: equipment_fault
repair_strategy: S2
signals:
  - mount_point: /data
  - usage_percent > 85
  - threshold: 85
affects:
  - disk_monitor
  - data_persistence
```

## 5. 协议演进

| 版本 | 核心变化 | 状态 |
|---|---|---|
| v1.0 | 标准字段定义 + `normalize_v2()` 补齐 | ✅ 当前 |
| v2.0 | 添加 `industry` 枚举 | 📅 v10.0 |
| v2.0 | 添加 `rbac_level` 标准化 | 📅 v10.0 |
| v2.0 | 全量模板格式统一 | 📅 v10.0 |

## 6. 安全边界

- `normalize_v2()` 不修改输入文件（运行时补齐）
- 非 dict 输入 → 原样返回
- 已包含 `templates` key → 跳过（识别为 v4.0 格式）
- 不调用修复引擎、不写入文件系统
