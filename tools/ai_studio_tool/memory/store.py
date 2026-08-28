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
_TOOL_ROOT = os.path.dirname(_SCRIPT_DIR) if os.path.basename(_SCRIPT_DIR) == "memory" else _SCRIPT_DIR

DATA_DIR = os.path.join(_TOOL_ROOT, "data", "memory")
MEMORY_DIR = DATA_DIR if os.path.exists(DATA_DIR) else os.path.join(_TOOL_ROOT, "memory")
MEMORY_STORE_PATH = os.path.join(MEMORY_DIR, "memory_store.json")
BASELINE_DIR = os.path.join(MEMORY_DIR, "baseline")
BASELINE_PATH = os.path.join(BASELINE_DIR, "memory_baseline.json")
CONSOLIDATION_LOG_PATH = os.path.join(MEMORY_DIR, "consolidation_log.json")

MEMORY_TYPES = ("episodic", "semantic", "procedural")
ASSOCIATION_TYPES = (
    "temporal", "causal", "semantic", "inferential",
    "consolidation", "derivation", "contradiction", "redundancy"
)

# Status memory untuk quotient forgetting
MEMORY_STATUS_ACTIVE = "active"
MEMORY_STATUS_ARCHIVED = "archived"


def _get_status(memory: Dict[str, Any]) -> str:
    """Ambil status memory dengan backward compatibility."""
    return memory.get("status", MEMORY_STATUS_ACTIVE)


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
    include_archived: bool = False,
) -> List[Dict[str, Any]]:
    """
    Recall memori berdasarkan filter.
    Default: hanya active memories (exclude archived).
    Ini adalah operasi READ — tidak mengubah access_count.
    Untuk access tracking, gunakan access_memory().
    """
    store = load_store()
    results = store["memories"]

    # Filter archived
    if not include_archived:
        results = [m for m in results if _get_status(m) == MEMORY_STATUS_ACTIVE]

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


def consolidate_by_tag(
    tag: str,
    content: Optional[str] = None,
    importance: float = 0.9,
    memory_type: str = "episodic",
    only_unconsolidated: bool = True,
) -> Dict[str, Any]:
    """
    Konsolidasi semua memori dengan tag tertentu menjadi satu semantic memory.
    
    Args:
        tag: Tag untuk filter memories
        content: Content untuk semantic memory baru. Jika None, auto-generate.
        importance: Importance score
        memory_type: Type memori yang di-filter (default: episodic)
        only_unconsolidated: Hanya proses yang belum di-consolidate
    """
    store = load_store()

    # Filter memories by tag
    candidates = [
        m for m in store["memories"]
        if m.get("type") == memory_type
        and tag in m.get("tags", [])
        and (not only_unconsolidated or m.get("consolidated_into") is None)
    ]

    if not candidates:
        return {
            "status": "no_candidates",
            "tag": tag,
            "message": f"No {memory_type} memories with tag '{tag}' found",
        }

    # Auto-generate content jika tidak disediakan
    if content is None:
        finding_types = set()
        files = set()
        content_previews = []
        for m in candidates:
            ctx = m.get("context", {})
            if ctx.get("finding_type"):
                finding_types.add(ctx["finding_type"])
            if ctx.get("file"):
                files.add(ctx["file"])
            # Fallback: ambil preview dari content jika context kosong
            if not ctx.get("finding_type") and not ctx.get("file"):
                content_previews.append(m.get("content", "")[:80])

        details = []
        if finding_types:
            details.append(f"Finding types: {', '.join(sorted(finding_types))}")
        if files:
            details.append(f"Files: {', '.join(sorted(files))}")
        if content_previews:
            details.append(f"Items: {'; '.join(content_previews[:3])}")

        detail_str = f" ({'. '.join(details)}.)" if details else ""
        content = (
            f"Consolidated pattern from {len(candidates)} memories tagged '{tag}'.{detail_str}"
        )

    # Consolidate
    source_ids = [m["id"] for m in candidates]
    result = consolidate_memories(
        source_ids=source_ids,
        content=content,
        tags=[tag, "auto_consolidated"],
        importance=importance,
    )
    result["status"] = "consolidated"
    result["tag"] = tag
    result["candidates_found"] = len(candidates)
    return result


