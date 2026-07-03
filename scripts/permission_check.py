#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
permission_check.py - RBAC 权限检查
检查指定角色的修改请求是否符合 rbac_policy.yaml 的权限规则。

用法：
    python scripts/permission_check.py --role CEO --changed-files data/runs/changed_files.json

输入：
    --role         角色名（CEO / OPS / SECURITY）
    --changed-files 修改文件列表 JSON 路径

输出：
    返回码 0 = PASS，1 = FAIL
    打印违规模块详情
"""

import os
import sys
import json
import argparse
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RBAC_PATH = os.path.join(BASE_DIR, "configs", "rbac_policy.yaml")


def load_rbac(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"RBAC 策略文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def match_pattern(path: str, pattern: str) -> bool:
    """简单的通配符匹配：* 匹配任意一段"""
    if pattern == "*":
        return True
    parts_path = path.split(".")
    parts_pattern = pattern.split(".")
    if len(parts_path) != len(parts_pattern):
        return False
    for p, pat in zip(parts_path, parts_pattern):
        if pat == "*":
            continue
        if p != pat:
            return False
    return True


def check_permissions(role: str, changed_files: list, rbac: dict) -> tuple:
    """检查权限，返回 (passed: bool, violations: list)"""
    roles = rbac.get("roles", {})
    role_config = roles.get(role)
    if not role_config:
        return False, [f"未知角色: {role}"]

    blocked_patterns = role_config.get("blocked_patterns", [])
    # SECURITY 角色允许所有
    allowed = role_config.get("allowed_paths", [])
    if "*" in allowed:
        return True, []

    violations = []
    for entry in changed_files:
        file_path = entry.get("file", "")
        config_path = entry.get("path", "")
        for pattern in blocked_patterns:
            # 先匹配 config path
            if config_path and match_pattern(config_path, pattern):
                violations.append({
                    "file": file_path,
                    "config_path": config_path,
                    "blocked_by": pattern,
                    "reason": role_config.get("deny_reason", f"{role} 不能修改 {pattern}")
                })
                break
            # 如果没有 config path，直接匹配文件名
            if not config_path and pattern == file_path:
                violations.append({
                    "file": file_path,
                    "config_path": config_path,
                    "blocked_by": pattern,
                    "reason": role_config.get("deny_reason", f"{role} 不能修改 {pattern}")
                })
                break

    return len(violations) == 0, violations


def main():
    parser = argparse.ArgumentParser(description="RBAC 权限检查")
    parser.add_argument("--role", required=True, help="角色名 (CEO / OPS / SECURITY)")
    parser.add_argument("--changed-files", required=True, help="修改文件列表 JSON 路径")
    args = parser.parse_args()

    if not os.path.exists(args.changed_files):
        print(f"permission_gate: FAIL (changed_files 文件不存在: {args.changed_files})")
        sys.exit(1)

    rbac = load_rbac(RBAC_PATH)
    with open(args.changed_files, "r", encoding="utf-8") as f:
        changed_files = json.load(f)

    passed, violations = check_permissions(args.role, changed_files, rbac)

    if passed:
        print(f"permission_gate: PASS (role {args.role} 可以修改所有文件)")
        sys.exit(0)
    else:
        print(f"permission_gate: FAIL (role {args.role} 违反权限)")
        for v in violations:
            print(f"  FAIL: role {args.role} cannot modify {v['config_path']}")
            print(f"        file: {v['file']}")
            print(f"        reason: {v['reason']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
