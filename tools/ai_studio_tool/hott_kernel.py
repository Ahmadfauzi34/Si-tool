"""
HoTT Kernel — Unified Entry Point
Schema Version: 3.0.0-kernel

Single entry point untuk seluruh analisis codebase.
Menggantikan 13 tool calls terpisah menjadi 1.

Usage:
    python3 hott_kernel.py analyze src
    python3 hott_kernel.py analyze src --analyzers topo.orphan,topo.entrypoint
    python3 hott_kernel.py analyzers
"""

import os
import sys
import json
import datetime
from typing import Any, Dict, List, Optional

# Import kernel components
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

try:
    from core.shared_graph import SOURCE_EXTENSIONS, build_shared_graph
    SHARED_GRAPH_AVAILABLE = True
except ImportError:
    try:
        from shared_graph import SOURCE_EXTENSIONS, build_shared_graph
        SHARED_GRAPH_AVAILABLE = True
    except ImportError:
        SOURCE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
        SHARED_GRAPH_AVAILABLE = False

try:
    from core.analyzer_registry import run_analyzers, get_available_analyzers
    REGISTRY_AVAILABLE = True
except ImportError:
    try:
        from analyzer_registry import run_analyzers, get_available_analyzers
        REGISTRY_AVAILABLE = True
    except ImportError:
        REGISTRY_AVAILABLE = False

try:
    from codebase.targeted_queries import query_impact, query_outline, query_brief
    TOPO_QUERIES_AVAILABLE = True
except ImportError:
    try:
        from topology_analyzers import query_impact, query_outline, query_brief
        TOPO_QUERIES_AVAILABLE = True
    except ImportError:
        TOPO_QUERIES_AVAILABLE = False

try:
    from core.synthesizer import synthesize_topological_integrity
    SYNTHESIS_AVAILABLE = True
except ImportError:
    try:
        from topological_integrity_orchestrator import synthesize_topological_integrity
        SYNTHESIS_AVAILABLE = True
    except ImportError:
        SYNTHESIS_AVAILABLE = False

try:
    from core.synthesizer import encode_topological_invariants
    ENCODER_AVAILABLE = True
except ImportError:
    try:
        from invariant_encoder import encode_topological_invariants
        ENCODER_AVAILABLE = True
    except ImportError:
        ENCODER_AVAILABLE = False

try:
    from core.synthesizer import establish_baseline, steer_decoder
    STEERING_AVAILABLE = True
except ImportError:
    try:
        from decoder_steering import establish_baseline, steer_decoder
        STEERING_AVAILABLE = True
    except ImportError:
        STEERING_AVAILABLE = False

try:
    from memory.store import (
        store_memory, recall_memories, get_memory_stats,
        load_store, save_store, access_memory, get_associations_for,
        store_association, consolidate_memories,
    )
    from memory.graph import build_memory_graph
    from memory.analyzers import run_memory_analyzers, MEMORY_ANALYZER_REGISTRY
    MEMORY_AVAILABLE = True
except ImportError:
    try:
        from memory_store import (
            store_memory, recall_memories, get_memory_stats,
            load_store, save_store, access_memory, get_associations_for,
            store_association, consolidate_memories,
        )
        from memory_graph import build_memory_graph
        from memory_analyzers import run_memory_analyzers, MEMORY_ANALYZER_REGISTRY
        MEMORY_AVAILABLE = True
    except ImportError:
        MEMORY_AVAILABLE = False

try:
    from memory.synthesizer import (
        compute_memory_fingerprint,
        establish_memory_baseline,
        load_memory_baseline,
        detect_memory_drift,
        generate_memory_steering_signals,
        assemble_memory_prompt_block,
    )
    MEMORY_SYNTH_AVAILABLE = True
except ImportError:
    try:
        from memory_synthesizer import (
            compute_memory_fingerprint,
            establish_memory_baseline,
            load_memory_baseline,
            detect_memory_drift,
            generate_memory_steering_signals,
            assemble_memory_prompt_block,
        )
        MEMORY_SYNTH_AVAILABLE = True
    except ImportError:
        MEMORY_SYNTH_AVAILABLE = False

try:
    from bridge.xanalyze import (
        filter_findings_for_memory,
        auto_store_findings,
        check_consolidation_trigger,
    )
    from bridge.xsteer import cross_domain_steer
    from bridge.xcontext import get_memory_context_for_file
    CROSS_DOMAIN_AVAILABLE = True
except ImportError:
    try:
        from cross_domain_bridge import (
            filter_findings_for_memory,
            auto_store_findings,
            check_consolidation_trigger,
            cross_domain_steer,
            get_memory_context_for_file,
        )
        CROSS_DOMAIN_AVAILABLE = True
    except ImportError:
        CROSS_DOMAIN_AVAILABLE = False

try:
    from context.fibration import (
        init_fiber, lift_to_fiber, descend_from_fiber,
        start_section, add_to_section, get_section_status,
        fiber_status, switch_base,
        transport_from_archive, list_archived_fibers,
    )
    FIBRATION_AVAILABLE = True
except ImportError:
    try:
        from memory_fibration import (
            init_fiber, lift_to_fiber, descend_from_fiber,
            start_section, add_to_section, get_section_status,
            fiber_status, switch_base,
            transport_from_archive, list_archived_fibers,
        )
        FIBRATION_AVAILABLE = True
    except ImportError:
        FIBRATION_AVAILABLE = False

try:
    from memory.kan_extension import left_kan_extension, right_kan_extension, kan_retrieve
    KAN_EXTENSION_AVAILABLE = True
except ImportError:
    try:
        from memory_kan_extension import left_kan_extension, right_kan_extension, kan_retrieve
        KAN_EXTENSION_AVAILABLE = True
    except ImportError:
        KAN_EXTENSION_AVAILABLE = False


CODEBASE_SCHEMA_VERSION = "3.0.0-kernel"


def _utc_timestamp() -> str:
    """Return an explicit UTC timestamp without deprecated naive datetime APIs."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _kernel_error(error_code: str, message: str, **details: Any) -> Dict[str, Any]:
    """Build a stable machine-readable error payload for CLI and API callers."""
    return {
        "schema_version": CODEBASE_SCHEMA_VERSION,
        "error": message,
        "error_code": error_code,
        **details,
    }


def _validate_scan_root(scan_root: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(scan_root):
        return _kernel_error(
            "scan_root_not_found",
            f"Scan root does not exist: {scan_root}",
            scan_root=scan_root,
        )
    if not os.path.isdir(scan_root):
        return _kernel_error(
            "scan_root_not_directory",
            f"Scan root is not a directory: {scan_root}",
            scan_root=scan_root,
        )
    return None


def _validate_output_mode(
    output_mode: str,
    allowed: tuple[str, ...],
) -> Optional[Dict[str, Any]]:
    if output_mode in allowed:
        return None
    return _kernel_error(
        "invalid_output_mode",
        f"Invalid output mode: {output_mode}",
        output_mode=output_mode,
        supported_output_modes=list(allowed),
    )


def _analysis_status(total_files: int, analyzers_failed: int = 0) -> Dict[str, Any]:
    """Describe whether a supported TS/JS analysis domain was discovered."""
    if total_files <= 0:
        state = "empty"
    elif analyzers_failed > 0:
        state = "partial"
    else:
        state = "complete"
    status = {
        "analysis_status": state,
        "supported_source_extensions": list(SOURCE_EXTENSIONS),
    }
    if total_files == 0:
        status["analysis_warning"] = (
            "No supported TypeScript/JavaScript source files were found in scan_root."
        )
    return status


def _emit_cli_result(result: Dict[str, Any]) -> None:
    """Print one JSON result and expose a reliable status to Bash callers."""
    print(json.dumps(result, indent=2))
    if result.get("error"):
        raise SystemExit(2)
    if result.get("unified_summary", {}).get("analyzers_failed", 0) > 0:
        raise SystemExit(3)


def kernel_memory_store(
    memory_type: str,
    content: str,
    source: str = "manual",
    importance: float = 0.5,
    tags: Optional[str] = None,
) -> Dict[str, Any]:
    """Simpan memori baru."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    try:
        memory = store_memory(
            memory_type=memory_type,
            content=content,
            source=source,
            importance=importance,
            tags=tag_list,
        )
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_store",
            "status": "stored",
            "memory": memory,
        }
    except Exception as exc:
        return {"error": str(exc)}


def kernel_memory_recall(
    query: Optional[str] = None,
    memory_type: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Recall memori berdasarkan filter."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    results = recall_memories(
        query=query,
        memory_type=memory_type,
        tags=tag_list,
        limit=limit,
    )

    return {
        "schema_version": "4.0.0-memory",
        "mode": "memory_recall",
        "query": query,
        "memory_type": memory_type,
        "results": results,
        "count": len(results),
    }


