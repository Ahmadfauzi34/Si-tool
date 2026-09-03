"""
Memory Kan Extension — HoTT Kernel
Schema Version: 4.1.0-memory

Implementasi Kan Extension dari hott2.txt:
- Left Kan Extension (Lan): Bottom-up completion
  Diberikan fragmen, bangun memori spesifik yang konsisten
- Right Kan Extension (Ran): Top-down completion  
  Diberikan fragmen, bangun generalisasi yang mencakup fragmen

Perbedaan dengan recall_memories biasa:
- recall: FILTER (cari yang match query)
- Kan Extension: COMPLETE (lengkapi fragmen dengan konteks relasional)
"""

from typing import Any, Dict, List, Set


def left_kan_extension(
    query_fragment: str,
    max_depth: int = 2,
    max_entry_points: int = 3,
    max_related_per_entry: int = 10,
    include_edge_types: bool = True,
) -> Dict[str, Any]:
    """
    Left Kan Extension (Lan): Bottom-up structured completion.
    
    Diberikan fragmen query, temukan entry points dan lengkapi
    dengan mengikuti asosiasi di memory graph.
    
    Ini adalah "recall sebagai path navigation" dari hott2.txt:
    "Alih-alih mencari titik terdekat di ruang metrik, proses mengingat
    dalam HoTT adalah mencari jalur (path) dari kondisi kognitif saat ini
    ke target memori."
    
    Args:
        query_fragment: Fragmen query untuk dicari
        max_depth: Maximum depth untuk BFS mengikuti asosiasi
        max_entry_points: Maximum entry points yang diproses
        max_related_per_entry: Maximum related memories per entry
        include_edge_types: Sertakan tipe edge di output
    
    Returns:
        Dict dengan completed memories dan relational context
    """
    try:
        from memory.store import recall_memories, load_store
        from memory.graph import build_memory_graph
    except ImportError:
        try:
            from memory_store import recall_memories, load_store
            from memory_graph import build_memory_graph
        except ImportError as exc:
            return {"error": f"Import failed: {exc}"}
    
    store = load_store()
    memory_map = {m["id"]: m for m in store.get("memories", [])}
    
    # Build graph untuk traversal
    memory_graph = build_memory_graph(include_archived=False)
    adjacency = memory_graph.get("adjacency", {})
    edge_types = memory_graph.get("edge_types", {})
    
    # Step 1: Cari entry points (memori yang match fragmen)
    entry_memories = recall_memories(
        query=query_fragment,
        limit=max_entry_points,
        include_archived=False,
    )
    
    if not entry_memories:
        return {
            "status": "no_match",
            "kan_type": "left",
            "query_fragment": query_fragment,
            "message": "No memories match the query fragment",
        }
    
    # Step 2: Untuk setiap entry, BFS mengikuti asosiasi
    completed = []
    total_related = 0
    
    for entry in entry_memories[:max_entry_points]:
        entry_id = entry["id"]
        
        # BFS dari entry point
        visited: Set[str] = {entry_id}
        frontier: List[str] = [entry_id]
        related_memories: List[Dict[str, Any]] = []
        paths_found: List[Dict[str, Any]] = []
        
        for depth in range(max_depth):
            next_frontier: List[str] = []
            for mid in frontier:
                for neighbor in adjacency.get(mid, []):
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    next_frontier.append(neighbor)
                    
                    neighbor_mem = memory_map.get(neighbor)
                    if neighbor_mem and len(related_memories) < max_related_per_entry:
                        # Tentukan edge type
                        edge_type = "unknown"
                        if include_edge_types:
                            edge_type = edge_types.get((mid, neighbor), "unknown")
                            if edge_type == "unknown":
                                edge_type = edge_types.get((neighbor, mid), "unknown")
                        
                        related_memories.append({
                            "id": neighbor,
                            "type": neighbor_mem.get("type"),
                            "content_preview": neighbor_mem.get("content", "")[:120],
                            "importance": neighbor_mem.get("importance", 0),
                            "connected_via": edge_type,
                            "depth": depth + 1,
                            "from_memory": mid,
                        })
                        
                        paths_found.append({
                            "from": entry_id,
                            "to": neighbor,
                            "via": mid if depth > 0 else entry_id,
                            "edge_type": edge_type,
                            "depth": depth + 1,
                        })
            
            frontier = next_frontier
            if not frontier:
                break
        
        completed.append({
            "entry_memory": {
                "id": entry_id,
                "type": entry.get("type"),
                "content_preview": entry.get("content", "")[:150],
                "importance": entry.get("importance", 0),
                "tags": entry.get("tags", []),
            },
            "related_memories": related_memories,
            "paths_found": paths_found,
            "related_count": len(related_memories),
        })
        total_related += len(related_memories)
    
    return {
        "status": "completed",
        "kan_type": "left",
        "query_fragment": query_fragment,
        "entry_points_found": len(entry_memories),
        "completed_memories": completed,
        "total_related_found": total_related,
        "max_depth_used": max_depth,
        "interpretation": (
            f"Left Kan Extension: query '{query_fragment}' completed with "
            f"{total_related} related memories across {len(entry_memories)} entry points. "
            f"Relational context preserved via {max_depth}-depth traversal."
        ),
    }


