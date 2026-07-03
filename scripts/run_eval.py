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
            "401_count": 0
        }

        for case in hardcases:
            metrics["total_cases"] += 1
            result = self.agent.handle_request(case)

            if result["error"] == "401":
                metrics["401_count"] += 1
            if result["login_redirect"]:
                metrics["login_redirect_count"] += 1

            if result["passed"]:
                metrics["passed_cases"] += 1
                metrics["latency_sum"] += result["latency"]
                metrics["latencies"].append(result["latency"])
            else:
                metrics["failed_cases"] += 1

        total = metrics["total_cases"]
        pass_rate = metrics["passed_cases"] / total if total > 0 else 0
        avg_latency = metrics["latency_sum"] / len(metrics["latencies"]) if metrics["latencies"] else 0
        sorted_lat = sorted(metrics["latencies"])
        p95 = sorted_lat[int(len(sorted_lat) * 0.95)] if sorted_lat else 0
        login_redirect_rate = metrics["login_redirect_count"] / total if total > 0 else 0
        crash_rate = metrics["failed_cases"] / total if total > 0 else 0
        auth_401_rate = metrics["401_count"] / total if total > 0 else 0

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
                "auth_401_rate": round(auth_401_rate, 4)
            }
        }

    def _empty_report(self) -> Dict:
        return {
            "run_id": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "suite": "hardcases",
            "summary": {
                "total_cases": 0, "passed_cases": 0, "failed_cases": 0,
                "pass_rate": 0, "avg_latency_ms": 0, "p95_latency_ms": 0,
                "login_redirect_rate": 0, "crash_rate": 0, "auth_401_rate": 0
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