def kernel_memory_analyze(
    analyzer_names: Optional[List[str]] = None,
    output_mode: str = "full",
) -> Dict[str, Any]:
    """Analisis topologi memori."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}

    memory_graph = build_memory_graph()
    analyzer_output = run_memory_analyzers(memory_graph, analyzer_names)

    total_findings = sum(
        len(r.get("findings", []))
        for r in analyzer_output.get("results", {}).values()
    )
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for r in analyzer_output.get("results", {}).values():
        for f in r.get("findings", []):
            sev = f.get("severity", "low")
            if sev in severity_counts:
                severity_counts[sev] += 1

    total_memories = memory_graph["summary"]["total_memories"]
    weighted_sum = (
        severity_counts["high"] * 3
        + severity_counts["medium"] * 2
        + severity_counts["low"] * 1
    )
    pressure = weighted_sum / max(1, total_memories)
    health_score = round(1.0 / (1.0 + pressure), 3)

    if output_mode == "summary":
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_analyze",
            "memory_stats": memory_graph["summary"],
            "memory_health_score": health_score,
            "findings_by_severity": severity_counts,
            "total_findings": total_findings,
            "analyzers_run": analyzer_output["analyzers_run"],
        }

    return {
        "schema_version": "4.0.0-memory",
        "mode": "memory_analyze",
        "memory_graph_summary": memory_graph["summary"],
        "analyzers": analyzer_output,
        "memory_health_score": health_score,
        "unified_summary": {
            "total_memories": total_memories,
            "total_associations": memory_graph["summary"]["total_associations"],
            "total_findings": total_findings,
            "findings_by_severity": severity_counts,
            "memory_health_score": health_score,
        },
    }


def kernel_memory_stats() -> Dict[str, Any]:
    """Statistik memory store."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}

    stats = get_memory_stats()
    return {
        "schema_version": "4.0.0-memory",
        "mode": "memory_stats",
        **stats,
    }


def kernel_memory_associate(
    from_id: str,
    to_id: str,
    assoc_type: str,
    strength: float = 0.5,
) -> Dict[str, Any]:
    """Buat asosiasi antara dua memori."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}

    try:
        assoc = store_association(
            from_id=from_id,
            to_id=to_id,
            assoc_type=assoc_type,
            strength=strength,
        )
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_associate",
            "status": "associated",
            "association": assoc,
        }
    except Exception as exc:
        return {"error": str(exc)}


def kernel_memory_consolidate(
    source_ids: List[str],
    content: str,
    tags: Optional[str] = None,
    importance: float = 0.9,
) -> Dict[str, Any]:
    """Konsolidasi memori (colimit operation)."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    try:
        result = consolidate_memories(
            source_ids=source_ids,
            content=content,
            tags=tag_list,
            importance=importance,
        )
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_consolidate",
            "status": "consolidated",
            **result,
        }
    except Exception as exc:
        return {"error": str(exc)}


def kernel_memory_steer(output_mode: str = "full") -> Dict[str, Any]:
    """Memory steering: topology → reasoning strategy."""
    if not MEMORY_AVAILABLE or not MEMORY_SYNTH_AVAILABLE:
        return {"error": "memory modules not available"}

    # Build memory graph
    memory_graph = build_memory_graph()

    # Run manifold analyzer untuk Betti numbers
    from memory.analyzers import analyze_manifold
    manifold_result = analyze_manifold(memory_graph)
    manifold_data = manifold_result.get("manifold", {})

    # Compute health score
    from memory.analyzers import run_memory_analyzers
    analyzer_output = run_memory_analyzers(memory_graph)
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for r in analyzer_output.get("results", {}).values():
        for f in r.get("findings", []):
            sev = f.get("severity", "low")
            if sev in severity_counts:
                severity_counts[sev] += 1

    total_memories = memory_graph["summary"]["total_memories"]
    weighted_sum = (
        severity_counts["high"] * 3
        + severity_counts["medium"] * 2
        + severity_counts["low"] * 1
    )
    pressure = weighted_sum / max(1, total_memories)
    health_score = round(1.0 / (1.0 + pressure), 3)

    # Compute fingerprint
    memory_stats = memory_graph["summary"]
    fingerprint = compute_memory_fingerprint(manifold_data, memory_stats)

    # Load baseline & detect drift
    baseline = load_memory_baseline()
    drift = detect_memory_drift(fingerprint, baseline)

    # Generate steering signals
    signals = generate_memory_steering_signals(fingerprint, drift, health_score)

    # Assemble prompt block
    prompt_block = assemble_memory_prompt_block(fingerprint, drift, signals, health_score)

    if output_mode == "summary":
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_steer",
            "summary": {
                "has_baseline": drift.get("has_baseline", False),
                "drift_interpretation": drift.get("interpretation", "no_baseline"),
                "reasoning_strategy": signals["reasoning_strategy"],
                "reasoning_budget": signals["reasoning_budget"],
                "regrounding_needed": signals["regrounding_needed"],
                "health_score": health_score,
            },
            "steering_signals": signals,
        }

    return {
        "schema_version": "4.0.0-memory",
        "mode": "memory_steer",
        "fingerprint": fingerprint,
        "health_score": health_score,
        "drift_analysis": drift,
        "steering_signals": signals,
        "steering_prompt_block": prompt_block,
    }


def kernel_memory_establish() -> Dict[str, Any]:
    """Establish memory baseline."""
    if not MEMORY_AVAILABLE or not MEMORY_SYNTH_AVAILABLE:
        return {"error": "memory modules not available"}

    # Build graph & compute fingerprint
    memory_graph = build_memory_graph()
    from memory.analyzers import analyze_manifold, run_memory_analyzers
    manifold_result = analyze_manifold(memory_graph)
    manifold_data = manifold_result.get("manifold", {})

    # Compute health score
    analyzer_output = run_memory_analyzers(memory_graph)
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for r in analyzer_output.get("results", {}).values():
        for f in r.get("findings", []):
            sev = f.get("severity", "low")
            if sev in severity_counts:
                severity_counts[sev] += 1

    total_memories = memory_graph["summary"]["total_memories"]
    weighted_sum = (
        severity_counts["high"] * 3
        + severity_counts["medium"] * 2
        + severity_counts["low"] * 1
    )
    pressure = weighted_sum / max(1, total_memories)
    health_score = round(1.0 / (1.0 + pressure), 3)

    # Compute fingerprint
    fingerprint = compute_memory_fingerprint(manifold_data, memory_graph["summary"])

    # Establish baseline
    result = establish_memory_baseline(fingerprint, health_score)

    return {
        "schema_version": "4.0.0-memory",
        "mode": "memory_establish",
        **result,
    }


def kernel_memory_drift() -> Dict[str, Any]:
    """Detect memory drift against baseline."""
    if not MEMORY_AVAILABLE or not MEMORY_SYNTH_AVAILABLE:
        return {"error": "memory modules not available"}

    # Build graph & compute fingerprint
    memory_graph = build_memory_graph()
    from memory.analyzers import analyze_manifold
    manifold_result = analyze_manifold(memory_graph)
    manifold_data = manifold_result.get("manifold", {})

    fingerprint = compute_memory_fingerprint(manifold_data, memory_graph["summary"])

    # Load baseline & detect drift
    baseline = load_memory_baseline()
    drift = detect_memory_drift(fingerprint, baseline)

    return {
        "schema_version": "4.0.0-memory",
        "mode": "memory_drift",
        "fingerprint": fingerprint,
        "drift_analysis": drift,
    }


def kernel_memory_consolidate_by_tag(
    tag: str,
    content: Optional[str] = None,
    importance: float = 0.9,
) -> Dict[str, Any]:
    """Konsolidasi memori berdasarkan tag."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}
    try:
        from memory.store import consolidate_by_tag
        result = consolidate_by_tag(tag=tag, content=content, importance=importance)
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_consolidate_by_tag",
            **result,
        }
    except Exception as exc:
        return {"error": str(exc)}


def kernel_memory_consolidate_auto(
    min_group_size: int = 3,
    importance: float = 0.9,
) -> Dict[str, Any]:
    """Otomatis konsolidasi semua tag groups yang memenuhi threshold."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}
    try:
        from memory.store import consolidate_by_tag_auto
        result = consolidate_by_tag_auto(
            min_group_size=min_group_size,
            importance=importance,
        )
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_consolidate_auto",
            **result,
        }
    except Exception as exc:
        return {"error": str(exc)}


def kernel_memory_unconsolidated_tags() -> Dict[str, Any]:
    """Lihat ringkasan unconsolidated memories by tag."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}
    try:
        from memory.store import get_unconsolidated_by_tag
        result = get_unconsolidated_by_tag()
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_unconsolidated_tags",
            **result,
        }
    except Exception as exc:
        return {"error": str(exc)}


def kernel_memory_betti_breakdown() -> Dict[str, Any]:
    """Hitung β₁ breakdown per kategori edge type."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}
    try:
        from memory.graph import build_memory_graph
        from memory.analyzers import analyze_betti_breakdown
        memory_graph = build_memory_graph()
        result = analyze_betti_breakdown(memory_graph)
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_betti_breakdown",
            **result,
        }
    except Exception as exc:
        return {"error": str(exc)}


