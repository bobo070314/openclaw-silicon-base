#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gate_check.py - MVP 门禁检查器（新版本，读取 latest_eval.json 对比 guardrails.yaml）
"""

import os
import sys
import json
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARDRAILS_PATH = os.path.join(BASE_DIR, "configs", "guardrails.yaml")
EVAL_REPORT_PATH = os.path.join(BASE_DIR, "data", "runs", "latest_eval.json")


class GateKeeper:
    def __init__(self):
        self.guardrails = self._load_yaml(GUARDRAILS_PATH)
        self.eval_report = self._load_json(EVAL_REPORT_PATH)

    def _load_yaml(self, path: str) -> dict:
        if not os.path.exists(path):
            raise FileNotFoundError(f"文件不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_json(self, path: str) -> dict:
        if not os.path.exists(path):
            raise FileNotFoundError(f"文件不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def check_gate(self) -> bool:
        summary = self.eval_report.get("summary", {})
        qg = self.guardrails.get("quality_gates", {})

        checks = [
            ("pass_rate",         summary.get("pass_rate", 0),        ">=", qg.get("min_pass_rate", 0.88)),
            ("login_redirect_rate", summary.get("login_redirect_rate", 1), "<=", qg.get("max_login_redirect_rate", 0.003)),
            ("crash_rate",        summary.get("crash_rate", 1),       "<=", qg.get("max_crash_rate", 0.005)),
            ("p95_latency_ms",    summary.get("p95_latency_ms", 99999), "<=", qg.get("max_latency_p95_ms", 9000)),
        ]

        all_passed = True
        print("\n=== 🛡️ 门禁检查 ===")
        for name, value, op, threshold in checks:
            passed = (value >= threshold) if op == ">=" else (value <= threshold)
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status} | {name}: {value:.4f} (阈值 {op} {threshold})")
            if not passed:
                all_passed = False

        print(f"\n最终结果: {'✅ 门禁通过' if all_passed else '❌ 门禁未通过'}")
        return all_passed


if __name__ == "__main__":
    keeper = GateKeeper()
    sys.exit(0 if keeper.check_gate() else 1)
