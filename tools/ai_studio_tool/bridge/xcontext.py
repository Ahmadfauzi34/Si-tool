"""Project-scoped Memory-Augmented Context — HoTT Kernel Bridge Domain."""

from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, Iterable, List, Optional


RETRIEVAL_CLAIM_BOUNDARY = (
    "deterministic lexical-and-path retrieval; not semantic embedding proof"
)


def _memory_modules():
    try:
        from memory.store import recall_memories
        from memory.runtime import memory_runtime_provenance
    except ImportError:
        from memory_store import recall_memories
        from memory_runtime import memory_runtime_provenance
    return recall_memories, memory_runtime_provenance


def _memory_view(memory: Dict[str, Any]) -> Dict[str, Any]:
    content = str(memory.get("content", ""))
    context = memory.get("context", {})
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
        "retrieval_match": memory.get("retrieval_match", {}),
        "content_sha256": f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}",
    }


def get_memory_evidence(
    query: Optional[str] = None,
    target_files: Optional[Iterable[str]] = None,
    max_memories: int = 5,
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
    if query and query.strip():
        candidates.extend(recall_memories(query=query, limit=max_memories * 2))

    normalized_targets = [str(path).replace("\\", "/") for path in (target_files or [])]
    for file_path in normalized_targets:
        file_name = os.path.basename(file_path)
        file_dir = os.path.dirname(file_path)
        dir_tag = file_dir.replace("/", ".") if file_dir else None
        candidates.extend(recall_memories(query=file_path, limit=max_memories))
        if file_name and file_name != file_path:
            candidates.extend(recall_memories(query=file_name, limit=max_memories))
        if dir_tag:
            candidates.extend(recall_memories(tags=[dir_tag], limit=max_memories))

    seen = set()
    selected: List[Dict[str, Any]] = []
    for memory in candidates:
        memory_id = memory.get("id")
        if not memory_id or memory_id in seen:
            continue
        seen.add(memory_id)
        selected.append(_memory_view(memory))
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
            "model": "scoped_lexical_path_recall_v1",
            "claim_boundary": RETRIEVAL_CLAIM_BOUNDARY,
            "archived_included": False,
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
