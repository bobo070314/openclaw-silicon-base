#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
comment_on_pr.py - PR 评论机器人
当门禁 FAIL 时，自动在 GitHub PR 发结构化评论。

用法：
    python scripts/comment_on_pr.py --pr 1

环境变量：
    GITHUB_TOKEN          GitHub Personal Access Token
    GITHUB_REPOSITORY     仓库名 (默认: bobo070314/openclaw-silicon-base)
    PR_NUMBER             PR 号（也可用 --pr 指定）
    EVAL_REPORT_PATH      评测报告路径 (默认: data/runs/latest_eval.json)
    ROLLBACK_REPORT_PATH  回滚报告路径 (默认: data/runs/rollback_report.json)

行为：
    - 有 PR_NUMBER 且门禁 FAIL → 发评论，exit 0
    - 无 PR_NUMBER → 打印 "PR comment skipped"，exit 0
    - Dry run → 只打印不发送
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.parse


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        print(f"WARN: 文件不存在: {path}")
        return {}
    # Handle UTF-8 BOM that PowerShell may add
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def get_thresholds() -> dict:
    """从 gate_check.py 逻辑中提取阈值"""
    return {
        "pass_rate": (">=", 0.88),
        "login_redirect_rate": ("<=", 0.003),
        "crash_rate": ("<=", 0.005),
        "p95_latency_ms": ("<=", 9000),
    }


def build_comment_body(eval_report: dict, rollback_report: dict, template_path: str) -> str:
    summary = eval_report.get("summary", {})
    thresholds = get_thresholds()

    # Build failed metrics rows
    failed_lines = []
    for metric, (op, threshold) in thresholds.items():
        value = summary.get(metric, None)
        if value is None:
            continue
        passed = (value >= threshold) if op == ">=" else (value <= threshold)
        if not passed:
            failed_lines.append(f"- **{metric}:** {value:.4f} (阈值 {op} {threshold}) ❌")

    # Test evidence gate
    missing_evidence = summary.get("cases_missing_test_evidence", 0)
    if missing_evidence > 0:
        failed_lines.append(f"- **test_evidence_gate:** {missing_evidence} cases missing evidence ❌")

    failed_metrics = "\n".join(failed_lines) if failed_lines else "  (none - all metrics passed)"

    # Rollback status
    rollback_status = rollback_report.get("rollback_status", "N/A")
    rb_verdict = "EXECUTED" if "SUCCESS" in str(rollback_status) or "SUCCESS" in str(rollback_report.get("verify_status", "")) else "SKIPPED"

    # Paths (relative for readability)
    eval_path = os.environ.get("EVAL_REPORT_PATH", "data/runs/latest_eval.json")
    rollback_path = os.environ.get("ROLLBACK_REPORT_PATH", "data/runs/rollback_report.json")

    # Load template or use default
    template = ""
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
    else:
        template = (
            "## 🛡️ OpenClaw Self-Evolve: Gate Failure Report\n\n"
            "**gate_result:** FAIL\n"
            "**rollback:** {{ROLLBACK_STATUS}}\n\n"
            "### 📊 Failed Metrics\n"
            "{{FAILED_METRICS}}\n\n"
            "### 📁 Audit Trail\n"
            "- **Eval report:** `{{EVAL_REPORT_PATH}}`\n"
            "- **Rollback report:** `{{ROLLBACK_REPORT_PATH}}`\n"
            "- **Config backup:** `{{CONFIG_BACKUP}}`\n"
            "- **Run ID:** `{{RUN_ID}}`\n\n"
            "### 🚀 Next Steps\n"
            "1. Review the gate check logs above.\n"
            "2. Fix the failing metrics or configuration.\n"
            "3. Re-run the pipeline.\n\n"
            "---\n"
            "*This message was generated automatically by the Silicon Body Group CI pipeline.*"
        )

    body = template.replace("{{ROLLBACK_STATUS}}", rb_verdict)
    body = body.replace("{{FAILED_METRICS}}", failed_metrics)
    body = body.replace("{{EVAL_REPORT_PATH}}", eval_path)
    body = body.replace("{{ROLLBACK_REPORT_PATH}}", rollback_path)
    body = body.replace("{{CONFIG_BACKUP}}", rollback_report.get("config_backup", "N/A"))
    body = body.replace("{{RUN_ID}}", eval_report.get("run_id", rollback_report.get("run_id", "N/A")))

    return body


def post_comment(repo: str, pr_number: int, body: str, token: str) -> dict:
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    data = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="PR 评论机器人 - 门禁失败自动评论")
    parser.add_argument("--pr", type=int, default=None, help="PR 号")
    parser.add_argument("--repo", default=None, help="GitHub 仓库 (owner/repo)")
    parser.add_argument("--dry-run", action="store_true", help="仅打印不发送")
    parser.add_argument("--eval-report", default=None, help="评测报告路径")
    parser.add_argument("--rollback-report", default=None, help="回滚报告路径")
    args = parser.parse_args()

    # Resolve PR number
    pr_number = args.pr or os.environ.get("PR_NUMBER")
    if not pr_number:
        print("PR comment skipped (no PR_NUMBER set)")
        sys.exit(0)

    try:
        pr_number = int(pr_number)
    except ValueError:
        print(f"PR comment skipped (invalid PR_NUMBER: {pr_number})")
        sys.exit(0)

    # Resolve repo
    repo = args.repo or os.environ.get("GITHUB_REPOSITORY", "bobo070314/openclaw-silicon-base")

    # Resolve paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    eval_path = args.eval_report or os.environ.get(
        "EVAL_REPORT_PATH",
        os.path.join(base_dir, "data", "runs", "latest_eval.json"),
    )
    rollback_path = args.rollback_report or os.environ.get(
        "ROLLBACK_REPORT_PATH",
        os.path.join(base_dir, "data", "runs", "rollback_report.json"),
    )
    template_path = os.path.join(base_dir, "configs", "pr_comment_template.md")

    # Load reports
    eval_report = load_json(eval_path)
    rollback_report = load_json(rollback_path)

    # Check if gate actually failed (skip if all passed)
    summary = eval_report.get("summary", {})
    thresholds = get_thresholds()
    all_passed = True
    for metric, (op, threshold) in thresholds.items():
        value = summary.get(metric, None)
        if value is None:
            continue
        passed = (value >= threshold) if op == ">=" else (value <= threshold)
        if not passed:
            all_passed = False
            break
    # Also check test_evidence gate
    missing_evidence = summary.get("cases_missing_test_evidence", 0)
    if missing_evidence > 0:
        all_passed = False

    if all_passed:
        print("PR comment skipped (all gates passed)")
        sys.exit(0)

    # Build body
    body = build_comment_body(eval_report, rollback_report, template_path)

    if args.dry_run:
        print("=== DRY RUN: Would post this comment ===")
        print(body)
        print("=== END DRY RUN ===")
        sys.exit(0)

    # Post
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("FAIL: GITHUB_TOKEN environment variable not set")
        sys.exit(1)

    try:
        result = post_comment(repo, pr_number, body, token)
        print(f"SUCCESS: Comment posted: {result.get('html_url', 'N/A')}")
    except Exception as e:
        print(f"FAIL: Failed to post comment: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
