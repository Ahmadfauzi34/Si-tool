"""
Memory Synthesizer — HoTT Kernel Memory Domain
Schema Version: 4.0.0-memory

Fungsi:
1. Memory steering signals (reasoning strategy dari topologi memori)
2. Memory baseline establishment
3. Memory drift detection
4. Memory steering prompt block assembly
"""

import os
import json
import math
import hashlib
import datetime
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "4.0.0-memory"

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_BASELINE_DIR = os.path.join(_SCRIPT_DIR, "memory", "baseline")
MEMORY_BASELINE_PATH = os.path.join(MEMORY_BASELINE_DIR, "memory_baseline.json")

# Mapping archetype → reasoning strategy untuk memory domain
MEMORY_ARCHETYPE_STRATEGY = {
    "memory_tree": (
        "hierarchical_recall",
        "Memory structure is a connected tree. Traverse from root memories "
        "to leaves for systematic recall. Top-down navigation is natural."
    ),
    "memory_modular": (
        "isolated_exploration",
        "Memory has disconnected clusters. Explore each cluster independently. "
        "Cross-cluster reasoning requires explicit bridge-building."
    ),
    "memory_sparse_cyclic": (
        "cycle_aware_recall",
        "Connected memory with sparse cycles. Verify you're not looping "
        "through the same reasoning before proceeding."
    ),
    "memory_mixed_cyclic": (
        "path_enumeration",
        "Moderate interconnection with cycles. Enumerate reasoning paths "
        "before committing to a conclusion."
    ),
    "memory_dense_mesh": (
        "conservative_recall",
        "Highly interconnected memory. Small queries may activate many "
        "associations. Use targeted filtering."
    ),
    "memory_fragmented_sparse_cyclic": (
        "bridge_building",
        "Multiple disconnected memory clusters with sparse cycles. "
        "Priority: build bridges between clusters before cross-domain reasoning."
    ),
    "memory_fragmented_cyclic": (
        "component_mapping",
        "Multiple clusters with cycles. Map component boundaries first. "
        "Cross-component inference requires explicit validation."
    ),
    "empty": ("direct_store", "No memory structure yet. Store new memories."),
    "trivial": ("direct_store", "Single memory node. Store new memories."),
}


# ============================================================
# 1. Memory Fingerprint Computation
# ============================================================

