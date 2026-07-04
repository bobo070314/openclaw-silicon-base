"""
apply_repair.py — Input-sanitized repair engine for Silicon Body Fixer.

Security layers:
  - Type check: reject non-string inputs
  - Length check: reject overlong inputs (>200 chars)
  - Path traversal: reject "..", absolute paths
  - Strategy validation: only S1/S2/S3 allowed
  - Path jail: ensure output stays inside project root

All violations logged as [SECURITY_ALERT].
"""

import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

S1_TEMPLATES = {
    "agent_chain.yaml": """# Agent Chain Configuration (auto-generated)
pipeline:
  name: "silicon-base-delivery"
  version: "1.0.1"
  stages:
    - name: init
      script: "scripts/init.ps1"
      timeout_seconds: 30
      required: true
    - name: validate
      script: "scripts/orchestrator.py"
      timeout_seconds: 60
      required: true
  rbac:
    enabled: true
    violation_log: "data/runs/violations.jsonl"
""",
    "README.deliver.md": """# OpenClaw Delivery Package (auto-generated)
## Quick Start
1. Run `scripts/init.ps1`
2. Run `scripts/run_all.ps1`
""",
}

S2_TEMPLATES = {
    "agent_chain.yaml": """# Agent Chain Configuration (auto-fixed S2 — ConfigError)
pipeline:
  name: "silicon-base-delivery"
  version: "1.0.1"
  stages:
    - name: init
    - name: validate
  rbac:
    enabled: true
    violation_log: "data/runs/violations.jsonl"
""",
}

S3_TEMPLATES = {
    "agent_chain.yaml": """# Agent Chain Configuration (auto-fixed S3 — RBACViolation)
pipeline:
  name: "silicon-base-delivery"
  version: "1.0.1"
  stages:
    - name: init
    - name: validate
  rbac:
    enabled: true
    violation_log: "data/runs/violations.jsonl"
    default_roles:
      - name: coder
        permissions:
          - read:configs
          - write:scripts
          - run:eval
""",
}


def apply_repair(strategy: str, target_name: str = "agent_chain.yaml") -> str | None:
    """
    Apply a repair template. Includes input sanitization.
    """
    if not isinstance(strategy, str) or not isinstance(target_name, str):
        _log_security_alert(f"Non-string input: strategy={type(strategy).__name__}, target={type(target_name).__name__}")
        return None
    if len(strategy) > 10 or len(target_name) > 200:
        _log_security_alert(f"Overlong: strategy={len(strategy)}, target={len(target_name)}")
        return None
    if ".." in target_name or target_name.startswith("/") or target_name.startswith("\\"):
        _log_security_alert(f"Path traversal: {target_name!r}")
        return None
    strategy = strategy.strip().upper()
    target_name = target_name.strip()
    if strategy not in ("S1", "S2", "S3"):
        _log_security_alert(f"Unknown strategy: {strategy!r}")
        return None

    templates = {"S1": S1_TEMPLATES, "S2": S2_TEMPLATES, "S3": S3_TEMPLATES}[strategy]
    content = templates.get(target_name)
    if content is None:
        return None

    if target_name.endswith(".yaml"):
        output = PROJECT_ROOT / "configs" / target_name
    else:
        output = PROJECT_ROOT / target_name

    # Path jail
    try:
        output = output.resolve()
    except (ValueError, OSError):
        pass
    if not str(output).startswith(str(PROJECT_ROOT.resolve())):
        _log_security_alert(f"Path jail: {output} outside {PROJECT_ROOT}")
        return None

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return str(output)


def _log_security_alert(detail: str):
    path = PROJECT_ROOT / "data" / "runs" / "violations.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    record = {"timestamp": now, "level": "SECURITY_ALERT", "action_type": "INPUT_SANITIZATION", "detail": detail}
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{now}] [SECURITY_ALERT] {json.dumps(record, ensure_ascii=False)}\n")
