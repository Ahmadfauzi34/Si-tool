"""Snapshot-consistent reference projection for deterministic memory recall.

The durable store remains canonical and unbounded by this module.  A projection
indexes retrieval-relevant fields from one loaded snapshot, then ranks only the
candidate subspace for one or more developer signals.  The index is a reference
machine for the declared lexical/path predicate; it is not a proof that omitted
records are semantically irrelevant.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Set


RECALL_PROJECTION_SCHEMA_VERSION = "memory-recall-projection-v1"
LEXICAL_MATCH_MODEL = "lexical_overlap_v1"
MULTI_SIGNAL_MATCH_MODEL = "multi_signal_memory_projection_v1"
INACTIVE_EVIDENCE_STATUSES = {
    "resolved",
    "stale",
    "orphaned",
    "superseded",
}
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _normalize_path(value: Any) -> str:
    return _normalize_text(str(value or "").replace("\\", "/"))


def _terms(value: Any, minimum_length: int = 1) -> Set[str]:
    return {
        token
        for token in _TOKEN_PATTERN.findall(_normalize_text(value))
        if len(token) >= minimum_length
    }


def _memory_status(memory: Dict[str, Any]) -> str:
    return str(memory.get("status", "active"))


def _evidence_status(memory: Dict[str, Any]) -> str:
    context = memory.get("context", {})
    if not context.get("dedup_key"):
        return "unverified"
    return str(context.get("evidence_status", "active"))


def _searchable_text(memory: Dict[str, Any]) -> str:
    context = memory.get("context", {})
    return _normalize_text(" ".join([
        str(memory.get("content", "")),
        str(memory.get("source", "")),
        " ".join(str(tag) for tag in memory.get("tags", [])),
        str(context.get("file", "")),
        str(context.get("finding_type", "")),
        str(context.get("source_analyzer", "")),
    ]))


def _append_index(index: Dict[str, List[int]], key: str, ordinal: int) -> None:
    if key:
        index.setdefault(key, []).append(ordinal)


def _projection_signature(entries: List[Dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        memory = entry["memory"]
        record = [
            str(memory.get("id", "")),
            entry["status"],
            entry["evidence_status"],
            str(memory.get("type", "")),
            float(memory.get("importance", 0.0)),
            str(memory.get("timestamp", "")),
            entry["file"],
            sorted(entry["tags"]),
            entry["searchable"],
        ]
        digest.update(json.dumps(
            record,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8"))
        digest.update(b"\n")
    return f"sha256:{digest.hexdigest()}"


def build_recall_projection(memories: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Build an inverted projection from one canonical memory-store snapshot."""
    entries: List[Dict[str, Any]] = []
    term_index: Dict[str, List[int]] = {}
    tag_index: Dict[str, List[int]] = {}
    type_index: Dict[str, List[int]] = {}
    file_index: Dict[str, List[int]] = {}
    basename_index: Dict[str, List[int]] = {}

    for ordinal, memory in enumerate(memories):
        context = memory.get("context", {})
        searchable = _searchable_text(memory)
        searchable_terms = _terms(searchable)
        tags = {str(tag) for tag in memory.get("tags", [])}
        file_path = _normalize_path(context.get("file", ""))
        basename = os.path.basename(file_path)
        entry = {
            "ordinal": ordinal,
            "memory": memory,
            "searchable": searchable,
            "terms": searchable_terms,
            "tags": tags,
            "file": file_path,
            "basename": basename,
            "status": _memory_status(memory),
            "evidence_status": _evidence_status(memory),
        }
        entries.append(entry)
        for term in sorted(searchable_terms):
            _append_index(term_index, term, ordinal)
        for tag in sorted(tags):
            _append_index(tag_index, tag, ordinal)
        _append_index(type_index, str(memory.get("type", "")), ordinal)
        _append_index(file_index, file_path, ordinal)
        _append_index(basename_index, basename, ordinal)

    return {
        "schema_version": RECALL_PROJECTION_SCHEMA_VERSION,
        "entries": entries,
        "term_index": term_index,
        "tag_index": tag_index,
        "type_index": type_index,
        "file_index": file_index,
        "basename_index": basename_index,
        "snapshot_signature": _projection_signature(entries),
        "snapshot_memory_count": len(entries),
        "indexed_term_count": len(term_index),
        "built_from_single_snapshot": True,
    }


def projection_metadata(projection: Dict[str, Any]) -> Dict[str, Any]:
    """Return the serializable proof surface, excluding in-process indexes."""
    return {
        "schema_version": projection.get("schema_version"),
        "snapshot_signature": projection.get("snapshot_signature"),
        "snapshot_memory_count": int(projection.get("snapshot_memory_count", 0)),
        "indexed_term_count": int(projection.get("indexed_term_count", 0)),
        "built_from_single_snapshot": bool(
            projection.get("built_from_single_snapshot", False)
        ),
    }


