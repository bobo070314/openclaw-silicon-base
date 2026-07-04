"""
silicon-body-fixer — Protocol Normalizer (v2.0 升级版 / v10.0)

在 v7.0 的基础上，新增:
  1. industry_type 字段补齐（从 fault_id 前缀推断）
  2. fault_source 字段补齐（从模板来源推断）
  3. rbac_level 字段补齐（从 severity 映射）
  4. sensor_type 字段补齐（从 fault_type 推断）
  5. v2_0_convert() 批量转换 v2.0 模板文件接口

纪律：
  - 只做字段补齐，不改修复策略（S1/S2/S3）
  - 不物理迁移文件（运行时补齐）
  - 所有新字段默认带空值，不破坏现有调用
"""

from __future__ import annotations
import hashlib
from typing import Any

# ════════════════════════════════════════════
# v7.0 原始映射表（保留完整兼容）
# ════════════════════════════════════════════

CATEGORY_MAP: dict[str, str] = {
    "disk_full":                           "equipment_fault",
    "network_timeout":                     "process_anomaly",
    "permission_escalation":               "equipment_fault",
    "config_corrupt":                      "equipment_fault",
    "dependency_offline":                  "equipment_fault",
    "memory_leak_warning":                 "equipment_fault",
    "cert_expiry_warning":                 "equipment_fault",
    "data_dir_perms":                      "equipment_fault",
    "cascade_signal":                      "process_anomaly",
    "temperature_anomaly":                 "process_anomaly",
    "log_rotation_failure":                "equipment_fault",
    "protocol_version_mismatch":           "process_anomaly",
    "connection_pool_exhausted":           "equipment_fault",
    "task_queue_backlog":                  "process_anomaly",
    "rate_limit_hit":                      "process_anomaly",
    "observation_window_expired":          "process_anomaly",
}

NAME_MAP: dict[str, str] = {
    "disk_full":                           "disk_space_exceeded",
    "network_timeout":                     "mes_api_timeout",
    "permission_escalation":               "unauthorized_access_attempt",
    "config_corrupt":                      "configuration_corruption",
    "dependency_offline":                  "external_dependency_unreachable",
    "memory_leak_warning":                 "memory_leak_detected",
    "cert_expiry_warning":                 "certificate_expiry_warning",
    "data_dir_perms":                      "data_directory_permissions",
    "cascade_signal":                      "cascade_fault_signal",
    "temperature_anomaly":                 "furnace_temperature_drift",
    "log_rotation_failure":                "log_file_rotation_failure",
    "protocol_version_mismatch":           "mcp_protocol_mismatch",
    "connection_pool_exhausted":           "database_connection_pool_exhausted",
    "task_queue_backlog":                  "repair_queue_backlog",
    "rate_limit_hit":                      "api_rate_limit_exceeded",
    "observation_window_expired":          "observation_window_silence",
}

# ════════════════════════════════════════════
# v10.0 新映射表
# ════════════════════════════════════════════

# v2.0 fault_type → industry_type 推断
INDUSTRY_MAP: dict[str, str] = {
    "disk_full":                           "general",
    "network_timeout":                     "general",
    "permission_escalation":               "general",
    "config_corrupt":                      "general",
    "dependency_offline":                  "general",
    "memory_leak_warning":                 "general",
    "cert_expiry_warning":                 "general",
    "data_dir_perms":                      "general",
    "cascade_signal":                      "general",
    "temperature_anomaly":                 "general",
    "log_rotation_failure":                "general",
    "protocol_version_mismatch":           "general",
    "connection_pool_exhausted":           "general",
    "task_queue_backlog":                  "general",
    "rate_limit_hit":                      "general",
    "observation_window_expired":          "general",
}

