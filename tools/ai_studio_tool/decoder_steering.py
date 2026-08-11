"""
Topological Decoder Steering (Proto-HoTT Stage 7)
Schema Version: 2.6.0-steering

Memanipulasi proses decoding agent AI melalui sinyal topologis,
TANPA menyentuh weight LLM. Tiga mekanisme:

1. Baseline Establishment: simpan fingerprint sebagai referensi
2. Drift Detection: deteksi perubahan bentuk topologis
3. Steering Signal Generation: hasilkan strategi reasoning + context block

Mode operasi:
- establish : buat baseline dari fingerprint saat ini
- steer     : bandingkan current vs baseline, hasilkan steering signal
- compare   : bandingkan dua root tanpa baseline

Output bersifat informational dan tidak memberikan rekomendasi perubahan.
Steering signal adalah conditioning context, bukan constraint.
"""

import datetime
import json
import os
import sys
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "2.6.0-steering"

# Tambahkan direktori script ke path untuk import Stage 6
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# Default baseline storage location (relatif terhadap script dir)
DEFAULT_BASELINE_PATH = os.path.join(_SCRIPT_DIR, "baseline", "topological_baseline.json")

try:
    import invariant_encoder as _stage6
    STAGE6_AVAILABLE = True
except ImportError:
    _stage6 = None
    STAGE6_AVAILABLE = False


# ============================================================
# Archetype → Reasoning Strategy Mapping
# ============================================================

ARCHETYPE_STRATEGY = {
    "tree_like": (
        "hierarchical_traversal",
        "Structure is a connected tree. Root-to-leaf traversal is natural; "
        "top-down changes propagate predictably downward."
    ),
    "modular": (
        "isolated_analysis",
        "Structure has disconnected components. Analyze per module; "
        "changes are likely localized within a component."
    ),
    "sparse_cyclic": (
        "cycle_aware_traversal",
        "Connected structure with sparse cycles. Verify cycle membership "
        "before changes that touch cyclic regions."
    ),
    "mixed_cyclic": (
        "path_enumeration",
        "Moderate interconnection with cycles. Enumerate dependency paths "
        "before modifying nodes with multiple routes."
    ),
    "dense_mesh": (
        "conservative_edit",
        "Highly interconnected mesh. Small changes may have wide-reaching "
        "effects; broad impact analysis is warranted."
    ),
    "fragmented_sparse_cyclic": (
        "component_localized_traversal",
        "Multiple disconnected components with sparse cycles. Changes are "
        "localized within a component; verify cycle membership only within "
        "the affected component. Cross-component impact is structurally impossible."
    ),
    "fragmented_cyclic": (
        "component_boundary_mapping",
        "Multiple disconnected components with cycles. Map component boundaries "
        "first; cross-component changes require explicit interface verification."
    ),
    "empty": (
        "direct_edit",
        "No topological structure present."
    ),
    "trivial": (
        "direct_edit",
        "Single isolated node; no structural complexity."
    ),
}


def compute_reasoning_budget(complexity_score: float) -> str:
    """
    Petakan complexity score ke reasoning budget.

    Ini adalah conditioning signal untuk agent:
    - low    : kompleksitas rendah, agent bisa langsung bekerja
    - medium : kompleksitas sedang, verifikasi impact disarankan
    - high   : kompleksitas tinggi, analisis mendalam diperlukan
    """
    if complexity_score < 0.2:
        return "low"
    elif complexity_score < 0.5:
        return "medium"
    else:
        return "high"


# ============================================================
# Baseline Management
# ============================================================