def _posting_union(index: Dict[str, List[int]], keys: Iterable[str]) -> Set[int]:
    result: Set[int] = set()
    for key in keys:
        result.update(index.get(key, []))
    return result


def _phrase_candidates(projection: Dict[str, Any], phrase: str) -> Set[int]:
    terms = sorted(_terms(phrase))
    if not terms:
        return set(range(len(projection["entries"])))
    postings = [set(projection["term_index"].get(term, [])) for term in terms]
    if not postings or any(not values for values in postings):
        return set()
    candidates = postings[0]
    for values in postings[1:]:
        candidates.intersection_update(values)
    return candidates


def _query_signals(
    projection: Dict[str, Any],
    query: Optional[str],
    signals: Dict[int, Dict[str, Any]],
) -> None:
    if not query:
        return
    normalized_query = _normalize_text(query)
    query_terms = _terms(normalized_query, minimum_length=2)
    candidates = (
        _posting_union(projection["term_index"], query_terms)
        if query_terms
        else set(range(len(projection["entries"])))
    )
    for ordinal in candidates:
        entry = projection["entries"][ordinal]
        matched_terms = query_terms & entry["terms"]
        exact = normalized_query in entry["searchable"]
        if not exact and query_terms and not matched_terms:
            continue
        if not exact and not query_terms:
            continue
        overlap = len(matched_terms) / max(1, len(query_terms))
        importance = float(entry["memory"].get("importance", 0.0))
        score = (4.0 if exact else 0.0) + 2.0 * overlap + importance
        signals.setdefault(ordinal, {})["query"] = {
            "model": LEXICAL_MATCH_MODEL,
            "score": round(score, 6),
            "exact_substring": exact,
            "matched_terms": sorted(matched_terms),
            "query_term_count": len(query_terms),
        }


def _target_signals(
    projection: Dict[str, Any],
    target_files: Iterable[str],
    signals: Dict[int, Dict[str, Any]],
) -> List[str]:
    normalized_targets: List[str] = []
    for raw_path in target_files:
        file_path = _normalize_path(raw_path)
        if not file_path or file_path in normalized_targets:
            continue
        normalized_targets.append(file_path)
        basename = os.path.basename(file_path)
        file_dir = os.path.dirname(file_path)
        directory_tag = file_dir.replace("/", ".") if file_dir else ""

        for ordinal in projection["file_index"].get(file_path, []):
            target = signals.setdefault(ordinal, {}).setdefault("target", {})
            target.setdefault("exact_files", set()).add(file_path)

        for ordinal in _phrase_candidates(projection, file_path):
            if file_path not in projection["entries"][ordinal]["searchable"]:
                continue
            target = signals.setdefault(ordinal, {}).setdefault("target", {})
            target.setdefault("path_phrases", set()).add(file_path)

        if basename:
            for ordinal in projection["basename_index"].get(basename, []):
                target = signals.setdefault(ordinal, {}).setdefault("target", {})
                target.setdefault("basenames", set()).add(basename)

        if directory_tag:
            for ordinal in projection["tag_index"].get(directory_tag, []):
                target = signals.setdefault(ordinal, {}).setdefault("target", {})
                target.setdefault("directory_tags", set()).add(directory_tag)
    return normalized_targets


def _target_strength(target: Dict[str, Any]) -> int:
    if target.get("exact_files"):
        return 4
    if target.get("path_phrases"):
        return 3
    if target.get("basenames"):
        return 2
    if target.get("directory_tags"):
        return 1
    return 0


def _serializable_match(
    signal: Dict[str, Any],
    importance: float,
) -> Dict[str, Any]:
    query_match = signal.get("query", {})
    target = signal.get("target", {})
    strength = _target_strength(target)
    selection_signals: List[str] = []
    if query_match:
        selection_signals.append(
            "query_exact" if query_match.get("exact_substring") else "query_terms"
        )
    if target.get("exact_files"):
        selection_signals.append("target_file_exact")
    if target.get("path_phrases"):
        selection_signals.append("target_path_phrase")
    if target.get("basenames"):
        selection_signals.append("target_basename")
    if target.get("directory_tags"):
        selection_signals.append("target_directory_tag")
    return {
        "model": MULTI_SIGNAL_MATCH_MODEL,
        "query": copy.deepcopy(query_match),
        "target": {
            key: sorted(value)
            for key, value in target.items()
            if value
        },
        "selection_signals": selection_signals,
        "rank_vector": {
            "target_strength": strength,
            "target_primary": strength >= 3,
            "query_score": float(query_match.get("score", 0.0)),
            "importance": importance,
        },
    }


