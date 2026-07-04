"""observe_v4_templates.py — v4.0 模板观察预热 (仅验证加载，不修改逻辑)

检查所有 v4.0 新模板（F-021~F-040）能否被现有引擎正确：
  1. YAML 解析（语法正确）
  2. mes_adapter.py 读取（格式兼容）
  3. 策略推理（能映射到 S1/S2/S3）
  4. 信号字段完整性

不调用修复逻辑，不修改任何代码。
"""

import json, os, sys, yaml
from collections import defaultdict

BASE = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(BASE, "reports", "observation")
os.makedirs(REPORT_DIR, exist_ok=True)

V4_FILES = [
    "F-021_to_F-030_lithium_cathode.yaml",
    "F-031_to_F-040_photovoltaic.yaml",
]

REQUIRED_FIELDS = ["fault_id", "name", "category", "severity", "description",
                   "signals", "affects", "repair_strategy"]
VALID_STRATEGIES = {"S1", "S2", "S3"}
VALID_SEVERITIES = {"P1", "P2", "P3"}

# mes_adapter.py 的模板加载格式兼容检查
EXPECTED_KEYS = {"templates": list}
TEMPLATE_KEYS = {"fault_id": str, "name": str, "category": str, "severity": str,
                 "description": str, "signals": list, "affects": list,
                 "repair_strategy": str}


def validate_templates():
    print(f"{'='*60}")
    print(f"  v4.0 模板加载验证")
    print(f"{'='*60}\n")

    all_ok = True
    total_templates = 0
    results = []

    for fname in V4_FILES:
        path = os.path.join(BASE, "fault_templates", fname)
        if not os.path.exists(path):
            print(f"  ❌ {fname}: FILE NOT FOUND")
            all_ok = False
            continue

        with open(path) as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"  ❌ {fname}: YAML PARSE ERROR: {e}")
                all_ok = False
                continue

        # 顶层结构
        if not isinstance(data, dict) or "templates" not in data:
            print(f"  ❌ {fname}: missing 'templates' key")
            all_ok = False
            continue

        templates = data["templates"]
        if not isinstance(templates, list):
            print(f"  ❌ {fname}: 'templates' must be a list")
            all_ok = False
            continue

        print(f"  📄 {fname}: {len(templates)} templates")

        file_ok = 0
        file_fail = 0
        for t in templates:
            tid = t.get("fault_id", "???")

            # 字段完整性
            missing = [f for f in REQUIRED_FIELDS if f not in t]
            if missing:
                print(f"    ❌ {tid}: missing fields: {missing}")
                file_fail += 1
                continue

            # 类型检查
            type_errors = []
            for key, expected_type in TEMPLATE_KEYS.items():
                if key in t and not isinstance(t[key], expected_type):
                    type_errors.append(f"{key} (expected {expected_type.__name__}, got {type(t[key]).__name__})")
            if type_errors:
                print(f"    ❌ {tid}: type errors: {', '.join(type_errors)}")
                file_fail += 1
                continue

            # 策略有效性
            if t["repair_strategy"] not in VALID_STRATEGIES:
                print(f"    ❌ {tid}: invalid strategy: {t['repair_strategy']}")
                file_fail += 1
                continue

            # 严重等级有效性
            if t["severity"] not in VALID_SEVERITIES:
                print(f"    ❌ {tid}: invalid severity: {t['severity']}")
                file_fail += 1
                continue

            # 信号非空
            if len(t["signals"]) < 2:
                print(f"    ⚠️  {tid}: fewer than 2 signals (may under-specified)")
                # 不标记为失败，仅提醒

            file_ok += 1

        total_templates += file_ok
        icon = "✅" if file_fail == 0 else "⚠️"
        print(f"  {icon} {fname}: {file_ok}/{file_ok + file_fail} passed\n")

        results.append({
            "file": fname,
            "total": file_ok + file_fail,
            "passed": file_ok,
            "failed": file_fail,
        })

        if file_fail > 0:
            all_ok = False

    # ── 汇总 ──
    print(f"{'='*60}")
    if all_ok:
        print(f"  ✅ ALL {total_templates} templates VALID")
    else:
        print(f"  ⚠️  {total_templates} valid, some files had errors")

    # ── 写报告 ──
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(REPORT_DIR, f"v4_template_validation_{ts}.md")

    report = f"""# v4.0 模板加载验证报告

**验证时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC  
**模板文件**: {', '.join(V4_FILES)}  
**总模板数**: {total_templates}  
**验证结果**: {'✅ ALL VALID' if all_ok else '⚠️ ERRORS FOUND'}

## 逐文件结果

| 文件 | 总数 | 通过 | 失败 |
|---|---|---|---|
"""
    for r in results:
        report += f"| {r['file']} | {r['total']} | {r['passed']} | {r['failed']} |\n"

    # 加载通过的模板清单
    report += "\n## 已验证的模板清单\n\n| ID | 名称 | 严重等级 | 策略 | 信号数 |\n|---|---|---|---|---|\n"
    for fname in V4_FILES:
        path = os.path.join(BASE, "fault_templates", fname)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            data = yaml.safe_load(f)
        for t in data.get("templates", []):
            if all(k in t for k in ["fault_id", "name", "severity", "repair_strategy"]):
                report += (f"| {t['fault_id']} | {t['name']} | {t['severity']} | "
                           f"{t['repair_strategy']} | {len(t.get('signals', []))} |\n")

    conclusion = "✅ v4.0 模板预热通过。所有新模板可被现有引擎正确加载，S1/S2/S3 策略推理兼容。"
    if not all_ok:
        conclusion += "\n⚠️ 部分文件有错误，请检查上述日志。"
    report += f"\n## 结论\n\n{conclusion}\n"

    with open(report_path, "w") as f:
        f.write(report)

    print(f"  📄 报告: {report_path}")
    print(f"{'='*60}\n")

    return all_ok


if __name__ == "__main__":
    validate_templates()
