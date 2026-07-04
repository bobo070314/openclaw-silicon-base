"""
锂电正极专用修复策略类 (v8.0)

继承 apply_repair.py 的函数接口（函数式，非 class），
绑定 F-021~F-030 锂电正极故障模板。

纪律:
  - 不修改 apply_repair.py
  - 纯继承 S1/S2/S3 策略函数
  - 仅通过 fault_id 路由绑定
"""

from __future__ import annotations
import sys, os
from typing import Any

# 向上两级到项目根
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)

from src.core.apply_repair import apply_repair, _log_security_alert

# ── 锂电正极故障 ID 集合 ──
LITHIUM_FAULT_IDS: set[str] = {
    "F-021",  # sintering_temp_exceeded
    "F-022",  # sintering_hold_time_insufficient
    "F-023",  # slurry_viscosity_deviation
    "F-024",  # ncm_cation_mixing_ratio_off
    "F-025",  # roll_press_burst
    "F-026",  # coating_edge_thickening
    "F-027",  # electrode_slitting_burr
    "F-028",  # solvent_recovery_pressure_drop
    "F-029",  # lithium_iron_phosphate_impurity
    "F-030",  # cathode_drying_oven_temp_gradient
}

# ── 故障 ID → 修复策略映射 ──
LITHIUM_STRATEGY_MAP: dict[str, str] = {
    "F-021": "S1",   # 补烧曲线配方
    "F-022": "S1",   # 延长保温参数
    "F-023": "S1",   # 调整固含量
    "F-024": "S2",   # 烧结气氛调整（需人工复核）
    "F-025": "S3",   # 产线主管干预
    "F-026": "S1",   # 调整模头间隙
    "F-027": "S1",   # 更换刀片参数
    "F-028": "S1",   # 清理冷凝器
    "F-029": "S2",   # 增加除磁工序（需质量确认）
    "F-030": "S1",   # 烘箱分区温度
}

# ── 模板描述（给 S1 补全用）──
LITHIUM_TEMPLATES: dict[str, str] = {
    "F-021": "agent_chain.yaml",
    "F-022": "agent_chain.yaml",
    "F-026": "agent_chain.yaml",
    "F-027": "agent_chain.yaml",
    "F-028": "agent_chain.yaml",
    "F-030": "agent_chain.yaml",
}


def is_lithium_fault(fault_id: str) -> bool:
    """判断是否锂电故障"""
    return fault_id.upper() in LITHIUM_FAULT_IDS


def get_lithium_strategy(fault_id: str, default: str = "S1") -> str:
    """获取锂电故障的修复策略"""
    return LITHIUM_STRATEGY_MAP.get(fault_id.upper(), default)


def apply_lithium_repair(fault_id: str, signals: list[str] | None = None) -> dict[str, Any]:
    """
    执行锂电故障修复。

    参数:
      fault_id: F-021 ~ F-030
      signals: 可观测信号列表（仅用于 S1 模板补全，可选）

    返回:
      {
        "fault_id": str,
        "strategy": str,
        "success": bool,
        "target": str | None,
        "detail": str,
      }
    """
    fid = fault_id.upper()
    if not is_lithium_fault(fid):
        return {
            "fault_id": fid,
            "strategy": "N/A",
            "success": False,
            "target": None,
            "detail": f"Not a lithium fault: {fid}",
        }

    strategy = get_lithium_strategy(fid)
    target = LITHIUM_TEMPLATES.get(fid)
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
