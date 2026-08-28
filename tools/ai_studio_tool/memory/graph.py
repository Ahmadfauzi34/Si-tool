"""
Memory Graph Builder — HoTT Kernel Memory Domain
Schema Version: 4.0.0-memory

Membangun graph dari memory store.
Setara dengan shared_graph.py untuk codebase.
"""

import json
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from memory.store import load_store, MEMORY_STORE_PATH
except ImportError:
    from memory_store import load_store, MEMORY_STORE_PATH


def build_memory_graph(include_archived: bool = False) -> Dict[str, Any]:
    """
    Bangun memory graph dari memory store.

    Args:
        include_archived: Jika True, include archived memories di graph.
                          Default False (hanya active memories).

    Returns:
        Dict dengan:
        - vertices: list of memory IDs
        - edges: list of (from_id, to_id) tuples
        - memory_map: dict of memory_id -> memory data
        - association_map: dict of association_id -> association data
        - adjacency: dict of memory_id -> list of connected memory IDs
        - node_metadata: dict of memory_id -> metadata
        - summary: statistics
    """
    store = load_store()
    memories = store.get("memories", [])
    associations = store.get("associations", [])

    # Filter archived
    if not include_archived:
        active_ids = {
            m["id"] for m in memories
            if m.get("status", "active") == "active"
        }
        memories = [m for m in memories if m["id"] in active_ids]
        associations = [
            a for a in associations
            if a.get("from") in active_ids and a.get("to") in active_ids
        ]

    # Build vertices and memory_map
    vertices: List[str] = []
    memory_map: Dict[str, Dict[str, Any]] = {}
    node_metadata: Dict[str, Dict[str, Any]] = {}

    for memory in memories:
        mid = memory["id"]
        vertices.append(mid)
        memory_map[mid] = memory
        node_metadata[mid] = {
            "type": memory.get("type", "unknown"),
            "importance": memory.get("importance", 0.0),
            "access_count": memory.get("access_count", 0),
            "tags": memory.get("tags", []),
            "is_consolidated": memory.get("consolidated_into") is not None,
        }

    # Build edges and adjacency
    edges: List[Tuple[str, str]] = []
    edge_types: Dict[Tuple[str, str], str] = {}
    adjacency: Dict[str, Set[str]] = {}
    association_map: Dict[str, Dict[str, Any]] = {}

    for assoc in associations:
        from_id = assoc.get("from", "")
        to_id = assoc.get("to", "")
        assoc_type = assoc.get("type", "semantic")

        if from_id in memory_map and to_id in memory_map:
            edges.append((from_id, to_id))
            edge_types[(from_id, to_id)] = assoc_type
            adjacency.setdefault(from_id, set()).add(to_id)
            adjacency.setdefault(to_id, set()).add(from_id)
            association_map[assoc["id"]] = assoc

    # Convert sets to sorted lists
    adjacency_list = {k: sorted(v) for k, v in adjacency.items()}

    # Compute fan_in / fan_out
    fan_in: Dict[str, int] = {}
    fan_out: Dict[str, int] = {}
    for src, tgt in edges:
        fan_out[src] = fan_out.get(src, 0) + 1
        fan_in[tgt] = fan_in.get(tgt, 0) + 1

    for mid in vertices:
        node_metadata[mid]["fan_in"] = fan_in.get(mid, 0)
        node_metadata[mid]["fan_out"] = fan_out.get(mid, 0)

    # Summary
    by_type = {}
    for m in memories:
        t = m.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "schema_version": "4.0.0-memory",
        "vertices": sorted(vertices),
        "edges": sorted(set(edges)),
        "edge_types": edge_types,
        "memory_map": memory_map,
        "association_map": association_map,
        "adjacency": adjacency_list,
        "node_metadata": node_metadata,
        "summary": {
            "total_memories": len(vertices),
            "total_associations": len(edges),
            "by_type": by_type,
            "by_edge_type": _count_edge_types(edge_types),
            "isolated_memories": sum(
                1 for mid in vertices
                if fan_in.get(mid, 0) == 0 and fan_out.get(mid, 0) == 0
            ),
        },
    }


def _count_edge_types(edge_types: Dict[Tuple[str, str], str]) -> Dict[str, int]:
    """Hitung jumlah edges per type."""
    counts: Dict[str, int] = {}
    for etype in edge_types.values():
        counts[etype] = counts.get(etype, 0) + 1
    return counts


def build_memory_graph_from_data(
    memories: List[Dict[str, Any]],
    associations: List[Dict[str, Any]],
    include_archived: bool = False,
) -> Dict[str, Any]:
    """
    Bangun memory graph dari data langsung (tanpa file).
    Berguna untuk testing dan inline operations.
    """
    if not include_archived:
        active_ids = {
            m["id"] for m in memories
            if m.get("status", "active") == "active"
        }
        memories = [m for m in memories if m["id"] in active_ids]
        associations = [
            a for a in associations
            if a.get("from") in active_ids and a.get("to") in active_ids
        ]

    vertices: List[str] = []
    memory_map: Dict[str, Dict[str, Any]] = {}
    node_metadata: Dict[str, Dict[str, Any]] = {}

    for memory in memories:
        mid = memory["id"]
        vertices.append(mid)
        memory_map[mid] = memory
        node_metadata[mid] = {
            "type": memory.get("type", "unknown"),
            "importance": memory.get("importance", 0.0),
            "access_count": memory.get("access_count", 0),
            "tags": memory.get("tags", []),
            "is_consolidated": memory.get("consolidated_into") is not None,
        }

    edges: List[Tuple[str, str]] = []
    edge_types: Dict[Tuple[str, str], str] = {}
    adjacency: Dict[str, Set[str]] = {}

    for assoc in associations:
        from_id = assoc.get("from", "")
        to_id = assoc.get("to", "")
        assoc_type = assoc.get("type", "semantic")
        if from_id in memory_map and to_id in memory_map:
            edges.append((from_id, to_id))
            edge_types[(from_id, to_id)] = assoc_type
            adjacency.setdefault(from_id, set()).add(to_id)
            adjacency.setdefault(to_id, set()).add(from_id)

    adjacency_list = {k: sorted(v) for k, v in adjacency.items()}

    fan_in: Dict[str, int] = {}
    fan_out: Dict[str, int] = {}
    for src, tgt in edges:
        fan_out[src] = fan_out.get(src, 0) + 1
        fan_in[tgt] = fan_in.get(tgt, 0) + 1

    for mid in vertices:
        node_metadata[mid]["fan_in"] = fan_in.get(mid, 0)
        node_metadata[mid]["fan_out"] = fan_out.get(mid, 0)

    return {
        "schema_version": "4.0.0-memory",
        "vertices": sorted(vertices),
        "edges": sorted(set(edges)),
        "edge_types": edge_types,
        "memory_map": memory_map,
        "adjacency": adjacency_list,
        "node_metadata": node_metadata,
        "summary": {
            "total_memories": len(vertices),
            "total_associations": len(edges),
            "by_edge_type": _count_edge_types(edge_types),
        },
    }
