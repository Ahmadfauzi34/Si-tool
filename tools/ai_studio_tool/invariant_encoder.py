"""
Invariant Encoder (Proto-HoTT Stage 6)
Schema Version: 2.5.0-encoder

Mengencode topological invariant vector menjadi topological fingerprint:
- signature_hash: identitas topologis deterministik (untuk change detection)
- normalized_vector: representasi unified [0,1] (untuk comparison)
- complexity_score: ukuran kompleksitas topologis (untuk difficulty estimation)
- structural_archetype: klasifikasi bentuk struktural (untuk reasoning strategy)
- context_block: representasi tekstual compact (untuk decoder injection)
- distance_metrics: jarak antar fingerprint (untuk drift detection di Stage 7)

Output bersifat informational dan tidak memberikan rekomendasi perubahan.
"""

import json
import math
import os
import sys
import hashlib
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "2.5.0-encoder"

# Tambahkan direktori script ke path untuk import Stage 5
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

try:
    import topological_manifold_builder as _stage5
    STAGE5_AVAILABLE = True
except ImportError:
    _stage5 = None
    STAGE5_AVAILABLE = False


# ============================================================
# Normalization
# ============================================================

def _saturate(x: float, half_point: float) -> float:
    """
    Saturasi nilai x ke rentang [0, 1].

    half_point adalah nilai x yang menghasilkan output 0.5.
    Fungsi ini asymptotic ke 1.0 untuk x yang sangat besar,
    sehingga stabil dan tidak pernah overflow.
    """
    if x <= 0:
        return 0.0
    if half_point <= 0:
        return 1.0
    return x / (x + half_point)


def _clamp01(x: float) -> float:
    """Clamp nilai ke [0, 1]."""
    return max(0.0, min(1.0, x))


def normalize_invariant_vector(invariant_vector: Dict[str, float]) -> Dict[str, float]:
    """
    Normalisasi invariant vector menjadi representasi unified [0,1].

    TERKALIBRASI (final): menggunakan n_avg_degree (scale-aware)


    average_degree = 2·E / V
    - Tree memiliki avg_degree ~2
    - Graph moderate ~3-5
    - Graph dense >5
    """
    beta_0 = invariant_vector.get("beta_0", 0.0)
    beta_1 = invariant_vector.get("beta_1", 0.0)
    beta_2 = invariant_vector.get("beta_2", 0.0)
    h0_mean = invariant_vector.get("h0_mean_persistence", 0.0)
    h1_mean = invariant_vector.get("h1_mean_persistence", 0.0)
    vertex_count = invariant_vector.get("vertex_count", 0.0)
    edge_count = invariant_vector.get("edge_count", 0.0)

    # Scale-aware interconnectedness: average degree
    average_degree = (2.0 * edge_count / vertex_count) if vertex_count > 0 else 0.0

    return {
        # Betti numbers: saturasi pada skala topologis
        "n_beta_0": round(_clamp01(_saturate(beta_0, 4.0)), 4),
        "n_beta_1": round(_clamp01(_saturate(beta_1, 8.0)), 4),
        "n_beta_2": round(_clamp01(_saturate(beta_2, 4.0)), 4),

        # Persistence: saturasi pada skala filtration steps
        "n_h0_persistence": round(_clamp01(_saturate(h0_mean, 10.0)), 4),
        "n_h1_persistence": round(_clamp01(_saturate(h1_mean, 10.0)), 4),

        # Skala codebase: saturasi pada ukuran tipikal
        "n_vertex_scale": round(_clamp01(_saturate(vertex_count, 100.0)), 4),
        "n_edge_scale": round(_clamp01(_saturate(edge_count, 200.0)), 4),

        # TERKALIBRASI: average degree menggantikan edge_density
        # half_point=5.0: tree (~2) rendah, dense mesh (>5) tinggi
        "n_avg_degree": round(_clamp01(_saturate(average_degree, 5.0)), 4),
    }


# ============================================================
# Signature Hash (Topological Identity)
# ============================================================

def compute_signature_hash(
    invariant_vector: Dict[str, float],
    precision: int = 4,
) -> str:
    """
    Hitung signature hash deterministik dari invariant vector.

    Hash ini adalah "identitas topologis" codebase:
    - Hash sama → bentuk topologis sama
    - Hash berbeda → bentuk topologis berubah

    Float dibulatkan ke `precision` untuk stabilitas terhadap
    variasi floating-point kecil.
    """
    canonical: Dict[str, Any] = {}

    for key in sorted(invariant_vector.keys()):
        value = invariant_vector[key]
        if isinstance(value, float):
            canonical[key] = round(value, precision)
        else:
            canonical[key] = value

    canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    hash_hex = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    return f"sha256:{hash_hex[:16]}"


# ============================================================
# Complexity Score
# ============================================================