def kernel_memory_compact(
    only_consolidated: bool = True,
    memory_type: str = "episodic",
    dry_run: bool = False,
    restore: bool = False,
    restore_all: bool = False,
    restore_id: Optional[str] = None,
    stats: bool = False,
) -> Dict[str, Any]:
    """Memory compact: quotient forgetting untuk archived memories."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}

    try:
        from memory.store import (
            compact_memories, get_archive_stats,
            restore_memory, restore_all_archived,
        )
        from memory.graph import build_memory_graph
        from memory.analyzers import analyze_manifold
    except ImportError as exc:
        return {"error": f"import failed: {exc}"}

    # Mode: stats
    if stats:
        archive_stats = get_archive_stats()
        # Hitung Betti untuk active graph
        active_graph = build_memory_graph(include_archived=False)
        active_manifold = analyze_manifold(active_graph)
        # Hitung Betti untuk full graph (termasuk archived)
        full_graph = build_memory_graph(include_archived=True)
        full_manifold = analyze_manifold(full_graph)

        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_compact_stats",
            "archive_stats": archive_stats,
            "active_graph_betti": active_manifold["manifold"]["betti_numbers"],
            "full_graph_betti": full_manifold["manifold"]["betti_numbers"],
        }

    # Mode: restore
    if restore_all:
        result = restore_all_archived()
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_compact_restore",
            **result,
        }

    if restore_id:
        result = restore_memory(restore_id)
        if result is None:
            return {"error": f"Memory not found: {restore_id}"}
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_compact_restore",
            "restored": result,
        }

    # Mode: compact (dengan Betti impact analysis)
    # Hitung Betti SEBELUM compact
    graph_before = build_memory_graph(include_archived=False)
    manifold_before = analyze_manifold(graph_before)
    betti_before = manifold_before["manifold"]["betti_numbers"]

    # Execute compact
    compact_result = compact_memories(
        only_consolidated=only_consolidated,
        memory_type=memory_type,
        dry_run=dry_run,
    )

    if dry_run:
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_compact",
            **compact_result,
            "betti_before": betti_before,
        }

    # Hitung Betti SESUDAH compact
    graph_after = build_memory_graph(include_archived=False)
    manifold_after = analyze_manifold(graph_after)
    betti_after = manifold_after["manifold"]["betti_numbers"]

    # Hitung Betti impact
    betti_impact = {
        "beta_0": {"before": betti_before["beta_0"], "after": betti_after["beta_0"],
                    "delta": betti_after["beta_0"] - betti_before["beta_0"]},
        "beta_1": {"before": betti_before["beta_1"], "after": betti_after["beta_1"],
                    "delta": betti_after["beta_1"] - betti_before["beta_1"]},
        "beta_2": {"before": betti_before["beta_2"], "after": betti_after["beta_2"],
                    "delta": betti_after["beta_2"] - betti_before["beta_2"]},
    }

    return {
        "schema_version": "4.0.0-memory",
        "mode": "memory_compact",
        **compact_result,
        "betti_before": betti_before,
        "betti_after": betti_after,
        "betti_impact": betti_impact,
    }


def kernel_memory_bridge(
    from_id: str,
    to_id: str,
    assoc_type: str = "semantic",
    strength: float = 0.7,
    safe_mode: bool = True,
) -> Dict[str, Any]:
    """Manual bridge antara dua memories."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}
    try:
        from memory.store import bridge_memories
        result = bridge_memories(
            from_id=from_id,
            to_id=to_id,
            assoc_type=assoc_type,
            strength=strength,
            safe_mode=safe_mode,
        )
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_bridge",
            **result,
        }
    except Exception as exc:
        return {"error": str(exc)}


def kernel_memory_bridge_auto(
    min_shared_tags: int = 1,
    assoc_type: str = "semantic",
    safe_mode: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Auto bridge: hubungkan semantic memories yang share tags."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}
    try:
        from memory.store import bridge_auto
        result = bridge_auto(
            min_shared_tags=min_shared_tags,
            assoc_type=assoc_type,
            safe_mode=safe_mode,
            dry_run=dry_run,
        )
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_bridge_auto",
            **result,
        }
    except Exception as exc:
        return {"error": str(exc)}


def kernel_memory_bridge_candidates(
    min_shared_tags: int = 1,
) -> Dict[str, Any]:
    """Lihat kandidat bridge sebelum eksekusi."""
    if not MEMORY_AVAILABLE:
        return {"error": "memory modules not available"}
    try:
        from memory.store import get_bridge_candidates
        result = get_bridge_candidates(min_shared_tags=min_shared_tags)
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_bridge_candidates",
            **result,
        }
    except Exception as exc:
        return {"error": str(exc)}


def kernel_memory_kan(
    query: str,
    mode: str = "both",
    max_depth: int = 2,
) -> Dict[str, Any]:
    """Kan Extension retrieval: structured completion."""
    if not KAN_EXTENSION_AVAILABLE:
        return {"error": "memory_kan_extension not available"}

    try:
        result = kan_retrieve(query, mode=mode, max_depth=max_depth)
        return {
            "schema_version": "4.0.0-memory",
            "mode": "memory_kan",
            **result,
        }
    except Exception as exc:
        return {"error": str(exc)}


def kernel_xanalyze(
    scan_root: str = ".",
    analyzer_names: Optional[List[str]] = None,
    output_mode: str = "summary",
    auto_store: bool = True,
) -> Dict[str, Any]:
    """
    Cross-Domain Analyze: analisis codebase + auto-store findings ke memory.
    """
    if not SHARED_GRAPH_AVAILABLE or not REGISTRY_AVAILABLE:
        return {"error": "required modules not available"}

    # Step 1: Build graph + run analyzers
    graph = build_shared_graph(scan_root)
    analyzer_output = run_analyzers(graph, analyzer_names)
    analyzer_results = analyzer_output.get("results", {})

    # Step 2: Synthesize (untuk correlations & fingerprint)
    total_files = graph.get("summary", {}).get("total_files", 0)
    health_score = _compute_topological_health_score(analyzer_output, total_files)
    correlations = _detect_cross_analyzer_correlations(graph, analyzer_output)
    fingerprint = {}
    if ENCODER_AVAILABLE:
        enc_res = encode_topological_invariants(scan_root)
        if enc_res.get("available"):
            fingerprint = enc_res.get("topological_fingerprint", {})
    if not fingerprint and "hott.manifold" in analyzer_results:
        manifold_data = analyzer_results["hott.manifold"].get("manifold", {})
        fingerprint = {
            "signature_hash": "sha256:unknown",
            "complexity_score": manifold_data.get("complexity_score", 0.0),
            "structural_archetype": manifold_data.get("structural_archetype", "unknown"),
        }

    # Step 3: Selective filter + auto-store
    store_result = {"stored_count": 0, "skipped": True}
    if auto_store and CROSS_DOMAIN_AVAILABLE:
        storeable = filter_findings_for_memory(analyzer_results, correlations)
        if storeable:
            store_result = auto_store_findings(storeable, scan_root)
        else:
            store_result = {"stored_count": 0, "reason": "no storeable findings"}

    # Step 4: Check consolidation trigger
    consolidation_signal = {"trigger": False}
    if CROSS_DOMAIN_AVAILABLE and store_result.get("stored_count", 0) > 0:
        consolidation_signal = check_consolidation_trigger()

    # Step 5: Format output
    total_findings = sum(
        len(r.get("findings", [])) for r in analyzer_results.values()
    )
    severity_counts = {"high": 0, "medium": 0, "low": 0, "info": 0}
    for r in analyzer_results.values():
        for f in r.get("findings", []):
            sev = f.get("severity", "info")
            if sev in severity_counts:
                severity_counts[sev] += 1

    if output_mode == "summary":
        return {
            "schema_version": "4.0.0-memory",
            "mode": "xanalyze",
            "scan_root": scan_root,
            "analysis_summary": {
                "total_findings": total_findings,
                "findings_by_severity": severity_counts,
                "correlation_count": len(correlations),
                "health_score": health_score,
                "archetype": fingerprint.get("structural_archetype", "unknown"),
            },
            "memory_store_result": store_result,
            "consolidation_signal": {
                "consolidation_candidate": consolidation_signal.get("trigger", False),
                "reasons": consolidation_signal.get("reasons", []),
            },
        }

    return {
        "schema_version": "4.0.0-memory",
        "mode": "xanalyze",
        "scan_root": scan_root,
        "analyzers": analyzer_output,
        "synthesis": {
            "fingerprint": fingerprint,
            "topological_health_score": health_score,
            "correlations": correlations,
        },
        "memory_store_result": store_result,
        "consolidation_signal": consolidation_signal,
    }


def kernel_xsteer(scan_root: str = ".", output_mode: str = "full") -> Dict[str, Any]:
    """Cross-Domain Steer: unified codebase + memory steering."""
    if not CROSS_DOMAIN_AVAILABLE:
        return {"error": "cross_domain_bridge not available"}

    result = cross_domain_steer(scan_root)

    if output_mode == "summary":
        return {
            "schema_version": "4.0.0-memory",
            "mode": "xsteer",
            "codebase": result.get("codebase_steering", {}),
            "memory": result.get("memory_steering", {}),
            "consolidation_candidate": result.get("consolidation_signal", {}).get("consolidation_candidate", False),
        }

    return result


