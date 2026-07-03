#!/usr/bin/env python3
"""收集失败样本：从 OpenClaw 日志中提取闪退/401/token 错误，存入 hardcases.jsonl"""

import os
import re
import json
from datetime import datetime

# ===== 配置 =====
LOG_PATH = os.path.expandvars(r"%USERPROFILE%\.openclaw\logs\gateway.log")
HARDCASES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "evalset", "hardcases.jsonl")
ERROR_KEYWORDS = [
    r"unauthorized",
    r"token_mismatch",
    r"closed before connect",
    r"login_redirect",
    r"\b401\b",
    r"provider auth state pre-warmed.*401",
    r"token_expired",
    r"OAuth token refresh failed",
    r"auth_permanent"
]


def extract_failures():
    if not os.path.exists(LOG_PATH):
        print(f"[WARN] 日志文件不存在: {LOG_PATH}")
        print("[WARN] 跳过收集，hardcases.jsonl 将保持不变")
        return

    os.makedirs(os.path.dirname(HARDCASES_PATH), exist_ok=True)

    collected = []
    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            for keyword in ERROR_KEYWORDS:
                if re.search(keyword, line, re.IGNORECASE):
                    timestamp_match = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
                    timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().isoformat()

                    # 判断错误类型
                    err_type = "login_redirect" if "login_redirect" in line.lower() else \
                               "auth_401" if "401" in line else \
                               "token_expired" if "token_expired" in line.lower() else \
                               "auth_error"

                    hardcase = {
                        "id": f"hard-{int(datetime.now().timestamp())}-{len(collected)}",
                        "input": "",
                        "expected_type": err_type,
                        "tags": list(set(["auth", "crash", err_type])),
                        "raw_log": line.strip(),
                        "collected_at": timestamp
                    }

                    collected.append(hardcase)
                    break

    if collected:
        with open(HARDCASES_PATH, "a", encoding="utf-8") as f:
            for item in collected:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"[INFO] 收集到 {len(collected)} 个失败样本，已追加到 {HARDCASES_PATH}")
    else:
        print("[INFO] 日志中未发现已知错误模式，hardcases.jsonl 不变")


if __name__ == "__main__":
    extract_failures()
