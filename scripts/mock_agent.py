#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mock_agent.py - Agent 行为模拟器
模拟不同场景的错误率，用于离线评测，不调用真实 OpenClaw API
"""

import json
import random
import time
from typing import Dict, Any


class MockAgent:
    """模拟 Agent 行为，支持不同 hardcase 场景的错误注入"""

    def __init__(self, provider: str = "mock"):
        self.provider = provider
        self.scenario_errors = {
            "HC-401-001": {"rate": 1.0, "error": "401", "latency": 500},
            "HC-401-002": {"rate": 0.8, "error": "401", "latency": 300},
            "HC-PREWARM-001": {"rate": 0.7, "error": "prewarm_failed", "latency": 1000},
            "default": {"rate": 0.1, "error": None, "latency": 200}
        }

    def handle_request(self, hardcase: Dict[str, Any]) -> Dict[str, Any]:
        """模拟 Agent 处理一条 hardcase 请求
        如果 provider=real，尝试真实 API，失败降级到 mock
        """
        # 如果是真实模式，路由到 RealAgentClient
        if self.provider == "real":
            try:
                from real_agent_client import RealAgentClient
                # 只初始化一次，用 lazy import 避免循环依赖
                if not hasattr(self, '_real_client'):
                    self._real_client = RealAgentClient(provider="real")
                return self._real_client.handle_request(hardcase)
            except Exception as e:
                # 如果 RealAgentClient 本身初始化失败，降级到 mock
                result = self._mock_handle(hardcase)
                result["fallback_reason"] = f"real_agent_init_failed: {e}"
                result["provider"] = "mock_fallback"
                return result
        return self._mock_handle(hardcase)

    def _mock_handle(self, hardcase: Dict[str, Any]) -> Dict[str, Any]:
        """纯模拟处理（原有逻辑）"""
        hc_id = hardcase.get("id", "unknown")
        scenario = self.scenario_errors.get(hc_id, self.scenario_errors["default"])

        # 模拟随机错误
        if random.random() < scenario["rate"]:
            error = scenario["error"]
            latency = scenario["latency"]
            response = ""
            passed = False
        else:
            error = None
            latency = scenario["latency"]
            response = f"模拟处理成功：{hardcase.get('input', '')[:60]}..."
            passed = True

        # 按角色模拟不同 Token 消耗
        context = hardcase.get("context", {})
        if isinstance(context, dict):
            role = context.get("role", "coder")
        else:
            role = "coder"
        tokens_map = {"coder": 1500, "fixer": 800, "chat": 300, "ceo": 200, "reviewer": 500}
        tokens = tokens_map.get(role, 500)

        # 模拟上下文传递（多 Agent 协作链）
        target_role = None
        context_passed = False
        if isinstance(context, dict):
            target_role = context.get("target_role")
        if target_role and passed:
            context_passed = True
            response = f"{role} 已将任务传递给 {target_role}"

        # 仅 HC-401-001 触发 login_redirect
        login_redirect = 1 if hc_id == "HC-401-001" and error == "401" else 0

        return {
            "hc_id": hc_id,
            "response": response,
            "error": error,
            "latency": latency,
            "passed": passed,
            "login_redirect": login_redirect,
            "tokens": tokens,
            "role": role,
            "target_role": target_role,
            "context_passed": context_passed,
            "timestamp": time.time()
        }


if __name__ == "__main__":
    # 测试
    agent = MockAgent()
    test_case = {"id": "HC-401-001", "input": "调试模型触发401跳登录页"}
    result = agent.handle_request(test_case)
    print(json.dumps(result, indent=2, ensure_ascii=False))
