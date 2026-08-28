"""
Query-Directed Context Optimizer — HoTT Kernel
Schema Version: 3.0.0-kernel

Builds a deterministic, budget-bounded context projection from one SharedGraph.
The optimizer never scans or reads source files itself; it consumes file_map and
analyzer evidence already produced from the canonical graph snapshot.

This is context selection, not a correctness proof or a model-specific tokenizer.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from collections import defaultdict, deque
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


CONTEXT_MODEL = "query_directed_quotient_context_v1"
CHARS_PER_TOKEN_ESTIMATE = 4
DEFAULT_BUDGET_TOKENS = 1200
MIN_BUDGET_TOKENS = 256
MAX_BUDGET_TOKENS = 32000
DEFAULT_MAX_HOPS = 2
MAX_HOPS = 5
MAX_SEMANTIC_SEEDS = 8
MAX_EXCERPT_LINES = 12

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_CAMEL_RE = re.compile(r"([a-z0-9])([A-Z])")
_STOPWORDS = {
    "a", "an", "and", "atau", "cek", "check", "code", "codebase",
    "dalam", "dan", "dari", "developer", "di", "file", "fix", "ini",
    "itu", "ke", "llm", "of", "pada", "periksa", "project", "proyek",
    "source", "the", "this", "to", "untuk", "yang",
}
_SEVERITY_SIGNAL = {"high": 1.0, "medium": 2.0 / 3.0, "low": 1.0 / 3.0, "info": 0.0}


def _normalize_path(value: str) -> str:
    normalized = os.path.normpath(value).replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _terms(value: str) -> Set[str]:
    expanded = _CAMEL_RE.sub(r"\1 \2", value or "")
    return {
        token.lower()
        for token in _TOKEN_RE.findall(expanded.replace("_", " "))
        if token.lower() not in _STOPWORDS and len(token) >= 2
    }


def _overlap(query_terms: Set[str], field_terms: Set[str]) -> Tuple[float, List[str]]:
    matched = sorted(query_terms & field_terms)
    if not query_terms:
        return 0.0, matched
    return len(matched) / len(query_terms), matched


def _content_signature(shared_graph: Dict[str, Any]) -> str:
    digest = hashlib.sha256()
    file_map = shared_graph.get("file_map", {})
    for path in sorted(shared_graph.get("vertices", [])):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_map.get(path, "").encode("utf-8"))
        digest.update(b"\0")
    for source, target in sorted(shared_graph.get("edges", [])):
        digest.update(source.encode("utf-8"))
        digest.update(b"->")
        digest.update(target.encode("utf-8"))
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _build_adjacency(
    vertices: Iterable[str],
    edges: Iterable[Tuple[str, str]],
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]], Dict[str, List[str]]]:
    forward: Dict[str, Set[str]] = defaultdict(set)
    reverse: Dict[str, Set[str]] = defaultdict(set)
    undirected: Dict[str, Set[str]] = defaultdict(set)
    for source, target in edges:
        forward[source].add(target)
        reverse[target].add(source)
        undirected[source].add(target)
        undirected[target].add(source)
    for vertex in vertices:
        forward.setdefault(vertex, set())
        reverse.setdefault(vertex, set())
        undirected.setdefault(vertex, set())
    return (
        {key: sorted(value) for key, value in forward.items()},
        {key: sorted(value) for key, value in reverse.items()},
        {key: sorted(value) for key, value in undirected.items()},
    )


def _resolve_target(target: str, vertices: Set[str]) -> Tuple[Optional[str], List[str]]:
    normalized = _normalize_path(target)
    if normalized in vertices:
        return normalized, []
    suffix = f"/{normalized}"
    matches = sorted(path for path in vertices if path.endswith(suffix))
    if len(matches) == 1:
        return matches[0], []
    return None, matches


def _finding_files(value: Any, vertices: Set[str], found: Set[str]) -> None:
    if isinstance(value, str):
        normalized = _normalize_path(value)
        if normalized in vertices:
            found.add(normalized)
    elif isinstance(value, dict):
        for nested in value.values():
            _finding_files(nested, vertices, found)
    elif isinstance(value, (list, tuple, set)):
        for nested in value:
            _finding_files(nested, vertices, found)


def _collect_evidence(
    analyzer_output: Dict[str, Any],
    vertices: Set[str],
) -> Dict[str, List[Dict[str, Any]]]:
    evidence: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for analyzer_name, result in sorted(analyzer_output.get("results", {}).items()):
        for finding in result.get("findings", []):
            files: Set[str] = set()
            _finding_files(finding, vertices, files)
            if not files:
                continue
            reasons = finding.get("reasons", finding.get("risk_reasons", []))
            if not isinstance(reasons, list):
                reasons = [str(reasons)]
            item = {
                "analyzer": analyzer_name,
                "type": finding.get("type", "finding"),
                "severity": finding.get("severity", "info"),
                "reasons": [str(reason) for reason in reasons],
                "observation": str(finding.get("observation", ""))[:320],
            }
            for path in sorted(files):
                evidence[path].append(item)
    for path in evidence:
        evidence[path].sort(
            key=lambda item: (
                -_SEVERITY_SIGNAL.get(item["severity"], 0.0),
                item["analyzer"],
                item["type"],
            )
        )
    return evidence


def _outline(shared_graph: Dict[str, Any], path: str) -> Dict[str, Any]:
    try:
        from codebase.topology_analyzers import query_outline
    except ImportError:
        from topology_analyzers import query_outline
    result = query_outline(shared_graph, path)
    if not result.get("exists"):
        return {"exports": [], "declarations": [], "stats": {}}
    return {
        "exports": result.get("exports", []),
        "declarations": [
            {
                "line": item.get("line"),
                "kind": item.get("kind"),
                "name": item.get("name"),
            }
            for item in result.get("declarations", [])
        ],
        "stats": result.get("stats", {}),
    }


def _multi_source_distances(
    seeds: Iterable[str],
    adjacency: Dict[str, List[str]],
    max_hops: int,
) -> Dict[str, int]:
    distances: Dict[str, int] = {}
    queue: deque[str] = deque()
    for seed in sorted(set(seeds)):
        distances[seed] = 0
        queue.append(seed)
    while queue:
        current = queue.popleft()
        distance = distances[current]
        if distance >= max_hops:
            continue
        for neighbor in adjacency.get(current, []):
            if neighbor in distances:
                continue
            distances[neighbor] = distance + 1
            queue.append(neighbor)
    return distances


def _source_excerpt(content: str, query_terms: Set[str]) -> Dict[str, Any]:
    lines = content.splitlines()
    matched_indices = [
        index
        for index, line in enumerate(lines)
        if query_terms and query_terms & _terms(line)
    ]
    strategy = "query_window"
    selected_indices: Set[int] = set()
    for index in matched_indices:
        selected_indices.update(
            candidate
            for candidate in (index - 1, index, index + 1)
            if 0 <= candidate < len(lines)
        )
    if not selected_indices:
        strategy = "structural_head"
        structural = [
            index
            for index, line in enumerate(lines)
            if line.strip().startswith(("import ", "export ", "@"))
        ]
        selected_indices.update(structural[:MAX_EXCERPT_LINES])
        if not selected_indices:
            selected_indices.update(
                index for index, line in enumerate(lines) if line.strip()
            )
    ordered = sorted(selected_indices)[:MAX_EXCERPT_LINES]
    return {
        "strategy": strategy,
        "matched_line_count": len(matched_indices),
        "truncated": len(selected_indices) > len(ordered) or len(ordered) < len(lines),
        "lines": [
            {"line": index + 1, "text": lines[index][:240]}
            for index in ordered
        ],
    }


def _build_quotient(
    shared_graph: Dict[str, Any],
    selected_paths: List[str],
) -> Dict[str, Any]:
    boundaries = shared_graph.get("boundaries", {})
    file_to_boundary = shared_graph.get("file_to_boundary", {})
    internal_edges: Dict[str, int] = defaultdict(int)
    cross_edges: Dict[Tuple[str, str], int] = defaultdict(int)
    cross_witnesses: Dict[Tuple[str, str], List[List[str]]] = defaultdict(list)
    for source, target in shared_graph.get("edges", []):
        source_boundary = file_to_boundary.get(source, shared_graph.get("scan_root", "."))
        target_boundary = file_to_boundary.get(target, shared_graph.get("scan_root", "."))
        if source_boundary == target_boundary:
            internal_edges[source_boundary] += 1
        else:
            edge = (source_boundary, target_boundary)
            cross_edges[edge] += 1
            if len(cross_witnesses[edge]) < 2:
                cross_witnesses[edge].append([source, target])

    relevant = sorted({file_to_boundary.get(path) for path in selected_paths if file_to_boundary.get(path)})
    relevant_set = set(relevant)
    relevant_nodes = []
    for boundary in relevant:
        data = boundaries.get(boundary, {})
        relevant_nodes.append({
            "boundary": boundary,
            "file_count": len(data.get("files", [])),
            "selected_file_count": sum(
                1 for path in selected_paths if file_to_boundary.get(path) == boundary
            ),
            "internal_edge_count": internal_edges.get(boundary, 0),
            "has_barrel": bool(data.get("barrel")),
        })

    relevant_edges = []
    for (source, target), count in sorted(cross_edges.items()):
        if source not in relevant_set and target not in relevant_set:
            continue
        relevant_edges.append({
            "source_boundary": source,
            "target_boundary": target,
            "edge_count": count,
            "witnesses": cross_witnesses[(source, target)],
        })
        if len(relevant_edges) >= 12:
            break

    return {
        "model": {
            "name": "boundary_quotient_graph",
            "definition": "G/P where P partitions files by SharedGraph boundary",
            "edge_semantics": "resolved relative imports aggregated by boundary pair",
        },
        "summary": {
            "original_vertex_count": len(shared_graph.get("vertices", [])),
            "original_edge_count": len(shared_graph.get("edges", [])),
            "quotient_vertex_count": len(boundaries),
            "quotient_cross_edge_count": len(cross_edges),
            "quotient_cross_edge_multiplicity": sum(cross_edges.values()),
            "relevant_boundary_count": len(relevant_nodes),
            "omitted_boundary_count": max(0, len(boundaries) - len(relevant_nodes)),
        },
        "relevant_boundaries": relevant_nodes,
        "relevant_cross_edges": relevant_edges,
    }


def _compact_list(values: List[str], limit: int = 3) -> str:
    if not values:
        return "-"
    shown = values[:limit]
    suffix = f" (+{len(values) - limit})" if len(values) > limit else ""
    return ", ".join(shown) + suffix


def _render_card(profile: Dict[str, Any], detail: str, char_cap: int) -> str:
    distance = profile.get("graph_distance")
    distance_text = "-" if distance is None else str(distance)
    lines = [
        f"FILE {profile['file']} | score={profile['score']:.4f} | d={distance_text}",
        f"why={_compact_list(profile['selection_signals'], 5)}",
        (
            f"topology=boundary:{profile['topology']['boundary']}; "
            f"type:{profile['topology']['node_type']}; "
            f"fan_in:{profile['topology']['fan_in']}; fan_out:{profile['topology']['fan_out']}"
        ),
        f"imports={_compact_list(profile['topology']['direct_imports'])}",
        f"imported_by={_compact_list(profile['topology']['direct_importers'])}",
    ]
    symbols = [
        f"{item.get('kind')}:{item.get('name')}@L{item.get('line')}"
        for item in profile.get("outline", {}).get("declarations", [])
    ]
    if symbols:
        lines.append(f"symbols={_compact_list(symbols, 5)}")
    findings = [
        f"{item['analyzer']}:{item['type']}:{item['severity']}"
        for item in profile.get("findings", [])
    ]
    if findings:
        lines.append(f"evidence={_compact_list(findings, 4)}")

    def joined(candidate: List[str]) -> str:
        return "\n".join(candidate) + "\n"

    while len(joined(lines)) > char_cap and len(lines) > 2:
        lines.pop()
    if detail == "source":
        excerpt_lines = profile.get("source_excerpt", {}).get("lines", [])
        if excerpt_lines:
            if len(joined(lines + ["source_excerpt:"])) <= char_cap:
                lines.append("source_excerpt:")
            for item in excerpt_lines:
                rendered = f"  L{item['line']}: {item['text']}"
                if len(joined(lines + [rendered])) > char_cap:
                    break
                lines.append(rendered)
    rendered = joined(lines)
    if len(rendered) > char_cap:
        rendered = rendered[: max(0, char_cap - 1)].rstrip() + "\n"
    return rendered


def build_context_pack(
    shared_graph: Dict[str, Any],
    query: str,
    target_files: Optional[List[str]] = None,
    budget_tokens: int = DEFAULT_BUDGET_TOKENS,
    max_hops: int = DEFAULT_MAX_HOPS,
    detail: str = "source",
    analyzer_output: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Project measured graph evidence into a deterministic prompt-sized pack."""
    vertices = sorted(shared_graph.get("vertices", []))
    vertex_set = set(vertices)
    file_map = shared_graph.get("file_map", {})
    node_metadata = shared_graph.get("node_metadata", {})
    file_to_boundary = shared_graph.get("file_to_boundary", {})
    query_terms = _terms(query)
    requested_targets = target_files or []

    if analyzer_output is None:
        try:
            from core.analyzer_registry import run_analyzers
        except ImportError:
            from analyzer_registry import run_analyzers
        analyzer_output = run_analyzers(shared_graph)

    resolved_targets: List[str] = []
    unresolved_targets: List[Dict[str, Any]] = []
    for requested in requested_targets:
        resolved, ambiguous = _resolve_target(requested, vertex_set)
        if resolved:
            resolved_targets.append(resolved)
        else:
            unresolved_targets.append({
                "requested": requested,
                "ambiguous_matches": ambiguous,
            })
    resolved_targets = sorted(set(resolved_targets))

    forward, reverse, undirected = _build_adjacency(
        vertices,
        shared_graph.get("edges", []),
    )
    evidence_by_file = _collect_evidence(analyzer_output, vertex_set)
    outlines: Dict[str, Dict[str, Any]] = {}
    lexical_data: Dict[str, Dict[str, Any]] = {}

    for path in vertices:
        outline = _outline(shared_graph, path)
        outlines[path] = outline
        path_score, path_matches = _overlap(query_terms, _terms(path))
        symbol_text = " ".join(
            list(outline.get("exports", []))
            + [item.get("name", "") for item in outline.get("declarations", [])]
        )
        symbol_score, symbol_matches = _overlap(query_terms, _terms(symbol_text))
        evidence_text = " ".join(
            " ".join([
                item.get("analyzer", ""),
                item.get("type", ""),
                item.get("observation", ""),
                " ".join(item.get("reasons", [])),
            ])
            for item in evidence_by_file.get(path, [])
        )
        evidence_score, evidence_matches = _overlap(query_terms, _terms(evidence_text))
        lexical = max(path_score, 0.9 * symbol_score, 0.8 * evidence_score)
        lexical_data[path] = {
            "score": lexical,
            "path_score": path_score,
            "symbol_score": symbol_score,
            "evidence_score": evidence_score,
            "path_matches": path_matches,
            "symbol_matches": symbol_matches,
            "evidence_matches": evidence_matches,
        }

    semantic_rank = sorted(
        (path for path in vertices if lexical_data[path]["score"] > 0.0),
        key=lambda path: (-lexical_data[path]["score"], path),
    )
    semantic_seeds = semantic_rank[:MAX_SEMANTIC_SEEDS]
    # Explicit targets define the projection base. Query matches still affect
    # ranking, but unrelated lexical matches must not pull in another subgraph.
    seeds = resolved_targets if resolved_targets else semantic_seeds
    distances = _multi_source_distances(seeds, undirected, max_hops) if seeds else {}

    if resolved_targets:
        selection_mode = "explicit_target_graph"
    elif semantic_seeds:
        selection_mode = "query_graph"
    else:
        selection_mode = "structural_fallback"

    candidates = set(distances)
    if not resolved_targets:
        candidates.update(semantic_rank)
    if not candidates:
        candidates.update(vertices)

    max_degree = max(
        (int(node_metadata.get(path, {}).get("fan_in", 0))
         + int(node_metadata.get(path, {}).get("fan_out", 0)) for path in vertices),
        default=0,
    )
    profiles: List[Dict[str, Any]] = []
    for path in sorted(candidates):
        metadata = node_metadata.get(path, {})
        lexical = lexical_data[path]
        distance = distances.get(path)
        proximity = 1.0 / (1.0 + distance) if distance is not None else 0.0
        degree = int(metadata.get("fan_in", 0)) + int(metadata.get("fan_out", 0))
        centrality = degree / max_degree if max_degree else 0.0
        findings = evidence_by_file.get(path, [])
        evidence_signal = max(
            (_SEVERITY_SIGNAL.get(item.get("severity", "info"), 0.0) for item in findings),
            default=0.0,
        )
        base_score = (
            0.45 * lexical["score"]
            + 0.25 * proximity
            + 0.20 * centrality
            + 0.10 * evidence_signal
        )
        mandatory = path in resolved_targets
        score = base_score + (1.0 if mandatory else 0.0)
        signals: List[str] = []
        if mandatory:
            signals.append("explicit_target")
        for label, matches in (
            ("query_path", lexical["path_matches"]),
            ("query_symbol", lexical["symbol_matches"]),
            ("query_finding", lexical["evidence_matches"]),
        ):
            if matches:
                signals.append(f"{label}:{','.join(matches)}")
        if distance is not None:
            signals.append(f"graph_distance:{distance}")
        if centrality >= 0.5:
            signals.append("structural_centrality")
        if evidence_signal > 0:
            signals.append(f"finding_severity:{findings[0].get('severity', 'info')}")
        if not signals:
            signals.append("structural_fallback")

        content = file_map.get(path, "")
        profiles.append({
            "file": path,
            "score": round(score, 6),
            "mandatory": mandatory,
            "graph_distance": distance,
            "selection_signals": signals,
            "matched_query_terms": {
                "path": lexical["path_matches"],
                "symbols": lexical["symbol_matches"],
                "findings": lexical["evidence_matches"],
            },
            "score_components": {
                "lexical": round(lexical["score"], 6),
                "proximity": round(proximity, 6),
                "degree_centrality": round(centrality, 6),
                "finding_severity": round(evidence_signal, 6),
                "explicit_target_bonus": 1.0 if mandatory else 0.0,
            },
            "topology": {
                "boundary": file_to_boundary.get(path, shared_graph.get("scan_root", ".")),
                "node_type": metadata.get("type", "Other"),
                "is_entrypoint": bool(metadata.get("is_entrypoint")),
                "is_test": bool(metadata.get("is_test")),
                "fan_in": int(metadata.get("fan_in", 0)),
                "fan_out": int(metadata.get("fan_out", 0)),
                "direct_imports": forward.get(path, []),
                "direct_importers": reverse.get(path, []),
            },
            "outline": outlines[path],
            "findings": findings[:6],
            "source_excerpt": _source_excerpt(content, query_terms),
            "content_sha256": f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}",
        })

    profiles.sort(key=lambda item: (-int(item["mandatory"]), -item["score"], item["file"]))
    char_budget = budget_tokens * CHARS_PER_TOKEN_ESTIMATE
    signature = _content_signature(shared_graph)
    query_display = " ".join(query.strip().split())[:240]
    header = (
        "[QUERY-DIRECTED CODE CONTEXT]\n"
        f"query={query_display}\n"
        f"model={CONTEXT_MODEL}; graph={signature}; "
        f"V={len(vertices)}; E={len(shared_graph.get('edges', []))}\n"
        f"selection={selection_mode}; hops<={max_hops}; "
        "score=target_bonus+0.45L+0.25P+0.20C+0.10F\n"
        "scope=static TS/JS graph evidence; excerpts may be partial; findings are observations.\n"
    )
    parts = [header]
    selected: List[Dict[str, Any]] = []
    allocation_divisor = max(1, min(len(profiles), 4))
    per_card_cap = max(260, min(1200, char_budget // allocation_divisor))
    footer_reserve = 110
    for profile in profiles:
        card = _render_card(profile, detail, per_card_cap)
        current_length = len("\n".join(parts))
        if current_length + len(card) + footer_reserve <= char_budget:
            parts.append(card)
            selected.append(profile)
            continue
        if profile["mandatory"]:
            compact = _render_card(profile, "outline", 260)
            if current_length + len(compact) + footer_reserve <= char_budget:
                parts.append(compact)
                selected.append(profile)

    selected_paths = [item["file"] for item in selected]
    footer = (
        f"SELECTED={len(selected)}/{len(vertices)}; "
        f"FILES_OMITTED={max(0, len(vertices) - len(selected))}; "
        f"CANDIDATES_OMITTED={max(0, len(profiles) - len(selected))}; "
        "request targeted source only when evidence is insufficient.\n"
    )
    context_block = "\n".join(parts) + footer
    if len(context_block) > char_budget:
        context_block = context_block[:char_budget].rstrip()
    used_chars = len(context_block)
    estimated_tokens = math.ceil(used_chars / CHARS_PER_TOKEN_ESTIMATE)
    max_lexical = max((item["score"] for item in lexical_data.values()), default=0.0)
    if resolved_targets:
        confidence = "high"
    elif max_lexical >= 0.5:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "schema_version": "3.0.0-kernel",
        "available": True,
        "model": {
            "name": CONTEXT_MODEL,
            "purpose": "deterministic query-directed projection of measured codebase evidence",
            "score_formula": "explicit_target_bonus + 0.45*L + 0.25*P + 0.20*C + 0.10*F",
            "terms": {
                "L": "max(path overlap, 0.9*symbol overlap, 0.8*finding overlap)",
                "P": "1/(1+undirected graph distance from a semantic seed)",
                "C": "normalized total degree (fan_in + fan_out)",
                "F": "maximum mapped analyzer-finding severity",
            },
            "claim_boundary": (
                "Ranking is deterministic context selection, not a proof that omitted files "
                "are irrelevant and not a model-specific token count."
            ),
        },
        "query": query,
        "selection": {
            "mode": selection_mode,
            "confidence": confidence,
            "query_terms": sorted(query_terms),
            "semantic_seeds": semantic_seeds,
            "graph_seeds": seeds,
            "requested_targets": requested_targets,
            "resolved_targets": resolved_targets,
            "unresolved_targets": unresolved_targets,
            "max_hops": max_hops,
            "selected_paths": selected_paths,
        },
        "budget": {
            "requested_estimated_tokens": budget_tokens,
            "char_budget": char_budget,
            "chars_per_token_estimate": CHARS_PER_TOKEN_ESTIMATE,
            "used_chars": used_chars,
            "estimated_tokens": estimated_tokens,
            "utilization": round(used_chars / char_budget, 4) if char_budget else 0.0,
            "within_budget": used_chars <= char_budget,
            "token_count_is_estimate": True,
        },
        "provenance": {
            "graph_content_signature": signature,
            "scan_root": shared_graph.get("scan_root"),
            "graph_cache": shared_graph.get("cache", {}),
            "shared_graph_scan_passes": 1,
            "optimizer_additional_filesystem_scans": 0,
            "analyzers_share_same_graph": True,
            "selected_file_count": len(selected),
            "omitted_file_count": max(0, len(vertices) - len(selected)),
            "analyzers_failed": analyzer_output.get("analyzers_failed", 0),
            "analyzer_errors": analyzer_output.get("errors", {}),
        },
        "quotient_graph": _build_quotient(shared_graph, selected_paths),
        "selected_files": selected,
        "context_block": context_block,
    }


__all__ = [
    "build_context_pack",
    "CONTEXT_MODEL",
    "DEFAULT_BUDGET_TOKENS",
    "DEFAULT_MAX_HOPS",
    "MIN_BUDGET_TOKENS",
    "MAX_BUDGET_TOKENS",
    "MAX_HOPS",
]
