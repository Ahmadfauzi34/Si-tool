"""
SharedGraph Builder — HoTT Kernel Foundation
Schema Version: 3.0.0-kernel

Membangun SharedGraph dalam SATU pass:
- Filesystem scan (1x, sebelumnya 9x)
- Import parsing (1x, sebelumnya 5x)
- Graph construction (1x, sebelumnya 4x)
- Node metadata extraction (1x)
- Boundary detection (1x)
- Type shape extraction (1x)

SharedGraph kemudian di-share ke semua analyzer.
Tidak ada analyzer yang boleh scan filesystem sendiri.
"""

import os
import re
import json
import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

SCHEMA_VERSION = "3.0.0-kernel"

SOURCE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
RESOLUTION_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
BARREL_FILENAMES = ("index.ts", "index.tsx", "index.js", "index.jsx", "public-api.ts")

DEFAULT_IGNORE_DIRS = {
    "node_modules", ".git", "dist", ".angular",
    ".Jules", "coverage", ".next", "out", "fixtures_min",
}

IMPORT_REGEX = re.compile(
    r"import\s+(?:[^\"']*\s+from\s+)?[\"']([^\"']+)[\"']"
)

ENTRYPOINT_RULES = [
    (re.compile(r"^main\.server\.(ts|js)$"), "ssr_bootstrap", 0.95),
    (re.compile(r"^main\.(ts|js)$"), "browser_bootstrap", 0.95),
    (re.compile(r"^server\.(ts|js)$"), "server_http", 0.90),
    (re.compile(r"^entry\.server\.(ts|js)$"), "ssr_bootstrap", 0.90),
    (re.compile(r"^entry\.client\.(ts|js)$"), "browser_bootstrap", 0.90),
    (re.compile(r"^bootstrap\.(ts|js)$"), "app_bootstrap", 0.80),
]

TEST_FILE_REGEX = re.compile(
    r"\.(spec|test)\.(ts|tsx|js|jsx)$"
)

INTERFACE_REGEX = re.compile(
    r"(?:export\s+)?interface\s+(\w+)[^{]*\{([^}]*)\}",
    re.DOTALL
)

TYPE_ALIAS_REGEX = re.compile(
    r"(?:export\s+)?type\s+(\w+)\s*=\s*\{([^}]*)\}",
    re.DOTALL
)


def _normalize_path(value: str) -> str:
    normalized = os.path.normpath(value).replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _is_source_file(filename: str) -> bool:
    return filename.endswith(SOURCE_EXTENSIONS) and not filename.endswith(".d.ts")


def _is_test_file(filename: str) -> bool:
    return bool(TEST_FILE_REGEX.search(filename))


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


def _detect_entrypoint(filename: str) -> Tuple[bool, str, float]:
    base = os.path.basename(filename)
    for pattern, kind, confidence in ENTRYPOINT_RULES:
        if pattern.match(base):
            return True, kind, confidence
    return False, "none", 0.0


def _classify_node(file_path: str, content: str) -> str:
    lower_path = file_path.lower()
    if ".service." in lower_path or "@Injectable" in content:
        return "Service"
    if ".component." in lower_path or "@Component" in content:
        return "Component"
    if ".module." in lower_path or ".routes." in lower_path:
        return "Module"
    if "util" in lower_path or "helper" in lower_path:
        return "Helper"
    return "Other"


def _resolve_import_path(base_file: str, import_path: str) -> str:
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


def _extract_type_shapes(content: str) -> Dict[str, Set[str]]:
    """Ekstrak nama type/interface dan himpunan property names."""
    shapes: Dict[str, Set[str]] = {}
    content = _strip_comments(content)

    for regex in (INTERFACE_REGEX, TYPE_ALIAS_REGEX):
        for match in regex.finditer(content):
            name = match.group(1)
            body = match.group(2)
            props: Set[str] = set()
            for line in body.split("\n"):
                line = line.strip().rstrip(";").rstrip(",")
                prop_match = re.match(r"^(readonly\s+)?(\w+)(\?)?\s*:", line)
                if prop_match:
                    props.add(prop_match.group(2))
            shapes[name] = props

    return shapes


def _detect_boundaries(
    all_files: List[str],
    scan_root: str,
) -> Tuple[Dict[str, Dict], Dict[str, str]]:
    """
    Deteksi module boundaries.
    Boundary = folder dengan barrel file, atau top-level folder.
    """
    scan_root_norm = _normalize_path(scan_root)

    # Identifikasi folder dengan barrel
    barrel_folders: Dict[str, str] = {}
    for fp in all_files:
        dirname = os.path.dirname(fp)
        basename = os.path.basename(fp)
        if basename in BARREL_FILENAMES:
            barrel_folders[dirname] = fp

    # Assign setiap file ke boundary
    boundaries: Dict[str, Dict] = {}
    file_to_boundary: Dict[str, str] = {}

    for fp in all_files:
        current = os.path.dirname(fp)
        assigned = None

        while current and current.startswith(scan_root_norm):
            if current in barrel_folders:
                assigned = current
                break
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

        if assigned is None:
            rel = os.path.relpath(fp, scan_root_norm)
            top_folder = rel.split("/")[0] if "/" in rel else ""
            if top_folder:
                assigned = _normalize_path(os.path.join(scan_root_norm, top_folder))
            else:
                assigned = scan_root_norm

        if assigned not in boundaries:
            boundaries[assigned] = {
                "barrel": barrel_folders.get(assigned),
                "files": [],
            }

        boundaries[assigned]["files"].append(fp)
        file_to_boundary[fp] = assigned

    return boundaries, file_to_boundary