def kernel_xcontext(file_path: str) -> Dict[str, Any]:
    """Cross-Domain Context: recall relevant memories untuk file."""
    if not CROSS_DOMAIN_AVAILABLE:
        return {"error": "cross_domain_bridge not available"}

    return get_memory_context_for_file(file_path)


def kernel_fiber(subcommand: str, args: List[str]) -> Dict[str, Any]:
    """Router untuk fiber operations."""
    if not FIBRATION_AVAILABLE:
        return {"error": "memory_fibration not available"}

    if subcommand == "init":
        task = args[0] if len(args) > 0 else "general"
        focus = args[1] if len(args) > 1 else "general"
        return {"schema_version": "4.0.0-memory", "mode": "fiber_init", **init_fiber(task, focus)}

    elif subcommand == "lift":
        query = None
        mem_type = None
        tags = None
        max_lift = 10
        i = 0
        while i < len(args):
            if args[i] == "--query" and i + 1 < len(args):
                query = args[i + 1]; i += 2
            elif args[i] == "--type" and i + 1 < len(args):
                mem_type = args[i + 1]; i += 2
            elif args[i] == "--tags" and i + 1 < len(args):
                tags = args[i + 1].split(","); i += 2
            elif args[i] == "--max" and i + 1 < len(args):
                try:
                    max_lift = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
            else:
                i += 1
        result = lift_to_fiber(query=query, memory_type=mem_type, tags=tags, max_lift=max_lift)
        return {"schema_version": "4.0.0-memory", "mode": "fiber_lift", **result}

    elif subcommand == "descend":
        memory_id = args[0] if args and not args[0].startswith("--") else None
        descend_all = "--all" in args
        reason = "task_completed"
        for i, arg in enumerate(args):
            if arg == "--reason" and i + 1 < len(args):
                reason = args[i + 1]
        result = descend_from_fiber(memory_id=memory_id, descend_all=descend_all, reason=reason)
        return {"schema_version": "4.0.0-memory", "mode": "fiber_descend", **result}

    elif subcommand == "status":
        return {"schema_version": "4.0.0-memory", "mode": "fiber_status", **fiber_status()}

    elif subcommand == "section_start":
        name = args[0] if len(args) > 0 else "unnamed"
        narrative = args[1] if len(args) > 1 else ""
        result = start_section(name, narrative)
        return {"schema_version": "4.0.0-memory", "mode": "fiber_section_start", **result}

    elif subcommand == "section_add":
        if not args:
            return {"error": "Usage: fiber section_add <memory_id>"}
        result = add_to_section(args[0])
        return {"schema_version": "4.0.0-memory", "mode": "fiber_section_add", **result}

    elif subcommand == "section_status":
        return {"schema_version": "4.0.0-memory", "mode": "fiber_section_status", **get_section_status()}

    elif subcommand == "switch":
        task = args[0] if len(args) > 0 else "new_task"
        focus = args[1] if len(args) > 1 else "new_focus"
        result = switch_base(task, focus)
        return {"schema_version": "4.0.0-memory", "mode": "fiber_switch", **result}

    elif subcommand == "list_archives":
        return kernel_fiber_list_archives()

    elif subcommand == "transport":
        if len(args) < 3:
            return {"error": "Usage: fiber transport <source_fiber_id> <new_task> <new_focus> [--threshold 0.6] [--max 10] [--dry-run]"}
        source_id = args[0]
        new_task = args[1]
        new_focus = args[2]
        threshold = 0.6
        max_transport = 10
        dry_run = False
        i = 3
        while i < len(args):
            if args[i] == "--threshold" and i + 1 < len(args):
                try:
                    threshold = float(args[i + 1])
                except ValueError:
                    pass
                i += 2
            elif args[i] == "--max" and i + 1 < len(args):
                try:
                    max_transport = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
            elif args[i] == "--dry-run":
                dry_run = True
                i += 1
            else:
                i += 1
        return kernel_fiber_transport(source_id, new_task, new_focus, threshold, max_transport, dry_run)

    else:
        return {"error": f"Unknown fiber subcommand: {subcommand}"}


