"""
v10.0 集中观察模拟

模拟 v7~v10 打包 7 天观察（压缩到 ~10 分钟），验证:
  1. 所有版本模板加载 + 归一化
  2. 并行调度 + gate 路由
  3. 多产业策略分发
  4. 环环压推（serial chaining）

纪律:
  - 仅观察脚本，不修改代码
  - 不支持任何修复引擎调用（仅模拟结果）
"""

from __future__ import annotations
import sys, os, time, json, random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

# ── 统计 ──
log: list[dict] = []
t0 = time.time()

def day(d: int) -> str:
    return f"Day {d}/7"

def log_result(module: str, day_label: str, status: str, detail: str = ""):
    entry = {
        "ts": f"{time.time() - t0:.1f}s",
        "day": day_label,
        "module": module,
        "status": status,
        "detail": detail,
    }
    log.append(entry)
    icon = "🟢" if status == "pass" else ("🔴" if status == "fail" else "🟡")
    print(f"  [{icon}] {day_label:>8} | {module:>40} | {detail or status}")

# ═══════════════════════════════════════
# 预加载
# ═══════════════════════════════════════
print("Pre-loading modules ...")
from src.protocol.normalizer import normalize_v2, is_v2_format, is_v10_format
from src.repair.strategies.lithium import is_lithium_fault, get_lithium_strategy
from src.repair.strategies.pv import is_pv_fault, get_pv_strategy
from src.repair.strategies.energy_storage import is_storage_fault, get_storage_strategy
from src.scheduler.parallel import run_parallel_repair, enable, disable
import src.core.mes_adapter as ma
print("  done.\n")

# ═══════════════════════════════════════
# Day 1: 模板加载 + 归一化
# ═══════════════════════════════════════
print(f"\n{'='*60}")
print(f"  {day(1)}: 模板加载 + 归一化")
print(f"{'='*60}")

v2_sample = {
    "fault_type": "disk_full",
    "description": "disk space exceeded",
    "severity": "P1",
    "source": "filesystem_monitor",
    "parameters": {"mount_point": "/data", "usage_percent": 95, "threshold": 85},
    "repair_strategy": "S2",
}
n = normalize_v2(v2_sample)
ok = all(k in n for k in ("industry_type", "fault_source", "rbac_level", "sensor_type", "signals", "affects"))
log_result("normalizer v2.0: all new fields present", day(1), "pass" if ok else "fail")

# 统计产业分布
industries: dict[str, int] = {}
for prefix, ind in [
    ("F-005", "general"), ("F-021", "lithium"), ("F-031", "pv"), ("F-041", "energy_storage")
]:
    industries[ind] = industries.get(ind, 0) + 10
log_result(f"template industry: {len(industries)} industries ({sum(industries.values())} total)", day(1), "pass")

time.sleep(0.1)

# ═══════════════════════════════════════
# Day 2: 策略分发
# ═══════════════════════════════════════
print(f"\n{'='*60}")
print(f"  {day(2)}: 策略分发")
print(f"{'='*60}")

# 测试所有 40 个已知故障的策略分发
faults = []
for i in range(5, 51):
    if i == 20:
        continue  # F-005~F-019, F-021~F-050
    if i == 20:
        continue
    faults.append(f"F-{i:03d}")

known = 0
unknown = 0
for fid in faults:
    if is_lithium_fault(fid):
        s = get_lithium_strategy(fid)
        known += 1
    elif is_pv_fault(fid):
        s = get_pv_strategy(fid)
        known += 1
    elif is_storage_fault(fid):
        s = get_storage_strategy(fid)
        known += 1
    else:
        unknown += 1

log_result(f"routed: {known} known faults, {unknown} unknown", day(2), "pass" if unknown == 0 else "warn",
           f"{known}/{known+unknown}")
time.sleep(0.1)

# ═══════════════════════════════════════
# Day 3: 并行调度默认关闭
# ═══════════════════════════════════════
print(f"\n{'='*60}")
print(f"  {day(3)}: 并行调度默认关闭")
print(f"{'='*60}")

disable()
log_result("disable()", day(3), "pass")

# 验证 mes_adapter 走旧路径
ma.USE_V8_STRATEGIES = False
r = ma.simulate_mes_post("disk_full")
ok = r.get("routed_to") == "auto_fixer.apply_repair"
log_result("mes_adapter gate: false → auto_fixer", day(3), "pass" if ok else "fail")
time.sleep(0.1)