# fault_id 前缀 → industry_type 推断（用于 v4.0 模板）
INDUSTRY_BY_FAULT_ID_PREFIX: dict[str, str] = {
    "F-005": "general",
    "F-006": "general",
    "F-007": "general",
    "F-008": "general",
    "F-009": "general",
    "F-010": "general",
    "F-011": "general",
    "F-012": "general",
    "F-013": "general",
    "F-014": "general",
    "F-015": "general",
    "F-016": "general",
    "F-017": "general",
    "F-018": "general",
    "F-019": "general",
    "F-020": "general",
    "F-021": "lithium",
    "F-022": "lithium",
    "F-023": "lithium",
    "F-024": "lithium",
    "F-025": "lithium",
    "F-026": "lithium",
    "F-027": "lithium",
    "F-028": "lithium",
    "F-029": "lithium",
    "F-030": "lithium",
    "F-031": "pv",
    "F-032": "pv",
    "F-033": "pv",
    "F-034": "pv",
    "F-035": "pv",
    "F-036": "pv",
    "F-037": "pv",
    "F-038": "pv",
    "F-039": "pv",
    "F-040": "pv",
    "F-041": "energy_storage",
    "F-042": "energy_storage",
    "F-043": "energy_storage",
    "F-044": "energy_storage",
    "F-045": "energy_storage",
    "F-046": "energy_storage",
    "F-047": "energy_storage",
    "F-048": "energy_storage",
    "F-049": "energy_storage",
    "F-050": "energy_storage",
}

# severity → rbac_level 映射
SEVERITY_RBAC_MAP: dict[str, str] = {
    "P1": "L3",
    "P2": "L2",
    "P3": "L1",
}

# fault_type → sensor_type 推断
SENSOR_MAP: dict[str, str] = {
    "disk_full":                           "filesystem_monitor",
    "network_timeout":                     "network_monitor",
    "permission_escalation":               "access_log",
    "config_corrupt":                      "config_watcher",
    "dependency_offline":                  "health_checker",
    "memory_leak_warning":                 "memory_profiler",
    "cert_expiry_warning":                 "cert_monitor",
    "data_dir_perms":                      "filesystem_watcher",
    "cascade_signal":                      "alert_manager",
    "temperature_anomaly":                 "sensor_probe",
    "log_rotation_failure":                "log_manager",
    "protocol_version_mismatch":           "handshake_layer",
    "connection_pool_exhausted":           "connection_monitor",
    "task_queue_backlog":                  "queue_watcher",
    "rate_limit_hit":                      "rate_limiter",
    "observation_window_expired":          "daemon_timer",
}

# fault_type → fault_source 推断
FAULT_SOURCE_MAP: dict[str, str] = {
    "disk_full":                           "infrastructure",
    "network_timeout":                     "infrastructure",
    "permission_escalation":               "security",
    "config_corrupt":                      "system",
    "dependency_offline":                  "infrastructure",
    "memory_leak_warning":                 "application",
    "cert_expiry_warning":                 "security",
    "data_dir_perms":                      "system",
    "cascade_signal":                      "application",
    "temperature_anomaly":                 "sensor",
    "log_rotation_failure":                "system",
    "protocol_version_mismatch":           "application",
    "connection_pool_exhausted":           "infrastructure",
    "task_queue_backlog":                  "application",
    "rate_limit_hit":                      "application",
    "observation_window_expired":          "application",
}


def _build_signals(fault: dict[str, Any]) -> list[str]:
    """从 old-format parameters 重建 signals 字段"""
    sigs: list[str] = []
    params = fault.get("parameters", {})

    for k, v in params.items():
        if isinstance(v, str):
            sigs.append(f"{k}: {v}")
        elif isinstance(v, (int, float)):
            threshold_key = f"threshold_{k}"
            threshold = params.get(threshold_key)
            if threshold is not None:
                sigs.append(f"{k} > {threshold}")
            else:
                sigs.append(f"{k}: {v}")

    if not sigs:
        sigs.append("monitor_event: triggered")

    return sigs


def _build_affects(fault: dict[str, Any]) -> list[str]:
    """从旧格式推导 affects 字段"""
    ft = fault.get("fault_type", "")
    if ft == "disk_full":
        return ["disk_monitor", "data_persistence"]
    if "network" in ft or "connection" in ft or "timeout" in ft:
        return ["mes_api", "network_connectivity"]
    if "permission" in ft or "data_dir" in ft:
        return ["access_control", "config_security"]
    if "corrupt" in ft or "config" in ft:
        return ["configuration", "system_settings"]
    if "dependency" in ft or "offline" in ft:
        return ["dependency_graph", "external_service"]
    if "memory" in ft:
        return ["memory_manager", "process_health"]
    if "cert" in ft:
        return ["cert_manager", "ssl_tls"]
    if "cascade" in ft:
        return ["alert_system", "fault_propagation"]
    if "temperature" in ft:
        return ["thermal_management", "annealing_process"]
    if "log" in ft:
        return ["log_manager", "file_system"]
    if "protocol" in ft:
        return ["handshake_layer", "mcp_compatibility"]
    if "queue" in ft or "backlog" in ft:
        return ["repair_pipeline", "task_scheduler"]
    if "rate" in ft:
        return ["api_gateway", "rate_limiter"]
    if "observation" in ft or "window" in ft:
        return ["daemon_scheduler", "observation_metrics"]
    return ["production_line", "system_health"]


