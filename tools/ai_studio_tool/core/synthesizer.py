"""
Synthesizer — HoTT Kernel Core
Schema Version: 3.0.0-kernel

Unifies:
- Topological integrity synthesis
- Invariant encoding (fingerprint)
- Baseline management & drift detection
- Decoder steering context generation
"""

import os
import sys
import json
import math
import hashlib
import datetime
from typing import Any, Dict, List, Optional, Tuple

_TOOL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CODEBASE_BASELINE_DIR = os.path.join(_TOOL_ROOT, "data", "codebase", "baseline")
DEFAULT_BASELINE_PATH = os.path.join(DEFAULT_CODEBASE_BASELINE_DIR, "topological_baseline.json")


def _ensure_baseline_dir(path: str = DEFAULT_BASELINE_PATH) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def _saturate(x: float, half_point: float) -> float:
    if x <= 0:
        return 0.0
    if half_point <= 0:
        return 1.0
    return x / (x + half_point)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def synthesize_topological_integrity(
    scan_root: str,
    ignore_dirs: Optional[List[str]] = None,
    output_mode: str = "full",
) -> Dict[str, Any]:
    """Menjalankan sintesis integritas topologis menggunakan shared graph dan registry."""
    try:
        from core.shared_graph import build_shared_graph
        from core.analyzer_registry import run_analyzers
    except ImportError:
        from shared_graph import build_shared_graph
        from analyzer_registry import run_analyzers

    shared_graph = build_shared_graph(scan_root, ignore_dirs=ignore_dirs)
    analyzers_result = run_analyzers(shared_graph)

    # Calculate severity counts
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    total_findings = 0
    for res in analyzers_result.get("results", {}).values():
        for f in res.get("findings", []):
            sev = f.get("severity", "low")
            if sev in severity_counts:
                severity_counts[sev] += 1
            total_findings += 1

    total_files = shared_graph["summary"]["total_files"]
    weighted_sum = (
        severity_counts["high"] * 3
        + severity_counts["medium"] * 2
        + severity_counts["low"] * 1
    )
    pressure = weighted_sum / max(1, total_files)
    health_score = round(1.0 / (1.0 + pressure), 3)

    summary_data = {
        "total_files": total_files,
        "total_findings": total_findings,
        "findings_by_severity": severity_counts,
        "topological_health_score": health_score,
    }

    return {
        "schema_version": "3.0.0-kernel",
        "scan_root": scan_root,
        "total_files": total_files,
        "total_findings": total_findings,
        "findings_by_severity": severity_counts,
        "topological_health_score": health_score,
        "unified_summary": summary_data,
        "analyzers": analyzers_result,
    }


