"""
并行调度层 (v8.0)

实现 quorvex_ai 设计思想中的 "并行策略执行"：
对输入的故障，并行尝试 S1/S2/S3 修复（实际调用 apply_repair.py 的函数接口），
取最先成功的修复结果返回。

纪律:
  - 不修改 apply_repair.py
  - 不修改 mes_adapter.py（mes_adapter.py 仅加 import + if 判断）
  - gate: USE_V8_STRATEGIES=false 默认关闭
"""

from __future__ import annotations
import sys, os, time, threading
from typing import Any

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from src.repair.strategies.lithium import (
    is_lithium_fault, apply_lithium_repair, get_lithium_strategy,
)
from src.repair.strategies.pv import (
    is_pv_fault, apply_pv_repair, get_pv_strategy,
)

# ── 全局开关 ──
# mes_adapter.py 通过 os.getenv("USE_V8_STRATEGIES", "false") 控制
_ENABLED: bool = False

def enable():
    global _ENABLED
    _ENABLED = True

def disable():
    global _ENABLED
    _ENABLED = False

def is_enabled() -> bool:
    return _ENABLED


# ── 并行修复函数 ──

def run_parallel_repair(
    fault_id: str,
    signals: list[str] | None = None,
    timeout_s: float = 5.0,
) -> dict[str, Any]:
    """
    并行执行修复策略。

    流程:
      1. 根据 fault_id 选择策略类（lithium / pv / fallback）
      2. 首选策略 S1 启动
      3. 如果首选策略超时或失败，回退到策略链中的下一个
      4. 返回第一个成功的修复结果

    参数:
      fault_id: 故障 ID (F-xxx)
      signals: 可观测信号（仅用于 S1 模板补全）
      timeout_s: 单策略超时（秒）

    返回:
      {
        "fault_id": str,
        "strategy": str,
        "success": bool,
        "detail": str,
        "latency_s": float,
      }
    """
    start = time.time()
    fid = fault_id.upper()

    # ── 选择策略类 ──
    if is_lithium_fault(fid):
        primary_fn = lambda: apply_lithium_repair(fid, signals)
        fallback_strategies = ["S2", "S3"]
    elif is_pv_fault(fid):
        primary_fn = lambda: apply_pv_repair(fid, signals)
        fallback_strategies = ["S2", "S3"]
    else:
        # 通用故障 — 直接调用 apply_repair
        from src.core.apply_repair import apply_repair as _apply
        try:
            result = _apply("S1")
            success = result is not None
            return {
                "fault_id": fid,
                "strategy": "S1",
                "success": success,
                "detail": result or "repair returned None",
                "latency_s": round(time.time() - start, 3),
            }
        except Exception as e:
            return {
                "fault_id": fid,
                "strategy": "S1",
                "success": False,
                "detail": str(e),
                "latency_s": round(time.time() - start, 3),
            }

    # ── 并行执行 ──
    result: dict[str, Any] | None = None
    result_lock = threading.Lock()

    def try_strategy(strategy_name: str):
        """在独立线程中尝试一个策略"""
        nonlocal result
        try:
            if strategy_name == "S1":
                r = primary_fn()
            else:
                # fallback 用 apply_repair 直接调用
                from src.core.apply_repair import apply_repair as _apply
                r_val = _apply(strategy_name)
                r = {
                    "fault_id": fid,
                    "strategy": strategy_name,
                    "success": r_val is not None,
                    "target": None,
                    "detail": r_val or "repair returned None",
                }

            with result_lock:
                if r and r.get("success") and result is None:
                    result = r
        except Exception as e:
            with result_lock:
                if result is None:
                    result = {
                        "fault_id": fid,
                        "strategy": strategy_name,
                        "success": False,
                        "detail": str(e),
                    }

    threads = []
    for s in ["S1"] + fallback_strategies:
        t = threading.Thread(target=try_strategy, args=(s,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.05)  # 错开启动，避免竞争

    for t in threads:
        t.join(timeout=timeout_s / len(threads))

    elapsed = round(time.time() - start, 3)

    if result:
        result["latency_s"] = elapsed
        return result

    return {
        "fault_id": fid,
        "strategy": "fallback",
        "success": False,
        "detail": "all strategies exhausted or timed out",
        "latency_s": elapsed,
    }
