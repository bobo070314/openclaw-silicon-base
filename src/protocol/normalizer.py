"""
silicon-body-fixer — Protocol Normalizer (v7.0)

将 v2.0 旧格式模板（F-005~F-020，单对象 YAML）在运行时可逆地补齐为
v4.0 兼容的新格式（templates[] + signals/category/name/affects 字段）。

纪律：
  - 只做字段补齐，不改修复策略（S1/S2/S3）
  - 不物理迁移文件（运行时补齐）
  - 归一化后的模板可直接喂给 mes_adapter.py
"""

from __future__ import annotations
import hashlib
from typing import Any

# ── v2.0 fault_type → v4.0 category 映射 ──
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

# ── v2.0 fault_type → v4.0 name 映射 ──
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

# ── v2.0 fault_type → signals 生成逻辑 ──
def _build_signals(fault: dict[str, Any]) -> list[str]:
    """从 old-format parameters 重建 signals 字段"""
    sigs: list[str] = []
    params = fault.get("parameters", {})

    # 通用策略：从 parameters 提取所有键值对转为字符串信号
    for k, v in params.items():
        if isinstance(v, str):
            sigs.append(f"{k}: {v}")
        elif isinstance(v, (int, float)):
            # 带 threshold 的字段自动生成阈值表达式
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


def normalize_v2(fault: dict[str, Any]) -> dict[str, Any]:
    """
    将 v2.0 单对象故障模板补齐为 v4.0 兼容的新格式。

    输入: 从 YAML 加载的单对象 dict
    输出: 带 signs/category/name/affects 的统一 dict

    不修改:
      - fault_id → 自动从 fault_type 生成
      - repair_strategy → 原样保留
      - severity → 原样保留
      - description → 原样保留

    安全:
      - 非 dict 输入 → 原样返回
      - 包含 'templates' key → 跳过（已是 v4.0 格式）
    """
    if not isinstance(fault, dict):
        return fault

    # 跳过已经是 v4.0 格式的
    if "templates" in fault:
        return fault

    fault_type = fault.get("fault_type", "unknown")
    fault_id = f"F-{fault_type.replace('_', '-').upper()}"

    result = dict(fault)  # 浅拷贝

    # 补齐 fault_id
    result.setdefault("fault_id", fault_id)

    # 补齐 name
    result.setdefault("name", NAME_MAP.get(fault_type, fault_type))

    # 补齐 category
    result.setdefault("category", CATEGORY_MAP.get(fault_type, "general"))

    # 补齐 signals
    if "signals" not in result:
        result["signals"] = _build_signals(fault)

    # 补齐 affects
    if "affects" not in result:
        result["affects"] = _build_affects(fault)

    # 补齐 name 字段（如果 name 在原始数据不存在的话）
    if "name" not in result:
        result["name"] = fault_type

    return result


def normalize_templates_list(templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    批量归一化模板列表（兼容混合格式）。

    如果传入的是 templates[] list，逐个归一化；
    如果传入空列表或 None，返回空列表。
    """
    if not templates:
        return []

    return [normalize_v2(t) for t in templates]


def is_v2_format(fault: dict[str, Any]) -> bool:
    """判断是否为 v2.0 旧格式"""
    return "fault_type" in fault and "templates" not in fault


def is_v4_format(fault: dict[str, Any]) -> bool:
    """判断是否为 v4.0 新格式"""
    return "templates" in fault or ("signals" in fault and "name" in fault)