def compute_complexity_score(normalized_vector: Dict[str, float]) -> float:
    """
    Hitung topological complexity score dalam [0, 1].

    TERKALIBRASI (final): menggunakan n_avg_degree (scale-aware)

    """
    weights = {
        "n_beta_1": 0.30,          # cycles = redundancy complexity
        "n_beta_0": 0.10,          # fragmentation
        "n_beta_2": 0.10,          # higher-order voids
        "n_avg_degree": 0.25,      # TERKALIBRASI: interconnectedness (scale-aware)
        "n_h1_persistence": 0.15,  # persistent cycles
        "n_edge_scale": 0.10,      # overall scale
    }

    score = 0.0
    for key, weight in weights.items():
        score += weight * normalized_vector.get(key, 0.0)

    return round(_clamp01(score), 4)


# ============================================================
# Structural Archetype Classification
# ============================================================

def classify_archetype(
    betti: Dict[str, int],
    edge_density: float,
    vertex_count: int,
) -> Tuple[str, str, float]:
    """
    Klasifikasikan codebase ke dalam structural archetype (TERKALIBRASI).

    Kalibrasi:
    - Menggunakan average_degree (scale-aware) menggantikan edge_density absolut.
      average_degree = edge_density * (vertex_count - 1)
    - Menghormati fragmentasi (beta_0 > 1) bahkan ketika ada cycles.

    Threshold average_degree:
    - < 2.5  : sparse (tree-like, avg degree tree ~2)
    - 2.5-5  : moderate interconnection
    - > 5    : dense
    """
    if vertex_count == 0:
        return "empty", "No topological structure", 1.0

    beta_0 = betti.get("beta_0", 0)
    beta_1 = betti.get("beta_1", 0)
    beta_2 = betti.get("beta_2", 0)

    if vertex_count == 1:
        return "trivial", "Single isolated node", 1.0

    # Scale-aware interconnectedness
    average_degree = edge_density * (vertex_count - 1) if vertex_count > 1 else 0.0

    is_fragmented = beta_0 > 1
    has_cycles = beta_1 > 0 or beta_2 > 0

    # Case 1: Acyclic
    if not has_cycles:
        if not is_fragmented:
            return (
                "tree_like",
                "Connected acyclic structure (hierarchical tree)",
                0.95,
            )
        else:
            return (
                "modular",
                f"{beta_0} disconnected acyclic components (isolated modules)",
                0.90,
            )

    # Case 2: Has cycles — hormati fragmentasi & gunakan average_degree
    if is_fragmented:
        if average_degree < 2.5:
            return (
                "fragmented_sparse_cyclic",
                f"{beta_0} disconnected components with {beta_1} independent "
                f"cycle(s); sparse interconnection (avg degree {average_degree:.2f})",
                0.80,
            )
        else:
            return (
                "fragmented_cyclic",
                f"{beta_0} disconnected components with {beta_1} independent "
                f"cycle(s); moderate interconnection (avg degree {average_degree:.2f})",
                0.75,
            )
    else:
        # Connected (beta_0 == 1)
        if average_degree < 2.5:
            return (
                "sparse_cyclic",
                "Connected with cycles but sparse interconnection "
                f"(avg degree {average_degree:.2f})",
                0.80,
            )
        elif average_degree < 5.0:
            return (
                "mixed_cyclic",
                "Connected with moderate interconnection and independent cycles "
                f"(avg degree {average_degree:.2f})",
                0.70,
            )
        else:
            return (
                "dense_mesh",
                "Highly interconnected with many independent cycles "
                f"(avg degree {average_degree:.2f})",
                0.75,
            )


# ============================================================
# Distance Metrics (untuk Stage 7 drift detection)
# ============================================================

def compute_fingerprint_distance(
    vector_a: Dict[str, float],
    vector_b: Dict[str, float],
) -> Dict[str, float]:
    """
    Hitung jarak antara dua normalized fingerprint vectors.

    Metrics:
    - euclidean: jarak geometris standar
    - cosine_similarity: kesamaan arah (1 = identik arah)
    - topological_distance: weighted, fokus pada Betti numbers
    """
    keys = sorted(set(vector_a.keys()) | set(vector_b.keys()))

    # Euclidean distance
    euclidean_sq = 0.0
    for k in keys:
        diff = vector_a.get(k, 0.0) - vector_b.get(k, 0.0)
        euclidean_sq += diff * diff
    euclidean = math.sqrt(euclidean_sq)

    # Cosine similarity
    dot = sum(vector_a.get(k, 0.0) * vector_b.get(k, 0.0) for k in keys)
    mag_a = math.sqrt(sum(vector_a.get(k, 0.0) ** 2 for k in keys))
    mag_b = math.sqrt(sum(vector_b.get(k, 0.0) ** 2 for k in keys))
    cosine = (dot / (mag_a * mag_b)) if (mag_a > 0 and mag_b > 0) else 0.0

    # Topological distance: bobot lebih pada Betti numbers
    topo_weights = {
        "n_beta_0": 2.0,
        "n_beta_1": 3.0,
        "n_beta_2": 2.0,
        "n_h0_persistence": 1.0,
        "n_h1_persistence": 1.5,
        "n_vertex_scale": 0.5,
        "n_edge_scale": 0.5,
        "n_avg_degree": 1.0,
    }
    topo_dist = 0.0
    total_weight = 0.0
    for k, w in topo_weights.items():
        diff = abs(vector_a.get(k, 0.0) - vector_b.get(k, 0.0))
        topo_dist += w * diff
        total_weight += w
    topological = (topo_dist / total_weight) if total_weight > 0 else 0.0

    return {
        "euclidean": round(euclidean, 4),
        "cosine_similarity": round(cosine, 4),
        "topological_distance": round(topological, 4),
    }


