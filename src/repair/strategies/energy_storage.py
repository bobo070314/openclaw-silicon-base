"""
储能电池系统专用修复策略类 (v9.0)

绑定 F-041~F-050 储能故障模板。

纪律:
  - 不修改 apply_repair.py
  - 纯继承 S1/S2/S3 策略函数
  - 仅通过 fault_id 路由绑定
"""

from __future__ import annotations
import sys, os
from typing import Any

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)

from src.core.apply_repair import apply_repair

# ── 储能故障 ID 集合 ──
STORAGE_FAULT_IDS: set[str] = {
    "F-041",  # bms_cell_voltage_deviation
    "F-042",  # thermal_runaway_precursor
    "F-043",  # soc_drift
    "F-044",  # insulation_resistance_drop
    "F-045",  # fan_cooling_failure
    "F-046",  # bms_communication_timeout
    "F-047",  # cell_balancing_overcurrent
    "F-048",  # contactor_weld_detection
    "F-049",  # soh_degradation_alarm
    "F-050",  # fire_suppression_false_alarm
}

# ── 故障 ID → 修复策略映射 ──
STORAGE_STRATEGY_MAP: dict[str, str] = {
    "F-041": "S1",   # BMS 均衡参数调整
    "F-042": "S3",   # 热失控 → 权限升级 + 紧急停机
    "F-043": "S2",   # SOC 校准（需质量确认）
    "F-044": "S3",   # 绝缘故障 → 安全权限升级
    "F-045": "S1",   # 风扇参数恢复
    "F-046": "S1",   # 通信参数重连
    "F-047": "S1",   # 均衡电流配置
    "F-048": "S3",   # 接触器粘连 → 安全权限升级
    "F-049": "S2",   # SOH 衰退（需质量确认）
    "F-050": "S2",   # 消防误报（需质量确认）
}

# ── 模板描述 ──
STORAGE_TEMPLATES: dict[str, str] = {
    "F-041": "agent_chain.yaml",
    "F-045": "agent_chain.yaml",
    "F-046": "agent_chain.yaml",
    "F-047": "agent_chain.yaml",
}


def is_storage_fault(fault_id: str) -> bool:
    """判断是否储能故障"""
    return fault_id.upper() in STORAGE_FAULT_IDS


def get_storage_strategy(fault_id: str, default: str = "S1") -> str:
    """获取储能故障的修复策略"""
    return STORAGE_STRATEGY_MAP.get(fault_id.upper(), default)


def apply_storage_repair(fault_id: str, signals: list[str] | None = None) -> dict[str, Any]:
    """
    执行储能故障修复。

    参数:
      fault_id: F-041 ~ F-050
      signals: 可观测信号列表（可选）

    返回:
      { fault_id, strategy, success, target, detail }
    """
    fid = fault_id.upper()
    if not is_storage_fault(fid):
        return {
            "fault_id": fid,
            "strategy": "N/A",
            "success": False,
            "target": None,
            "detail": f"Not a storage fault: {fid}",
        }

    strategy = get_storage_strategy(fid)
    target = STORAGE_TEMPLATES.get(fid)
    detail: str

    try:
        result = apply_repair(strategy, target_name=target or "agent_chain.yaml")
        if result is not None:
            detail = f"repair applied: {result} (target={target})"
            success = True
        else:
            detail = f"repair returned None (target={target})"
            success = False
    except Exception as e:
        detail = f"repair raised: {e}"
        success = False

    return {
        "fault_id": fid,
        "strategy": strategy,
        "success": success,
        "target": target,
        "detail": detail,
    }