def _infer_industry_from_fault_id(fault_id: str) -> str:
    """从故障 ID 推断 industry_type"""
    prefix = fault_id.rsplit("-", 1)[0] if "-" in fault_id else fault_id
    # 匹配前缀: F-021 → F-021 前缀
    for pfx in sorted(INDUSTRY_BY_FAULT_ID_PREFIX.keys(), reverse=True):
        if fault_id.startswith(pfx):
            return INDUSTRY_BY_FAULT_ID_PREFIX[pfx]
    return "general"


# ════════════════════════════════════════════
# 核心函数
# ════════════════════════════════════════════

def normalize_v2(fault: dict[str, Any]) -> dict[str, Any]:
    """
    将 v2.0 单对象故障模板补齐为 v4.0/v10.0 兼容格式。

    输入: 从 YAML 加载的单对象 dict
    输出: 带 signs/category/name/affects + v10.0 新字段的统一 dict

    安全:
      - 非 dict 输入 → 原样返回
      - 包含 'templates' key → 跳过（已是 v4.0 格式）
    """
    if not isinstance(fault, dict):
        return fault

    if "templates" in fault:
        return fault

    fault_type = fault.get("fault_type", "unknown")
    fault_id = fault.get("fault_id", f"F-{fault_type.replace('_', '-').upper()}")
    severity = fault.get("severity", "P2")

    result = dict(fault)

    # ── v7.0 遗留补齐 ──
    result.setdefault("fault_id", fault_id)
    result.setdefault("name", NAME_MAP.get(fault_type, fault_type))
    result.setdefault("category", CATEGORY_MAP.get(fault_type, "general"))
    if "signals" not in result:
        result["signals"] = _build_signals(fault)
    if "affects" not in result:
        result["affects"] = _build_affects(fault)
    if "name" not in result:
        result["name"] = fault_type

    # ── v10.0 新字段补齐 ──
    # industry_type
    if "industry_type" not in result:
        result["industry_type"] = INDUSTRY_MAP.get(fault_type, _infer_industry_from_fault_id(fault_id))

    # fault_source
    if "fault_source" not in result:
        result["fault_source"] = FAULT_SOURCE_MAP.get(fault_type, "system")

    # rbac_level
    if "rbac_level" not in result:
        result["rbac_level"] = SEVERITY_RBAC_MAP.get(severity, "L1")

    # sensor_type
    if "sensor_type" not in result:
        result["sensor_type"] = SENSOR_MAP.get(fault_type, "unknown")

    # industry (v6.0 草案兼容)
    if "industry" not in result:
        result["industry"] = result.get("industry_type", "general")

    return result


def normalize_templates_list(templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """批量归一化模板列表"""
    if not templates:
        return []
    return [normalize_v2(t) for t in templates]


def is_v2_format(fault: dict[str, Any]) -> bool:
    """判断是否为 v2.0 旧格式（未经过 normalize_v2 处理的原始格式）"""
    return ("fault_type" in fault
            and "fault_id" not in fault
            and "signals" not in fault
            and "name" not in fault
            and "templates" not in fault)


def is_v4_format(fault: dict[str, Any]) -> bool:
    """判断是否为 v4.0 新格式"""
    return "templates" in fault or ("signals" in fault and "name" in fault)


def is_v10_format(fault: dict[str, Any]) -> bool:
    """判断是否为 v10.0 兼容格式（含 industry_type / fault_source）"""
    return "industry_type" in fault and "fault_source" in fault


def v2_0_roundtrip(v2_fault: dict[str, Any]) -> dict[str, Any]:
    """
    v2.0 → v10.0 全量转换。

    适用于将 v2.0 模板运行时读入后转换为标准格式。
    与 normalize_v2() 等同，语义更明确。
    """
    return normalize_v2(v2_fault)
