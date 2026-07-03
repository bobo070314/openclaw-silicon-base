#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
orchestrator.py - 多 Agent 状态机编排器
按 agent_chain.yaml 顺序执行 CEO -> Fixer -> Coder -> Reviewer -> Gate
输出 agent_trace.json 供审计追踪
"""

import os
import sys
import json
import time
import yaml
from typing import Dict, List, Any, Optional

# 让 Python 能找到同级脚本
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mock_agent import MockAgent

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAIN_PATH = os.path.join(BASE_DIR, "configs", "agent_chain.yaml")
TRACE_PATH = os.path.join(BASE_DIR, "data", "runs", "agent_trace.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "runs", "latest_eval.json")


class Orchestrator:
    """多 Agent 状态机编排器"""

    def __init__(self, chain_path: str = CHAIN_PATH):
        self.agent = MockAgent()
        self.chain = self._load_chain(chain_path)
        self.trace: List[Dict] = []
        self.chain_result = {
            "status": "unknown",
            "failed_step": None,
            "total_steps": 0,
            "passed_steps": 0,
            "total_latency_ms": 0
        }

    def _load_chain(self, path: str) -> Dict:
        if not os.path.exists(path):
            print(f"[ORCH] WARN: agent_chain.yaml not found at {path}, using defaults")
            return self._default_chain()
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _default_chain(self) -> Dict:
        return {
            "chain": [
                {"role": "ceo", "timeout_seconds": 30, "retry_count": 1,
                 "next_on_success": "fixer", "next_on_failure": None},
                {"role": "fixer", "timeout_seconds": 60, "retry_count": 2,
                 "next_on_success": "coder", "next_on_failure": "coder"},
                {"role": "coder", "timeout_seconds": 120, "retry_count": 1,
                 "next_on_success": "reviewer", "next_on_failure": "reviewer"},
                {"role": "reviewer", "timeout_seconds": 30, "retry_count": 1,
                 "next_on_success": "gate", "next_on_failure": None},
                {"role": "gate", "timeout_seconds": 15, "retry_count": 0,
                 "next_on_success": None, "next_on_failure": None},
            ],
            "global": {
                "trace_path": "data/runs/agent_trace.json",
                "max_chain_runtime_seconds": 300,
                "step_record_fields": ["agent", "status", "latency_ms",
                                       "input_summary", "output_summary", "artifacts"]
            }
        }

    def run_chain(self, hardcases: List[Dict]) -> Dict:
        """执行整条 Agent 链"""
        chain_def = self.chain.get("chain", [])
        if not chain_def:
            print("[ORCH] WARN: empty chain definition")
            return self._empty_result()

        start_time = time.time()
        self.trace = []
        self.chain_result["total_steps"] = len(chain_def)
        self.chain_result["status"] = "running"
        chain_failed = False

        for step in chain_def:
            role = step["role"]
            # Find matching hardcase for this role (simulate task delegation)
            case = self._find_case_for_role(hardcases, role)
            if not case:
                # Synthetic empty task for chain steps without matching hardcase
                case = {
                    "id": f"ORCH-{role.upper()}-001",
                    "input": f"{role} executing chain step",
                    "context": {"role": role}
                }

            print(f"[ORCH] Step: {role} -> processing case {case['id']}")
            step_start = time.time()
            step_result = self.agent.handle_request(case)
            step_elapsed = int((time.time() - step_start) * 1000)

            # Build trace record
            record = {
                "agent": role,
                "status": "PASS" if step_result.get("passed", False) else "FAIL",
                "latency_ms": step_elapsed,
                "input_summary": case.get("input", "")[:80],
                "output_summary": step_result.get("response", "")[:80],
                "artifacts": {
                    "tokens_used": step_result.get("tokens", 0),
                    "target_role": step_result.get("target_role"),
                    "context_passed": step_result.get("context_passed", False)
                }
            }
            self.trace.append(record)

            if step_result.get("passed", False):
                self.chain_result["passed_steps"] += 1
            else:
                chain_failed = True
                self.chain_result["failed_step"] = role
                print(f"[ORCH] FAIL at step '{role}' -> breaking chain")
                # Check next_on_failure
                next_fail = step.get("next_on_failure")
                if not next_fail:
                    self.chain_result["status"] = "chain_broken"
                    break
                else:
                    print(f"[ORCH] -> falling forward to: {next_fail}")
                    continue

            # Check if this was the last step
            next_success = step.get("next_on_success")
            if not next_success:
                self.chain_result["status"] = "chain_complete"
                break

        elapsed = int((time.time() - start_time) * 1000)
        self.chain_result["total_latency_ms"] = elapsed
        if self.chain_result["status"] == "running":
            self.chain_result["status"] = "chain_complete" if not chain_failed else "chain_broken"

        # Save trace
        self._save_trace()

        return {
            "chain_result": self.chain_result,
            "trace": self.trace
        }

    def _find_case_for_role(self, hardcases: List[Dict], role: str) -> Optional[Dict]:
        for case in hardcases:
            ctx = case.get("context", {})
            if isinstance(ctx, dict) and ctx.get("role") == role:
                return case
        return None

    def _save_trace(self):
        trace_dir = os.path.dirname(TRACE_PATH)
        os.makedirs(trace_dir, exist_ok=True)
        output = {
            "run_id": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "chain_result": self.chain_result,
            "trace": self.trace
        }
        with open(TRACE_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"[ORCH] Trace saved: {TRACE_PATH}")
        return output

    def _empty_result(self) -> Dict:
        return {
            "chain_result": {"status": "empty", "failed_step": None, "total_steps": 0,
                             "passed_steps": 0, "total_latency_ms": 0},
            "trace": []
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-Agent Orchestrator MVP")
    parser.add_argument("--cases", default=None, help="Path to hardcases JSONL file")
    parser.add_argument("--chain", default=None, help="Path to agent_chain.yaml")
    args = parser.parse_args()

    cases_path = args.cases or os.path.join(BASE_DIR, "data", "evalset", "hardcases_multi_agent.jsonl")
    chain_path = args.chain or CHAIN_PATH

    # Load hardcases
    if not os.path.exists(cases_path):
        print(f"[ORCH] FAIL: hardcases file not found: {cases_path}")
        sys.exit(1)

    hardcases = []
    with open(cases_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                hardcases.append(json.loads(line))

    print(f"[ORCH] Loaded {len(hardcases)} multi-agent hardcases from {cases_path}")

    # Run orchestrator
    orch = Orchestrator(chain_path)
    result = orch.run_chain(hardcases)

    # Print summary
    cr = result["chain_result"]
    print(f"\n[ORCH] === Chain Result ===")
    print(f"  Status:        {cr['status']}")
    print(f"  Total steps:   {cr['total_steps']}")
    print(f"  Passed steps:  {cr['passed_steps']}")
    print(f"  Failed step:   {cr['failed_step'] or '(none)'}")
    print(f"  Total latency: {cr['total_latency_ms']}ms")
    print(f"\n[ORCH] Trace ({len(result['trace'])} records):")
    for t in result["trace"]:
        print(f"  [{t['status']}] {t['agent']} -> {t.get('artifacts', {}).get('target_role', '-')}  ({t['latency_ms']}ms)")
    print(f"\n[ORCH] Full trace saved to: {TRACE_PATH}")


if __name__ == "__main__":
    main()
