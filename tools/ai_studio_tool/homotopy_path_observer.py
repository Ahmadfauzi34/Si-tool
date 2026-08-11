"""
Homotopy Path Observer (Proto-HoTT Stage 3)
Schema Version: 2.2.0-hott

Mengobservasi struktur homotopi pada dependency graph:
- diamond_dependency: dua jalur berbeda antara source & target yang sama (A->B->D, A->C->D)
- mergeable_import: file yang sama mengimpor modul yang sama dalam statement terpisah
- multi_importer_hub: node dengan konsentrasi jalur masuk yang tinggi

Konsep HoTT:
- Path p : A -> B adalah jalur import
- Dua path p, q dengan endpoint sama adalah homotopic (redundant routes)
- Contractible path adalah jalur yang bisa digabung (mergeable)

Output bersifat informational dan tidak memberikan rekomendasi perubahan.
"""

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

SCHEMA_VERSION = "2.2.0-hott"

SOURCE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
RESOLUTION_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")

DEFAULT_IGNORE_DIRS = {
    "node_modules", ".git", "dist", ".angular",
    ".Jules", "coverage", ".next", "out",
    "fixtures_min"
}

IMPORT_REGEX = re.compile(
    r"import\s+(?:[^\"']*\s+from\s+)?[\"']([^\"']+)[\"']"
)


def _normalize_path(value: str) -> str:
    normalized = os.path.normpath(value).replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _is_source_file(filename: str) -> bool:
    return filename.endswith(SOURCE_EXTENSIONS) and not filename.endswith(".d.ts")


def _strip_comments(content: str) -> str:
    content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"/\*[\s\S]*?\*/", "", content)
    return content


def _read_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return None


def _resolve_import_path(base_file: str, import_path: str) -> str:
    """Resolve relative import path terhadap base file."""
    if not import_path.startswith("."):
        return import_path

    base_dir = os.path.dirname(base_file)
    parts = base_dir.split("/") if base_dir else []

    for segment in import_path.split("/"):
        if segment == "..":
            if parts:
                parts.pop()
        elif segment and segment != ".":
            parts.append(segment)

    return "/".join(parts)


def _candidate_targets(resolved_base: str) -> List[str]:
    """Daftar kandidat resolusi untuk import tanpa ekstensi."""
    candidates: List[str] = []
    seen: Set[str] = set()

    def add(c: str) -> None:
        if c and c not in seen:
            seen.add(c)
            candidates.append(c)

    add(resolved_base)

    if not any(resolved_base.endswith(ext) for ext in RESOLUTION_EXTENSIONS):
        for ext in RESOLUTION_EXTENSIONS:
            add(resolved_base + ext)
        for ext in RESOLUTION_EXTENSIONS:
            add(f"{resolved_base}/index{ext}")

    return candidates


# ============================================================
# Graph Construction
# ============================================================

