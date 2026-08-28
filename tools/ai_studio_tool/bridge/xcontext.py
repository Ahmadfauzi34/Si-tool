"""
Memory-Augmented Context per File — HoTT Kernel Bridge Domain
Schema Version: 4.0.0-memory
"""

import os
from typing import Any, Dict, List, Optional


def get_memory_context_for_file(
    file_path: str,
    max_memories: int = 5,
) -> Dict[str, Any]:
    """Cari memori yang relevan dengan file tertentu."""
    try:
        from memory.store import recall_memories
    except ImportError:
        try:
            from memory_store import recall_memories
        except ImportError:
            return {"error": "memory_store not available", "memories": []}

    file_name = os.path.basename(file_path)
    file_dir = os.path.dirname(file_path)
    dir_tag = file_dir.replace("/", ".") if file_dir else None

    # Recall by file path
    path_memories = recall_memories(query=file_path, limit=max_memories)

    # Recall by file name
    name_memories = recall_memories(query=file_name, limit=max_memories)

    # Recall by dir tag
    tag_memories = recall_memories(tags=[dir_tag], limit=max_memories) if dir_tag else []

    # Combine & deduplicate
    seen_ids = set()
    combined = []
    for mem in path_memories + name_memories + tag_memories:
        if mem["id"] not in seen_ids:
            seen_ids.add(mem["id"])
            combined.append(mem)
            if len(combined) >= max_memories:
                break

    return {
        "file": file_path,
        "memory_count": len(combined),
        "memories": [
            {
                "id": m["id"],
                "type": m["type"],
                "content": m["content"],
                "importance": m["importance"],
                "tags": m.get("tags", []),
            }
            for m in combined
        ],
    }
