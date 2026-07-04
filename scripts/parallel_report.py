"""parallel_report.py — 多产线并行报告模拟器 (v3.0 7.15 compliance)

不修改任何 B-Line 代码。纯独立脚本。
模拟 3 条产线并行报告日志 + 聚合统计。
"""

import json, os, sys, time, random, hashlib
from datetime import datetime, timezone
from collections import defaultdict

# ── 配置 ──
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "parallel")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports", "parallel")
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs", "parallel_agents")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

PRODUCTION_LINES = [
    {"id": "annealing_01", "name": "退火炉#1", "location": "合盛 1#车间"},
    {"id": "coating_03", "name": "涂布线#3", "location": "合盛 2#车间"},
    {"id": "quality_01", "name": "质检站#1", "location": "合盛 质检中心"},
]

FAULT_TYPES = ["disk_full", "network_timeout", "permission_escalation", "config_corrupt",
               "dependency_offline", "memory_leak_warning", "connection_pool_exhausted",
               "rate_limit_hit", "tcp_connection_timeout", "io_error_retry_limit"]

SEVERITIES = {"P1": 0.05, "P2": 0.30, "P3": 0.65}


def gen_fault():
    """随机产线故障"""
    sev = random.choices(list(SEVERITIES.keys()), weights=list(SEVERITIES.values()))[0]
    ft = random.choice(FAULT_TYPES)
    line = random.choice(PRODUCTION_LINES)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": line["id"],
        "fault_type": ft,
        "severity": sev,
        "payload": {"session_id": hashlib.md5(str(random.random()).encode()).hexdigest()[:12]},
    }


def simulate_line(line_id, cycles=5, burst=3):
    """模拟一条产线产生 burst 条故障"""
    events = []
    for _ in range(cycles):
        batch = [gen_fault() for _ in range(burst)]
        # 每个 batch 固定 source
        for b in batch:
            b["source"] = line_id
        events.extend(batch)
    return events


def run_parallel_simulation():
    """模拟 3 条产线并行上报"""
    print(f"{'='*60}")
    print(f"  多产线并行报告模拟")
    print(f"{'='*60}")
    print(f"  产线: {[l['name'] for l in PRODUCTION_LINES]}\n")

    all_events = []
    for line in PRODUCTION_LINES:
        events = simulate_line(line["id"], cycles=4, burst=3)
        all_events.extend(events)
        print(f"  ✅ {line['name']:>10} | {line['location']} | {len(events)} 条事件")

    # 写入 JSONL
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DATA_DIR, f"parallel_{ts}.jsonl")
    with open(path, "w") as f:
        for e in all_events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"\n  📄 已写入: {path} ({len(all_events)} events)")

    # ── 聚合统计 ──
    by_severity = defaultdict(int)
    by_type = defaultdict(int)
    by_source = defaultdict(int)
    for e in all_events:
        by_severity[e["severity"]] += 1
        by_type[e["fault_type"]] += 1
        by_source[e["source"]] += 1

    print("\n  严重等级分布:")
    for s in ["P1", "P2", "P3"]:
        print(f"    {s}: {by_severity.get(s, 0)} 条")

    print("\n  产线分布:")
    for line in PRODUCTION_LINES:
        cnt = by_source.get(line["id"], 0)
        pct = round(cnt / len(all_events) * 100, 1) if all_events else 0
        print(f"    {line['name']:>10}: {cnt} 条 ({pct}%)")

    # ── 写报告 ──
    report_path = os.path.join(REPORT_DIR, f"parallel_{ts}.md")
    top_types = sorted(by_type.items(), key=lambda x: -x[1])[:5]

    report = f"""# 多产线并行报告 — {ts}

**模拟运行**: 3 lines × 4 cycles × 3 burst = {len(all_events)} events

## 产线分布

| 产线 | 位置 | 事件数 | 占比 |
|---|---|---|---|
"""
    for line in PRODUCTION_LINES:
        cnt = by_source.get(line["id"], 0)
        pct = round(cnt / len(all_events) * 100, 1) if all_events else 0
        report += f"| {line['name']} | {line['location']} | {cnt} | {pct}% |\n"

    report += f"""
## 严重等级

| 等级 | 数量 |
|---|---|
| P1 | {by_severity.get('P1', 0)} |
| P2 | {by_severity.get('P2', 0)} |
| P3 | {by_severity.get('P3', 0)} |

## Top 故障类型

| 类型 | 数量 |
|---|---|
"""
    for t, c in top_types:
        report += f"| {t} | {c} |\n"

    report += f"""
## 结论

- 多产线并行上报能力: ✅
- 数据全量记录: ✅ (`data/parallel/`)
- 报告自动生成: ✅ (`reports/parallel/`)
"""

    with open(report_path, "w") as f:
        f.write(report)
    print(f"\n  📄 报告: {report_path}")
    print(f"{'='*60}\n")
    return report_path


if __name__ == "__main__":
    run_parallel_simulation()
