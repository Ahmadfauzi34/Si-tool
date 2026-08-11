"""
Memory Graph Builder — HoTT Kernel Memory Domain
Schema Version: 4.0.0-memory

Membangun graph dari memory store.
Setara dengan shared_graph.py untuk codebase.
"""

import json
from typing import Any, Dict, List, Optional, Set, Tuple

from memory_store import load_store, MEMORY_STORE_PATH


def build_memory_graph() -> Dict[str, Any]:
    """
    Bangun memory graph dari memory store.

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
    adjacency: Dict[str, Set[str]] = {}
    association_map: Dict[str, Dict[str, Any]] = {}

    for assoc in associations:
        from_id = assoc.get("from", "")
        to_id = assoc.get("to", "")

        if from_id in memory_map and to_id in memory_map:
            edges.append((from_id, to_id))
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
        "memory_map": memory_map,
        "association_map": association_map,
        "adjacency": adjacency_list,
        "node_metadata": node_metadata,
        "summary": {
            "total_memories": len(vertices),
            "total_associations": len(edges),
            "by_type": by_type,
            "isolated_memories": sum(
                1 for mid in vertices
                if fan_in.get(mid, 0) == 0 and fan_out.get(mid, 0) == 0
            ),
        },
    }


def build_memory_graph_from_data(
    memories: List[Dict[str, Any]],
    associations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Bangun memory graph dari data langsung (tanpa file).
    Berguna untuk testing dan inline operations.
    """
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
    adjacency: Dict[str, Set[str]] = {}

    for assoc in associations:
        from_id = assoc.get("from", "")
        to_id = assoc.get("to", "")
        if from_id in memory_map and to_id in memory_map:
            edges.append((from_id, to_id))
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
        "memory_map": memory_map,
        "adjacency": adjacency_list,
        "node_metadata": node_metadata,
        "summary": {
            "total_memories": len(vertices),
            "total_associations": len(edges),
        },
    }