# ============================================================
# Context Block (bridge to decoder)
# ============================================================

def generate_context_block(
    fingerprint: Dict[str, Any],
    betti: Dict[str, int],
) -> str:
    """
    Generate compact textual representation untuk LLM context injection.

    Ini adalah "bahasa" yang akan dibaca decoder agent di Stage 7.
    Format dirancang untuk token-efisien tapi informatif.
    """
    lines = [
        "[TOPOLOGICAL FINGERPRINT]",
        f"archetype={fingerprint['structural_archetype']}",
        f"complexity={fingerprint['complexity_score']}",
        f"beta_0(components)={betti.get('beta_0', 0)}",
        f"beta_1(cycles)={betti.get('beta_1', 0)}",
        f"beta_2(voids)={betti.get('beta_2', 0)}",
        f"signature={fingerprint['signature_hash']}",
    ]
    return "\n".join(lines)


# ============================================================
# Main Encoder
# ============================================================

def encode_topological_invariants(scan_root: str = ".") -> Dict[str, Any]:
    """
    Orkestrasi penuh Invariant Encoder.

    1. Jalankan Stage 5 untuk mendapatkan manifold + invariant_vector
    2. Normalize invariant vector
    3. Compute signature hash
    4. Compute complexity score
    5. Classify structural archetype
    6. Generate context block
    7. Siapkan distance metrics (untuk Stage 7)
    """
    if not STAGE5_AVAILABLE:
        return {
            "schema_version": SCHEMA_VERSION,
            "scan_root": scan_root,
            "error": "topological_manifold_builder module not found",
            "available": False,
        }

    try:
        manifold_result = _stage5.build_topological_manifold(scan_root)
    except Exception as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "scan_root": scan_root,
            "error": str(exc),
            "available": False,
        }

    invariant_vector = manifold_result.get("invariant_vector", {})
    betti = manifold_result.get("manifold", {}).get("betti_numbers", {})
    vertex_count = manifold_result.get("manifold", {}).get("vertex_count", 0)
    edge_density = invariant_vector.get("edge_density", 0.0)

    # Step 2: Normalize
    normalized_vector = normalize_invariant_vector(invariant_vector)

    # Step 3: Signature hash
    signature_hash = compute_signature_hash(invariant_vector)

    # Step 4: Complexity score
    complexity_score = compute_complexity_score(normalized_vector)

    # Step 5: Archetype classification
    archetype, archetype_desc, archetype_confidence = classify_archetype(
        betti, edge_density, vertex_count
    )

    # Susun fingerprint
    fingerprint = {
        "signature_hash": signature_hash,
        "normalized_vector": normalized_vector,
        "complexity_score": complexity_score,
        "structural_archetype": archetype,
        "archetype_description": archetype_desc,
        "archetype_confidence": archetype_confidence,
    }

    # Step 6: Context block
    context_block = generate_context_block(fingerprint, betti)

    # Step 7: Distance metrics (self-distance = 0, reference = null)
    self_distance = compute_fingerprint_distance(normalized_vector, normalized_vector)

    return {
        "schema_version": SCHEMA_VERSION,
        "scan_root": scan_root,
        "available": True,
        "source_invariant_vector": invariant_vector,
        "topological_fingerprint": fingerprint,
        "context_block": context_block,
        "distance_metrics": {
            "self_distance": self_distance,
            "reference_distance": None,
            "note": "reference_distance akan terisi di Stage 7 saat baseline tersedia",
        },
        "summary": {
            "vertex_count": vertex_count,
            "betti_numbers": betti,
            "structural_archetype": archetype,
            "complexity_score": complexity_score,
            "signature_hash": signature_hash,
        },
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = "."

    print(json.dumps(encode_topological_invariants(root), indent=2))
