"""
Topological Integrity Orchestrator (Proto-HoTT Stage 4)
Schema Version: 2.3.0-synthesis

Reference machine yang menjalankan seluruh Proto-HoTT pipeline:
- Stage 1: type_isomorphism_observer (Univalence Approximation)
- Stage 2: boundary_sheaf_checker (Sheaf Cohomology)
- Stage 3: homotopy_path_observer (Homotopy Path Equivalence)

Kemudian melakukan gluing synthesis:
- Mengagregasi seluruh local observations menjadi unified report
- Menghitung topological_health_score
- Mendeteksi cross-stage correlations

Output bersifat informational dan tidak memberikan rekomendasi perubahan.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "2.3.0-synthesis"

# Tambahkan direktori script ke path untuk import sibling modules
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# ============================================================
# Stage Module Imports (graceful degradation)
# ============================================================

try:
    import type_isomorphism_observer as _stage1
    STAGE1_AVAILABLE = True
except ImportError:
    _stage1 = None
    STAGE1_AVAILABLE = False

try:
    import boundary_sheaf_checker as _stage2
    STAGE2_AVAILABLE = True
except ImportError:
    _stage2 = None
    STAGE2_AVAILABLE = False

try:
    import homotopy_path_observer as _stage3
    STAGE3_AVAILABLE = True
except ImportError:
    _stage3 = None
    STAGE3_AVAILABLE = False


# ============================================================
# Severity Weights & Health Score
# ============================================================

SEVERITY_WEIGHTS = {"high": 3, "medium": 2, "low": 1}


def compute_health_score(findings: List[Dict[str, Any]], total_files: int) -> float:
    """
    Hitung topological health score dalam rentang (0.0, 1.0].

    Formula: score = 1 / (1 + pressure)
    di mana pressure = weighted_obstructions / max(1, total_files)

    - 1.0  : tidak ada obstruksi (topologi bersih sempurna)
    - 0.5  : tekanan obstruksi sebanding dengan jumlah file
    - ~0.0 : obstruksi sangat dominan
    """
    if total_files <= 0:
        return 1.0 if not findings else 0.5

    weighted_sum = 0
    for f in findings:
        sev = f.get("severity", "low")
        weighted_sum += SEVERITY_WEIGHTS.get(sev, 1)

    pressure = weighted_sum / max(1, total_files)
    score = 1.0 / (1.0 + pressure)
    return round(score, 3)


# ============================================================
# Stage Runners
# ============================================================

def run_stage1(scan_root: str) -> Dict[str, Any]:
    """Jalankan Stage 1: Type Isomorphism Observer."""
    if not STAGE1_AVAILABLE:
        return {
            "available": False,
            "error": "type_isomorphism_observer module not found",
        }
    try:
        result = _stage1.scan_directory_for_isomorphisms(scan_root)
        return {"available": True, "result": result}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def run_stage2(scan_root: str) -> Dict[str, Any]:
    """Jalankan Stage 2: Boundary Sheaf Checker."""
    if not STAGE2_AVAILABLE:
        return {
            "available": False,
            "error": "boundary_sheaf_checker module not found",
        }
    try:
        result = _stage2.analyze_boundaries(scan_root)
        return {"available": True, "result": result}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def run_stage3(scan_root: str) -> Dict[str, Any]:
    """Jalankan Stage 3: Homotopy Path Observer."""
    if not STAGE3_AVAILABLE:
        return {
            "available": False,
            "error": "homotopy_path_observer module not found",
        }
    try:
        result = _stage3.observe_homotopy_paths(scan_root)
        return {"available": True, "result": result}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


# ============================================================
# Finding Normalization
# ============================================================

def normalize_stage1_findings(stage1_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalisasi temuan Stage 1 dengan severity default 'low' (observasional)."""
    findings = []
    for pair in stage1_result.get("isomorphic_pairs", []):
        normalized = dict(pair)
        normalized.setdefault("severity", "low")
        normalized["stage"] = "type_isomorphism"
        findings.append(normalized)
    return findings


