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
    from shared_graph import build_shared_graph
    SHARED_GRAPH_AVAILABLE = True
except ImportError:
    SHARED_GRAPH_AVAILABLE = False

try:
    from analyzer_registry import run_analyzers, get_available_analyzers
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False

try:
    from topology_analyzers import query_impact, query_outline, query_brief
    TOPO_QUERIES_AVAILABLE = True
except ImportError:
    TOPO_QUERIES_AVAILABLE = False

try:
    from topological_integrity_orchestrator import synthesize_topological_integrity
    SYNTHESIS_AVAILABLE = True
except ImportError:
    SYNTHESIS_AVAILABLE = False

try:
    from invariant_encoder import encode_topological_invariants
    ENCODER_AVAILABLE = True
except ImportError:
    ENCODER_AVAILABLE = False

try:
    from decoder_steering import establish_baseline, steer_decoder
    STEERING_AVAILABLE = True
except ImportError:
    STEERING_AVAILABLE = False

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
    from memory_analyzers import analyze_manifold
    manifold_result = analyze_manifold(memory_graph)
    manifold_data = manifold_result.get("manifold", {})

    # Compute health score
    from memory_analyzers import run_memory_analyzers
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
    from memory_analyzers import analyze_manifold, run_memory_analyzers
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
    from memory_analyzers import analyze_manifold
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
    }

    base = {
        "schema_version": "3.0.0-kernel",
        "mode": "analyze",
        "output_mode": output_mode,
        "scan_root": scan_root,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
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
    result = establish_baseline(scan_root, baseline_path)
    return {
        "schema_version": "3.0.0-kernel",
        **result,
    }


def _compute_topological_health_score(analyzer_output: Dict[str, Any], total_files: int) -> float:
    """Hitung health score (0.0 to 1.0] dari seluruh 12 analyzer."""
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

    correlations.sort(key=lambda c: (c.get("severity", ""), c.get("type", ""), c.get("file", "")))
    return correlations


def kernel_synthesize(
    scan_root: str = ".",
    output_mode: str = "full",
    analyzer_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Synthesis: SEMUA 12 analyzer + fingerprint + health + correlations.
    Menggunakan analyzer_registry.
    """
    if not SHARED_GRAPH_AVAILABLE or not REGISTRY_AVAILABLE:
        return {"error": "required modules not available", "available": False}

    # Step 1: Build SharedGraph (1x scan)
    graph = build_shared_graph(scan_root)

    # Step 2: Run ALL 12 analyzers
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

    result = steer_decoder(scan_root, baseline_path)

    if output_mode == "summary":
        return {
            "schema_version": "3.0.0-kernel",
            "mode": "steer",
            "scan_root": scan_root,
            "baseline": result.get("baseline"),
            "summary": result.get("summary"),
            "steering_signals": result.get("steering_signals"),
        }

    return {
        "schema_version": "3.0.0-kernel",
        "mode": "steer",
        **result,
    }


def main():
    if len(sys.argv) < 2:
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
            print(json.dumps({"error": f"Invalid output mode: {output_mode}"}))
            return

        result = kernel_analyze(root, analyzers, output_mode)
        print(json.dumps(result, indent=2))

    elif mode == "analyzers":
        if REGISTRY_AVAILABLE:
            print(json.dumps({
                "available_analyzers": get_available_analyzers(),
            }, indent=2))
        else:
            print(json.dumps({"error": "registry not available"}))

    elif mode == "impact":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: hott_kernel.py impact <file> [root]"}))
            return
        target = sys.argv[2]
        root = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "."
        output_mode = "full"
        for i, arg in enumerate(sys.argv):
            if arg == "--output" and i + 1 < len(sys.argv):
                output_mode = sys.argv[i + 1]
        result = kernel_impact(root, target, output_mode)
        print(json.dumps(result, indent=2))

    elif mode == "outline":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: hott_kernel.py outline <file> [root]"}))
            return
        target = sys.argv[2]
        root = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "."
        result = kernel_outline(root, target)
        print(json.dumps(result, indent=2))

    elif mode == "brief":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: hott_kernel.py brief <file> [root]"}))
            return
        target = sys.argv[2]
        root = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "."
        output_mode = "full"
        for i, arg in enumerate(sys.argv):
            if arg == "--output" and i + 1 < len(sys.argv):
                output_mode = sys.argv[i + 1]
        result = kernel_brief(root, target, output_mode)
        print(json.dumps(result, indent=2))

    elif mode == "establish":
        root = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "."
        baseline_path = None
        for i, arg in enumerate(sys.argv):
            if arg == "--baseline" and i + 1 < len(sys.argv):
                baseline_path = sys.argv[i + 1]
        result = kernel_establish(root, baseline_path)
        print(json.dumps(result, indent=2))

    elif mode == "synthesize":
        root = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "."
        output_mode = "full"
        for i, arg in enumerate(sys.argv):
            if arg == "--output" and i + 1 < len(sys.argv):
                output_mode = sys.argv[i + 1]
        result = kernel_synthesize(root, output_mode)
        print(json.dumps(result, indent=2))

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
        print(json.dumps(result, indent=2))

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
        else:
            print(json.dumps({"error": f"Unknown memory submode: {submode}"}))

    else:
        print(json.dumps({"error": f"Unknown mode: {mode}"}))



if __name__ == "__main__":
    main()
