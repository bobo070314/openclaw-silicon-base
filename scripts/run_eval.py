#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_eval.py - MVP 评测器（新版本，对接 mock_agent）
读取 hardcases.jsonl → 调用 mock_agent → 输出评测报告
"""

import os
import sys
import json
import time
from typing import List, Dict

# 让 Python 能找到同级脚本
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mock_agent import MockAgent

# ===== 配置路径 =====
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARDCASES_PATH = os.path.join(BASE_DIR, "data", "evalset", "hardcases.jsonl")
RUNS_DIR = os.path.join(BASE_DIR, "data", "runs")
OUTPUT_PATH = os.path.join(RUNS_DIR, "latest_eval.json")


class Evaluator:
    def __init__(self):
        self.agent = MockAgent()
        os.makedirs(RUNS_DIR, exist_ok=True)

    def load_hardcases(self) -> List[Dict]:
        if not os.path.exists(HARDCASES_PATH):
            raise FileNotFoundError(f"Hardcases 文件不存在: {HARDCASES_PATH}")

        cases = []
        with open(HARDCASES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    cases.append(json.loads(line))
        return cases

    def run_eval(self) -> Dict:
        hardcases = self.load_hardcases()
        if not hardcases:
            print("[WARN] 没有 hardcase 用例")
            return self._empty_report()

        metrics = {
            "total_cases": 0,
            "passed_cases": 0,
            "failed_cases": 0,
            "latency_sum": 0,
            "latencies": [],
            "login_redirect_count": 0,
            "401_count": 0,
            "cases_with_test_evidence": 0,
            "cases_missing_test_evidence": 0,
            "total_tokens": 0,
            "cost_by_role": {}
        }

        collaboration_chain = []

        require_test_evidence = os.environ.get("REQUIRE_TEST_EVIDENCE", "1") == "1"

        for case in hardcases:
            metrics["total_cases"] += 1
            result = self.agent.handle_request(case)

            if result["error"] == "401":
                metrics["401_count"] += 1
            if result["login_redirect"]:
                metrics["login_redirect_count"] += 1

            # 检查测试证据
            expected = case.get("expected", {})
            must_include = expected.get("must_include", [])
            has_test_evidence = (
                "测试结果" in str(must_include)
                or "通过/失败" in str(must_include)
                or "回滚点" in str(must_include)
            )

            if result["passed"]:
                metrics["passed_cases"] += 1
                metrics["latency_sum"] += result["latency"]
                metrics["latencies"].append(result["latency"])
            else:
                metrics["failed_cases"] += 1

            if has_test_evidence:
                metrics["cases_with_test_evidence"] += 1
            else:
                metrics["cases_missing_test_evidence"] += 1

            # 统计 Token 消耗
            tokens = result.get("tokens", 0)
            if tokens is None:
                tokens = 0
            metrics["total_tokens"] += tokens
            role = result.get("role", "other")
            if role not in metrics["cost_by_role"]:
                metrics["cost_by_role"][role] = 0
            metrics["cost_by_role"][role] += tokens

            # 记录协作链
            if result.get("context_passed"):
                collaboration_chain.append({
                    "from": result["role"],
                    "to": result.get("target_role"),
                    "hc_id": result["hc_id"],
                    "status": "PASS" if result["passed"] else "FAIL"
                })

        total = metrics["total_cases"]
        pass_rate = metrics["passed_cases"] / total if total > 0 else 0
        avg_latency = metrics["latency_sum"] / len(metrics["latencies"]) if metrics["latencies"] else 0
        sorted_lat = sorted(metrics["latencies"])
        p95 = sorted_lat[int(len(sorted_lat) * 0.95)] if sorted_lat else 0
        login_redirect_rate = metrics["login_redirect_count"] / total if total > 0 else 0
        crash_rate = metrics["failed_cases"] / total if total > 0 else 0
        auth_401_rate = metrics["401_count"] / total if total > 0 else 0
        require_test_evidence = os.environ.get("REQUIRE_TEST_EVIDENCE", "1") == "1"
        missing_test_evidence = metrics["cases_missing_test_evidence"]
        has_test_evidence_gate = missing_test_evidence == 0 if require_test_evidence else True

        daily_budget = int(os.environ.get("COST_BUDGET_DAILY", "50000"))
        total_tokens = metrics["total_tokens"]
        remaining = max(0, daily_budget - total_tokens)
        usage_pct = round((total_tokens / daily_budget) * 100, 2) if daily_budget > 0 else 0

        return {
            "run_id": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "suite": "hardcases",
            "summary": {
                "total_cases": total,
                "passed_cases": metrics["passed_cases"],
                "failed_cases": metrics["failed_cases"],
                "pass_rate": round(pass_rate, 4),
                "avg_latency_ms": round(avg_latency, 2),
                "p95_latency_ms": round(p95, 2),
                "login_redirect_rate": round(login_redirect_rate, 4),
                "crash_rate": round(crash_rate, 4),
                "auth_401_rate": round(auth_401_rate, 4),
                "cases_with_test_evidence": metrics["cases_with_test_evidence"],
                "cases_missing_test_evidence": metrics["cases_missing_test_evidence"],
                "test_evidence_gate_passed": has_test_evidence_gate
            },
            "cost_breakdown": {
                "total_tokens": total_tokens,
                "by_role": metrics["cost_by_role"],
                "budget_daily": daily_budget,
                "remaining_tokens": remaining,
                "usage_pct": usage_pct
            },
            "collaboration_chain": collaboration_chain
        }

    def _empty_report(self) -> Dict:
        return {
            "run_id": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "suite": "hardcases",
            "summary": {
                "total_cases": 0, "passed_cases": 0, "failed_cases": 0,
                "pass_rate": 0, "avg_latency_ms": 0, "p95_latency_ms": 0,
                "login_redirect_rate": 0, "crash_rate": 0, "auth_401_rate": 0
            },
            "cost_breakdown": {
                "total_tokens": 0,
                "by_role": {},
                "budget_daily": 50000,
                "remaining_tokens": 50000,
                "usage_pct": 0
            }
        }

    def save_report(self, report: Dict):
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[SUCCESS] 评测报告已保存: {OUTPUT_PATH}")
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    evaluator = Evaluator()
    report = evaluator.run_eval()
    evaluator.save_report(report)
