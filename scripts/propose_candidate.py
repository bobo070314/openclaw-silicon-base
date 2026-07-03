#!/usr/bin/env python3
"""生成候选策略：基于当前配置和失败样本，生成候选策略 YAML"""

import os
import json
import yaml
from datetime import datetime

CANDIDATES_DIR = os.path.join(os.path.dirname(__file__), "..", "configs", "candidates")
BASE_CONFIG = os.path.join(os.path.dirname(__file__), "..", "configs", "base.yaml")
HARDCASES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "evalset", "hardcases.jsonl")


def load_base_config():
    with open(BASE_CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_failures():
    if not os.path.exists(HARDCASES_PATH):
        return []
    with open(HARDCASES_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip() and not line.startswith("#")]


def generate_candidate(base, failures):
    # 从 base 版本号递增
    parts = base.get("version", "v1.0.0").lstrip("v").split(".")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    new_version = f"v{major}.{minor}.{patch + 1}"

    candidate = dict(base)
    candidate["version"] = new_version
    candidate["generated_at"] = datetime.now().isoformat()
    candidate["failure_count"] = len(failures)
    candidate["improvements"] = []

    # 如果有 login_redirect 类型的失败，添加专项治理
    login_failures = [f for f in failures if "login_redirect" in f.get("tags", [])]
    if login_failures:
        candidate["improvements"].append({
            "target": "login_redirect",
            "action": "strengthen_auth_refresh_handling",
            "count": len(login_failures)
        })

    # 如果有 401 失败，添加 fallback 强化
    auth_failures = [f for f in failures if "401" in f.get("tags", [])]
    if auth_failures:
        candidate["improvements"].append({
            "target": "auth_401",
            "action": "add_fallback_on_auth_failure",
            "count": len(auth_failures)
        })

    return candidate


def save_candidate(candidate):
    os.makedirs(CANDIDATES_DIR, exist_ok=True)
    filename = f"{candidate['version']}.yaml"
    path = os.path.join(CANDIDATES_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(candidate, f, default_flow_style=False, allow_unicode=True)
    print(f"[INFO] 候选策略已生成: {path}")

    # 同时写一份 latest.yaml
    latest_path = os.path.join(CANDIDATES_DIR, "latest.yaml")
    with open(latest_path, "w", encoding="utf-8") as f:
        yaml.dump(candidate, f, default_flow_style=False, allow_unicode=True)
    print(f"[INFO] 已更新 latest.yaml")


if __name__ == "__main__":
    base = load_base_config()
    failures = load_failures()
    candidate = generate_candidate(base, failures)
    save_candidate(candidate)