def establish_baseline(
    scan_root: str = ".",
    baseline_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Simpan topological fingerprint saat ini sebagai baseline referensi.

    Baseline ini menjadi acuan untuk drift detection di masa depan.
    """
    if not STAGE6_AVAILABLE:
        return {
            "schema_version": SCHEMA_VERSION,
            "error": "invariant_encoder module not found",
            "available": False,
        }

    if baseline_path is None:
        baseline_path = DEFAULT_BASELINE_PATH

    encoded = _stage6.encode_topological_invariants(scan_root)

    if not encoded.get("available", False):
        return {
            "schema_version": SCHEMA_VERSION,
            "error": encoded.get("error", "encoding failed"),
            "available": False,
        }

    baseline = {
        "schema_version": SCHEMA_VERSION,
        "established_at": datetime.datetime.utcnow().isoformat() + "Z",
        "scan_root": scan_root,
        "signature_hash": encoded["topological_fingerprint"]["signature_hash"],
        "complexity_score": encoded["topological_fingerprint"]["complexity_score"],
        "structural_archetype": encoded["topological_fingerprint"]["structural_archetype"],
        "invariant_vector": encoded["source_invariant_vector"],
        "normalized_vector": encoded["topological_fingerprint"]["normalized_vector"],
        "betti_numbers": encoded["summary"]["betti_numbers"],
    }

    # Persist ke file
    try:
        parent_dir = os.path.dirname(baseline_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "error": f"baseline_save_failed: {exc}",
            "available": False,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "establish",
        "baseline_path": baseline_path,
        "baseline": baseline,
        "available": True,
    }


def load_baseline(baseline_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load baseline dari file. Return None jika tidak ada."""
    if baseline_path is None:
        baseline_path = DEFAULT_BASELINE_PATH

    if not os.path.isfile(baseline_path):
        return None

    try:
        with open(baseline_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ============================================================
# Drift Detection
# ============================================================

def detect_drift(
    current_fingerprint: Dict[str, Any],
    current_invariant_vector: Dict[str, float],
    baseline: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Bandingkan fingerprint saat ini dengan baseline.

    Menghasilkan drift analysis:
    - has_drift: apakah ada perubahan topologis
    - drift_score: magnitudo perubahan
    - per_dimension: breakdown perubahan per dimensi
    - topology_changed: apakah signature hash berubah
    """
    baseline_hash = baseline.get("signature_hash", "")
    current_hash = current_fingerprint.get("signature_hash", "")

    # Signature comparison (fast path)
    topology_changed = baseline_hash != current_hash

    # Distance comparison (detailed)
    baseline_normalized = baseline.get("normalized_vector", {})
    current_normalized = current_fingerprint.get("normalized_vector", {})

    distance = _stage6.compute_fingerprint_distance(
        current_normalized, baseline_normalized
    )

    # Drift score: gunakan topological_distance sebagai metrik utama
    drift_score = distance.get("topological_distance", 0.0)

    # Interpretasi drift
    if drift_score < 0.05:
        interpretation = "none"
    elif drift_score < 0.15:
        interpretation = "low"
    elif drift_score < 0.30:
        interpretation = "medium"
    else:
        interpretation = "high"

    has_drift = topology_changed or drift_score >= 0.05

    # Per-dimension breakdown
    per_dimension = {}
    all_keys = sorted(set(baseline_normalized.keys()) | set(current_normalized.keys()))
    for key in all_keys:
        before = baseline_normalized.get(key, 0.0)
        after = current_normalized.get(key, 0.0)
        delta = round(after - before, 4)
        if abs(delta) > 0.0001:
            per_dimension[key] = {
                "before": before,
                "after": after,
                "delta": delta,
            }

    return {
        "has_drift": has_drift,
        "topology_changed": topology_changed,
        "drift_score": drift_score,
        "interpretation": interpretation,
        "distance_metrics": distance,
        "per_dimension": per_dimension,
        "baseline_signature": baseline_hash,
        "current_signature": current_hash,
    }


# ============================================================
# Steering Signal Generation
# ============================================================

def generate_steering_signals(
    fingerprint: Dict[str, Any],
    drift_analysis: Optional[Dict[str, Any]],
    betti: Dict[str, int],
) -> Dict[str, Any]:
    """
    Hasilkan steering signals berdasarkan fingerprint + drift.

    Steering signals adalah conditioning context untuk decoder:
    - reasoning_strategy: cara menalar yang sesuai bentuk topologis
    - reasoning_budget: seberapa dalam analisis diperlukan
    - regrounding_needed: apakah agent perlu memperbarui pemahaman
    - structural_context: konteks topologis ringkas
    """
    archetype = fingerprint.get("structural_archetype", "empty")
    complexity = fingerprint.get("complexity_score", 0.0)

    strategy, strategy_desc = ARCHETYPE_STRATEGY.get(
        archetype, ("direct_edit", "No specific strategy")
    )

    budget = compute_reasoning_budget(complexity)

    # Regrounding decision berdasarkan drift
    regrounding_needed = False
    if drift_analysis:
        if drift_analysis.get("topology_changed"):
            regrounding_needed = True
        elif drift_analysis.get("interpretation") in ("medium", "high"):
            regrounding_needed = True

    # Attention priorities berdasarkan Betti numbers
    attention_priorities = []
    if betti.get("beta_1", 0) > 0:
        attention_priorities.append("independent_cycles_present")
    if betti.get("beta_0", 0) > 1:
        attention_priorities.append("multiple_disconnected_components")
    if betti.get("beta_2", 0) > 0:
        attention_priorities.append("enclosed_voids_present")

    return {
        "reasoning_strategy": strategy,
        "strategy_description": strategy_desc,
        "reasoning_budget": budget,
        "regrounding_needed": regrounding_needed,
        "attention_priorities": attention_priorities,
        "structural_context": {
            "archetype": archetype,
            "complexity": complexity,
            "connected_components": betti.get("beta_0", 0),
            "independent_cycles": betti.get("beta_1", 0),
            "enclosed_voids": betti.get("beta_2", 0),
        },
    }


# ============================================================
# Steering Prompt Block Assembly
# ============================================================

def assemble_steering_prompt_block(
    fingerprint: Dict[str, Any],
    drift_analysis: Optional[Dict[str, Any]],
    steering_signals: Dict[str, Any],
    betti: Dict[str, int],
) -> str:
    """
    Gabungkan semua sinyal menjadi prompt block compact untuk decoder.

    Format dirancang token-efisien tapi informatif.
    Ini adalah teks yang akan di-inject ke LLM context window.
    """
    signature = fingerprint.get("signature_hash", "unknown")
    archetype = fingerprint.get("structural_archetype", "unknown")
    complexity = fingerprint.get("complexity_score", 0.0)
    budget = steering_signals.get("reasoning_budget", "low")
    strategy = steering_signals.get("reasoning_strategy", "direct_edit")

    # Drift status
    if drift_analysis is None:
        drift_status = "no_baseline"
    elif not drift_analysis.get("has_drift"):
        drift_status = "stable"
    else:
        drift_status = f"drift_{drift_analysis.get('interpretation', 'unknown')}"

    regrounding = steering_signals.get("regrounding_needed", False)

    lines = [
        "[TOPOLOGICAL STEERING SIGNAL]",
        f"archetype={archetype}",
        f"complexity={complexity} (budget={budget})",
        f"reasoning_strategy={strategy}",
        f"drift={drift_status}",
        f"regrounding={'true' if regrounding else 'false'}",
        f"beta_0={betti.get('beta_0', 0)} beta_1={betti.get('beta_1', 0)} beta_2={betti.get('beta_2', 0)}",
        f"signature={signature}",
        "[STEERING CONTEXT]",
        steering_signals.get("strategy_description", ""),
    ]

    # Tambahkan attention priorities jika ada
    priorities = steering_signals.get("attention_priorities", [])
    if priorities:
        lines.append(f"attention={','.join(priorities)}")

    return "\n".join(lines)


# ============================================================
# Main Orchestrator
# ============================================================

def steer_decoder(
    scan_root: str = ".",
    baseline_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Orkestrasi penuh Decoder Steering (mode: steer).

    1. Encode fingerprint saat ini (Stage 6)
    2. Load baseline
    3. Detect drift
    4. Generate steering signals
    5. Assemble steering prompt block
    """
    if not STAGE6_AVAILABLE:
        return {
            "schema_version": SCHEMA_VERSION,
            "error": "invariant_encoder module not found",
            "available": False,
        }

    # Step 1: Encode current fingerprint
    encoded = _stage6.encode_topological_invariants(scan_root)

    if not encoded.get("available", False):
        return {
            "schema_version": SCHEMA_VERSION,
            "error": encoded.get("error", "encoding failed"),
            "available": False,
        }

    current_fingerprint = encoded["topological_fingerprint"]
    current_invariant_vector = encoded["source_invariant_vector"]
    betti = encoded["summary"]["betti_numbers"]

    # Step 2: Load baseline
    baseline = load_baseline(baseline_path)
    has_baseline = baseline is not None

    # Step 3: Detect drift
    drift_analysis = None
    if has_baseline:
        drift_analysis = detect_drift(
            current_fingerprint, current_invariant_vector, baseline
        )

    # Step 4: Generate steering signals
    steering_signals = generate_steering_signals(
        current_fingerprint, drift_analysis, betti
    )

    # Step 5: Assemble steering prompt block
    steering_prompt_block = assemble_steering_prompt_block(
        current_fingerprint, drift_analysis, steering_signals, betti
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "steer",
        "scan_root": scan_root,
        "available": True,
        "baseline": {
            "exists": has_baseline,
            "path": baseline_path or DEFAULT_BASELINE_PATH,
            "established_at": baseline.get("established_at") if baseline else None,
            "signature_hash": baseline.get("signature_hash") if baseline else None,
        },
        "current_fingerprint": current_fingerprint,
        "drift_analysis": drift_analysis,
        "steering_signals": steering_signals,
        "steering_prompt_block": steering_prompt_block,
        "summary": {
            "has_baseline": has_baseline,
            "topology_changed": drift_analysis.get("topology_changed") if drift_analysis else None,
            "drift_interpretation": drift_analysis.get("interpretation") if drift_analysis else "no_baseline",
            "reasoning_strategy": steering_signals["reasoning_strategy"],
            "reasoning_budget": steering_signals["reasoning_budget"],
            "regrounding_needed": steering_signals["regrounding_needed"],
        },
    }


def compare_roots(root_a: str, root_b: str) -> Dict[str, Any]:
    """
    Bandingkan topological fingerprint dua root tanpa baseline (mode: compare).
    """
    if not STAGE6_AVAILABLE:
        return {
            "schema_version": SCHEMA_VERSION,
            "error": "invariant_encoder module not found",
            "available": False,
        }

    encoded_a = _stage6.encode_topological_invariants(root_a)
    encoded_b = _stage6.encode_topological_invariants(root_b)

    if not encoded_a.get("available") or not encoded_b.get("available"):
        return {
            "schema_version": SCHEMA_VERSION,
            "error": "encoding failed for one or both roots",
            "available": False,
        }

    fp_a = encoded_a["topological_fingerprint"]
    fp_b = encoded_b["topological_fingerprint"]

    distance = _stage6.compute_fingerprint_distance(
        fp_a["normalized_vector"], fp_b["normalized_vector"]
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "compare",
        "root_a": root_a,
        "root_b": root_b,
        "signature_a": fp_a["signature_hash"],
        "signature_b": fp_b["signature_hash"],
        "signatures_match": fp_a["signature_hash"] == fp_b["signature_hash"],
        "archetype_a": fp_a["structural_archetype"],
        "archetype_b": fp_b["structural_archetype"],
        "distance_metrics": distance,
        "available": True,
    }


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "steer"

    if mode == "establish":
        root = sys.argv[2] if len(sys.argv) > 2 else "."
        baseline_path = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(establish_baseline(root, baseline_path), indent=2))

    elif mode == "steer":
        root = sys.argv[2] if len(sys.argv) > 2 else "."
        baseline_path = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(steer_decoder(root, baseline_path), indent=2))

    elif mode == "compare":
        root_a = sys.argv[2] if len(sys.argv) > 2 else "."
        root_b = sys.argv[3] if len(sys.argv) > 3 else "."
        print(json.dumps(compare_roots(root_a, root_b), indent=2))

    else:
        print(json.dumps({
            "tool": "decoder_steering",
            "schema_version": SCHEMA_VERSION,
            "usage": {
                "establish": "python3 decoder_steering.py establish [root] [baseline_path]",
                "steer": "python3 decoder_steering.py steer [root] [baseline_path]",
                "compare": "python3 decoder_steering.py compare [root_a] [root_b]",
            }
        }, indent=2))