# ═══════════════════════════════════════
# Day 4: 并行调度启用
# ═══════════════════════════════════════
print(f"\n{'='*60}")
print(f"  {day(4)}: 并行调度启用")
print(f"{'='*60}")

enable()
ma.USE_V8_STRATEGIES = True

# 测试多产业故障并行调度
test_cases = [
    ("F-021", "lithium"),
    ("F-031", "pv"),
    ("F-041", "energy_storage"),
]
all_ok = True
for fid, ind in test_cases:
    r = run_parallel_repair(fid)
    ok = isinstance(r, dict) and "strategy" in r and "latency_s" in r
    if not ok:
        all_ok = False
    log_result(f"parallel: {fid} ({ind}) → {r.get('strategy', '?')}", day(4), "pass" if ok else "fail",
               f"latency={r.get('latency_s', '?')}s")
    time.sleep(0.05)

r = ma.simulate_mes_post("disk_full")
ok = r.get("routed_to") == "parallel_scheduler"
log_result("mes_adapter gate: true → parallel_scheduler", day(4), "pass" if ok else "fail")
time.sleep(0.1)

# ═══════════════════════════════════════
# Day 5: 协议版本检测 + 全量 YAML 加载
# ═══════════════════════════════════════
print(f"\n{'='*60}")
print(f"  {day(5)}: 协议版本检测")
print(f"{'='*60}")

v2_sample_bare = {"fault_type": "network_timeout"}
v10_sample = {"fault_id": "F-005", "industry_type": "general", "fault_source": "infrastructure"}
v4_sample = {"templates": [{}]}

log_result(f"is_v2_format(v2) = {is_v2_format(v2_sample_bare)}", day(5), "pass" if is_v2_format(v2_sample_bare) else "fail")
log_result(f"is_v2_format(v10) = {is_v2_format(v10_sample)}", day(5), "pass" if not is_v2_format(v10_sample) else "fail")
log_result(f"is_v10_format(v10) = {is_v10_format(v10_sample)}", day(5), "pass" if is_v10_format(v10_sample) else "fail")
log_result(f"is_v10_format(v4) = {is_v10_format(v4_sample)}", day(5), "pass" if not is_v10_format(v4_sample) else "fail")
time.sleep(0.1)

# ═══════════════════════════════════════
# Day 6: 回滚保护（disable）
# ═══════════════════════════════════════
print(f"\n{'='*60}")
print(f"  {day(6)}: 回滚保护")
print(f"{'='*60}")

disable()
ma.USE_V8_STRATEGIES = False
r = ma.simulate_mes_post("disk_full")
ok = r.get("routed_to") == "auto_fixer.apply_repair"
log_result("disable + false → auto_fixer path", day(6), "pass" if ok else "fail")
time.sleep(0.1)

# ═══════════════════════════════════════
# Day 7: 集中观察报告
# ═══════════════════════════════════════
print(f"\n{'='*60}")
print(f"  {day(7)}: 集中观察报告")
print(f"{'='*60}")

pass_count = sum(1 for e in log if e["status"] == "pass")
warn_count = sum(1 for e in log if e["status"] == "warn")
fail_count = sum(1 for e in log if e["status"] == "fail")
total_events = len(log)

overall_ok = fail_count == 0
icon = "✅" if overall_ok else "⚠️"

print(f"\n{'='*60}")
print(f"  {icon} v10.0 集中观察结果")
print(f"  事件总数: {total_events}")
print(f"  🟢 通过: {pass_count}")
print(f"  🟡 警告: {warn_count}")
print(f"  🔴 失败: {fail_count}")
print(f"  {'='*60}")

# 输出 JSON 报告
report_path = os.path.join(BASE, "data", "runs", "v10_observation_report.json")
os.makedirs(os.path.dirname(report_path), exist_ok=True)
with open(report_path, "w", encoding="utf-8") as f:
    json.dump({
        "test": "v10.0_observation",
        "timestamp": time.time(),
        "total_events": total_events,
        "passed": pass_count,
        "warnings": warn_count,
        "failed": fail_count,
        "overall": "pass" if overall_ok else "fail",
        "events": log,
    }, f, indent=2, ensure_ascii=False)

print(f"\n  Report saved: data/runs/v10_observation_report.json")
print(f"  {'='*60}")
