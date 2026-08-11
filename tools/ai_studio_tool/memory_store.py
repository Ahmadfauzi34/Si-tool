"""
Memory Store — HoTT Kernel Memory Domain
Schema Version: 4.0.0-memory

File-based memory storage engine.
Supports episodic, semantic, and procedural memory types.
"""

import os
import json
import uuid
import datetime
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "4.0.0-memory"

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(_SCRIPT_DIR, "memory")
MEMORY_STORE_PATH = os.path.join(MEMORY_DIR, "memory_store.json")
BASELINE_DIR = os.path.join(MEMORY_DIR, "baseline")
BASELINE_PATH = os.path.join(BASELINE_DIR, "memory_baseline.json")
CONSOLIDATION_LOG_PATH = os.path.join(MEMORY_DIR, "consolidation_log.json")

MEMORY_TYPES = ("episodic", "semantic", "procedural")
ASSOCIATION_TYPES = (
    "temporal", "causal", "semantic", "inferential",
    "consolidation", "derivation", "contradiction", "redundancy"
)


def _ensure_dirs():
    """Pastikan direktori memory ada."""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    os.makedirs(BASELINE_DIR, exist_ok=True)


def _generate_id(memory_type: str) -> str:
    """Generate unique ID dengan prefix tipe."""
    prefix_map = {"episodic": "ep", "semantic": "sem", "procedural": "proc"}
    prefix = prefix_map.get(memory_type, "mem")
    short_uuid = uuid.uuid4().hex[:8]
    return f"{prefix}_{short_uuid}"


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def load_store() -> Dict[str, Any]:
    """Load memory store dari file."""
    _ensure_dirs()
    if not os.path.isfile(MEMORY_STORE_PATH):
        return {
            "schema_version": SCHEMA_VERSION,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "memories": [],
            "associations": [],
        }
    try:
        with open(MEMORY_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "schema_version": SCHEMA_VERSION,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "memories": [],
            "associations": [],
        }


def save_store(store: Dict[str, Any]) -> None:
    """Simpan memory store ke file."""
    _ensure_dirs()
    store["updated_at"] = _now_iso()
    with open(MEMORY_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)


