#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
real_agent_client.py - 真实 OpenClaw API 客户端
继承 MockAgent，兼容相同接口；失败自动降级到 mock + 审计字段

用法：
    agent = RealAgentClient(provider="real")
    result = agent.handle_request(hardcase)

安全策略：
    1. 默认 provider=mock（防误调）
    2. API Token 只在内存使用，不写入日志
    3. 失败自动降级 + 写 fallback_reason 字段
"""

import os
import sys
import json
import time
import random
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mock_agent import MockAgent


# Fallback token mapping for role-based simulation when real API fails
FALLBACK_TOKEN_MAP = {
    "ceo": 200, "fixer": 800, "coder": 1500,
    "chat": 300, "reviewer": 500
}
DEFAULT_FALLBACK_TOKENS = 500


class RealAgentClient(MockAgent):
    """真实 OpenClaw API 客户端，继承 MockAgent 保证接口兼容"""

    def __init__(self, provider: str = "mock",
                 gateway_url: Optional[str] = None,
                 api_token: Optional[str] = None):
        super().__init__()
        self.provider = provider
        self.gateway_url = gateway_url or os.environ.get(
            "OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18900"
        )
        self.api_token = api_token or os.environ.get("OPENCLAW_API_TOKEN", "")
        self._real_calls = 0
        self._fallback_count = 0

    def handle_request(self, hardcase: Dict[str, Any]) -> Dict[str, Any]:
        """统一入口：provider=real 走真实 API，否则走 mock"""
        if self.provider != "real":
            return super().handle_request(hardcase)

        # 尝试真实 API
        prompt = self._build_prompt(hardcase)
        try:
            response_text, latency = self._call_openclaw(prompt)
            self._real_calls += 1
            parsed = self._parse_response(response_text, hardcase, latency)
            return parsed
        except Exception as e:
            self._fallback_count += 1
            fallback_result = super().handle_request(hardcase)
            fallback_result["fallback_reason"] = str(e)
            fallback_result["provider"] = "mock_fallback"
            return fallback_result

    def _build_prompt(self, hardcase: Dict[str, Any]) -> str:
        """从 hardcase 构建 API prompt"""
        title = hardcase.get("title", "")
        inp = hardcase.get("input", "")
        context = hardcase.get("context", {})
        context_str = json.dumps(context, ensure_ascii=False) if context else ""

        prompt = f"请处理以下任务：\n标题：{title}\n输入：{inp}"
        if context_str:
            prompt += f"\n上下文：{context_str}"
        return prompt

    def _call_openclaw(self, prompt: str) -> tuple:
        """
        调用 OpenClaw /v1/chat/completions
        返回 (response_text, latency_ms)
        """
        url = f"{self.gateway_url.rstrip('/')}/v1/chat/completions"

        body = {
            "model": "openclaw",
            "messages": [{"role": "user", "content": prompt}]
        }
        data = json.dumps(body).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        start = time.time()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode("utf-8")
                resp_json = json.loads(resp_body)
        except urllib.error.HTTPError as e:
            # Read error body for diagnostics, but don't log the token
            error_body = e.read().decode("utf-8", errors="replace")[:200]
            raise RuntimeError(f"API HTTP {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"API call failed: {e}")

        elapsed_ms = int((time.time() - start) * 1000)

        # Extract response text
        choices = resp_json.get("choices", [])
        if not choices:
            raise RuntimeError("API returned empty choices")
        response_text = choices[0].get("message", {}).get("content", "")
        return response_text, elapsed_ms

    def _parse_response(self, response_text: str, hardcase: Dict[str, Any],
                        latency: int) -> Dict[str, Any]:
        """解析真实 API 响应为标准返回格式"""
        hc_id = hardcase.get("id", "unknown")
        context = hardcase.get("context", {})
        role = context.get("role", "coder") if isinstance(context, dict) else "coder"

        # Determine token usage (from API response or estimate)
        tokens_used = len(response_text) // 2  # rough char-to-token estimate
        tokens_used = max(tokens_used, 50)

        return {
            "hc_id": hc_id,
            "response": response_text[:200],
            "error": None,
            "latency": latency,
            "passed": True,
            "login_redirect": 0,
            "tokens": tokens_used,
            "role": role,
            "target_role": context.get("target_role") if isinstance(context, dict) else None,
            "context_passed": False,
            "provider": "real",
            "timestamp": time.time()
        }

    def get_stats(self) -> Dict:
        return {
            "provider": self.provider,
            "real_calls": self._real_calls,
            "fallback_count": self._fallback_count
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Real Agent Client MVP")
    parser.add_argument("--provider", choices=["mock", "real"], default="mock",
                        help="Agent provider (default: mock, for safety)")
    parser.add_argument("--case", default=None, help="Single hardcase JSON")
    parser.add_argument("--file", default=None, help="Hardcases JSONL file")
    args = parser.parse_args()

    client = RealAgentClient(provider=args.provider)

    cases = []
    if args.case:
        cases.append(json.loads(args.case))
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    cases.append(json.loads(line))
    else:
        # Default test case
        cases.append({
            "id": "REAL-TEST-001",
            "title": "Hello World",
            "input": "Say hello and tell me your model name",
            "context": {"role": "chat"}
        })

    for case in cases:
        print(f"\n=== Processing: {case.get('id', 'unknown')} ===")
        print(f"  Input: {case.get('input', '')[:60]}...")
        result = client.handle_request(case)
        print(f"  Response: {result.get('response', '')[:120]}...")
        print(f"  Provider: {result.get('provider', 'N/A')}")
        if result.get("fallback_reason"):
            print(f"  Fallback: {result['fallback_reason']}")
        print(f"  Tokens: {result.get('tokens', 0)}")
        print(f"  Latency: {result.get('latency', 0)}ms")

    print(f"\n=== Stats ===")
    print(json.dumps(client.get_stats(), indent=2))


if __name__ == "__main__":
    main()
