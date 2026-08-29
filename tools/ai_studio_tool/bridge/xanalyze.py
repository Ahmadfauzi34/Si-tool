"""
Cross-Domain Analysis & Auto-Store — HoTT Kernel Bridge Domain
Schema Version: 4.1.0-memory
"""

import os
import json
import hashlib
import datetime
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "4.1.0-memory"

CONSOLIDATION_EPISODIC_THRESHOLD = 15
CONSOLIDATION_BETA0_THRESHOLD = 5
CRITICAL_IMPACT_FAN_IN_THRESHOLD = 3


def filter_findings_for_memory(
    analyzer_results: Dict[str, Any],
    correlations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Filter findings berdasarkan severity dan relevansi."""
    storeable: List[Dict[str, Any]] = []

    for analyzer_name, result in analyzer_results.items():
        for finding in result.get("findings", []):
            severity = finding.get("severity", "info")

            if severity == "high":
                storeable.append({
                    "source_analyzer": analyzer_name,
                    "finding_type": finding.get("type", "unknown"),
                    "severity": severity,
                    "file": finding.get("file", ""),
                    "content": finding.get("observation", ""),
                    "category": "high_severity_finding",
                })
            elif severity == "medium":
                ftype = finding.get("type", "")
                if ftype in ("circular_dependency", "entrypoint_high_risk", "change_risk"):
                    storeable.append({
                        "source_analyzer": analyzer_name,
                        "finding_type": ftype,
                        "severity": severity,
                        "file": finding.get("file", ""),
                        "content": finding.get("observation", ""),
                        "category": "critical_medium_finding",
                    })

    for corr in correlations:
        storeable.append({
            "source_analyzer": "cross_analyzer",
            "finding_type": corr.get("type", "unknown"),
            "severity": corr.get("severity", "medium"),
            "file": corr.get("file", ""),
            "content": corr.get("observation", ""),
            "category": "cross_analyzer_correlation",
        })

    return storeable


def auto_store_findings(
    storeable_findings: List[Dict[str, Any]],
    scan_root: str = "src",
    evidence_signature: Optional[str] = None,
) -> Dict[str, Any]:
    """Atomically upsert analyzer observations by deterministic identity."""
    try:
        from memory.store import upsert_memory_observations
        from memory.runtime import memory_runtime_provenance
    except ImportError:
        try:
            from memory_store import upsert_memory_observations
            from memory_runtime import memory_runtime_provenance
        except ImportError:
            return {"error": "memory_store not available", "stored_count": 0}

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    runtime = memory_runtime_provenance()
    scope_id = runtime["scope_id"]
    observations: List[Dict[str, Any]] = []

    for finding in storeable_findings:
        content = (
            f"[{finding['category']}] "
            f"{finding['finding_type']} di {finding['file'] or scan_root}: "
            f"{finding['content']}"
        )

        tags = [
            finding["category"],
            finding["source_analyzer"],
            finding["severity"],
        ]
        if finding["file"]:
            file_dir = os.path.dirname(finding["file"])
            if file_dir:
                tags.append(file_dir.replace("/", "."))

        context = {
            "scan_root": scan_root,
            "source_analyzer": finding["source_analyzer"],
            "finding_type": finding["finding_type"],
            "severity": finding["severity"],
            "file": finding["file"],
            "batch_timestamp": timestamp,
            "evidence_signature": evidence_signature,
            "memory_scope_id": scope_id,
        }
        identity_payload = {
            "scope_id": scope_id,
            "category": finding["category"],
            "source_analyzer": finding["source_analyzer"],
            "finding_type": finding["finding_type"],
            "severity": finding["severity"],
            "file": str(finding["file"]).replace("\\", "/"),
            "content": " ".join(str(finding["content"]).split()),
        }
        identity_json = json.dumps(identity_payload, sort_keys=True, separators=(",", ":"))
        dedup_key = f"finding:{hashlib.sha256(identity_json.encode('utf-8')).hexdigest()}"
        observations.append({
            "dedup_key": dedup_key,
            "memory_type": "episodic",
            "content": content,
            "source": f"hott_kernel xanalyze {scan_root}",
            "importance": 0.9 if finding["severity"] == "high" else 0.7,
            "tags": tags,
            "context": context,
        })

    result = upsert_memory_observations(observations)
    result.update({
        "status": "auto_observed",
        "batch_timestamp": timestamp,
        "evidence_signature": evidence_signature,
        "memory_scope": runtime,
    })
    return result


def check_consolidation_trigger() -> Dict[str, Any]:
    """Cek apakah kondisi memori memerlukan consolidation."""
    try:
        from memory.store import load_store
        from memory.graph import build_memory_graph
        from memory.analyzers import analyze_fragmentation
    except ImportError:
        try:
            from memory_store import load_store
            from memory_graph import build_memory_graph
            from memory_analyzers import analyze_fragmentation
        except ImportError:
            return {"error": "memory modules not available", "trigger": False}

    store = load_store()
    memories = store.get("memories", [])
    episodic_memories = [m for m in memories if m.get("type") == "episodic"]
    episodic_count = len(episodic_memories)

    unconsolidated = [
        m for m in episodic_memories
        if m.get("consolidated_into") is None
    ]
    unconsolidated_count = len(unconsolidated)

    memory_graph = build_memory_graph()
    frag_result = analyze_fragmentation(memory_graph)
    beta_0 = frag_result.get("summary", {}).get("beta_0", 0)

    isolated_episodic = [
        m for m in unconsolidated
        if memory_graph.get("node_metadata", {}).get(m["id"], {}).get("fan_in", 0) == 0
        and memory_graph.get("node_metadata", {}).get(m["id"], {}).get("fan_out", 0) == 0
    ]

    triggers: List[str] = []
    if unconsolidated_count >= CONSOLIDATION_EPISODIC_THRESHOLD:
        triggers.append(f"episodic_count_exceeded: {unconsolidated_count} >= {CONSOLIDATION_EPISODIC_THRESHOLD}")
    if beta_0 > CONSOLIDATION_BETA0_THRESHOLD:
        triggers.append(f"fragmentation_exceeded: beta_0={beta_0} > {CONSOLIDATION_BETA0_THRESHOLD}")
    if len(isolated_episodic) >= 5:
        triggers.append(f"isolated_episodic_exceeded: {len(isolated_episodic)} isolated")

    return {
        "trigger": len(triggers) > 0,
        "reasons": triggers,
        "metrics": {
            "total_episodic": episodic_count,
            "unconsolidated_episodic": unconsolidated_count,
            "isolated_episodic": len(isolated_episodic),
            "beta_0": beta_0,
            "thresholds": {
                "episodic_threshold": CONSOLIDATION_EPISODIC_THRESHOLD,
                "beta0_threshold": CONSOLIDATION_BETA0_THRESHOLD,
            },
        },
        "candidate_ids": [m["id"] for m in unconsolidated[:20]],
    }