def encode_topological_invariants(
    scan_root: str,
    ignore_dirs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Mengencode topological fingerprint dari codebase."""
    try:
        from codebase.hott_analyzers import analyze_manifold
        from core.shared_graph import build_shared_graph
    except ImportError:
        from hott_analyzers import analyze_manifold
        from shared_graph import build_shared_graph

    graph = build_shared_graph(scan_root, ignore_dirs=ignore_dirs)
    manifold_result = analyze_manifold(graph)
    manifold = manifold_result.get("manifold", {})
    betti = manifold.get("betti_numbers", {})
    summary = manifold_result.get("summary", {})

    total_nodes = graph["summary"]["total_files"]
    total_edges = graph["summary"]["total_edges"]
    avg_degree = manifold.get("average_degree", (2.0 * total_edges / total_nodes) if total_nodes > 0 else 0.0)

    n_nodes = _saturate(total_nodes, 20.0)
    n_edges = _saturate(total_edges, 40.0)
    n_avg_degree = _saturate(avg_degree, 3.0)
    n_beta_0 = _saturate(betti.get("beta_0", 1), 3.0)
    n_beta_1 = _saturate(betti.get("beta_1", 0), 2.0)
    n_beta_2 = _saturate(betti.get("beta_2", 0), 2.0)

    complexity = manifold.get("complexity_score", (
        0.20 * n_nodes
        + 0.15 * n_edges
        + 0.15 * n_avg_degree
        + 0.15 * n_beta_0
        + 0.25 * n_beta_1
        + 0.10 * n_beta_2
    ))

    sig_src = f"V1|N:{total_nodes}|E:{total_edges}|B0:{betti.get('beta_0', 1)}|B1:{betti.get('beta_1', 0)}|B2:{betti.get('beta_2', 0)}"
    sig_hash = f"sha256:{hashlib.sha256(sig_src.encode('utf-8')).hexdigest()[:16]}"

    archetype = manifold.get("structural_archetype", "tree_like")

    normalized_vec = {
        "n_nodes": round(n_nodes, 4),
        "n_edges": round(n_edges, 4),
        "n_avg_degree": round(n_avg_degree, 4),
        "n_beta_0": round(n_beta_0, 4),
        "n_beta_1": round(n_beta_1, 4),
        "n_beta_2": round(n_beta_2, 4),
    }

    context_block = (
        f"[TOPOLOGICAL FINGERPRINT]\n"
        f"Signature: {sig_hash}\n"
        f"Archetype: {archetype}\n"
        f"Complexity: {complexity}\n"
        f"Betti: β₀={betti.get('beta_0', 1)}, β₁={betti.get('beta_1', 0)}, β₂={betti.get('beta_2', 0)}\n"
    )

    return {
        "available": True,
        "schema_version": "3.0.0-kernel",
        "topological_fingerprint": {
            "signature_hash": sig_hash,
            "normalized_vector": normalized_vec,
            "complexity_score": round(complexity, 4),
            "structural_archetype": archetype,
        },
        "summary": {
            "betti_numbers": betti,
            "total_files": total_nodes,
            "total_edges": total_edges,
            "average_degree": avg_degree,
            **summary,
        },
        "context_block": context_block,
    }


def establish_baseline(
    scan_root: str,
    baseline_path: str = DEFAULT_BASELINE_PATH,
    ignore_dirs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Establish and save codebase topological baseline."""
    _ensure_baseline_dir(baseline_path)
    encoded = encode_topological_invariants(scan_root, ignore_dirs=ignore_dirs)
    data = {
        "schema_version": "3.0.0-kernel",
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "scan_root": scan_root,
        "fingerprint": encoded.get("topological_fingerprint", {}),
    }
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return {
        "available": True,
        "status": "established",
        "baseline_path": baseline_path,
        **data,
    }


def load_baseline(baseline_path: str = DEFAULT_BASELINE_PATH) -> Optional[Dict[str, Any]]:
    """Load baseline if exists, fallback to legacy location."""
    if os.path.exists(baseline_path):
        try:
            with open(baseline_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback to legacy location
    legacy_path = os.path.join(_TOOL_ROOT, "baseline", "topological_baseline.json")
    if os.path.exists(legacy_path):
        try:
            with open(legacy_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def steer_decoder(
    scan_root: str,
    baseline_path: str = DEFAULT_BASELINE_PATH,
    ignore_dirs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate decoder steering signals for codebase."""
    current = encode_topological_invariants(scan_root, ignore_dirs=ignore_dirs)
    curr_fp = current.get("topological_fingerprint", {})
    base = load_baseline(baseline_path)
    has_baseline = base is not None
    base_fp = base.get("fingerprint", {}) if base else {}

    # Distance calculation
    dist = 0.0
    if has_baseline and curr_fp and base_fp:
        v_curr = curr_fp.get("normalized_vector", {})
        v_base = base_fp.get("normalized_vector", {})
        sq_sum = sum((v_curr.get(k, 0) - v_base.get(k, 0)) ** 2 for k in v_curr)
        dist = round(math.sqrt(sq_sum), 4)

    archetype = curr_fp.get("structural_archetype", "tree_like")
    if archetype == "tree_like":
        strategy = "hierarchical_traversal"
    elif "cyclic" in archetype:
        strategy = "cycle_breaking_and_layering"
    else:
        strategy = "modular_component_expansion"

    complexity = curr_fp.get("complexity_score", 0.5)
    budget = "low" if complexity < 0.3 else ("medium" if complexity < 0.7 else "high")
    regrounding = dist > 0.25

    prompt_block = (
        f"[TOPOLOGICAL STEERING SIGNAL]\n"
        f"Signature: {curr_fp.get('signature_hash', '')}\n"
        f"Archetype: {archetype}\n"
        f"Strategy: {strategy}\n"
        f"Budget: {budget}\n"
    )

    return {
        "available": True,
        "schema_version": "3.0.0-kernel",
        "baseline": {
            "exists": has_baseline,
            "path": baseline_path,
        },
        "has_baseline": has_baseline,
        "drift_analysis": {
            "has_drift": dist > 0.1,
            "drift_distance": dist,
            "topology_changed": dist > 0.05,
        },
        "drift_distance": dist,
        "steering_signals": {
            "reasoning_strategy": strategy,
            "reasoning_budget": budget,
            "regrounding_needed": regrounding,
        },
        "steering_prompt_block": prompt_block,
        "current_fingerprint": curr_fp,
        "baseline_fingerprint": base_fp if has_baseline else None,
    }
