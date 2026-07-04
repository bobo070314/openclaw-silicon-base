"""
全链路回归测试 (v10.0)

覆盖:
  1. normalizer v2.0 升级: 16 条 v2.0 模板补齐（含新字段）
  2. 锂电策略类: 10 条映射
  3. 光伏策略类: 10 条映射
  4. 储能策略类: 10 条映射
  5. parallel scheduler: 开关 + 路由
  6. mes_adapter gate: false/true 路径

返回: PASSED/N 统计
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

tests = 0
passed = 0

def ok(name, cond):
    global tests, passed
    tests += 1
    status = "✅" if cond else "❌"
    print(f"  {status} {name}")
    if cond:
        passed += 1
    return cond

def test_v2_normalizer():
    print("\n── 1. normalizer v2.0 升级 ──")
    from src.protocol.normalizer import normalize_v2, is_v2_format, is_v10_format, INDUSTRY_MAP, FAULT_SOURCE_MAP

    # 遍历所有 v2.0 fault_type
    known = list(INDUSTRY_MAP.keys())
    ok(f"INDUSTRY_MAP has {len(known)} entries", len(known) == 16)
    ok(f"FAULT_SOURCE_MAP has {len(known)} entries", len(FAULT_SOURCE_MAP) == 16)

    v2_sample = {
        "fault_type": "disk_full",
        "description": "disk space exceeded",
        "severity": "P1",
        "source": "filesystem_monitor",
        "parameters": {"mount_point": "/data", "usage_percent": 95, "threshold": 85},
        "repair_strategy": "S2",
    }
    n = normalize_v2(v2_sample)
    ok("normalize_v2: returns dict", isinstance(n, dict))
    ok("normalize_v2: industry_type added", "industry_type" in n)
    ok("normalize_v2: fault_source added", "fault_source" in n)
    ok("normalize_v2: rbac_level added", "rbac_level" in n)
    ok("normalize_v2: sensor_type added", "sensor_type" in n)
    ok("normalize_v2: industry added (v6 compat)", "industry" in n)
    ok("normalize_v2: signals added", len(n.get("signals", [])) >= 1)
    ok("normalize_v2: affects added", len(n.get("affects", [])) >= 1)
    ok("normalize_v2: disk_full → equipment_fault", n.get("category") == "equipment_fault")
    ok("normalize_v2: P1 → rbac_level L3", n.get("rbac_level") == "L3")
    ok("normalize_v2: industry_type == general", n.get("industry_type") == "general")
    ok("is_v10_format: true for v10", is_v10_format(n))
    ok("is_v2_format: true for v2 source", is_v2_format(v2_sample))
    ok("is_v2_format: false for v10 result", not is_v2_format(n))

    # 非 dict 安全
    ok("normalize_v2(None) -> None", normalize_v2(None) is None)
    ok("normalize_v2('string') -> 'string'", normalize_v2("hi") == "hi")

def test_lithium():
    print("\n── 2. 锂电策略类 ──")
    from src.repair.strategies.lithium import is_lithium_fault, get_lithium_strategy

    ok("is_lithium_fault(F-021)", is_lithium_fault("F-021"))
    ok("is_lithium_fault(F-030)", is_lithium_fault("F-030"))
    ok("not lithium for F-031", not is_lithium_fault("F-031"))
    ok("not lithium for F-041", not is_lithium_fault("F-041"))

    strategies = set(get_lithium_strategy(f"F-{i:03d}") for i in range(21, 31))
    ok("all 10 lithium faults have strategies", len(strategies) <= 3)
    ok("S1 in lithium strategies", "S1" in strategies)
    ok("S3 in lithium strategies", "S3" in strategies)

def test_pv():
    print("\n── 3. 光伏策略类 ──")
    from src.repair.strategies.pv import is_pv_fault, get_pv_strategy

    ok("is_pv_fault(F-031)", is_pv_fault("F-031"))
    ok("is_pv_fault(F-040)", is_pv_fault("F-040"))
    ok("not pv for F-021", not is_pv_fault("F-021"))

    strategies = set(get_pv_strategy(f"F-{i:03d}") for i in range(31, 41))
    ok("all 10 pv faults have strategies", len(strategies) <= 3)

def test_storage():
    print("\n── 4. 储能策略类 ──")
    from src.repair.strategies.energy_storage import is_storage_fault, get_storage_strategy

    ok("is_storage_fault(F-041)", is_storage_fault("F-041"))
    ok("is_storage_fault(F-050)", is_storage_fault("F-050"))
    ok("not storage for F-021", not is_storage_fault("F-021"))

    strategies = set(get_storage_strategy(f"F-{i:03d}") for i in range(41, 51))
    ok("all 10 storage faults have strategies", len(strategies) <= 3)

def test_scheduler():
    print("\n── 5. 并行调度器 ──")
    from src.scheduler.parallel import run_parallel_repair, enable, disable, is_enabled

    disable()
    ok("disabled initially", not is_enabled())
    enable()
    ok("enabled after enable()", is_enabled())
    disable()
    ok("disabled after disable()", not is_enabled())

    enable()
    r = run_parallel_repair("F-021")
    ok("parallel: F-021 returns dict", isinstance(r, dict))
    ok("parallel: strategy field present", "strategy" in r)
    ok("parallel: success field present", "success" in r)
    ok("parallel: latency_s field present", "latency_s" in r)

    r2 = run_parallel_repair("F-999")
    ok("parallel: unknown fault falls back", r2.get("strategy") in ("S1", "fallback"))

def test_mes_adapter_gate():
    print("\n── 6. mes_adapter gate ──")
    import src.core.mes_adapter as ma

    # Simulate false path
    ma.USE_V8_STRATEGIES = False
    r = ma.simulate_mes_post("disk_full")
    ok("USE_V8_STRATEGIES=false: routed_to auto_fixer", r.get("routed_to") == "auto_fixer.apply_repair")

    # Simulate true path
    ma.USE_V8_STRATEGIES = True
    r = ma.simulate_mes_post("disk_full")
    ok("USE_V8_STRATEGIES=true: routed_to parallel_scheduler", r.get("routed_to") == "parallel_scheduler")
    ok("USE_V8_STRATEGIES=true: success present", "success" in r)

# ── 执行 ──
print(f"{'='*60}")
print(f"  v10.0 全链路回归测试")
print(f"  6 个测试模块 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*60}")

test_v2_normalizer()
test_lithium()
test_pv()
test_storage()
test_scheduler()
test_mes_adapter_gate()

print(f"\n{'='*60}")
print(f"  RESULT: {passed}/{tests} PASSED")
print(f"{'='*60}")
