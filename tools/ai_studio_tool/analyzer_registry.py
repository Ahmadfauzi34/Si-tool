"""
Analyzer Registry — HoTT Kernel
Schema Version: 3.0.0-kernel

Setiap analyzer adalah fungsi yang menerima SharedGraph
dan mengembalikan findings. Tidak ada analyzer yang boleh
melakukan filesystem scan sendiri.

Interface:
    def analyzer_name(shared_graph: Dict) -> Dict:
        return {
            "analyzer": "name",
            "findings": [...],
            "summary": {...}
        }
"""

from typing import Any, Dict, List, Optional

# Import topology analyzers
try:
    from topology_analyzers import (
        analyze_circular,
        analyze_risk,
    )
    TOPO_ANALYZERS_AVAILABLE = True
except ImportError:
    TOPO_ANALYZERS_AVAILABLE = False


# Import performance analyzers
try:
    from performance_analyzers import (
        analyze_async_waterfall,
        analyze_deopt,
        analyze_gc_pressure,
        analyze_cache,
    )
    PERF_ANALYZERS_AVAILABLE = True
except ImportError:
    PERF_ANALYZERS_AVAILABLE = False


# Import HoTT analyzers
try:
    from hott_analyzers import (
        analyze_isomorphism,
        analyze_sheaf,
        analyze_homotopy,
        analyze_manifold,
    )
    HOTT_ANALYZERS_AVAILABLE = True
except ImportError:
    HOTT_ANALYZERS_AVAILABLE = False
    

# ============================================================
# Analyzer Interface Documentation
# ============================================================
#
# Setiap analyzer HARUS memenuhi kontrak ini:
#
# 1. Input: shared_graph dict (dari build_shared_graph)
# 2. Output: dict dengan keys "analyzer", "findings", "summary"
# 3. DILARANG melakukan os.walk(), open(), atau I/O filesystem
# 4. Semua data diambil dari shared_graph
# 5. Deterministik: output sama untuk input yang sama
#


def analyze_orphan(shared_graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter untuk unreferenced_files detection.
    Menggunakan shared_graph alih-alih scan sendiri.
    """
    findings = []
    metadata = shared_graph.get("node_metadata", {})

    for fp, meta in metadata.items():
        fan_in = meta.get("fan_in", 0)
        is_entrypoint = meta.get("is_entrypoint", False)
        is_test = meta.get("is_test", False)

        if fan_in == 0 and not is_entrypoint and not is_test:
            findings.append({
                "type": "unreferenced_file",
                "severity": "low",
                "file": fp,
                "node_type": meta.get("type", "Other"),
                "observation": (
                    f"File '{fp}' has fan_in=0 and is not an entrypoint "
                    f"or test file. Potentially unreferenced."
                ),
            })

    findings.sort(key=lambda f: f["file"])

    return {
        "analyzer": "topo.orphan",
        "findings": findings,
        "summary": {
            "total_findings": len(findings),
        },
    }


def analyze_entrypoint_impact(shared_graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter untuk entrypoint impact analysis.
    """
    findings = []
    metadata = shared_graph.get("node_metadata", {})

    for fp, meta in metadata.items():
        if meta.get("is_entrypoint"):
            findings.append({
                "type": "entrypoint",
                "severity": "info",
                "file": fp,
                "entrypoint_kind": meta.get("entrypoint_kind", "none"),
                "confidence": meta.get("entrypoint_confidence", 0.0),
                "fan_in": meta.get("fan_in", 0),
                "fan_out": meta.get("fan_out", 0),
            })

    return {
        "analyzer": "topo.entrypoint",
        "findings": findings,
        "summary": {
            "total_entrypoints": len(findings),
        },
    }


# ============================================================
# ANALYZER REGISTRY
# ============================================================
# Tambahkan analyzer baru di sini.
# Setiap analyzer harus memenuhi kontrak di atas.

ANALYZER_REGISTRY: Dict[str, Any] = {
    # Topology analyzers
    "topo.orphan": analyze_orphan,
    "topo.entrypoint": analyze_entrypoint_impact,
    "topo.circular": analyze_circular if TOPO_ANALYZERS_AVAILABLE else None,
    "topo.risk": analyze_risk if TOPO_ANALYZERS_AVAILABLE else None,

    # Performance analyzers (MIGRATED)
    "perf.async": analyze_async_waterfall if PERF_ANALYZERS_AVAILABLE else None,
    "perf.deopt": analyze_deopt if PERF_ANALYZERS_AVAILABLE else None,
    "perf.gc": analyze_gc_pressure if PERF_ANALYZERS_AVAILABLE else None,
    "perf.cache": analyze_cache if PERF_ANALYZERS_AVAILABLE else None,

    # HoTT analyzers (Batch 2 — MIGRATED)
    "hott.isomorphism": analyze_isomorphism if HOTT_ANALYZERS_AVAILABLE else None,
    "hott.sheaf": analyze_sheaf if HOTT_ANALYZERS_AVAILABLE else None,
    "hott.homotopy": analyze_homotopy if HOTT_ANALYZERS_AVAILABLE else None,
    "hott.manifold": analyze_manifold if HOTT_ANALYZERS_AVAILABLE else None,
}

# Filter out None entries (unavailable analyzers)
ANALYZER_REGISTRY = {k: v for k, v in ANALYZER_REGISTRY.items() if v is not None}


def get_available_analyzers() -> List[str]:
    """Return list of registered analyzer names."""
    return sorted(ANALYZER_REGISTRY.keys())


def run_analyzers(
    shared_graph: Dict[str, Any],
    analyzer_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Jalankan selected analyzers terhadap SharedGraph.

    Args:
        shared_graph: Output dari build_shared_graph()
        analyzer_names: List analyzer yang ingin dijalankan.
                        None = jalankan semua.

    Returns:
        Dict dengan hasil setiap analyzer.
    """
    if analyzer_names is None:
        analyzer_names = list(ANALYZER_REGISTRY.keys())

    results = {}
    errors = {}

    for name in analyzer_names:
        if name not in ANALYZER_REGISTRY:
            errors[name] = f"Analyzer '{name}' not found in registry"
            continue

        try:
            results[name] = ANALYZER_REGISTRY[name](shared_graph)
        except Exception as exc:
            errors[name] = str(exc)

    return {
        "results": results,
        "errors": errors,
        "analyzers_run": len(results),
        "analyzers_failed": len(errors),
    }
