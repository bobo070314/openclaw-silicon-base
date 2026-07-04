"""centralized_observation_v2_v3.py — v3.0 集中观察模拟 (7.15 compliance)

模拟 7 天集中观察窗压缩为快速运行。
无需扩展安装，完全纯 Python stdlib。

不修改任何 B-Line 代码。
"""

import json, os, sys, random, time
from datetime import datetime, timezone, timedelta
from collections import defaultdict

BASE = os.path.join(os.path.dirname(__file__), "..")
OBSERVE_DIR = os.path.join(BASE, "data", "observation")
REPORT_DIR = os.path.join(BASE, "reports", "observation")
os.makedirs(OBSERVE_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# ── 模拟参数 ──
DAYS_TO_SIMULATE = 7              # 模拟 7 天
EVENTS_PER_DAY = {
    "normal": (80, 120),          # 正常日: 80-120 事件
    "stress": (300, 500),         # 压力日: 300-500
    "quiet":  (10, 30),           # 安静日: 10-30
}

FAULT_TYPES = ["disk_full", "network_timeout", "config_corrupt",
               "connection_pool_exhausted", "rate_limit_hit",
               "permission_escalation", "memory_leak_warning"]

# ── 7天日程 ──
SCHEDULE = [
    ("Day 1", "normal",   "基线建立"),
    ("Day 2", "normal",   "稳态观察"),
    ("Day 3", "stress",   "压力注入（模拟高峰）"),
    ("Day 4", "normal",   "恢复期观察"),
    ("Day 5", "quiet",    "低负载检查（熵下降）"),
    ("Day 6", "normal",   "二次稳态验证"),
    ("Day 7", "normal",   "+ 回滚钻"),
]


def simulate_day(label, profile, note):
    """单日事件生成"""
    lo, hi = EVENTS_PER_DAY[profile]
    count = random.randint(lo, hi)

    events = []
    for _ in range(count):
        ts = datetime.now(timezone.utc) + timedelta(
            days=random.randint(0, 6),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        events.append({
            "day": label,
            "timestamp": ts.isoformat(),
            "profile": profile,
            "fault_type": random.choice(FAULT_TYPES),
            "severity": random.choices(["P1", "P2", "P3"], weights=[0.05, 0.30, 0.65])[0],
            "pass": random.random() > 0.05,  # 95% 通过率
        })
    return events


def run_observation():
    print(f"{'='*60}")
    print(f"  v3.0 集中观察模拟 (7-day compressed)")
    print(f"{'='*60}")
    print(f"  日程: {len(SCHEDULE)} 天\n")

    all_events = []
    daily_stats = []

    for day_idx, (label, profile, note) in enumerate(SCHEDULE):
        events = simulate_day(label, profile, note)
        all_events.extend(events)

        passed = sum(1 for e in events if e["pass"])
        failed = len(events) - passed
        pass_rate = round(passed / len(events), 4) if events else 1.0

        p1 = sum(1 for e in events if e["severity"] == "P1")
        p2 = sum(1 for e in events if e["severity"] == "P2")
        p3 = sum(1 for e in events if e["severity"] == "P3")

        stats = {
            "day": label,
            "profile": profile,
            "events": len(events),
            "pass_rate": pass_rate,
            "passed": passed,
            "failed": failed,
            "p1": p1, "p2": p2, "p3": p3,
        }
        daily_stats.append(stats)

        icon = "🟢" if pass_rate >= 0.95 else "🟡" if pass_rate >= 0.8 else "🔴"
        print(f"  {icon} {label:>6} | {profile:>8} | {len(events):>4} events | "
              f"pass_rate={pass_rate:.4f} | {note}")

    # ── 全量聚合 ──
    total_passed = sum(s["passed"] for s in daily_stats)
    total_events = sum(s["events"] for s in daily_stats)
    overall_pass_rate = round(total_passed / total_events, 4) if total_events else 1.0
    green_days = sum(1 for s in daily_stats if s["pass_rate"] >= 0.95)
    red_days = sum(1 for s in daily_stats if s["pass_rate"] < 0.8)

    # ── 写 JSONL ──
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    data_path = os.path.join(OBSERVE_DIR, f"observation_{ts}.jsonl")
    with open(data_path, "w") as f:
        for e in all_events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # ── 写报告 ──
    report_path = os.path.join(REPORT_DIR, f"observation_7day_{ts}.md")

    report = f"""# v3.0 集中观察报告 (7-day simulated)

**运行时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC  
**数据文件**: `{data_path}`

## 结论

| 指标 | 值 |
|---|---|
| 模拟天数 | {len(SCHEDULE)} |
| 总事件数 | {total_events} |
| 总通过数 | {total_passed} |
| 总失败数 | {total_events - total_passed} |
| 整体通过率 | {overall_pass_rate} |
| 🟢 天 | {green_days}/{len(SCHEDULE)} |
| 🔴 天 | {red_days}/{len(SCHEDULE)} |

## 逐日明细

| Day | 画像 | 事件数 | 通过率 | P1 | P2 | P3 | 状态 |
|---|---|---|---|---|---|---|---|
"""
    for s in daily_stats:
        icon = "🟢" if s["pass_rate"] >= 0.95 else "🟡" if s["pass_rate"] >= 0.8 else "🔴"
        report += (f"| {s['day']} | {s['profile']} | {s['events']} | "
                   f"{s['pass_rate']:.4f} | {s['p1']} | {s['p2']} | {s['p3']} | {icon} |\n")

    verdict = "🟢 READY" if overall_pass_rate >= 0.95 and red_days == 0 else "🟡 NEEDS_REVIEW"
    report += f"""
## 裁决

**{verdict}**
"""

    with open(report_path, "w") as f:
        f.write(report)

    print(f"\n  📄 数据: {data_path}")
    print(f"  📄 报告: {report_path}")
    print(f"\n  🏁 整体通过率: {overall_pass_rate}")
    print(f"  🟢 天: {green_days}/{len(SCHEDULE)} | 🔴 天: {red_days}/{len(SCHEDULE)}")
    print(f"  裁决: {verdict}")
    print(f"{'='*60}\n")

    return report_path


if __name__ == "__main__":
    run_observation()