def consolidate_by_tag_auto(
    min_group_size: int = 3,
    importance: float = 0.9,
) -> Dict[str, Any]:
    """
    Otomatis detect semua tag groups dan consolidate yang memenuhi threshold.
    
    Args:
        min_group_size: Minimum jumlah memories per tag untuk trigger consolidation
        importance: Importance score untuk semantic memories baru
    """
    store = load_store()

    # Group unconsolidated episodic by tag
    tag_groups: Dict[str, List[str]] = {}
    for m in store["memories"]:
        if m.get("type") != "episodic":
            continue
        if m.get("consolidated_into") is not None:
            continue
        for tag in m.get("tags", []):
            # Skip generic tags
            if tag in ("consolidated", "auto_consolidated"):
                continue
            if tag not in tag_groups:
                tag_groups[tag] = []
            tag_groups[tag].append(m["id"])

    # Filter groups by threshold
    eligible_groups = {
        tag: ids for tag, ids in tag_groups.items()
        if len(ids) >= min_group_size
    }

    if not eligible_groups:
        return {
            "status": "no_eligible_groups",
            "message": f"No tag groups with >= {min_group_size} unconsolidated memories",
            "tag_groups_found": {tag: len(ids) for tag, ids in tag_groups.items()},
        }

    # Consolidate each eligible group
    results = []
    for tag, ids in sorted(eligible_groups.items()):
        result = consolidate_by_tag(
            tag=tag,
            importance=importance,
        )
        if result.get("status") == "consolidated" or "new_semantic_memory" in result:
            results.append({
                "tag": tag,
                "memories_consolidated": len(ids),
                "new_semantic_id": result.get("new_semantic_memory", {}).get("id"),
            })

    return {
        "status": "consolidated",
        "groups_consolidated": len(results),
        "results": results,
        "skipped_groups": {
            tag: len(ids) for tag, ids in tag_groups.items()
            if tag not in eligible_groups
        },
    }


def get_unconsolidated_by_tag() -> Dict[str, Any]:
    """
    Dapatkan ringkasan unconsolidated episodic memories grouped by tag.
    Berguna untuk exploration sebelum consolidation.
    """
    store = load_store()

    tag_groups: Dict[str, List[Dict[str, Any]]] = {}
    unconsolidated_count = 0

    for m in store["memories"]:
        if m.get("type") != "episodic":
            continue
        if m.get("consolidated_into") is not None:
            continue
        unconsolidated_count += 1
        for tag in m.get("tags", []):
            if tag not in tag_groups:
                tag_groups[tag] = []
            tag_groups[tag].append({
                "id": m["id"],
                "content_preview": m.get("content", "")[:100],
                "importance": m.get("importance", 0.5),
            })

    return {
        "unconsolidated_count": unconsolidated_count,
        "tag_groups": {
            tag: {
                "count": len(mems),
                "memories": mems,
            }
            for tag, mems in sorted(tag_groups.items())
        },
    }


def archive_memory(memory_id: str, reason: str = "consolidated") -> Optional[Dict[str, Any]]:
    """
    Archive satu memory (quotient forgetting).
    Memory tidak dihapus, hanya ditandai sebagai archived.
    """
    store = load_store()
    for memory in store["memories"]:
        if memory["id"] == memory_id:
            memory["status"] = MEMORY_STATUS_ARCHIVED
            memory["archived_at"] = _now_iso()
            memory["archive_reason"] = reason
            save_store(store)
            return memory
    return None


def restore_memory(memory_id: str) -> Optional[Dict[str, Any]]:
    """Restore satu archived memory kembali aktif."""
    store = load_store()
    for memory in store["memories"]:
        if memory["id"] == memory_id:
            memory["status"] = MEMORY_STATUS_ACTIVE
            memory.pop("archived_at", None)
            memory.pop("archive_reason", None)
            save_store(store)
            return memory
    return None


def restore_all_archived() -> Dict[str, Any]:
    """Restore semua archived memories."""
    store = load_store()
    restored_count = 0
    for memory in store["memories"]:
        if _get_status(memory) == MEMORY_STATUS_ARCHIVED:
            memory["status"] = MEMORY_STATUS_ACTIVE
            memory.pop("archived_at", None)
            memory.pop("archive_reason", None)
            restored_count += 1
    save_store(store)
    return {"restored_count": restored_count}


def get_compact_candidates(
    only_consolidated: bool = True,
    memory_type: str = "episodic",
) -> List[Dict[str, Any]]:
    """
    Dapatkan kandidat untuk compact:
    - Memory yang sudah consolidated (consolidated_into != null)
    - Memory dengan status aktif
    - Memory dengan tipe tertentu (default: episodic)
    """
    store = load_store()
    candidates = []

    for memory in store["memories"]:
        if _get_status(memory) != MEMORY_STATUS_ACTIVE:
            continue
        if memory.get("type") != memory_type:
            continue
        if only_consolidated and memory.get("consolidated_into") is None:
            continue
        candidates.append(memory)

    return candidates