def right_kan_extension(
    query_fragment: str,
    max_specific: int = 5,
    max_siblings: int = 5,
) -> Dict[str, Any]:
    """
    Right Kan Extension (Ran): Top-down structured completion.
    
    Diberikan fragmen spesifik, temukan generalisasi yang mencakupnya.
    Ini mengikuti relasi consolidated_into untuk menemukan pola yang lebih luas.
    
    Dari hott2.txt:
    "Right Kan Extension (Ran): Membangun generalisasi memori yang masih
    mencakup fragmen tersebut (pendekatan dari atas)."
    
    Args:
        query_fragment: Fragmen query untuk dicari
        max_specific: Maximum memori spesifik yang diproses
        max_siblings: Maximum sibling examples per generalisasi
    
    Returns:
        Dict dengan generalisasi dan sibling examples
    """
    try:
        from memory.store import recall_memories, load_store
    except ImportError:
        try:
            from memory_store import recall_memories, load_store
        except ImportError as exc:
            return {"error": f"Import failed: {exc}"}
    
    store = load_store()
    memory_map = {m["id"]: m for m in store.get("memories", [])}
    
    # Step 1: Cari memori spesifik yang match
    specific_memories = recall_memories(
        query=query_fragment,
        limit=max_specific,
        include_archived=True,  # Include archived untuk menemukan yang sudah consolidated
    )
    
    if not specific_memories:
        return {
            "status": "no_match",
            "kan_type": "right",
            "query_fragment": query_fragment,
            "message": "No memories match the query fragment",
        }
    
    # Step 2: Untuk setiap memori spesifik, cari generalisasinya
    generalizations: List[Dict[str, Any]] = []
    generalized_count = 0
    
    for mem in specific_memories[:max_specific]:
        consolidated_into = mem.get("consolidated_into")
        
        if consolidated_into and consolidated_into in memory_map:
            # Memori sudah di-consolidate → ambil generalisasinya
            general_mem = memory_map[consolidated_into]
            
            # Cari siblings (memori lain yang juga consolidated ke semantic yang sama)
            siblings = [
                m for m in store.get("memories", [])
                if m.get("consolidated_into") == consolidated_into
                and m["id"] != mem["id"]
                and m.get("status", "active") != "archived"
            ]
            
            generalizations.append({
                "specific_memory": {
                    "id": mem["id"],
                    "type": mem.get("type"),
                    "content_preview": mem.get("content", "")[:120],
                },
                "generalization": {
                    "id": consolidated_into,
                    "type": general_mem.get("type"),
                    "content_preview": general_mem.get("content", "")[:200],
                    "importance": general_mem.get("importance", 0),
                    "tags": general_mem.get("tags", []),
                },
                "sibling_examples": [
                    {
                        "id": s["id"],
                        "content_preview": s.get("content", "")[:80],
                    }
                    for s in siblings[:max_siblings]
                ],
                "sibling_count": len(siblings),
            })
            generalized_count += 1
        
        else:
            # Memori belum di-consolidate → tandai sebagai candidate
            generalizations.append({
                "specific_memory": {
                    "id": mem["id"],
                    "type": mem.get("type"),
                    "content_preview": mem.get("content", "")[:120],
                },
                "generalization": None,
                "note": "Not yet consolidated. Consider running memory consolidate.",
            })
    
    return {
        "status": "completed",
        "kan_type": "right",
        "query_fragment": query_fragment,
        "specific_memories_found": len(specific_memories),
        "generalizations": generalizations,
        "generalized_count": generalized_count,
        "not_yet_consolidated": len(specific_memories) - generalized_count,
        "interpretation": (
            f"Right Kan Extension: query '{query_fragment}' mapped to "
            f"{generalized_count} generalization(s). "
            f"{len(specific_memories) - generalized_count} memories not yet consolidated."
        ),
    }


def kan_retrieve(
    query_fragment: str,
    mode: str = "both",
    max_depth: int = 2,
) -> Dict[str, Any]:
    """
    Unified Kan Extension retrieval.
    
    Args:
        query_fragment: Fragmen query
        mode: "lan" (left only), "ran" (right only), "both"
        max_depth: Max depth untuk Lan traversal
    
    Returns:
        Dict dengan hasil Lan dan/atau Ran
    """
    result: Dict[str, Any] = {
        "status": "completed",
        "query_fragment": query_fragment,
        "mode": mode,
    }
    
    if mode in ("lan", "both"):
        result["left_kan_extension"] = left_kan_extension(
            query_fragment, max_depth=max_depth
        )
    
    if mode in ("ran", "both"):
        result["right_kan_extension"] = right_kan_extension(query_fragment)
    
    # Synthesize interpretation
    lan_result = result.get("left_kan_extension", {})
    ran_result = result.get("right_kan_extension", {})
    
    lan_related = lan_result.get("total_related_found", 0)
    ran_generalized = ran_result.get("generalized_count", 0)
    
    result["synthesis"] = {
        "specific_context_found": lan_related,
        "generalizations_found": ran_generalized,
        "recommendation": (
            "Use Left Kan results for detailed relational context. "
            "Use Right Kan results for high-level patterns and generalizations."
            if mode == "both"
            else f"Retrieved via {mode.upper()} only."
        ),
    }
    
    return result