def build_shared_graph(
    scan_root: str = ".",
    ignore_dirs: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Bangun SharedGraph dalam SATU pass.

    Ini adalah satu-satunya fungsi yang boleh melakukan os.walk().
    Semua analyzer mengonsumsi output fungsi ini.
    """
    if ignore_dirs is None:
        ignore_dirs = set(DEFAULT_IGNORE_DIRS)

    scan_root_norm = _normalize_path(scan_root)

    # ============================================================
    # PASS 1: Filesystem scan + file reading + import parsing
    # ============================================================
    all_files: List[str] = []
    file_map: Dict[str, str] = {}           # path -> content
    file_imports: Dict[str, List[str]] = {}  # path -> raw import paths

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

            all_files.append(full_path)
            file_map[full_path] = content

            stripped = _strip_comments(content)
            file_imports[full_path] = IMPORT_REGEX.findall(stripped)

    # ============================================================
    # PASS 2: Node metadata extraction
    # ============================================================
    node_metadata: Dict[str, Dict[str, Any]] = {}

    for fp in all_files:
        content = file_map[fp]
        filename = os.path.basename(fp)

        is_entrypoint, ep_kind, ep_conf = _detect_entrypoint(filename)
        is_test = _is_test_file(filename)
        node_type = _classify_node(fp, content)

        node_metadata[fp] = {
            "type": node_type,
            "is_entrypoint": is_entrypoint,
            "entrypoint_kind": ep_kind,
            "entrypoint_confidence": ep_conf,
            "is_test": is_test,
        }

    # ============================================================
    # PASS 3: Import resolution + graph construction
    # ============================================================
    all_files_set = set(all_files)
    edges: List[Tuple[str, str]] = []
    resolved_imports: Dict[str, List[str]] = {}
    unresolved_imports: List[Dict[str, Any]] = []
    external_imports: List[Dict[str, Any]] = []

    for fp in all_files:
        resolved_targets: List[str] = []

        for raw_import in file_imports.get(fp, []):
            if not raw_import.startswith("."):
                external_imports.append({
                    "importer": fp,
                    "raw_import": raw_import,
                })
                continue

            resolved_base = _resolve_import_path(fp, raw_import)
            candidates = _candidate_targets(resolved_base)
            matched = None

            for cand in candidates:
                if cand in all_files_set:
                    matched = cand
                    break

            if matched:
                edges.append((fp, matched))
                resolved_targets.append(matched)
            else:
                unresolved_imports.append({
                    "importer": fp,
                    "raw_import": raw_import,
                    "attempted_candidates": candidates,
                })

        resolved_imports[fp] = resolved_targets

    # Deduplicate edges
    edges = sorted(set(edges))

    # ============================================================
    # PASS 4: Fan in/out calculation
    # ============================================================
    fan_in: Dict[str, int] = {}
    fan_out: Dict[str, int] = {}

    for src, tgt in edges:
        fan_out[src] = fan_out.get(src, 0) + 1
        fan_in[tgt] = fan_in.get(tgt, 0) + 1

    for fp in all_files:
        node_metadata[fp]["fan_in"] = fan_in.get(fp, 0)
        node_metadata[fp]["fan_out"] = fan_out.get(fp, 0)

    # ============================================================
    # PASS 5: Boundary detection
    # ============================================================
    boundaries, file_to_boundary = _detect_boundaries(all_files, scan_root)

    # ============================================================
    # PASS 6: Type shape extraction
    # ============================================================
    type_shapes: Dict[str, Dict[str, List[str]]] = {}

    for fp in all_files:
        content = file_map[fp]
        shapes = _extract_type_shapes(content)
        if shapes:
            type_shapes[fp] = {
                name: sorted(props) for name, props in shapes.items()
            }

    # ============================================================
    # Assemble SharedGraph
    # ============================================================
    return {
        "schema_version": SCHEMA_VERSION,
        "scan_root": scan_root_norm,
        "scan_timestamp": datetime.datetime.utcnow().isoformat() + "Z",

        # Core topology
        "vertices": sorted(all_files),
        "edges": edges,
        "file_map": file_map,
        "node_metadata": node_metadata,

        # Import resolution
        "resolved_imports": resolved_imports,
        "unresolved_imports": unresolved_imports,
        "external_imports": external_imports,

        # Boundaries
        "boundaries": boundaries,
        "file_to_boundary": file_to_boundary,

        # Type shapes
        "type_shapes": type_shapes,

        # Summary
        "summary": {
            "total_files": len(all_files),
            "total_edges": len(edges),
            "total_boundaries": len(boundaries),
            "total_type_shapes": sum(len(v) for v in type_shapes.values()),
            "total_unresolved": len(unresolved_imports),
            "total_external": len(external_imports),
            "entrypoint_count": sum(
                1 for m in node_metadata.values() if m.get("is_entrypoint")
            ),
            "test_file_count": sum(
                1 for m in node_metadata.values() if m.get("is_test")
            ),
        },
    }


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    graph = build_shared_graph(root)
    # Jangan print file_map (terlalu besar), hapus untuk output
    output = {k: v for k, v in graph.items() if k != "file_map"}
    print(json.dumps(output, indent=2))