def compact_memories(
    only_consolidated: bool = True,
    memory_type: str = "episodic",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Compact memories: archive yang sudah consolidated.
    
    Args:
        only_consolidated: Hanya archive yang sudah di-consolidate
        memory_type: Tipe memory yang di-compact
        dry_run: Jika True, hanya preview tanpa eksekusi
    """
    candidates = get_compact_candidates(only_consolidated, memory_type)

    if dry_run:
        return {
            "status": "dry_run",
            "candidates_count": len(candidates),
            "candidates": [
                {
                    "id": m["id"],
                    "type": m.get("type"),
                    "content_preview": m.get("content", "")[:80],
                    "consolidated_into": m.get("consolidated_into"),
                }
                for m in candidates
            ],
        }

    # Execute compact
    archived_ids = []
    for memory in candidates:
        result = archive_memory(memory["id"], reason="quotient_forgetting")
        if result:
            archived_ids.append(memory["id"])

    return {
        "status": "compacted",
        "archived_count": len(archived_ids),
        "archived_ids": archived_ids,
        "memory_type": memory_type,
    }


def get_archive_stats() -> Dict[str, Any]:
    """Statistik archived vs active memories."""
    store = load_store()
    active_count = 0
    archived_count = 0
    archived_by_type: Dict[str, int] = {}

    for memory in store["memories"]:
        status = _get_status(memory)
        if status == MEMORY_STATUS_ACTIVE:
            active_count += 1
        elif status == MEMORY_STATUS_ARCHIVED:
            archived_count += 1
            mtype = memory.get("type", "unknown")
            archived_by_type[mtype] = archived_by_type.get(mtype, 0) + 1

    return {
        "total_memories": active_count + archived_count,
        "active_count": active_count,
        "archived_count": archived_count,
        "archived_by_type": archived_by_type,
    }


# Edge types yang dihitung sebagai β₁_reasoning (dari memory_analyzers)
REASONING_EDGE_TYPES = {"inferential", "causal"}


def _build_reasoning_adjacency(store: Dict[str, Any]) -> Dict[str, List[str]]:
    """Build adjacency hanya untuk reasoning edges (inferential, causal)."""
    adj: Dict[str, List[str]] = {}
    active_ids = {
        m["id"] for m in store.get("memories", [])
        if _get_status(m) == MEMORY_STATUS_ACTIVE
    }
    for assoc in store.get("associations", []):
        if assoc.get("type") in REASONING_EDGE_TYPES:
            src, tgt = assoc.get("from"), assoc.get("to")
            if src in active_ids and tgt in active_ids and src and tgt:
                adj.setdefault(src, []).append(tgt)
    return adj


def would_create_reasoning_cycle(
    from_id: str,
    to_id: str,
    store: Dict[str, Any],
) -> bool:
    """
    Cek apakah menambah edge from_id -> to_id akan membuat reasoning cycle.
    Menggunakan DFS: jika sudah ada path dari to_id ke from_id via reasoning edges,
    maka menambah from_id -> to_id akan membentuk cycle.
    """
    adj = _build_reasoning_adjacency(store)

    # DFS dari to_id, cek apakah bisa reach from_id
    visited = set()
    stack = [to_id]
    while stack:
        node = stack.pop()
        if node == from_id:
            return True  # Cycle akan terbentuk
        if node in visited:
            continue
        visited.add(node)
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                stack.append(neighbor)
    return False


def bridge_memories(
    from_id: str,
    to_id: str,
    assoc_type: str = "semantic",
    strength: float = 0.7,
    metadata: Optional[Dict[str, Any]] = None,
    safe_mode: bool = True,
) -> Dict[str, Any]:
    """
    Buat asosiasi tingkat tinggi antara dua memories (biasanya semantic).
    Ini adalah "lem level-2" yang menghubungkan pulau-pulau pengetahuan.
    """
    store = load_store()
    memory_ids = {m["id"] for m in store.get("memories", [])}

    # Validasi memory ada
    if from_id not in memory_ids:
        return {"status": "error", "error": f"Memory not found: {from_id}"}
    if to_id not in memory_ids:
        return {"status": "error", "error": f"Memory not found: {to_id}"}
    if from_id == to_id:
        return {"status": "error", "error": "Cannot bridge memory to itself"}

    # Safety check untuk reasoning edges
    if safe_mode and assoc_type in REASONING_EDGE_TYPES:
        if would_create_reasoning_cycle(from_id, to_id, store):
            return {
                "status": "rejected",
                "reason": "would_create_reasoning_cycle",
                "from_id": from_id,
                "to_id": to_id,
                "assoc_type": assoc_type,
                "message": (
                    f"Bridge {from_id} --{assoc_type}--> {to_id} would create "
                    f"a reasoning cycle (β₁_reasoning would increase). "
                    f"Use assoc_type='semantic' or reverse the direction."
                ),
            }

    # Buat bridge
    assoc = store_association(
        from_id=from_id,
        to_id=to_id,
        assoc_type=assoc_type,
        strength=strength,
        metadata=metadata or {"reason": "semantic_bridging"},
    )

    return {
        "status": "bridged",
        "association": assoc,
        "from_id": from_id,
        "to_id": to_id,
        "assoc_type": assoc_type,
        "safe_mode": safe_mode,
    }


def get_bridge_candidates(
    memory_type: str = "semantic",
    min_shared_tags: int = 1,
) -> Dict[str, Any]:
    """
    Lihat kandidat bridge: pairs of memories yang share tags.
    Berguna untuk exploration sebelum bridge_auto.
    """
    store = load_store()

    candidates = [
        m for m in store.get("memories", [])
        if m.get("type") == memory_type
        and _get_status(m) == MEMORY_STATUS_ACTIVE
    ]

    # Existing pairs (untuk avoid duplicate)
    existing_pairs = set()
    for a in store.get("associations", []):
        existing_pairs.add((a.get("from"), a.get("to")))
        existing_pairs.add((a.get("to"), a.get("from")))

    # Find pairs with shared tags
    bridge_candidates = []
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            m1, m2 = candidates[i], candidates[j]
            shared_tags = set(m1.get("tags", [])) & set(m2.get("tags", []))
            # Exclude generic tags
            shared_tags -= {"consolidated", "auto_consolidated", "pattern"}

            if len(shared_tags) >= min_shared_tags:
                pair = (m1["id"], m2["id"])
                already_bridged = pair in existing_pairs
                bridge_candidates.append({
                    "from_id": m1["id"],
                    "to_id": m2["id"],
                    "from_content_preview": m1.get("content", "")[:60],
                    "to_content_preview": m2.get("content", "")[:60],
                    "shared_tags": sorted(shared_tags),
                    "already_bridged": already_bridged,
                })

    return {
        "candidates_count": len(bridge_candidates),
        "new_bridges_possible": sum(1 for c in bridge_candidates if not c["already_bridged"]),
        "candidates": bridge_candidates,
    }


def bridge_auto(
    min_shared_tags: int = 1,
    memory_type: str = "semantic",
    assoc_type: str = "semantic",
    safe_mode: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Otomatis hubungkan memories yang share tags.
    Membangun "knowledge graph" tingkat tinggi.
    """
    store = load_store()

    candidates = [
        m for m in store.get("memories", [])
        if m.get("type") == memory_type
        and _get_status(m) == MEMORY_STATUS_ACTIVE
    ]

    # Existing pairs
    existing_pairs = set()
    for a in store.get("associations", []):
        existing_pairs.add((a.get("from"), a.get("to")))
        existing_pairs.add((a.get("to"), a.get("from")))

    # Find eligible pairs
    bridges_to_create = []
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            m1, m2 = candidates[i], candidates[j]
            shared_tags = set(m1.get("tags", [])) & set(m2.get("tags", []))
            shared_tags -= {"consolidated", "auto_consolidated", "pattern"}

            if len(shared_tags) >= min_shared_tags:
                if (m1["id"], m2["id"]) in existing_pairs:
                    continue

                # Tentukan arah: dari importance rendah ke tinggi (spesifik → umum)
                if m1.get("importance", 0.5) <= m2.get("importance", 0.5):
                    from_m, to_m = m1, m2
                else:
                    from_m, to_m = m2, m1

                bridges_to_create.append({
                    "from_id": from_m["id"],
                    "to_id": to_m["id"],
                    "shared_tags": sorted(shared_tags),
                    "from_importance": from_m.get("importance", 0.5),
                    "to_importance": to_m.get("importance", 0.5),
                })

    if dry_run:
        return {
            "status": "dry_run",
            "bridges_count": len(bridges_to_create),
            "bridges": bridges_to_create,
            "assoc_type": assoc_type,
            "safe_mode": safe_mode,
        }

    # Execute bridges dengan safety check
    created = []
    rejected = []
    for bridge in bridges_to_create:
        result = bridge_memories(
            from_id=bridge["from_id"],
            to_id=bridge["to_id"],
            assoc_type=assoc_type,
            strength=0.7,
            metadata={
                "shared_tags": bridge["shared_tags"],
                "reason": "auto_bridging",
                "direction": "specific_to_general",
            },
            safe_mode=safe_mode,
        )
        if result.get("status") == "bridged":
            created.append(result)
        elif result.get("status") == "rejected":
            rejected.append(result)

    return {
        "status": "bridged",
        "bridges_created": len(created),
        "bridges_rejected": len(rejected),
        "rejected_reasons": [r.get("reason") for r in rejected],
        "created_bridges": [
            {"from": c["from_id"], "to": c["to_id"], "type": c["assoc_type"]}
            for c in created
        ],
    }