def compute_memory_fingerprint(
    manifold_data: Dict[str, Any],
    memory_stats: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Hitung memory fingerprint dari manifold data dan stats.
    """
    betti = manifold_data.get("betti_numbers", {})
    vertex_count = manifold_data.get("vertex_count", 0)
    edge_count = manifold_data.get("edge_count", 0)
    avg_degree = manifold_data.get("average_degree", 0.0)
    archetype = manifold_data.get("memory_archetype", "empty")

    # Build invariant vector
    invariant_vector = {
        "beta_0": float(betti.get("beta_0", 0)),
        "beta_1": float(betti.get("beta_1", 0)),
        "beta_2": float(betti.get("beta_2", 0)),
        "vertex_count": float(vertex_count),
        "edge_count": float(edge_count),
        "avg_degree": round(avg_degree, 4),
        "total_memories": float(memory_stats.get("total_memories", 0)),
        "total_associations": float(memory_stats.get("total_associations", 0)),
    }

    # Signature hash
    canonical = {}
    for key in sorted(invariant_vector.keys()):
        val = invariant_vector[key]
        if isinstance(val, float):
            canonical[key] = round(val, 4)
        else:
            canonical[key] = val
    canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    hash_hex = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    signature_hash = f"sha256:{hash_hex[:16]}"

    return {
        "signature_hash": signature_hash,
        "invariant_vector": invariant_vector,
        "betti_numbers": betti,
        "memory_archetype": archetype,
        "archetype_description": manifold_data.get("archetype_description", ""),
        "archetype_confidence": manifold_data.get("archetype_confidence", 0.0),
    }


# ============================================================
# 2. Memory Baseline Management
# ============================================================

def establish_memory_baseline(
    fingerprint: Dict[str, Any],
    health_score: float,
) -> Dict[str, Any]:
    """Simpan memory fingerprint sebagai baseline."""
    os.makedirs(MEMORY_BASELINE_DIR, exist_ok=True)

    baseline = {
        "schema_version": SCHEMA_VERSION,
        "established_at": datetime.datetime.utcnow().isoformat() + "Z",
        "signature_hash": fingerprint["signature_hash"],
        "invariant_vector": fingerprint["invariant_vector"],
        "betti_numbers": fingerprint["betti_numbers"],
        "memory_archetype": fingerprint["memory_archetype"],
        "health_score": health_score,
    }

    with open(MEMORY_BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)

    return {"status": "established", "baseline_path": MEMORY_BASELINE_PATH, "baseline": baseline}


def load_memory_baseline() -> Optional[Dict[str, Any]]:
    """Load memory baseline dari file."""
    if not os.path.isfile(MEMORY_BASELINE_PATH):
        return None
    try:
        with open(MEMORY_BASELINE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ============================================================
# 3. Memory Drift Detection
# ============================================================

def detect_memory_drift(
    fingerprint: Dict[str, Any],
    baseline: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Bandingkan fingerprint saat ini dengan baseline."""
    if baseline is None:
        return {
            "has_baseline": False,
            "has_drift": False,
            "interpretation": "no_baseline",
        }

    baseline_hash = baseline.get("signature_hash", "")
    current_hash = fingerprint.get("signature_hash", "")
    topology_changed = baseline_hash != current_hash

    # Distance pada invariant vector
    baseline_iv = baseline.get("invariant_vector", {})
    current_iv = fingerprint.get("invariant_vector", {})

    keys = sorted(set(baseline_iv.keys()) | set(current_iv.keys()))
    euclidean_sq = sum(
        (current_iv.get(k, 0.0) - baseline_iv.get(k, 0.0)) ** 2 for k in keys
    )
    euclidean = math.sqrt(euclidean_sq)
    drift_score = round(euclidean, 4)

    if drift_score < 0.05:
        interpretation = "none"
    elif drift_score < 0.15:
        interpretation = "low"
    elif drift_score < 0.30:
        interpretation = "medium"
    else:
        interpretation = "high"

    has_drift = topology_changed or drift_score >= 0.05

    # Betti number changes
    baseline_betti = baseline.get("betti_numbers", {})
    current_betti = fingerprint.get("betti_numbers", {})
    betti_changes = {}
    for key in ("beta_0", "beta_1", "beta_2"):
        b_val = baseline_betti.get(key, 0)
        c_val = current_betti.get(key, 0)
        if b_val != c_val:
            betti_changes[key] = {"before": b_val, "after": c_val, "delta": c_val - b_val}

    return {
        "has_baseline": True,
        "has_drift": has_drift,
        "topology_changed": topology_changed,
        "drift_score": drift_score,
        "interpretation": interpretation,
        "betti_changes": betti_changes,
        "baseline_signature": baseline_hash,
        "current_signature": current_hash,
    }


# ============================================================
# 4. Memory Steering Signal Generation
# ============================================================

def generate_memory_steering_signals(
    fingerprint: Dict[str, Any],
    drift: Dict[str, Any],
    health_score: float,
) -> Dict[str, Any]:
    """Hasilkan steering signals dari memory topology."""
    archetype = fingerprint.get("memory_archetype", "empty")
    betti = fingerprint.get("betti_numbers", {})

    strategy, strategy_desc = MEMORY_ARCHETYPE_STRATEGY.get(
        archetype, ("direct_store", "No specific strategy")
    )

    # Reasoning budget dari health score
    if health_score > 0.7:
        budget = "low"
    elif health_score > 0.4:
        budget = "medium"
    else:
        budget = "high"

    # Regrounding dari drift
    regrounding = False
    if drift.get("topology_changed"):
        regrounding = True
    elif drift.get("interpretation") in ("medium", "high"):
        regrounding = True

    # Attention priorities dari Betti numbers
    attention = []
    if betti.get("beta_0", 0) > 1:
        attention.append("knowledge_fragmentation")
    if betti.get("beta_1", 0) > 0:
        attention.append("circular_reasoning_present")
    if betti.get("beta_2", 0) > 0:
        attention.append("missing_abstraction")
    if health_score < 0.5:
        attention.append("low_memory_health")

    return {
        "reasoning_strategy": strategy,
        "strategy_description": strategy_desc,
        "reasoning_budget": budget,
        "regrounding_needed": regrounding,
        "attention_priorities": attention,
        "structural_context": {
            "archetype": archetype,
            "health_score": health_score,
            "connected_components": betti.get("beta_0", 0),
            "independent_cycles": betti.get("beta_1", 0),
            "enclosed_voids": betti.get("beta_2", 0),
        },
    }


# ============================================================
# 5. Memory Steering Prompt Block
# ============================================================

def assemble_memory_prompt_block(
    fingerprint: Dict[str, Any],
    drift: Dict[str, Any],
    signals: Dict[str, Any],
    health_score: float,
) -> str:
    """Assemble compact prompt block untuk memory steering."""
    betti = fingerprint.get("betti_numbers", {})

    if not drift.get("has_baseline"):
        drift_status = "no_baseline"
    elif not drift.get("has_drift"):
        drift_status = "stable"
    else:
        drift_status = f"drift_{drift.get('interpretation', 'unknown')}"

    lines = [
        "[MEMORY STEERING SIGNAL]",
        f"archetype={fingerprint.get('memory_archetype', 'unknown')}",
        f"health={health_score} (budget={signals['reasoning_budget']})",
        f"reasoning_strategy={signals['reasoning_strategy']}",
        f"drift={drift_status}",
        f"regrounding={'true' if signals['regrounding_needed'] else 'false'}",
        f"beta_0={betti.get('beta_0', 0)} beta_1={betti.get('beta_1', 0)} beta_2={betti.get('beta_2', 0)}",
        f"signature={fingerprint.get('signature_hash', 'unknown')}",
        "[MEMORY CONTEXT]",
        signals.get("strategy_description", ""),
    ]

    attention = signals.get("attention_priorities", [])
    if attention:
        lines.append(f"attention={','.join(attention)}")

    return "\n".join(lines)
