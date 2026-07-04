"""
mes_adapter.py — MES 模拟对接适配器 (v2.0)

模拟 HTTP POST 接收合盛 MES 的故障告警，
路由到 auto_fixer 修复引擎。

运行:
  python mes_adapter.py           # 启动模拟 HTTP 服务 (mock 模式)
  python mes_adapter.py --dry-run # 只打印不执行
  python mes_adapter.py --inject  # 注入一个模拟故障（测试用）
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Path setup
ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = ROOT / "fault_templates"
INBOUND_DIR = ROOT / "mes_inbound"
REPAIR_LOG = ROOT / "data" / "runs" / "mes_adapter.jsonl"


def load_fault_templates() -> dict:
    """Load all fault YAML templates into a dict keyed by fault_type."""
    templates = {}
    if not TEMPLATES_DIR.exists():
        return templates
    for yaml_file in sorted(TEMPLATES_DIR.glob("*.yaml")):
        content = yaml_file.read_text(encoding="utf-8")
        # Simple YAML-like parser (no pyyaml dependency)
        current = {}
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                current[key] = val
                if key == "fault_type" and val:
                    templates[val] = {"source": yaml_file.name}
    return templates


def simulate_mes_post(fault_type: str, params: dict | None = None) -> dict:
    """
    模拟 MES HTTP POST 请求。
    返回修复路由结果。
    """
    templates = load_fault_templates()
    if fault_type not in templates:
        return {
            "status": "rejected",
            "reason": f"Unknown fault_type: {fault_type}. Known: {list(templates.keys())}",
            "ts": datetime.now(timezone.utc).isoformat(),
        }

    # 路由到修复引擎
    result = {
        "status": "routed",
        "fault_type": fault_type,
        "strategy": _infer_strategy(fault_type),
        "params": params or {},
        "routed_to": "auto_fixer.apply_repair",
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    _log_repair(result)
    return result


def _infer_strategy(fault_type: str) -> str:
    """Infer repair strategy from fault type name."""
    ft = fault_type.lower()
    if any(k in ft for k in ["permission", "escalation", "perms", "rbac"]):
        return "S3"
    if any(k in ft for k in ["config", "corrupt", "memory", "disk", "connection", "rate"]):
        return "S2"
    # Default to S1
    return "S1"


def _log_repair(entry: dict):
    """Append repair entry to running log."""
    INBOUND_DIR.mkdir(parents=True, exist_ok=True)
    REPAIR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(REPAIR_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def inject_test_fault():
    """注入一个模拟故障用于测试。"""
    fault = {
        "fault_type": "disk_full",
        "params": {"mount_point": "/data", "usage_percent": 95},
    }
    result = simulate_mes_post(**fault)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\nTest fault injected. Check data/runs/mes_adapter.jsonl")


def main():
    parser = argparse.ArgumentParser(description="MES Adapter — 合盛 MES 模拟对接")
    parser.add_argument("--dry-run", action="store_true", help="只打印不执行")
    parser.add_argument("--inject", action="store_true", help="注入一个模拟故障")
    parser.add_argument("--status", action="store_true", help="显示适配器状态")
    args = parser.parse_args()

    if args.inject:
        inject_test_fault()
        return

    if args.dry_run:
        templates = load_fault_templates()
        print(f"[DRY RUN] MES Adapter initialized")
        print(f"  Templates loaded: {len(templates)}")
        print(f"  Fault types: {list(templates.keys())}")
        print(f"  Inbound dir: {INBOUND_DIR}")
        print(f"  Log file: {REPAIR_LOG}")
        return

    if args.status:
        print(f"  Templates: {len(load_fault_templates())} loaded")
        print(f"  Inbound dir exists: {INBOUND_DIR.exists()}")
        print(f"  Repair log entries: {sum(1 for _ in open(REPAIR_LOG)) if REPAIR_LOG.exists() else 0}")
        return

    # Default: run interactive mode
    print("MES Adapter — 合盛 MES 模拟对接 (mock mode)")
    print("  Type a fault_type to simulate, or 'list' to see available, or 'quit'")
    templates = load_fault_templates()
    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if cmd.lower() in ("quit", "exit", "q"):
            break
        if cmd.lower() == "list":
            for ft in sorted(templates.keys()):
                src = templates[ft]["source"]
                strategy = _infer_strategy(ft)
                print(f"  {ft:30s} → {strategy:4s} ({src})")
            continue
        result = simulate_mes_post(cmd)
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
