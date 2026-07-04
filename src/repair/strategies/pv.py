"""
光伏电池/组件专用修复策略类 (v8.0)

继承 apply_repair.py 的函数接口（函数式，非 class），
绑定 F-031~F-040 光伏故障模板。

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

from src.core.apply_repair import apply_repair, _log_security_alert

# ── 光伏故障 ID 集合 ──
PV_FAULT_IDS: set[str] = {
    "F-031",  # cell_micro_crack
    "F-032",  # ribbon_offset
    "F-033",  # el_dark_star_cluster
    "F-034",  # lamination_void
    "F-035",  # iv_ff_degradation
    "F-036",  # glass_breakage_during_layup
    "F-037",  # junction_box_adhesion_fail
    "F-038",  # bypass_diode_overheat
    "F-039",  # frame_corrosion_precursor
    "F-040",  # string_current_reversal
}

# ── 故障 ID → 修复策略映射 ──
PV_STRATEGY_MAP: dict[str, str] = {
    "F-031": "S2",   # 质检主管判定降级/返修
    "F-032": "S1",   # 调整串焊机视觉定位
    "F-033": "S3",   # 权限升级 + 批次报废判定
    "F-034": "S1",   # 调整层压参数
    "F-035": "S2",   # 质量部门确认分档降级
    "F-036": "S3",   # 紧急停机 + 产线主管介入
    "F-037": "S1",   # 调整固化参数
    "F-038": "S2",   # 电气工程师确认更换
    "F-039": "S1",   # 增加密封胶/保护层工艺参数
    "F-040": "S3",   # 权限升级 + 质检主管确认返工
}

# ── 模板描述（给 S1 补全用）──
PV_TEMPLATES: dict[str, str] = {
    "F-032": "agent_chain.yaml",
    "F-034": "agent_chain.yaml",
    "F-037": "agent_chain.yaml",
    "F-039": "agent_chain.yaml",
}


def is_pv_fault(fault_id: str) -> bool:
    """判断是否光伏故障"""
    return fault_id.upper() in PV_FAULT_IDS


def get_pv_strategy(fault_id: str, default: str = "S1") -> str:
    """获取光伏故障的修复策略"""
    return PV_STRATEGY_MAP.get(fault_id.upper(), default)


def apply_pv_repair(fault_id: str, signals: list[str] | None = None) -> dict[str, Any]:
    """
    执行光伏故障修复。

    参数:
      fault_id: F-031 ~ F-040
      signals: 可观测信号列表（可选）

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
    if not is_pv_fault(fid):
        return {
            "fault_id": fid,
            "strategy": "N/A",
            "success": False,
            "target": None,
            "detail": f"Not a PV fault: {fid}",
        }

    strategy = get_pv_strategy(fid)
    target = PV_TEMPLATES.get(fid)
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
