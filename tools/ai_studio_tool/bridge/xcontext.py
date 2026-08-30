"""Project-scoped Memory-Augmented Context — HoTT Kernel Bridge Domain."""

from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, Iterable, List, Optional


RETRIEVAL_CLAIM_BOUNDARY = (
    "deterministic lexical-and-path retrieval with snapshot freshness gating; "
    "not semantic embedding proof"
)


def _memory_modules():
    try:
        from memory.store import recall_memories
        from memory.runtime import memory_runtime_provenance
    except ImportError:
        from memory_store import recall_memories
        from memory_runtime import memory_runtime_provenance
    return recall_memories, memory_runtime_provenance


def _evidence_freshness(
    memory: Dict[str, Any],
    current_graph_signature: Optional[str],
    current_file_hashes: Dict[str, str],
) -> str:
    context = memory.get("context", {})
    if not context.get("dedup_key"):
        return "unverified"
    persisted = str(context.get("evidence_status", "active"))
    if persisted != "active":
        return persisted
    file_path = str(context.get("file", "")).replace("\\", "/")
    if file_path and current_file_hashes and file_path not in current_file_hashes:
        return "orphaned"
    stored_file_hash = context.get("source_content_sha256")
    if (
        file_path
        and stored_file_hash
        and current_file_hashes.get(file_path)
        and current_file_hashes[file_path] != stored_file_hash
    ):
        return "stale"
    stored_graph_signature = context.get("graph_content_signature")
    if current_graph_signature and stored_graph_signature:
        return "fresh" if current_graph_signature == stored_graph_signature else "stale"
    return "unverified"


def _memory_view(
    memory: Dict[str, Any],
    current_graph_signature: Optional[str] = None,
    current_file_hashes: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    content = str(memory.get("content", ""))
    context = memory.get("context", {})
    normalized_hashes = {
        str(path).replace("\\", "/"): str(value)
        for path, value in (current_file_hashes or {}).items()
    }
    freshness = _evidence_freshness(
        memory, current_graph_signature, normalized_hashes
    )
    return {
        "id": memory["id"],
        "type": memory.get("type", "unknown"),
        "content": content,
        "importance": float(memory.get("importance", 0.0)),
        "tags": list(memory.get("tags", [])),
        "source": memory.get("source", "unknown"),
        "finding_type": context.get("finding_type"),
        "file": context.get("file"),
        "observation_count": int(context.get("observation_count", 1)),
        "last_observed_at": context.get("last_observed_at"),
        "first_evidence_signature": context.get("first_evidence_signature"),
        "last_evidence_signature": context.get("last_evidence_signature"),
        "graph_content_signature": context.get("graph_content_signature"),
        "source_content_sha256": context.get("source_content_sha256"),
        "evidence_status": context.get(
            "evidence_status", "unverified" if not context.get("dedup_key") else "active"
        ),
        "freshness": freshness,
        "revision_count": int(context.get("revision_count", 1)),
        "retrieval_match": memory.get("retrieval_match", {}),
        "content_sha256": f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}",
    }


def get_memory_evidence(
    query: Optional[str] = None,
    target_files: Optional[Iterable[str]] = None,
    max_memories: int = 5,
    current_graph_signature: Optional[str] = None,
    current_file_hashes: Optional[Dict[str, str]] = None,
    include_stale: bool = False,
) -> Dict[str, Any]:
    """Recall scoped evidence for a developer query and optional file targets."""
    try:
        recall_memories, runtime_provenance = _memory_modules()
    except ImportError:
        return {
            "error": "memory_store not available",
            "selected_count": 0,
            "memories": [],
        }

    candidates: List[Dict[str, Any]] = []
    recall_options = {"include_historical_evidence": include_stale}
    if query and query.strip():
        candidates.extend(recall_memories(
            query=query, limit=max_memories * 4, **recall_options
        ))

    normalized_targets = [str(path).replace("\\", "/") for path in (target_files or [])]
    for file_path in normalized_targets:
        file_name = os.path.basename(file_path)
        file_dir = os.path.dirname(file_path)
        dir_tag = file_dir.replace("/", ".") if file_dir else None
        candidates.extend(recall_memories(
            query=file_path, limit=max_memories * 2, **recall_options
        ))
        if file_name and file_name != file_path:
            candidates.extend(recall_memories(
                query=file_name, limit=max_memories * 2, **recall_options
            ))
        if dir_tag:
            candidates.extend(recall_memories(
                tags=[dir_tag], limit=max_memories * 2, **recall_options
            ))

    seen = set()
    selected: List[Dict[str, Any]] = []
    excluded_by_freshness: Dict[str, int] = {}
    for memory in candidates:
        memory_id = memory.get("id")
        if not memory_id or memory_id in seen:
            continue
        seen.add(memory_id)
        view = _memory_view(
            memory,
            current_graph_signature=current_graph_signature,
            current_file_hashes=current_file_hashes,
        )
        freshness = str(view.get("freshness", "unverified"))
        if freshness in {"resolved", "stale", "orphaned", "superseded"} and not include_stale:
            excluded_by_freshness[freshness] = (
                excluded_by_freshness.get(freshness, 0) + 1
            )
            continue
        selected.append(view)
        if len(selected) >= max_memories:
            break

    runtime = runtime_provenance()
    return {
        "query": query,
        "target_files": normalized_targets,
        "selected_count": len(selected),
        "memories": selected,
        "memory_scope": runtime,
        "retrieval": {
            "model": "scoped_lexical_path_recall_v2_freshness",
            "claim_boundary": RETRIEVAL_CLAIM_BOUNDARY,
            "archived_included": False,
            "stale_included": include_stale,
            "current_graph_signature": current_graph_signature,
            "excluded_by_freshness": excluded_by_freshness,
            "max_memories": max_memories,
        },
    }


def get_memory_context_for_file(
    file_path: str,
    max_memories: int = 5,
) -> Dict[str, Any]:
    """Compatibility wrapper for file-oriented scoped recall."""
    result = get_memory_evidence(
        query=file_path,
        target_files=[file_path],
        max_memories=max_memories,
    )
    return {
        "file": file_path,
        "memory_count": result.get("selected_count", 0),
        "memories": result.get("memories", []),
        "memory_scope": result.get("memory_scope", {}),
        "retrieval": result.get("retrieval", {}),
        **({"error": result["error"]} if result.get("error") else {}),
    }


__all__ = [
    "get_memory_context_for_file",
    "get_memory_evidence",
    "RETRIEVAL_CLAIM_BOUNDARY",
]
