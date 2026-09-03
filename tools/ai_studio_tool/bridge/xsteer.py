"""
Unified Cross-Domain Steering — HoTT Kernel Bridge Domain
Schema Version: 4.1.0-memory
"""

from typing import Any, Dict, Optional

SCHEMA_VERSION = "4.1.0-memory"


def cross_domain_steer(
    scan_root: str = "src",
    shared_graph: Optional[Dict[str, Any]] = None,
    analyzer_output: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Gabungkan codebase steering + memory steering menjadi unified signal."""
    result = {
        "schema_version": SCHEMA_VERSION,
        "mode": "xsteer",
        "scan_root": scan_root,
    }

    # Codebase Steering
    try:
        from core.synthesizer import steer_decoder
        from core.shared_graph import build_shared_graph
        from core.analyzer_registry import run_analyzers
    except ImportError:
        try:
            from decoder_steering import steer_decoder
            from shared_graph import build_shared_graph
            from analyzer_registry import run_analyzers
        except ImportError:
            result["codebase_steering"] = {"error": "codebase modules not available"}
            return result

    if shared_graph is None:
        codebase_res = steer_decoder(scan_root)
    else:
        codebase_res = steer_decoder(
            scan_root,
            shared_graph=shared_graph,
            analyzer_output=analyzer_output,
        )
    codebase_signals = codebase_res.get("steering_signals", {})
    codebase_drift = codebase_res.get("drift_analysis") or {}
    codebase_fingerprint = codebase_res.get("current_fingerprint") or codebase_res.get("fingerprint", {})

    try:
        cg = shared_graph if shared_graph is not None else build_shared_graph(scan_root)
        c_output = analyzer_output
        if c_output is None:
            c_output = run_analyzers(cg, None)
        c_total_files = cg.get("summary", {}).get("total_files", 0)
        c_weights = {"high": 3, "medium": 2, "low": 1, "info": 0}
        c_wsum = sum(
            c_weights.get(f.get("severity", "info"), 0)
            for r in c_output.get("results", {}).values()
            for f in r.get("findings", [])
        )
        c_pressure = c_wsum / max(1, c_total_files)
        codebase_health = round(1.0 / (1.0 + c_pressure), 3)
    except Exception:
        codebase_health = 1.0

    result["codebase_steering"] = {
        "archetype": codebase_fingerprint.get("structural_archetype", "unknown"),
        "health_score": codebase_health,
        "strategy": codebase_signals.get("reasoning_strategy", codebase_res.get("reasoning_strategy", "modular_component_expansion")),
        "budget": codebase_signals.get("reasoning_budget", "medium"),
        "drift": codebase_drift.get("interpretation", "no_baseline") if codebase_drift else "no_baseline",
    }
    if shared_graph is not None:
        result["graph_cache"] = shared_graph.get("cache", {})
    if analyzer_output is not None:
        result["analyzer_cache"] = analyzer_output.get("cache", {})

    # Memory Steering
    try:
        from memory.graph import build_memory_graph
        from memory.analyzers import analyze_manifold, run_memory_analyzers
        from memory.synthesizer import (
            compute_memory_fingerprint, load_memory_baseline,
            detect_memory_drift, generate_memory_steering_signals,
        )
        from memory.runtime import memory_runtime_provenance
    except ImportError:
        try:
            from memory_graph import build_memory_graph
            from memory_analyzers import analyze_manifold, run_memory_analyzers
            from memory_synthesizer import (
                compute_memory_fingerprint, load_memory_baseline,
                detect_memory_drift, generate_memory_steering_signals,
            )
            from memory_runtime import memory_runtime_provenance
        except ImportError:
            result["memory_steering"] = {"error": "memory modules not available"}
            return result

    memory_graph = build_memory_graph()
    manifold_result = analyze_manifold(memory_graph)
    manifold_data = manifold_result.get("manifold", {})

    mem_analyzer_output = run_memory_analyzers(memory_graph)
    sev_counts = {"high": 0, "medium": 0, "low": 0}
    for r in mem_analyzer_output.get("results", {}).values():
        for f in r.get("findings", []):
            sev = f.get("severity", "low")
            if sev in sev_counts:
                sev_counts[sev] += 1

    total_mems = memory_graph["summary"]["total_memories"]
    w_sum = sev_counts["high"] * 3 + sev_counts["medium"] * 2 + sev_counts["low"] * 1
    pressure = w_sum / max(1, total_mems)
    mem_health = round(1.0 / (1.0 + pressure), 3)

    mem_fingerprint = compute_memory_fingerprint(manifold_data, memory_graph["summary"])
    mem_baseline = load_memory_baseline()
    mem_drift = detect_memory_drift(mem_fingerprint, mem_baseline)
    directed_reasoning_count = (
        mem_analyzer_output.get("results", {})
        .get("mem.betti_breakdown", {})
        .get("summary", {})
        .get("directed_reasoning_cycle_witness_count", 0)
    )
    mem_signals = generate_memory_steering_signals(
        mem_fingerprint,
        mem_drift,
        mem_health,
        directed_reasoning_cycle_witness_count=directed_reasoning_count,
    )

    result["memory_steering"] = {
        "archetype": mem_fingerprint.get("memory_archetype", "unknown"),
        "health_score": mem_health,
        "strategy": mem_signals.get("reasoning_strategy", "unknown"),
        "budget": mem_signals.get("reasoning_budget", "medium"),
        "drift": mem_drift.get("interpretation", "no_baseline"),
    }
    result["memory_scope"] = memory_runtime_provenance()

    # Synthesize Cross-Domain Signal
    cb_strat = result["codebase_steering"]["strategy"]
    mem_strat = result["memory_steering"]["strategy"]
    comb_strat = f"{cb_strat}+{mem_strat}"

    weights = {"low": 1, "medium": 2, "high": 3, "extended": 4}
    cb_b = weights.get(result["codebase_steering"]["budget"], 2)
    mem_b = weights.get(result["memory_steering"]["budget"], 2)
    comb_b = max(cb_b, mem_b)
    budget_map = {1: "low", 2: "medium", 3: "high", 4: "extended"}

    result["cross_domain_signal"] = {
        "unified_strategy": comb_strat,
        "recommended_budget": budget_map.get(comb_b, "medium"),
        "regrounding_needed": mem_signals.get("regrounding_needed", False) or codebase_signals.get("regrounding_needed", False),
        "codebase_health": codebase_health,
        "memory_health": mem_health,
    }

    return result
