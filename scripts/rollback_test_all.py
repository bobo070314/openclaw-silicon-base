"""
rollback_test_all.py — 批量验证所有 git commit 可回滚 (v2.0)

验证策略:
1. 获取所有关键 commit hash（手动维护清单）
2. 对每个 commit 执行 `git checkout` + 验证关键文件存在
3. 最终切回 main

用法:
  python scripts/rollback_test_all.py              # 完整测试
  python scripts/rollback_test_all.py --quick      # 只测 latest + main
  python scripts/rollback_test_all.py --list       # 只列出待测 commit
"""

import sys
import subprocess
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# (描述, commit hash, 期望存在的文件清单)
KEY_COMMITS = [
    (
        "mes_adapter + gitignore fix",
        "d6cb9b6",
        [
            "README.md",
            "docs/specs/AUTO_FIXER_PROTOCOL_v1.md",
            "src/core/apply_repair.py",
            "src/core/mes_adapter.py",
            "fault_templates/F-005_to_F-020.yaml",
            "scripts/rollback_test_all.py",
        ],
    ),
    (
        "mes_adapter initial",
        "4440fe4",
        [
            "README.md",
            "docs/specs/AUTO_FIXER_PROTOCOL_v1.md",
            "src/core/apply_repair.py",
            "src/core/mes_adapter.py",
            "fault_templates/F-005_to_F-020.yaml",
        ],
    ),
    (
        "F-005~F-020 fault templates",
        "d30b51f",
        [
            "README.md",
            "docs/specs/AUTO_FIXER_PROTOCOL_v1.md",
            "src/core/apply_repair.py",
            "fault_templates/F-005_to_F-020.yaml",
        ],
    ),
    (
        "hoshine template + phase3 docs",
        "6afb0a5",
        [
            "README.md",
            "docs/specs/AUTO_FIXER_PROTOCOL_v1.md",
            "src/core/apply_repair.py",
        ],
    ),
    (
        "initial README + roadmap",
        "5ea1f39",
        [
            "README.md",
            "docs/roadmap/VERSION_EVOLUTION.md",
        ],
    ),
]


def run_git(cmd: list[str], cwd: Path = REPO_ROOT) -> tuple[int, str]:
    """Run a git command and return (returncode, stdout+stderr)."""
    result = subprocess.run(
        ["git"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def verify_commit(hash: str, files: list[str]) -> list[str]:
    """Checkout commit and verify files exist. Return missing file list."""
    rc, out = run_git(["checkout", hash])
    if rc != 0:
        return [f"checkout failed: {out[:200]}"]

    missing = []
    for path in files:
        if not (REPO_ROOT / path).exists():
            missing.append(path)
    return missing


def list_commits():
    """Print key commits list."""
    print(f"{'Description':40s} {'Hash':10s} {'Files to verify':20s} State")
    print("-" * 80)
    for desc, h, files in KEY_COMMITS:
        rc, _ = run_git(["cat-file", "-t", h])
        status = "✅" if rc == 0 else "❌ missing"
        print(f"{desc:40s} {h:10s} {str(len(files))+' files':20s} {status}")


def main():
    parser = argparse.ArgumentParser(description="Batch rollback test for silicon-body-fixer")
    parser.add_argument("--list", action="store_true", help="List key commits and exit")
    parser.add_argument("--quick", action="store_true", help="Only test latest commit + main")
    args = parser.parse_args()

    if args.list:
        list_commits()
        return

    # Verify all hashes exist first
    bad = []
    for desc, h, _ in KEY_COMMITS:
        rc, _ = run_git(["cat-file", "-t", h])
        if rc != 0:
            bad.append((desc, h))
    if bad:
        print("[ERROR] Missing commits:")
        for desc, h in bad:
            print(f"  {desc:40s} {h}")
        sys.exit(1)
    print(f"✅ All {len(KEY_COMMITS)} commits validated. Testing rollback...\n")

    targets = KEY_COMMITS[:1] if args.quick else KEY_COMMITS
    failures = 0

    for desc, h, files in targets:
        errors = verify_commit(h, files)
        if errors:
            print(f"  ❌ {desc:40s} → {errors[0]}")
            failures += 1
        else:
            print(f"  ✅ {desc:40s} → all {len(files)} files OK")

    # Restore main
    rc, out = run_git(["checkout", "main"])
    if rc != 0:
        print(f"\n[ERROR] Failed to restore main: {out}")
        sys.exit(1)
    print(f"\n✅ Restored to main")

    total = len(targets)
    passed = total - failures
    print(f"\n{'='*50}")
    print(f"Rollback Test Results: {passed}/{total} passed")
    if failures == 0:
        print("✅ ALL COMMITS ROLLBACK-READY")
    else:
        print(f"❌ {failures} commit(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