def rank_recall_projection(
    projection: Dict[str, Any],
    query: Optional[str] = None,
    target_files: Optional[Iterable[str]] = None,
    memory_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    min_importance: float = 0.0,
    include_archived: bool = False,
    include_historical_evidence: bool = False,
) -> Dict[str, Any]:
    """Rank candidate references without copying the canonical memory records."""
    signals: Dict[int, Dict[str, Any]] = {}
    _query_signals(projection, query, signals)
    normalized_targets = _target_signals(
        projection, target_files or [], signals
    )
    has_directed_signal = bool(query or normalized_targets)
    candidate_ordinals = (
        set(signals)
        if has_directed_signal
        else set(range(len(projection["entries"])))
    )

    if memory_type:
        candidate_ordinals.intersection_update(
            projection["type_index"].get(memory_type, [])
        )
    if tags:
        candidate_ordinals.intersection_update(
            _posting_union(projection["tag_index"], tags)
        )

    ranked: List[Dict[str, Any]] = []
    filtered_counts: Dict[str, int] = {}
    for ordinal in candidate_ordinals:
        entry = projection["entries"][ordinal]
        memory = entry["memory"]
        exclusion: Optional[str] = None
        if not include_archived and entry["status"] != "active":
            exclusion = "archived"
        elif (
            not include_historical_evidence
            and entry["evidence_status"] in INACTIVE_EVIDENCE_STATUSES
        ):
            exclusion = entry["evidence_status"]
        elif float(memory.get("importance", 0.0)) < min_importance:
            exclusion = "below_min_importance"
        if exclusion:
            filtered_counts[exclusion] = filtered_counts.get(exclusion, 0) + 1
            continue

        importance = float(memory.get("importance", 0.0))
        signal = signals.get(ordinal, {})
        match = _serializable_match(signal, importance)
        rank_vector = match["rank_vector"]
        ranked.append({
            "ordinal": ordinal,
            "memory": memory,
            "retrieval_match": match,
            "sort_key": (
                -float(rank_vector["query_score"]),
                -int(bool(rank_vector["target_primary"])),
                -int(rank_vector["target_strength"]),
                -importance,
                str(memory.get("timestamp", "")),
                str(memory.get("id", "")),
            ),
        })

    if not has_directed_signal:
        ranked.sort(key=lambda item: int(item["ordinal"]))
        ranked.sort(
            key=lambda item: str(item["memory"].get("timestamp", "")),
            reverse=True,
        )
        ranked.sort(
            key=lambda item: float(item["memory"].get("importance", 0.0)),
            reverse=True,
        )
    else:
        ranked.sort(key=lambda item: item["sort_key"])

    total = len(projection["entries"])
    candidate_count = len(candidate_ordinals)
    return {
        "candidates": ranked,
        "trace": {
            **projection_metadata(projection),
            "query": query,
            "target_files": normalized_targets,
            "candidate_count": candidate_count,
            "ranked_count": len(ranked),
            "filtered_counts": filtered_counts,
            "projection_pruned_count": max(0, total - candidate_count),
            "candidate_ratio": round(candidate_count / max(1, total), 6),
            "snapshot_consistent": True,
            "predicate_completeness": (
                "exact_for_declared_lexical_and_path_predicates"
            ),
            "omitted_semantic_relevance_proven": False,
        },
    }


def recall_from_projection(
    projection: Dict[str, Any],
    query: Optional[str] = None,
    memory_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    min_importance: float = 0.0,
    limit: int = 20,
    include_archived: bool = False,
    include_historical_evidence: bool = False,
) -> List[Dict[str, Any]]:
    """Compatibility recall over a prebuilt projection."""
    ranked = rank_recall_projection(
        projection,
        query=query,
        memory_type=memory_type,
        tags=tags,
        min_importance=min_importance,
        include_archived=include_archived,
        include_historical_evidence=include_historical_evidence,
    )
    results: List[Dict[str, Any]] = []
    for candidate in ranked["candidates"][:limit]:
        memory = copy.deepcopy(candidate["memory"])
        if query:
            memory["retrieval_match"] = copy.deepcopy(
                candidate["retrieval_match"].get("query", {})
            )
        results.append(memory)
    return results


__all__ = [
    "LEXICAL_MATCH_MODEL",
    "MULTI_SIGNAL_MATCH_MODEL",
    "RECALL_PROJECTION_SCHEMA_VERSION",
    "build_recall_projection",
    "projection_metadata",
    "rank_recall_projection",
    "recall_from_projection",
]