def build_dependency_graph(
    scan_root: str,
    ignore_dirs: Optional[Set[str]] = None,
) -> Tuple[Dict[str, Set[str]], Set[str]]:
    """
    Bangun dependency graph: node -> set of imported targets (resolved).

    Returns:
    - graph: Dict[file_path, Set[target_file_path]]
    - all_files: Set[file_path]
    """
    if ignore_dirs is None:
        ignore_dirs = set(DEFAULT_IGNORE_DIRS)

    all_files: Set[str] = set()
    file_imports: Dict[str, List[str]] = {}  # file -> list of raw import paths

    # Pass 1: kumpulkan semua source files dan raw imports
    for root, dirs, files in os.walk(scan_root):
        dirs[:] = sorted(
            [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
        )
        for f in sorted(files):
            if not _is_source_file(f):
                continue

            full_path = _normalize_path(os.path.join(root, f))
            all_files.add(full_path)

            content = _read_file(full_path)
            if content is None:
                continue

            content = _strip_comments(content)
            raw_imports = IMPORT_REGEX.findall(content)
            file_imports[full_path] = raw_imports

    # Pass 2: resolve imports menjadi edge graph
    graph: Dict[str, Set[str]] = {}

    for src, raw_imports in file_imports.items():
        targets: Set[str] = set()

        for raw in raw_imports:
            if not raw.startswith("."):
                continue  # skip external

            resolved_base = _resolve_import_path(src, raw)
            candidates = _candidate_targets(resolved_base)

            for cand in candidates:
                if cand in all_files:
                    targets.add(cand)
                    break

        if targets:
            graph[src] = targets

    return graph, all_files


def build_reverse_graph(graph: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """Bangun reverse graph: node -> set of importers (dependents)."""
    reverse: Dict[str, Set[str]] = {}

    for src, targets in graph.items():
        for tgt in targets:
            if tgt not in reverse:
                reverse[tgt] = set()
            reverse[tgt].add(src)

    return reverse


# ============================================================
# Obstruction Detectors
# ============================================================

def detect_diamond_dependencies(
    graph: Dict[str, Set[str]],
    reverse: Dict[str, Set[str]],
) -> List[Dict[str, Any]]:
    """
    Homotopy Obstruction: dua jalur berbeda antara source & target yang sama.

    Diamond: A -> B -> D dan A -> C -> D
    Di sini, ada dua path homotopic dari A ke D (melalui B dan melalui C).
    """
    findings: List[Dict[str, Any]] = []
    seen_diamonds: Set[Tuple[str, str, str, str]] = set()

    # Untuk setiap node D dengan >= 2 direct importers
    for node_d, importers in sorted(reverse.items()):
        if len(importers) < 2:
            continue

        importer_list = sorted(importers)

        # Untuk setiap pair of importers (B, C)
        for i in range(len(importer_list)):
            for j in range(i + 1, len(importer_list)):
                node_b = importer_list[i]
                node_c = importer_list[j]

                # Cari common dependents: A yang mengimpor B dan C
                dependents_b = reverse.get(node_b, set())
                dependents_c = reverse.get(node_c, set())
                common_a = dependents_b & dependents_c

                for node_a in sorted(common_a):
                    diamond_key = (node_a, node_b, node_c, node_d)

                    # Normalize agar tidak duplikat (B dan C bisa tertukar)
                    normalized_key = (
                        node_a,
                        min(node_b, node_c),
                        max(node_b, node_c),
                        node_d,
                    )

                    if normalized_key in seen_diamonds:
                        continue
                    seen_diamonds.add(normalized_key)

                    findings.append({
                        "type": "diamond_dependency",
                        "severity": "medium",
                        "source": node_a,
                        "path_one": [node_a, node_b, node_d],
                        "path_two": [node_a, node_c, node_d],
                        "convergence": node_d,
                        "observation": (
                            f"Two homotopic paths from '{node_a}' to '{node_d}': "
                            f"'{node_a}' -> '{node_b}' -> '{node_d}' and "
                            f"'{node_a}' -> '{node_c}' -> '{node_d}'. "
                            f"Redundant routes converge at '{node_d}'."
                        ),
                        "invariant": "H1_multiple_paths",
                    })

    findings.sort(key=lambda f: (f["source"], f["convergence"]))
    return findings


def detect_mergeable_imports(
    scan_root: str,
    graph: Dict[str, Set[str]],
    ignore_dirs: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Contractible Path: file yang sama mengimpor modul yang sama
    dalam beberapa import statement terpisah.

    Ini adalah jalur yang bisa "dikontraksi" menjadi satu statement.
    """
    if ignore_dirs is None:
        ignore_dirs = set(DEFAULT_IGNORE_DIRS)

    findings: List[Dict[str, Any]] = []

    for root, dirs, files in os.walk(scan_root):
        dirs[:] = sorted(
            [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
        )
        for f in sorted(files):
            if not _is_source_file(f):
                continue

            full_path = _normalize_path(os.path.join(root, f))
            content = _read_file(full_path)
            if content is None:
                continue

            content = _strip_comments(content)
            raw_imports = IMPORT_REGEX.findall(content)

            # Hitung kemunculan setiap resolved module
            module_count: Dict[str, int] = {}
            for raw in raw_imports:
                if not raw.startswith("."):
                    continue
                resolved = _resolve_import_path(full_path, raw)
                # Normalize dengan menghapus ekstensi untuk grouping
                base = resolved
                for ext in RESOLUTION_EXTENSIONS:
                    if base.endswith(ext):
                        base = base[: -len(ext)]
                        break
                if base.endswith("/index"):
                    base = base[: -len("/index")]
                module_count[base] = module_count.get(base, 0) + 1

            for module, count in sorted(module_count.items()):
                if count >= 2:
                    findings.append({
                        "type": "mergeable_import",
                        "severity": "low",
                        "file": full_path,
                        "module": module,
                        "import_count": count,
                        "observation": (
                            f"File '{full_path}' imports module '{module}' "
                            f"in {count} separate statements. "
                            f"These paths are contractible into a single import."
                        ),
                        "invariant": "H0_contractible_path",
                    })

    findings.sort(key=lambda f: (f["file"], f["module"]))
    return findings


def detect_multi_importer_hubs(
    reverse: Dict[str, Set[str]],
    threshold: int = 4,
) -> List[Dict[str, Any]]:
    """
    High Path Concentration: node dengan banyak jalur masuk.

    Node seperti ini adalah "hub" di mana banyak path homotopic berkonvergensi.
    """
    findings: List[Dict[str, Any]] = []

    for node, importers in sorted(reverse.items()):
        if len(importers) >= threshold:
            findings.append({
                "type": "multi_importer_hub",
                "severity": "low",
                "node": node,
                "importer_count": len(importers),
                "importers": sorted(importers),
                "observation": (
                    f"Node '{node}' is a path-concentration hub with "
                    f"{len(importers)} incoming import paths."
                ),
                "invariant": "H0_path_concentration",
            })

    findings.sort(key=lambda f: -f["importer_count"])
    return findings


# ============================================================
# Main Orchestrator
# ============================================================

def observe_homotopy_paths(
    scan_root: str = ".",
    ignore_dirs: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Orkestrasi penuh Homotopy Path Observer.
    """
    if ignore_dirs is None:
        ignore_dirs = set(DEFAULT_IGNORE_DIRS)

    scan_root_norm = _normalize_path(scan_root)

    # Step 1: Bangun graph
    graph, all_files = build_dependency_graph(scan_root_norm, ignore_dirs)
    reverse = build_reverse_graph(graph)

    # Step 2: Jalankan semua detector
    all_findings: List[Dict[str, Any]] = []
    all_findings.extend(detect_diamond_dependencies(graph, reverse))
    all_findings.extend(detect_mergeable_imports(scan_root_norm, graph, ignore_dirs))
    all_findings.extend(detect_multi_importer_hubs(reverse))

    # Step 3: Sort deterministik
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_findings.sort(
        key=lambda f: (
            severity_order.get(f.get("severity", "low"), 3),
            f.get("type", ""),
            f.get("source", f.get("file", f.get("node", ""))),
        )
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "scan_root": scan_root_norm,
        "total_files": len(all_files),
        "total_edges": sum(len(t) for t in graph.values()),
        "obstructions": all_findings,
        "summary": {
            "total_obstructions": len(all_findings),
            "by_type": {
                "diamond_dependency": sum(
                    1 for f in all_findings if f["type"] == "diamond_dependency"
                ),
                "mergeable_import": sum(
                    1 for f in all_findings if f["type"] == "mergeable_import"
                ),
                "multi_importer_hub": sum(
                    1 for f in all_findings if f["type"] == "multi_importer_hub"
                ),
            },
            "by_severity": {
                "high": sum(
                    1 for f in all_findings if f.get("severity") == "high"
                ),
                "medium": sum(
                    1 for f in all_findings if f.get("severity") == "medium"
                ),
                "low": sum(
                    1 for f in all_findings if f.get("severity") == "low"
                ),
            },
        },
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = "."

    print(json.dumps(observe_homotopy_paths(root), indent=2))