def kernel_fiber_transport(
    source_fiber_id: str,
    new_task: str,
    new_focus: str,
    threshold: float = 0.6,
    max_transport: int = 10,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Parallel transport dari fiber lama ke fiber baru."""
    if not FIBRATION_AVAILABLE:
        return {"error": "memory_fibration not available"}
    
    try:
        result = transport_from_archive(
            source_fiber_id=source_fiber_id,
            new_task=new_task,
            new_focus=new_focus,
            threshold=threshold,
            max_transport=max_transport,
            dry_run=dry_run,
        )
        return {"schema_version": "4.0.0-memory", "mode": "fiber_transport", **result}
    except Exception as exc:
        return {"error": str(exc)}


def kernel_fiber_list_archives() -> Dict[str, Any]:
    """List archived fibers."""
    if not FIBRATION_AVAILABLE:
        return {"error": "memory_fibration not available"}
    
    try:
        result = list_archived_fibers()
        return {"schema_version": "4.0.0-memory", "mode": "fiber_list_archives", **result}
    except Exception as exc:
        return {"error": str(exc)}




def kernel_analyze(
    scan_root: str = ".",
    analyzer_names: Optional[List[str]] = None,
    output_mode: str = "full",
) -> Dict[str, Any]:
    """
    Orkestrasi penuh: build SharedGraph + run analyzers + synthesize.

    Output modes:
    - "full"     : semua data termasuk shared_graph (default)
    - "summary"  : hanya unified_summary + counts
    - "findings" : findings analyzers + summary, tanpa shared_graph
    - "graph"    : hanya shared_graph (tanpa file_map), tanpa analyzers
    """
    if not SHARED_GRAPH_AVAILABLE:
        return {"error": "shared_graph module not found", "available": False}

    root_error = _validate_scan_root(scan_root)
    if root_error:
        return root_error
    output_error = _validate_output_mode(
        output_mode,
        ("full", "summary", "findings", "graph"),
    )
    if output_error:
        return output_error

    # Step 1: Build SharedGraph (1x scan, 1x graph build)
    shared_graph = build_shared_graph(scan_root)

    # Mode graph: langsung return tanpa jalankan analyzers
    if output_mode == "graph":
        graph_output = {k: v for k, v in shared_graph.items() if k != "file_map"}
        return {
            "schema_version": "3.0.0-kernel",
            "mode": "graph",
            "scan_root": scan_root,
            "shared_graph": graph_output,
        }

    # Step 2: Run analyzers
    if REGISTRY_AVAILABLE:
        analyzer_output = run_analyzers(shared_graph, analyzer_names)
    else:
        analyzer_output = {"results": {}, "errors": {}, "analyzers_run": 0}

    # Step 3: Build unified summary
    unified_summary = {
        "total_files": shared_graph["summary"]["total_files"],
        "total_edges": shared_graph["summary"]["total_edges"],
        "total_boundaries": shared_graph["summary"]["total_boundaries"],
        "total_type_shapes": shared_graph["summary"]["total_type_shapes"],
        "entrypoint_count": shared_graph["summary"]["entrypoint_count"],
        "test_file_count": shared_graph["summary"]["test_file_count"],
        "total_findings": sum(
            len(r.get("findings", []))
            for r in analyzer_output.get("results", {}).values()
        ),
        "findings_by_severity": _count_findings_by_severity(analyzer_output),
        "analyzers_run": analyzer_output.get("analyzers_run", 0),
        "analyzers_failed": analyzer_output.get("analyzers_failed", 0),
        "analyzer_errors": analyzer_output.get("errors", {}),
        **_analysis_status(
            shared_graph["summary"]["total_files"],
            analyzer_output.get("analyzers_failed", 0),
        ),
    }

    base = {
        "schema_version": "3.0.0-kernel",
        "mode": "analyze",
        "output_mode": output_mode,
        "scan_root": scan_root,
        "timestamp": _utc_timestamp(),
    }

    # Step 4: Filter output berdasarkan mode
    if output_mode == "summary":
        base["unified_summary"] = unified_summary
        return base

    elif output_mode == "findings":
        base["analyzers"] = analyzer_output
        base["unified_summary"] = unified_summary
        return base

    else:  # "full"
        graph_output = {k: v for k, v in shared_graph.items() if k != "file_map"}
        base["shared_graph"] = graph_output
        base["analyzers"] = analyzer_output
        base["unified_summary"] = unified_summary
        return base


def _count_findings_by_severity(analyzer_output: Dict[str, Any]) -> Dict[str, int]:
    """Hitung total findings per severity level dari semua analyzer."""
    counts = {"high": 0, "medium": 0, "low": 0, "info": 0}
    for result in analyzer_output.get("results", {}).values():
        for finding in result.get("findings", []):
            sev = finding.get("severity", "info")
            if sev in counts:
                counts[sev] += 1
    return counts


def kernel_impact(
    scan_root: str,
    target_file: str,
    output_mode: str = "full",
) -> Dict[str, Any]:
    """Targeted impact analysis via SharedGraph."""
    if not SHARED_GRAPH_AVAILABLE or not TOPO_QUERIES_AVAILABLE:
        return {"error": "required modules not available"}

    root_error = _validate_scan_root(scan_root)
    if root_error:
        return root_error
    output_error = _validate_output_mode(output_mode, ("full", "summary"))
    if output_error:
        return output_error

    graph = build_shared_graph(scan_root)
    result = query_impact(graph, target_file)

    if output_mode == "summary":
        return {
            "schema_version": "3.0.0-kernel",
            "mode": "impact",
            "target": result.get("target"),
            "exists": result.get("exists"),
            "change_risk_level": result.get("change_risk_level"),
            "affected_entrypoints": result.get("affected_entrypoints", []),
            "downstream_count": result.get("downstream_count", 0),
            "upstream_count": result.get("upstream_count", 0),
            "target_fan_in": result.get("target_fan_in", 0),
        }

    return {
        "schema_version": "3.0.0-kernel",
        "mode": "impact",
        **result,
    }


def kernel_outline(
    scan_root: str,
    target_file: str,
) -> Dict[str, Any]:
    """Targeted outline extraction via SharedGraph."""
    if not SHARED_GRAPH_AVAILABLE or not TOPO_QUERIES_AVAILABLE:
        return {"error": "required modules not available"}

    root_error = _validate_scan_root(scan_root)
    if root_error:
        return root_error

    graph = build_shared_graph(scan_root)
    result = query_outline(graph, target_file)

    return {
        "schema_version": "3.0.0-kernel",
        "mode": "outline",
        **result,
    }


def kernel_brief(
    scan_root: str,
    target_file: str,
    output_mode: str = "full",
) -> Dict[str, Any]:
    """Targeted brief (outline + impact) via SharedGraph."""
    if not SHARED_GRAPH_AVAILABLE or not TOPO_QUERIES_AVAILABLE:
        return {"error": "required modules not available"}

    root_error = _validate_scan_root(scan_root)
    if root_error:
        return root_error
    output_error = _validate_output_mode(output_mode, ("full", "summary"))
    if output_error:
        return output_error

    graph = build_shared_graph(scan_root)
    result = query_brief(graph, target_file)

    if output_mode == "summary":
        impact_data = result.get("impact", {})
        outline_data = result.get("outline", {})
        return {
            "schema_version": "3.0.0-kernel",
            "mode": "brief",
            "file": result.get("file"),
            "exists": result.get("exists"),
            "export_count": outline_data.get("stats", {}).get("export_count", 0),
            "import_count": outline_data.get("stats", {}).get("import_count", 0),
            "change_risk_level": impact_data.get("change_risk_level"),
            "affected_entrypoints": impact_data.get("affected_entrypoints", []),
            "downstream_count": impact_data.get("downstream_count", 0),
        }

    return {
        "schema_version": "3.0.0-kernel",
        "mode": "brief",
        **result,
    }


def kernel_establish(
    scan_root: str = ".",
    baseline_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Establish topological baseline via decoder_steering."""
    if not STEERING_AVAILABLE:
        return {"error": "steering module not available"}
    root_error = _validate_scan_root(scan_root)
    if root_error:
        return root_error
    result = establish_baseline(scan_root, baseline_path)
    return {
        "schema_version": "3.0.0-kernel",
        **result,
    }


def _compute_topological_health_score(analyzer_output: Dict[str, Any], total_files: int) -> float:
    """Hitung health score (0.0 to 1.0] dari seluruh 13 analyzer."""
    if total_files <= 0:
        return 1.0
    weights = {"high": 3, "medium": 2, "low": 1, "info": 0}
    weighted_sum = 0
    results = analyzer_output.get("results", {})
    for res in results.values():
        for finding in res.get("findings", []):
            sev = finding.get("severity", "info")
            weighted_sum += weights.get(sev, 0)

    pressure = weighted_sum / max(1, total_files)
    return round(1.0 / (1.0 + pressure), 3)


def _detect_cross_analyzer_correlations(
    graph: Dict[str, Any],
    analyzer_output: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Deteksi korelasi lintas analyzer (gluing synthesis)."""
    correlations: List[Dict[str, Any]] = []
    results = analyzer_output.get("results", {})

    # 1. Isomorphic types across boundaries
    iso_res = results.get("hott.isomorphism", {}).get("findings", [])
    sheaf_res = results.get("hott.sheaf", {}).get("findings", [])
    if iso_res:
        boundaries = [b.get("boundary") for b in sheaf_res if b.get("boundary")]
        for finding in iso_res:
            if finding.get("type") == "structural_isomorphism":
                file_a = finding.get("file", "")
                file_b = finding.get("file_b", "")
                space_a = finding.get("space_a", {})
                space_b = finding.get("space_b", {})
                correlations.append({
                    "type": "boundary_isomorphism",
                    "severity": "low",
                    "file": file_a,
                    "file_b": file_b,
                    "type_name_a": space_a.get("name", "unknown"),
                    "type_name_b": space_b.get("name", "unknown"),
                    "isomorphism_confidence": finding.get("isomorphism_confidence", 0.0),
                    "observation": (
                        f"Isomorphic types '{space_a.get('name')}' ({file_a}) and "
                        f"'{space_b.get('name')}' ({file_b}) reside in a boundary structure. "
                        f"Type duplication correlates with boundary surface."
                    ),
                })

    # 2. Orphan files with performance issues
    orphan_res = results.get("topo.orphan", {}).get("findings", [])
    orphan_files = {f.get("file") for f in orphan_res if f.get("file")}
    if orphan_files:
        for analyzer_name in ("perf.async", "perf.cache", "perf.deopt", "perf.gc", "topo.risk"):
            for finding in results.get(analyzer_name, {}).get("findings", []):
                f_path = finding.get("file")
                if f_path and f_path in orphan_files and finding.get("severity") in ("high", "medium"):
                    correlations.append({
                        "type": "orphan_with_issues",
                        "severity": finding.get("severity", "medium"),
                        "file": f_path,
                        "analyzer": analyzer_name,
                        "issue_type": finding.get("type"),
                        "observation": f"Orphan file '{f_path}' has high/medium finding ({finding.get('type')}) from '{analyzer_name}'.",
                    })

    # 3. Entrypoints with high risk or perf issues
    risk_res = results.get("topo.risk", {}).get("findings", [])
    for finding in risk_res:
        if finding.get("risk_level") == "high":
            f_path = finding.get("file")
            correlations.append({
                "type": "entrypoint_high_risk",
                "severity": "high",
                "file": f_path,
                "reasons": finding.get("reasons", []),
                "observation": f"High change risk detected on '{f_path}' affecting entrypoints.",
            })

    # 4. Change risk without a static test-import witness
    test_reachability = results.get("topo.test_reachability", {})
    unreachable_from_tests = set(test_reachability.get("unreachable_sources", []))
    for finding in risk_res:
        f_path = finding.get("file")
        risk_level = finding.get("risk_level")
        if f_path in unreachable_from_tests and risk_level in ("high", "medium"):
            correlations.append({
                "type": "change_risk_without_test_path",
                "severity": risk_level,
                "file": f_path,
                "risk_score": finding.get("risk_score", 0),
                "risk_reasons": finding.get("reasons", []),
                "test_model": "static_test_import_reachability",
                "observation": (
                    f"'{f_path}' has {risk_level} change risk but no static import "
                    "path from a supported test file. This is not runtime coverage evidence."
                ),
            })

    correlations.sort(key=lambda c: (c.get("severity", ""), c.get("type", ""), c.get("file", "")))
    return correlations


def kernel_synthesize(
    scan_root: str = ".",
    output_mode: str = "full",
    analyzer_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Synthesis: SEMUA 13 analyzer + fingerprint + health + correlations.
    Menggunakan analyzer_registry.
    """
    if not SHARED_GRAPH_AVAILABLE or not REGISTRY_AVAILABLE:
        return {"error": "required modules not available", "available": False}

    root_error = _validate_scan_root(scan_root)
    if root_error:
        return root_error
    output_error = _validate_output_mode(
        output_mode,
        ("full", "summary", "findings"),
    )
    if output_error:
        return output_error

    # Step 1: Build SharedGraph (1x scan)
    graph = build_shared_graph(scan_root)

    # Step 2: Run ALL 13 analyzers
    analyzer_output = run_analyzers(graph, analyzer_names)
    results = analyzer_output.get("results", {})

    # Step 3: Fingerprint via invariant_encoder
    fingerprint = None
    if ENCODER_AVAILABLE:
        enc_res = encode_topological_invariants(scan_root)
        if enc_res.get("available"):
            fingerprint = enc_res.get("topological_fingerprint")

    if not fingerprint and "hott.manifold" in results:
        manifold_data = results["hott.manifold"].get("manifold", {})
        fingerprint = {
            "signature_hash": "sha256:unknown",
            "complexity_score": manifold_data.get("complexity_score", 0.0),
            "structural_archetype": manifold_data.get("structural_archetype", "unknown"),
        }

    # Step 4: Compute health score & correlations
    total_files = graph.get("summary", {}).get("total_files", 0)
    health_score = _compute_topological_health_score(analyzer_output, total_files)
    correlations = _detect_cross_analyzer_correlations(graph, analyzer_output)

    # Step 5: Unified summary
    unified_summary = {
        "total_files": total_files,
        "total_edges": graph.get("summary", {}).get("total_edges", 0),
        "total_boundaries": graph.get("summary", {}).get("total_boundaries", 0),
        "total_type_shapes": graph.get("summary", {}).get("total_type_shapes", 0),
        "entrypoint_count": graph.get("summary", {}).get("entrypoint_count", 0),
        "test_file_count": graph.get("summary", {}).get("test_file_count", 0),
        "total_findings": sum(len(r.get("findings", [])) for r in results.values()),
        "findings_by_severity": _count_findings_by_severity(analyzer_output),
        "correlation_count": len(correlations),
        "analyzers_run": analyzer_output.get("analyzers_run", 0),
        "analyzers_failed": analyzer_output.get("analyzers_failed", 0),
        "topological_health_score": health_score,
        "analyzer_errors": analyzer_output.get("errors", {}),
        **_analysis_status(
            total_files,
            analyzer_output.get("analyzers_failed", 0),
        ),
    }

    if output_mode == "summary":
        return {
            "schema_version": "3.0.0-kernel",
            "mode": "synthesize",
            "scan_root": scan_root,
            "fingerprint": fingerprint,
            "topological_health_score": health_score,
            "correlations": correlations,
            "unified_summary": unified_summary,
        }
    elif output_mode == "findings":
        return {
            "schema_version": "3.0.0-kernel",
            "mode": "synthesize",
            "scan_root": scan_root,
            "fingerprint": fingerprint,
            "topological_health_score": health_score,
            "correlations": correlations,
            "unified_summary": unified_summary,
            "analyzers": analyzer_output,
        }
    else:  # "full"
        graph_output = {k: v for k, v in graph.items() if k != "file_map"}
        return {
            "schema_version": "3.0.0-kernel",
            "mode": "synthesize",
            "scan_root": scan_root,
            "shared_graph": graph_output,
            "fingerprint": fingerprint,
            "topological_health_score": health_score,
            "correlations": correlations,
            "unified_summary": unified_summary,
            "analyzers": analyzer_output,
        }


def kernel_steer(
    scan_root: str = ".",
    baseline_path: Optional[str] = None,
    output_mode: str = "full",
) -> Dict[str, Any]:
    """Topological decoder steering via decoder_steering."""
    if not STEERING_AVAILABLE:
        return {"error": "steering module not available"}

    root_error = _validate_scan_root(scan_root)
    if root_error:
        return root_error
    output_error = _validate_output_mode(output_mode, ("full", "summary"))
    if output_error:
        return output_error

    result = steer_decoder(scan_root, baseline_path)

    if output_mode == "summary":
        return {
            "schema_version": "3.0.0-kernel",
            "mode": "steer",
            "scan_root": scan_root,
            "baseline": result.get("baseline"),
            "summary": result.get("summary"),
            "steering_signals": result.get("steering_signals"),
            "cycle_semantics": result.get("cycle_semantics"),
            "test_topology": result.get("test_topology"),
            "steering_prompt_block": result.get("steering_prompt_block"),
        }

    return {
        "schema_version": "3.0.0-kernel",
        "mode": "steer",
        **result,
    }


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h", "help"):
        print(json.dumps({
            "tool": "hott_kernel",
            "schema_version": "4.0.0-kernel",
            "usage": {
                "analyze": "python3 hott_kernel.py analyze [root] [--analyzers a,b] [--output full|summary|findings|graph]",
                "analyzers": "python3 hott_kernel.py analyzers",
                "impact": "python3 hott_kernel.py impact <file> [root] [--output full|summary]",
                "outline": "python3 hott_kernel.py outline <file> [root]",
                "brief": "python3 hott_kernel.py brief <file> [root] [--output full|summary]",
                "establish": "python3 hott_kernel.py establish [root] [--baseline path]",
                "synthesize": "python3 hott_kernel.py synthesize [root] [--output full|summary]",
                "steer": "python3 hott_kernel.py steer [root] [--output full|summary] [--baseline path]",
                "memory_store": "python3 hott_kernel.py memory_store <type> <content> [--source src] [--importance 0.5] [--tags t1,t2]",
                "memory_recall": "python3 hott_kernel.py memory_recall [query] [--type t] [--tags t1,t2] [--limit 20]",
                "memory_analyze": "python3 hott_kernel.py memory_analyze [--analyzers a,b] [--output full|summary]",
                "memory_stats": "python3 hott_kernel.py memory_stats",
                "memory_associate": "python3 hott_kernel.py memory_associate <from_id> <to_id> <type> [--strength 0.7]",
                "memory_consolidate": "python3 hott_kernel.py memory_consolidate <id1,id2,...> --content '...' [--tags t1,t2]",
                "memory_steer": "python3 hott_kernel.py memory_steer [--output full|summary]",
                "memory_establish": "python3 hott_kernel.py memory_establish",
                "memory_drift": "python3 hott_kernel.py memory_drift",
                "memory_compact": "python3 hott_kernel.py memory compact [--consolidated|--all] [--type episodic] [--dry-run|--stats|--restore <id>|--restore-all]",
                "memory_bridge": "python3 hott_kernel.py memory bridge <from_id> <to_id> [type] [--strength 0.7] [--unsafe]",
                "memory_bridge_auto": "python3 hott_kernel.py memory bridge_auto [--min-shared-tags 1] [--type semantic] [--dry-run]",
                "memory_bridge_candidates": "python3 hott_kernel.py memory bridge_candidates [--min-shared-tags 1]",
                "memory_kan": "python3 hott_kernel.py memory kan <query> [--mode lan|ran|both] [--max-depth 2]",
                "fiber_init": "python3 hott_kernel.py fiber init <task> <focus>",
                "fiber_lift": "python3 hott_kernel.py fiber lift [--query q] [--type t] [--tags t1,t2] [--max 10]",
                "fiber_descend": "python3 hott_kernel.py fiber descend <memory_id> | --all [--reason r]",
                "fiber_status": "python3 hott_kernel.py fiber status",
                "fiber_section_start": "python3 hott_kernel.py fiber section_start <name> <narrative>",
                "fiber_section_add": "python3 hott_kernel.py fiber section_add <memory_id>",
                "fiber_section_status": "python3 hott_kernel.py fiber section_status",
                "fiber_switch": "python3 hott_kernel.py fiber switch <new_task> <new_focus>",
                "fiber_transport": "python3 hott_kernel.py fiber transport <source_fiber_id> <new_task> <new_focus> [--threshold 0.6] [--max 10] [--dry-run]",
                "fiber_list_archives": "python3 hott_kernel.py fiber list_archives",
                "xanalyze": "python3 hott_kernel.py xanalyze [root] [--output summary|full] [--no-store] [--analyzers a,b]",
                "xsteer": "python3 hott_kernel.py xsteer [root] [--output full|summary]",
                "xcontext": "python3 hott_kernel.py xcontext <file_path>",
            },
        }, indent=2))
        return

    mode = sys.argv[1]

    if mode == "analyze":
        root = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "."

        # Parse flags
        analyzers = None
        output_mode = "full"

        for i, arg in enumerate(sys.argv):
            if arg == "--analyzers" and i + 1 < len(sys.argv):
                analyzers = sys.argv[i + 1].split(",")
            elif arg == "--output" and i + 1 < len(sys.argv):
                output_mode = sys.argv[i + 1]

        if output_mode not in ("full", "summary", "findings", "graph"):
            _emit_cli_result(_kernel_error(
                "invalid_output_mode",
                f"Invalid output mode: {output_mode}",
                output_mode=output_mode,
                supported_output_modes=["full", "summary", "findings", "graph"],
            ))

        result = kernel_analyze(root, analyzers, output_mode)
        _emit_cli_result(result)

    elif mode == "analyzers":
        if REGISTRY_AVAILABLE:
            _emit_cli_result({
                "available_analyzers": get_available_analyzers(),
            })
        else:
            _emit_cli_result(_kernel_error(
                "registry_unavailable",
                "registry not available",
            ))

    elif mode == "impact":
        if len(sys.argv) < 3:
            _emit_cli_result(_kernel_error(
                "missing_argument",
                "Usage: hott_kernel.py impact <file> [root]",
            ))
        target = sys.argv[2]
        root = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "."
        output_mode = "full"
        for i, arg in enumerate(sys.argv):
            if arg == "--output" and i + 1 < len(sys.argv):
                output_mode = sys.argv[i + 1]
        result = kernel_impact(root, target, output_mode)
        _emit_cli_result(result)

    elif mode == "outline":
        if len(sys.argv) < 3:
            _emit_cli_result(_kernel_error(
                "missing_argument",
                "Usage: hott_kernel.py outline <file> [root]",
            ))
        target = sys.argv[2]
        root = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "."
        result = kernel_outline(root, target)
        _emit_cli_result(result)

    elif mode == "brief":
        if len(sys.argv) < 3:
            _emit_cli_result(_kernel_error(
                "missing_argument",
                "Usage: hott_kernel.py brief <file> [root]",
            ))
        target = sys.argv[2]
        root = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "."
        output_mode = "full"
        for i, arg in enumerate(sys.argv):
            if arg == "--output" and i + 1 < len(sys.argv):
                output_mode = sys.argv[i + 1]
        result = kernel_brief(root, target, output_mode)
        _emit_cli_result(result)

    elif mode == "establish":
        root = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "."
        baseline_path = None
        for i, arg in enumerate(sys.argv):
            if arg == "--baseline" and i + 1 < len(sys.argv):
                baseline_path = sys.argv[i + 1]
        result = kernel_establish(root, baseline_path)
        _emit_cli_result(result)

    elif mode == "synthesize":
        root = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "."
        output_mode = "full"
        for i, arg in enumerate(sys.argv):
            if arg == "--output" and i + 1 < len(sys.argv):
                output_mode = sys.argv[i + 1]
        result = kernel_synthesize(root, output_mode)
        _emit_cli_result(result)

    elif mode == "steer":
        root = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "."
        output_mode = "full"
        baseline_path = None
        for i, arg in enumerate(sys.argv):
            if arg == "--output" and i + 1 < len(sys.argv):
                output_mode = sys.argv[i + 1]
            elif arg == "--baseline" and i + 1 < len(sys.argv):
                baseline_path = sys.argv[i + 1]
        result = kernel_steer(root, baseline_path, output_mode)
        _emit_cli_result(result)

    elif mode == "memory_store":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: hott_kernel.py memory_store <type> <content> [--source src] [--importance 0.5] [--tags t1,t2]"}))
            return
        m_type = sys.argv[2]
        m_content = sys.argv[3]
        m_source = "manual"
        m_importance = 0.5
        m_tags = None
        for i, arg in enumerate(sys.argv):
            if arg == "--source" and i + 1 < len(sys.argv):
                m_source = sys.argv[i + 1]
            elif arg == "--importance" and i + 1 < len(sys.argv):
                try:
                    m_importance = float(sys.argv[i + 1])
                except ValueError:
                    pass
            elif arg == "--tags" and i + 1 < len(sys.argv):
                m_tags = sys.argv[i + 1]
        result = kernel_memory_store(m_type, m_content, m_source, m_importance, m_tags)
        print(json.dumps(result, indent=2))

    elif mode == "memory_recall":
        m_query = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
        m_type = None
        m_tags = None
        m_limit = 20
        for i, arg in enumerate(sys.argv):
            if arg == "--type" and i + 1 < len(sys.argv):
                m_type = sys.argv[i + 1]
            elif arg == "--tags" and i + 1 < len(sys.argv):
                m_tags = sys.argv[i + 1]
            elif arg == "--limit" and i + 1 < len(sys.argv):
                try:
                    m_limit = int(sys.argv[i + 1])
                except ValueError:
                    pass
        result = kernel_memory_recall(m_query, m_type, m_tags, m_limit)
        print(json.dumps(result, indent=2))

    elif mode == "memory_analyze":
        m_analyzers = None
        m_output = "full"
        for i, arg in enumerate(sys.argv):
            if arg == "--analyzers" and i + 1 < len(sys.argv):
                m_analyzers = sys.argv[i + 1].split(",")
            elif arg == "--output" and i + 1 < len(sys.argv):
                m_output = sys.argv[i + 1]
        result = kernel_memory_analyze(m_analyzers, m_output)
        print(json.dumps(result, indent=2))

    elif mode == "memory_stats":
        result = kernel_memory_stats()
        print(json.dumps(result, indent=2))

    elif mode in ("memory_associate", "associate"):
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: hott_kernel.py memory_associate <from_id> <to_id> <type> [--strength 0.7]"}))
            return
        from_id = sys.argv[2]
        to_id = sys.argv[3]
        assoc_type = sys.argv[4]
        strength = 0.5
        for i, arg in enumerate(sys.argv):
            if arg == "--strength" and i + 1 < len(sys.argv):
                try:
                    strength = float(sys.argv[i + 1])
                except ValueError:
                    pass
        result = kernel_memory_associate(from_id, to_id, assoc_type, strength)
        print(json.dumps(result, indent=2))

    elif mode in ("memory_consolidate", "consolidate"):
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: hott_kernel.py memory_consolidate <id1,id2,...> --content '...'"}))
            return
        source_ids = sys.argv[2].split(",")
        content = ""
        tags = None
        importance = 0.9
        for i, arg in enumerate(sys.argv):
            if arg == "--content" and i + 1 < len(sys.argv):
                content = sys.argv[i + 1]
            elif arg == "--tags" and i + 1 < len(sys.argv):
                tags = sys.argv[i + 1]
            elif arg == "--importance" and i + 1 < len(sys.argv):
                try:
                    importance = float(sys.argv[i + 1])
                except ValueError:
                    pass
        if not content:
            print(json.dumps({"error": "--content is required"}))
            return
        result = kernel_memory_consolidate(source_ids, content, tags, importance)
        print(json.dumps(result, indent=2))

    elif mode in ("memory_steer",):
        output_mode = "full"
        for i, arg in enumerate(sys.argv):
            if arg == "--output" and i + 1 < len(sys.argv):
                output_mode = sys.argv[i + 1]
        result = kernel_memory_steer(output_mode)
        print(json.dumps(result, indent=2))

    elif mode in ("memory_establish",):
        result = kernel_memory_establish()
        print(json.dumps(result, indent=2))

    elif mode in ("memory_drift",):
        result = kernel_memory_drift()
        print(json.dumps(result, indent=2))

    elif mode == "memory":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: hott_kernel.py memory <submode> ..."}))
            return
        submode = sys.argv[2]
        if submode == "store":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "Usage: memory store <type> <content> [--source src] [--importance 0.5] [--tags t1,t2]"}))
                return
            m_type = sys.argv[3]
            m_content = sys.argv[4]
            m_source = "manual"
            m_importance = 0.5
            m_tags = None
            for i, arg in enumerate(sys.argv):
                if arg == "--source" and i + 1 < len(sys.argv):
                    m_source = sys.argv[i + 1]
                elif arg == "--importance" and i + 1 < len(sys.argv):
                    try:
                        m_importance = float(sys.argv[i + 1])
                    except ValueError:
                        pass
                elif arg == "--tags" and i + 1 < len(sys.argv):
                    m_tags = sys.argv[i + 1]
            result = kernel_memory_store(m_type, m_content, m_source, m_importance, m_tags)
            print(json.dumps(result, indent=2))
        elif submode == "recall":
            m_query = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else None
            m_type = None
            m_tags = None
            m_limit = 20
            for i, arg in enumerate(sys.argv):
                if arg == "--type" and i + 1 < len(sys.argv):
                    m_type = sys.argv[i + 1]
                elif arg == "--tags" and i + 1 < len(sys.argv):
                    m_tags = sys.argv[i + 1]
                elif arg == "--limit" and i + 1 < len(sys.argv):
                    try:
                        m_limit = int(sys.argv[i + 1])
                    except ValueError:
                        pass
            result = kernel_memory_recall(m_query, m_type, m_tags, m_limit)
            print(json.dumps(result, indent=2))
        elif submode == "analyze":
            m_analyzers = None
            m_output = "full"
            for i, arg in enumerate(sys.argv):
                if arg == "--analyzers" and i + 1 < len(sys.argv):
                    m_analyzers = sys.argv[i + 1].split(",")
                elif arg == "--output" and i + 1 < len(sys.argv):
                    m_output = sys.argv[i + 1]
            result = kernel_memory_analyze(m_analyzers, m_output)
            print(json.dumps(result, indent=2))
        elif submode == "stats":
            result = kernel_memory_stats()
            print(json.dumps(result, indent=2))
        elif submode == "associate":
            if len(sys.argv) < 6:
                print(json.dumps({"error": "Usage: memory associate <from_id> <to_id> <type> [--strength 0.7]"}))
                return
            from_id = sys.argv[3]
            to_id = sys.argv[4]
            assoc_type = sys.argv[5]
            strength = 0.5
            for i, arg in enumerate(sys.argv):
                if arg == "--strength" and i + 1 < len(sys.argv):
                    try:
                        strength = float(sys.argv[i + 1])
                    except ValueError:
                        pass
            result = kernel_memory_associate(from_id, to_id, assoc_type, strength)
            print(json.dumps(result, indent=2))
        elif submode == "consolidate":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "Usage: memory consolidate <id1,id2,...> --content '...'"}))
                return
            source_ids = sys.argv[3].split(",")
            content = ""
            tags = None
            importance = 0.9
            for i, arg in enumerate(sys.argv):
                if arg == "--content" and i + 1 < len(sys.argv):
                    content = sys.argv[i + 1]
                elif arg == "--tags" and i + 1 < len(sys.argv):
                    tags = sys.argv[i + 1]
                elif arg == "--importance" and i + 1 < len(sys.argv):
                    try:
                        importance = float(sys.argv[i + 1])
                    except ValueError:
                        pass
            if not content:
                print(json.dumps({"error": "--content is required"}))
                return
            result = kernel_memory_consolidate(source_ids, content, tags, importance)
            print(json.dumps(result, indent=2))
        elif submode == "steer":
            output_mode = "full"
            for i, arg in enumerate(sys.argv):
                if arg == "--output" and i + 1 < len(sys.argv):
                    output_mode = sys.argv[i + 1]
            result = kernel_memory_steer(output_mode)
            print(json.dumps(result, indent=2))
        elif submode == "establish":
            result = kernel_memory_establish()
            print(json.dumps(result, indent=2))
        elif submode == "drift":
            result = kernel_memory_drift()
            print(json.dumps(result, indent=2))
        elif submode == "betti_breakdown":
            result = kernel_memory_betti_breakdown()
            print(json.dumps(result, indent=2))
        elif submode == "consolidate_by_tag":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: memory consolidate_by_tag <tag> [--content '...'] [--importance 0.9]"}))
                return
            m_tag = sys.argv[3]
            m_content = None
            m_importance = 0.9
            for i, arg in enumerate(sys.argv):
                if arg == "--content" and i + 1 < len(sys.argv):
                    m_content = sys.argv[i + 1]
                elif arg == "--importance" and i + 1 < len(sys.argv):
                    try:
                        m_importance = float(sys.argv[i + 1])
                    except ValueError:
                        pass
            result = kernel_memory_consolidate_by_tag(m_tag, m_content, m_importance)
            print(json.dumps(result, indent=2))
        elif submode == "consolidate_auto":
            min_size = 3
            m_importance = 0.9
            for i, arg in enumerate(sys.argv):
                if arg == "--min-size" and i + 1 < len(sys.argv):
                    try:
                        min_size = int(sys.argv[i + 1])
                    except ValueError:
                        pass
                elif arg == "--importance" and i + 1 < len(sys.argv):
                    try:
                        m_importance = float(sys.argv[i + 1])
                    except ValueError:
                        pass
            result = kernel_memory_consolidate_auto(min_size, m_importance)
            print(json.dumps(result, indent=2))
        elif submode == "unconsolidated_tags":
            result = kernel_memory_unconsolidated_tags()
            print(json.dumps(result, indent=2))
        elif submode == "compact":
            # Parse flags
            only_consolidated = True
            memory_type = "episodic"
            dry_run = False
            restore = False
            restore_all = False
            restore_id = None
            stats = False

            i = 3
            while i < len(sys.argv):
                arg = sys.argv[i]
                if arg == "--consolidated":
                    only_consolidated = True
                elif arg == "--all":
                    only_consolidated = False
                elif arg == "--type" and i + 1 < len(sys.argv):
                    memory_type = sys.argv[i + 1]
                    i += 1
                elif arg == "--dry-run":
                    dry_run = True
                elif arg == "--restore-all":
                    restore_all = True
                elif arg == "--restore" and i + 1 < len(sys.argv):
                    restore_id = sys.argv[i + 1]
                    i += 1
                elif arg == "--stats":
                    stats = True
                i += 1

            result = kernel_memory_compact(
                only_consolidated=only_consolidated,
                memory_type=memory_type,
                dry_run=dry_run,
                restore_id=restore_id,
                restore_all=restore_all,
                stats=stats,
            )
            print(json.dumps(result, indent=2))
        elif submode == "bridge":
            # memory bridge <from_id> <to_id> [type] [--strength 0.7] [--unsafe]
            if len(sys.argv) < 5:
                print(json.dumps({"error": "Usage: memory bridge <from_id> <to_id> [type] [--strength 0.7]"}))
                return
            from_id = sys.argv[3]
            to_id = sys.argv[4]
            assoc_type = sys.argv[5] if len(sys.argv) > 5 and not sys.argv[5].startswith("--") else "semantic"
            strength = 0.7
            safe_mode = True
            for i, arg in enumerate(sys.argv):
                if arg == "--strength" and i + 1 < len(sys.argv):
                    try:
                        strength = float(sys.argv[i + 1])
                    except ValueError:
                        pass
                elif arg == "--unsafe":
                    safe_mode = False
            result = kernel_memory_bridge(from_id, to_id, assoc_type, strength, safe_mode)
            print(json.dumps(result, indent=2))

        elif submode == "bridge_auto":
            # memory bridge_auto [--min-shared-tags 1] [--type semantic] [--dry-run] [--unsafe]
            min_shared_tags = 1
            assoc_type = "semantic"
            dry_run = False
            safe_mode = True
            for i, arg in enumerate(sys.argv):
                if arg == "--min-shared-tags" and i + 1 < len(sys.argv):
                    try:
                        min_shared_tags = int(sys.argv[i + 1])
                    except ValueError:
                        pass
                elif arg == "--type" and i + 1 < len(sys.argv):
                    assoc_type = sys.argv[i + 1]
                elif arg == "--dry-run":
                    dry_run = True
                elif arg == "--unsafe":
                    safe_mode = False
            result = kernel_memory_bridge_auto(min_shared_tags, assoc_type, safe_mode, dry_run)
            print(json.dumps(result, indent=2))

        elif submode == "bridge_candidates":
            # memory bridge_candidates [--min-shared-tags 1]
            min_shared_tags = 1
            for i, arg in enumerate(sys.argv):
                if arg == "--min-shared-tags" and i + 1 < len(sys.argv):
                    try:
                        min_shared_tags = int(sys.argv[i + 1])
                    except ValueError:
                        pass
            result = kernel_memory_bridge_candidates(min_shared_tags)
            print(json.dumps(result, indent=2))
        elif submode == "kan":
            # memory kan <query> [--mode lan|ran|both] [--max-depth 2]
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: memory kan <query> [--mode lan|ran|both] [--max-depth 2]"}))
                return
            query = sys.argv[3]
            kan_mode = "both"
            max_depth = 2
            for i, arg in enumerate(sys.argv):
                if arg == "--mode" and i + 1 < len(sys.argv):
                    kan_mode = sys.argv[i + 1]
                elif arg == "--max-depth" and i + 1 < len(sys.argv):
                    try:
                        max_depth = int(sys.argv[i + 1])
                    except ValueError:
                        pass
            if kan_mode not in ("lan", "ran", "both"):
                print(json.dumps({"error": f"Invalid mode: {kan_mode}. Use lan, ran, or both."}))
                return
            result = kernel_memory_kan(query, kan_mode, max_depth)
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps({"error": f"Unknown memory submode: {submode}"}))

    elif mode == "xanalyze":
        root = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "."
        output_mode = "summary"
        auto_store = True
        analyzers = None
        for i, arg in enumerate(sys.argv):
            if arg == "--output" and i + 1 < len(sys.argv):
                output_mode = sys.argv[i + 1]
            elif arg == "--no-store":
                auto_store = False
            elif arg == "--analyzers" and i + 1 < len(sys.argv):
                analyzers = sys.argv[i + 1].split(",")
        result = kernel_xanalyze(root, analyzers, output_mode, auto_store)
        print(json.dumps(result, indent=2))

    elif mode == "xsteer":
        root = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "."
        output_mode = "full"
        for i, arg in enumerate(sys.argv):
            if arg == "--output" and i + 1 < len(sys.argv):
                output_mode = sys.argv[i + 1]
        result = kernel_xsteer(root, output_mode)
        print(json.dumps(result, indent=2))

    elif mode == "xcontext":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: hott_kernel.py xcontext <file_path>"}))
            return
        file_path = sys.argv[2]
        result = kernel_xcontext(file_path)
        print(json.dumps(result, indent=2))

    elif mode == "fiber":
        if len(sys.argv) < 3:
            print(json.dumps({
                "error": "Usage: hott_kernel.py fiber <init|lift|descend|status|section_start|section_add|section_status|switch|transport|list_archives> [args]"
            }))
            return
        subcommand = sys.argv[2]
        
        if subcommand == "transport":
            # fiber transport <source_fiber_id> <new_task> <new_focus> [--threshold 0.6] [--max 10] [--dry-run]
            if len(sys.argv) < 6:
                print(json.dumps({
                    "error": "Usage: fiber transport <source_fiber_id> <new_task> <new_focus> [--threshold 0.6] [--max 10] [--dry-run]"
                }))
                return
            source_id = sys.argv[3]
            new_task = sys.argv[4]
            new_focus = sys.argv[5]
            threshold = 0.6
            max_transport = 10
            dry_run = False
            i = 6
            while i < len(sys.argv):
                if sys.argv[i] == "--threshold" and i + 1 < len(sys.argv):
                    try:
                        threshold = float(sys.argv[i + 1])
                    except ValueError:
                        pass
                    i += 2
                elif sys.argv[i] == "--max" and i + 1 < len(sys.argv):
                    try:
                        max_transport = int(sys.argv[i + 1])
                    except ValueError:
                        pass
                    i += 2
                elif sys.argv[i] == "--dry-run":
                    dry_run = True
                    i += 1
                else:
                    i += 1
            result = kernel_fiber_transport(source_id, new_task, new_focus, threshold, max_transport, dry_run)
            print(json.dumps(result, indent=2))
        
        elif subcommand == "list_archives":
            result = kernel_fiber_list_archives()
            print(json.dumps(result, indent=2))
        
        else:
            args = sys.argv[3:]
            result = kernel_fiber(subcommand, args)
            print(json.dumps(result, indent=2))

    else:
        _emit_cli_result(_kernel_error(
            "unknown_mode",
            f"Unknown mode: {mode}",
            mode=mode,
        ))



if __name__ == "__main__":
    main()