def store_memory(
    memory_type: str,
    content: str,
    source: str = "manual",
    importance: float = 0.5,
    tags: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Simpan memori baru."""
    if memory_type not in MEMORY_TYPES:
        raise ValueError(f"Invalid memory type: {memory_type}. Must be one of {MEMORY_TYPES}")

    store = load_store()
    memory_id = _generate_id(memory_type)

    memory = {
        "id": memory_id,
        "type": memory_type,
        "content": content,
        "source": source,
        "timestamp": _now_iso(),
        "importance": max(0.0, min(1.0, importance)),
        "access_count": 0,
        "last_accessed": _now_iso(),
        "tags": tags or [],
        "context": context or {},
        "consolidated_into": None,
    }

    store["memories"].append(memory)
    save_store(store)
    return memory


def store_association(
    from_id: str,
    to_id: str,
    assoc_type: str,
    strength: float = 0.5,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Simpan asosiasi antara dua memori."""
    if assoc_type not in ASSOCIATION_TYPES:
        raise ValueError(f"Invalid association type: {assoc_type}")

    store = load_store()

    # Validasi bahwa kedua memori ada
    memory_ids = {m["id"] for m in store["memories"]}
    if from_id not in memory_ids:
        raise ValueError(f"Memory not found: {from_id}")
    if to_id not in memory_ids:
        raise ValueError(f"Memory not found: {to_id}")

    assoc_id = f"assoc_{uuid.uuid4().hex[:8]}"
    association = {
        "id": assoc_id,
        "from": from_id,
        "to": to_id,
        "type": assoc_type,
        "strength": max(0.0, min(1.0, strength)),
        "created_at": _now_iso(),
        "metadata": metadata or {},
    }

    store["associations"].append(association)
    save_store(store)
    return association


def consolidate_memories(
    source_ids: List[str],
    content: str,
    tags: Optional[List[str]] = None,
    importance: float = 0.9,
    pattern_type: str = "correlation",
    confidence: float = 0.8,
) -> Dict[str, Any]:
    """
    Konsolidasi beberapa memori menjadi satu memori semantik baru.
    Ini adalah operasi COLIMIT dalam istilah HoTT.

    Args:
        source_ids: List of memory IDs to consolidate
        content: Consolidated content (the abstraction)
        tags: Tags for the new semantic memory
        importance: Importance of the consolidated memory
        pattern_type: Type of pattern detected
        confidence: Confidence in the consolidation

    Returns:
        Dict with new semantic memory and consolidation info
    """
    store = load_store()
    memory_ids = {m["id"] for m in store["memories"]}

    # Validasi semua source IDs ada
    for sid in source_ids:
        if sid not in memory_ids:
            raise ValueError(f"Memory not found: {sid}")

    # Buat semantic memory baru (colimit)
    batch_id = f"batch_{uuid.uuid4().hex[:6]}"
    new_semantic = store_memory(
        memory_type="semantic",
        content=content,
        source=f"consolidation:{','.join(source_ids)}",
        importance=importance,
        tags=(tags or []) + ["consolidated"],
        context={
            "consolidated_from": source_ids,
            "pattern_type": pattern_type,
            "confidence": confidence,
            "consolidation_batch": batch_id,
        },
    )

    # Buat asosiasi consolidation dari setiap source ke semantic baru
    for sid in source_ids:
        store_association(
            from_id=sid,
            to_id=new_semantic["id"],
            assoc_type="consolidation",
            strength=confidence,
            metadata={
                "reason": "colimit_construction",
                "consolidation_batch": batch_id,
            },
        )

    # Tandai source memories sebagai consolidated
    store = load_store()  # reload setelah perubahan
    for memory in store["memories"]:
        if memory["id"] in source_ids:
            memory["consolidated_into"] = new_semantic["id"]
    save_store(store)

    # Log konsolidasi
    _log_consolidation(batch_id, source_ids, new_semantic["id"], content)

    return {
        "new_semantic_memory": new_semantic,
        "consolidated_from": source_ids,
        "associations_created": len(source_ids),
        "consolidation_batch": batch_id,
    }


def _log_consolidation(
    batch_id: str,
    source_ids: List[str],
    target_id: str,
    content: str,
) -> None:
    """Log konsolidasi untuk audit trail."""
    log_path = CONSOLIDATION_LOG_PATH
    log = []
    if os.path.isfile(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                log = json.load(f)
        except Exception:
            log = []

    log.append({
        "batch_id": batch_id,
        "timestamp": _now_iso(),
        "source_ids": source_ids,
        "target_id": target_id,
        "content_summary": content[:200],
    })

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def recall_memories(
    query: Optional[str] = None,
    memory_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    min_importance: float = 0.0,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Recall memori berdasarkan filter.
    Ini adalah operasi READ — tidak mengubah access_count.
    Untuk access tracking, gunakan access_memory().
    """
    store = load_store()
    results = store["memories"]

    if memory_type:
        results = [m for m in results if m.get("type") == memory_type]

    if tags:
        results = [m for m in results if any(t in m.get("tags", []) for t in tags)]

    if min_importance > 0:
        results = [m for m in results if m.get("importance", 0) >= min_importance]

    if query:
        query_lower = query.lower()
        results = [
            m for m in results
            if query_lower in m.get("content", "").lower()
            or query_lower in " ".join(m.get("tags", [])).lower()
        ]

    # Sort by importance desc, then timestamp desc
    results.sort(key=lambda m: (-m.get("importance", 0), m.get("timestamp", "")), reverse=False)

    return results[:limit]


def access_memory(memory_id: str) -> Optional[Dict[str, Any]]:
    """Tandai memori sebagai diakses (update access_count dan last_accessed)."""
    store = load_store()
    for memory in store["memories"]:
        if memory["id"] == memory_id:
            memory["access_count"] = memory.get("access_count", 0) + 1
            memory["last_accessed"] = _now_iso()
            save_store(store)
            return memory
    return None


def get_memory(memory_id: str) -> Optional[Dict[str, Any]]:
    """Ambil satu memori by ID."""
    store = load_store()
    for memory in store["memories"]:
        if memory["id"] == memory_id:
            return memory
    return None


def get_associations_for(memory_id: str) -> List[Dict[str, Any]]:
    """Ambil semua asosiasi yang melibatkan memori tertentu."""
    store = load_store()
    return [
        a for a in store["associations"]
        if a.get("from") == memory_id or a.get("to") == memory_id
    ]


def get_memory_stats() -> Dict[str, Any]:
    """Statistik memory store."""
    store = load_store()
    memories = store.get("memories", [])
    associations = store.get("associations", [])

    by_type = {}
    for m in memories:
        t = m.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    by_assoc_type = {}
    for a in associations:
        t = a.get("type", "unknown")
        by_assoc_type[t] = by_assoc_type.get(t, 0) + 1

    return {
        "total_memories": len(memories),
        "total_associations": len(associations),
        "by_type": by_type,
        "by_association_type": by_assoc_type,
        "schema_version": store.get("schema_version", "unknown"),
        "updated_at": store.get("updated_at", "unknown"),
    }