def normalize_stage2_findings(stage2_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalisasi temuan Stage 2 (obstructions sudah punya severity)."""
    findings = []
    for obs in stage2_result.get("obstructions", []):
        normalized = dict(obs)
        normalized.setdefault("severity", "low")
        normalized["stage"] = "boundary_sheaf"
        findings.append(normalized)
    return findings


def normalize_stage3_findings(stage3_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalisasi temuan Stage 3 (obstructions sudah punya severity)."""
    findings = []
    for obs in stage3_result.get("obstructions", []):
        normalized = dict(obs)
        normalized.setdefault("severity", "low")
        normalized["stage"] = "homotopy_paths"
        findings.append(normalized)
    return findings


# ============================================================
# Cross-Stage Correlation Detector
# ============================================================

def detect_cross_stage_correlations(
    stage1_result: Optional[Dict[str, Any]],
    stage2_result: Optional[Dict[str, Any]],
    stage3_result: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Deteksi korelasi lintas stage (gluing synthesis).

    Correlation 1: Isomorphic types across different boundaries
    - Stage 1 menemukan pasangan type isomorfik
    - Stage 2 mengidentifikasi boundary tiap file
    - Jika dua type isomorfik berada di boundary berbeda, ini adalah
      korelasi: duplikasi type berkorelasi dengan fragmentasi boundary.
    """
    correlations: List[Dict[str, Any]] = []

    if not stage1_result or not stage2_result:
        return correlations

    # Kumpulkan boundary paths
    boundary_paths = [b.get("path") for b in stage2_result.get("boundaries", []) if b.get("path")]

    def find_boundary_for_file(file_path: str) -> Optional[str]:
        for bp in boundary_paths:
            if file_path.startswith(bp + "/") or file_path == bp:
                return bp
        return None

    # Cek setiap pasangan isomorfik
    for pair in stage1_result.get("isomorphic_pairs", []):
        space_a = pair.get("space_a", {})
        space_b = pair.get("space_b", {})

        file_a = space_a.get("file") or pair.get("file", "")
        file_b = space_b.get("file") or pair.get("file_b", file_a)

        if not file_a or not file_b:
            continue

        boundary_a = find_boundary_for_file(file_a)
        boundary_b = find_boundary_for_file(file_b)

        if (
            boundary_a
            and boundary_b
            and boundary_a != boundary_b
        ):
            correlations.append({
                "type": "isomorphic_across_boundaries",
                "severity": "medium",
                "type_name_a": space_a.get("name", "unknown"),
                "type_name_b": space_b.get("name", "unknown"),
                "boundary_a": boundary_a,
                "boundary_b": boundary_b,
                "isomorphism_confidence": pair.get("isomorphism_confidence", 0.0),
                "observation": (
                    f"Isomorphic types '{space_a.get('name')}' ({boundary_a}) and "
                    f"'{space_b.get('name')}' ({boundary_b}) are structurally equivalent "
                    f"but reside in different boundaries. Type duplication correlates "
                    f"with boundary fragmentation."
                ),
                "invariant": "cross_stage_isomorphism_boundary",
            })

    correlations.sort(key=lambda c: (c.get("boundary_a", ""), c.get("type_name_a", "")))
    return correlations


# ============================================================
# Main Synthesis Orchestrator
# ============================================================

def synthesize_topological_integrity(scan_root: str = ".") -> Dict[str, Any]:
    """
    Orkestrasi penuh Proto-HoTT pipeline + gluing synthesis.

    1. Jalankan Stage 1, 2, 3 (graceful degradation jika module tidak ada)
    2. Normalisasi dan agregasi seluruh findings
    3. Hitung topological_health_score
    4. Deteksi cross-stage correlations
    5. Susun unified report deterministik
    """
    # Step 1: Jalankan semua stage
    s1 = run_stage1(scan_root)
    s2 = run_stage2(scan_root)
    s3 = run_stage3(scan_root)

    # Step 2: Ekstrak findings dari setiap stage yang tersedia
    all_findings: List[Dict[str, Any]] = []

    stage1_result = s1.get("result") if s1.get("available") else None
    stage2_result = s2.get("result") if s2.get("available") else None
    stage3_result = s3.get("result") if s3.get("available") else None

    if stage1_result:
        all_findings.extend(normalize_stage1_findings(stage1_result))
    if stage2_result:
        all_findings.extend(normalize_stage2_findings(stage2_result))
    if stage3_result:
        all_findings.extend(normalize_stage3_findings(stage3_result))

    # Step 3: Tentukan total_files dari stage yang tersedia
    total_files = 0
    if stage3_result:
        total_files = stage3_result.get("total_files", 0)
    elif stage1_result:
        total_files = stage1_result.get("files_scanned", 0)

    # Step 4: Hitung health score
    health_score = compute_health_score(all_findings, total_files)

    # Step 5: Deteksi cross-stage correlations
    correlations = detect_cross_stage_correlations(
        stage1_result, stage2_result, stage3_result
    )

    # Step 6: Hitung ringkasan per severity dan per stage
    by_severity = {"high": 0, "medium": 0, "low": 0}
    by_stage = {
        "type_isomorphism": 0,
        "boundary_sheaf": 0,
        "homotopy_paths": 0,
    }

    for f in all_findings:
        sev = f.get("severity", "low")
        if sev in by_severity:
            by_severity[sev] += 1

        stage = f.get("stage", "")
        if stage in by_stage:
            by_stage[stage] += 1

    # Hitung obstructions (high/medium) vs observations (low)
    total_obstructions = by_severity["high"] + by_severity["medium"]
    total_observations = by_severity["low"]

    # Step 7: Sort findings deterministik
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_findings.sort(
        key=lambda f: (
            severity_order.get(f.get("severity", "low"), 3),
            f.get("stage", ""),
            f.get("type", ""),
        )
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "scan_root": scan_root,
        "generated_stages": {
            "type_isomorphism": STAGE1_AVAILABLE,
            "boundary_sheaf": STAGE2_AVAILABLE,
            "homotopy_paths": STAGE3_AVAILABLE,
        },
        "stages": {
            "type_isomorphism": stage1_result if stage1_result else s1,
            "boundary_sheaf": stage2_result if stage2_result else s2,
            "homotopy_paths": stage3_result if stage3_result else s3,
        },
        "unified_summary": {
            "total_files": total_files,
            "total_findings": len(all_findings),
            "total_obstructions": total_obstructions,
            "total_observations": total_observations,
            "by_severity": by_severity,
            "by_stage": by_stage,
            "topological_health_score": health_score,
        },
        "all_findings": all_findings,
        "cross_stage_correlations": correlations,
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = "."

    print(json.dumps(synthesize_topological_integrity(root), indent=2))
