"""
Boundary Sheaf Checker (Proto-HoTT Stage 2)
Schema Version: 2.1.0-sheaf

Mengobservasi cohomology obstructions pada module boundaries:
- boundary_violation: import bypass barrel/public-api (encapsulation leak)
- circular_boundary: siklus dependensi antar module boundaries
- section_conflict: type name collision dengan shape berbeda lintas boundary
- missing_barrel_export: simbol diimpor cross-boundary tapi tidak di-export barrel

Konsep Sheaf Theory:
- Open Sets = module boundaries (folder dengan index.ts/public-api.ts)
- Sections = exported types/interfaces/contracts
- Restriction Maps = cross-boundary imports
- H^1 obstructions = kegagalan gluing local sections menjadi global consistency

Output bersifat informational dan tidak memberikan rekomendasi perubahan.
"""

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

SCHEMA_VERSION = "2.1.0-sheaf"

SOURCE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
BARREL_FILENAMES = ("index.ts", "index.tsx", "index.js", "index.jsx", "public-api.ts", "barrel.ts")

DEFAULT_IGNORE_DIRS = {
    "node_modules", ".git", "dist", ".angular",
    ".Jules", "coverage", ".next", "out",
    "fixtures_min"
}

ENTRYPOINT_BASENAMES = {
    "main.ts", "main.js",
    "main.server.ts", "main.server.js",
    "server.ts", "server.js",
    "entry.client.ts", "entry.client.js",
    "entry.server.ts", "entry.server.js",
    "bootstrap.ts", "bootstrap.js",
    "index.ts", "index.js",  # entry bundle root
}


def _is_entrypoint_file(file_path: str) -> bool:
    """Cek apakah file adalah bootstrap/entrypoint yang sah merakit aplikasi."""
    base = os.path.basename(file_path)
    return base in ENTRYPOINT_BASENAMES


def _import_direction(src_boundary: str, tgt_boundary: str) -> str:
    """
    Tentukan arah import antar boundary.

    - downward : source adalah ancestor dari target (parent -> child)
    - upward   : source adalah descendant dari target (child -> parent)
    - sibling  : source dan target berada di level yang sama
    """
    src = _normalize_path(src_boundary)
    tgt = _normalize_path(tgt_boundary)

    if tgt.startswith(src + "/"):
        return "downward"
    if src.startswith(tgt + "/"):
        return "upward"
    return "sibling"

IMPORT_REGEX = re.compile(
    r"import\s+(?:\{([^}]*)\}\s+from\s+)?(?:\*\s+as\s+\w+\s+from\s+)?"
    r"[\"']([^\"']+)[\"']",
    re.MULTILINE
)

EXPORT_NAMED_REGEX = re.compile(
    r"export\s+(?:\{([^}]*)\}|interface\s+(\w+)|type\s+(\w+)\s*=|"
    r"class\s+(\w+)|function\s+(\w+)|const\s+(\w+)|enum\s+(\w+))"
)

EXPORT_FROM_REGEX = re.compile(
    r"export\s+\{([^}]*)\}\s+from\s+[\"']([^\"']+)[\"']"
)

EXPORT_STAR_REGEX = re.compile(
    r"export\s+\*\s+from\s+[\"']([^\"']+)[\"']"
)

INTERFACE_PROPS_REGEX = re.compile(
    r"(?:export\s+)?interface\s+(\w+)[^{]*\{([^}]*)\}",
    re.DOTALL
)

TYPE_ALIAS_PROPS_REGEX = re.compile(
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


def _is_barrel_file(filename: str) -> bool:
    return filename in BARREL_FILENAMES


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


def _extract_exported_names(content: str) -> Set[str]:
    """Ekstrak semua nama yang di-export dari sebuah file."""
    names: Set[str] = set()
    content = _strip_comments(content)

    # export { A, B as C }
    for match in re.finditer(r"export\s+\{([^}]*)\}", content):
        for item in match.group(1).split(","):
            item = item.strip()
            if " as " in item:
                names.add(item.split(" as ")[-1].strip())
            elif item:
                names.add(item.strip())

    # export { A, B } from './...'
    for match in EXPORT_FROM_REGEX.finditer(content):
        for item in match.group(1).split(","):
            item = item.strip()
            if " as " in item:
                names.add(item.split(" as ")[-1].strip())
            elif item:
                names.add(item.strip())

    # export interface/type/class/function/const/enum
    for match in EXPORT_NAMED_REGEX.finditer(content):
        for g in range(2, 8):
            if match.group(g):
                names.add(match.group(g))

    # export default
    if re.search(r"export\s+default", content):
        names.add("default")

    return names


def _extract_imported_symbols(content: str) -> List[Dict[str, Any]]:
    """Ekstrak semua import statements dengan simbol dan path target."""
    imports: List[Dict[str, Any]] = []
    content = _strip_comments(content)

    for match in IMPORT_REGEX.finditer(content):
        symbols_str = match.group(1)
        import_path = match.group(2)

        symbols: List[str] = []
        if symbols_str:
            for sym in symbols_str.split(","):
                sym = sym.strip()
                if " as " in sym:
                    sym = sym.split(" as ")[0].strip()
                if sym:
                    symbols.append(sym)

        imports.append({
            "symbols": symbols,
            "path": import_path,
            "is_relative": import_path.startswith("."),
        })

    return imports


def _resolve_import_target(base_file: str, import_path: str) -> str:
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


def _find_target_boundary(resolved: str, file_to_boundary: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """Resolve resolved path (bisa extensionless) ke (actual_file_path, boundary_path)."""
    if resolved in file_to_boundary:
        return resolved, file_to_boundary[resolved]
    for ext in SOURCE_EXTENSIONS:
        candidate = resolved + ext
        if candidate in file_to_boundary:
            return candidate, file_to_boundary[candidate]
    return None, None


def _extract_type_shapes(content: str) -> Dict[str, Set[str]]:
    """Ekstrak nama type/interface dan himpunan property names."""
    shapes: Dict[str, Set[str]] = {}
    content = _strip_comments(content)

    for regex in (INTERFACE_PROPS_REGEX, TYPE_ALIAS_PROPS_REGEX):
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


# ============================================================
# Boundary Detection
# ============================================================

def detect_boundaries(
    scan_root: str,
    ignore_dirs: Optional[Set[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Identifikasi module boundaries.

    Boundary = folder yang memiliki barrel file (index.ts, public-api.ts, dll).
    Fallback: top-level folder di bawah scan_root jika tidak ada barrel.

    Returns:
    - dict: boundary_path -> { barrel: str|None, files: [str] }
    """
    if ignore_dirs is None:
        ignore_dirs = set(DEFAULT_IGNORE_DIRS)

    scan_root_norm = _normalize_path(scan_root)
    all_files: List[str] = []

    for root, dirs, files in os.walk(scan_root):
        dirs[:] = sorted(
            [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
        )
        for f in sorted(files):
            if _is_source_file(f):
                all_files.append(_normalize_path(os.path.join(root, f)))

    # Identifikasi folder yang punya barrel
    barrel_folders: Dict[str, str] = {}  # folder_path -> barrel_file_path
    for fp in all_files:
        dirname = os.path.dirname(fp)
        basename = os.path.basename(fp)
        if _is_barrel_file(basename):
            barrel_folders[dirname] = fp

    # Assign setiap file ke boundary terdekat
    boundaries: Dict[str, Dict[str, Any]] = {}

    for fp in all_files:
        # Cari ancestor folder terdekat yang punya barrel
        current = os.path.dirname(fp)
        assigned_boundary = None

        while current and current.startswith(scan_root_norm):
            if current in barrel_folders:
                assigned_boundary = current
                break
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

        # Fallback: top-level folder di bawah scan_root
        if assigned_boundary is None:
            rel = os.path.relpath(fp, scan_root_norm)
            top_folder = rel.split("/")[0] if "/" in rel else ""
            if top_folder:
                assigned_boundary = _normalize_path(
                    os.path.join(scan_root_norm, top_folder)
                )
            else:
                assigned_boundary = scan_root_norm

        if assigned_boundary not in boundaries:
            boundaries[assigned_boundary] = {
                "barrel": barrel_folders.get(assigned_boundary),
                "files": [],
                "exported_names": set(),
                "type_shapes": {},
            }

        boundaries[assigned_boundary]["files"].append(fp)

    # Ekstrak export names dan type shapes per boundary
    for bpath, bdata in boundaries.items():
        for fp in bdata["files"]:
            content = _read_file(fp)
            if content is None:
                continue

            exported = _extract_exported_names(content)
            bdata["exported_names"].update(exported)

            shapes = _extract_type_shapes(content)
            for tname, tprops in shapes.items():
                if tname not in bdata["type_shapes"]:
                    bdata["type_shapes"][tname] = {
                        "properties": tprops,
                        "file": fp,
                    }

    return boundaries


# ============================================================
# Obstruction Detectors
# ============================================================

def detect_boundary_violations(
    boundaries: Dict[str, Dict[str, Any]],
    file_to_boundary: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    H^1 Obstruction: Encapsulation Leak (versi presisi).

    Perilaku:
    - Jika boundary target TIDAK punya barrel, import tidak dianggap violation.
      Boundary tersebut dikumpulkan untuk observasi 'boundary_without_public_api'.
    - Entrypoint files dikecualikan sebagai sumber violation.
    - Setiap violation disertai arah import (downward/upward/sibling).

    Returns:
    - violations: List[Dict]
    - boundaries_without_public_api: List[Dict]
    """
    violations: List[Dict[str, Any]] = []
    no_public_api_set: Set[str] = set()

    for src_boundary, bdata in boundaries.items():
        barrel_of_src = bdata.get("barrel")

        for fp in bdata["files"]:
            if fp == barrel_of_src:
                continue

            content = _read_file(fp)
            if content is None:
                continue

            imports = _extract_imported_symbols(content)

            for imp in imports:
                if not imp["is_relative"]:
                    continue

                resolved = _resolve_import_target(fp, imp["path"])
                actual_target, tgt_boundary = _find_target_boundary(resolved, file_to_boundary)

                if tgt_boundary is None or tgt_boundary == src_boundary:
                    continue

                tgt_barrel = boundaries[tgt_boundary].get("barrel")

                # Jika boundary target tidak punya barrel, tidak ada kontrak
                # enkapsulasi yang bisa dilanggar. Catat sebagai observasi.
                if not tgt_barrel:
                    no_public_api_set.add(tgt_boundary)
                    continue

                # Entrypoint files bebas merakit aplikasi lintas boundary (tidak memicu violation)
                if _is_entrypoint_file(fp):
                    continue

                # Cek apakah import lewat barrel atau bypass
                barrel_no_ext = os.path.splitext(tgt_barrel)[0]
                target_to_check = actual_target or resolved
                is_via_barrel = (
                    target_to_check == tgt_barrel
                    or target_to_check == barrel_no_ext
                    or resolved == tgt_barrel
                    or resolved == barrel_no_ext
                    or resolved == tgt_boundary
                )

                direction = _import_direction(src_boundary, tgt_boundary)

                if not is_via_barrel:
                    violations.append({
                        "type": "boundary_violation",
                        "severity": "high",
                        "source_file": fp,
                        "source_boundary": src_boundary,
                        "target_file": actual_target or resolved,
                        "target_boundary": tgt_boundary,
                        "target_barrel": tgt_barrel,
                        "import_path": imp["path"],
                        "symbols": imp["symbols"],
                        "direction": direction,
                        "observation": (
                            f"Import from '{src_boundary}' bypasses barrel of "
                            f"'{tgt_boundary}' ({direction}) — accesses internal "
                            f"file '{actual_target or resolved}' directly."
                        ),
                        "invariant": "H1_encapsulation_leak",
                    })

    violations.sort(
        key=lambda f: (f["source_boundary"], f["source_file"], f["target_file"])
    )

    # Konsolidasi boundary tanpa public API menjadi satu observasi per boundary
    no_public_api_findings: List[Dict[str, Any]] = []
    for bpath in sorted(no_public_api_set):
        no_public_api_findings.append({
            "type": "boundary_without_public_api",
            "severity": "low",
            "boundary": bpath,
            "observation": (
                f"Boundary '{bpath}' is imported across boundaries but has no "
                f"barrel file (index.ts / public-api.ts). No explicit public "
                f"API surface is declared — cross-boundary access is uncontrolled."
            ),
            "invariant": "H0_missing_public_api",
        })

    return violations, no_public_api_findings


def detect_circular_boundaries(
    boundaries: Dict[str, Dict[str, Any]],
    file_to_boundary: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    H^1 Obstruction: Circular Boundary Dependency.

    Siklus dependensi pada level boundary (bukan file-level).
    """
    # Bangun boundary-level dependency graph
    boundary_graph: Dict[str, Set[str]] = {}

    for src_boundary, bdata in boundaries.items():
        if src_boundary not in boundary_graph:
            boundary_graph[src_boundary] = set()

        barrel_of_src = bdata.get("barrel")

        for fp in bdata["files"]:
            if fp == barrel_of_src:
                continue

            content = _read_file(fp)
            if content is None:
                continue

            imports = _extract_imported_symbols(content)

            for imp in imports:
                if not imp["is_relative"]:
                    continue

                resolved = _resolve_import_target(fp, imp["path"])
                _, tgt_boundary = _find_target_boundary(resolved, file_to_boundary)

                if tgt_boundary and tgt_boundary != src_boundary:
                    boundary_graph[src_boundary].add(tgt_boundary)

    # Deteksi cycle menggunakan DFS
    findings: List[Dict[str, Any]] = []
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    cycles_found: List[List[str]] = []

    def dfs(node: str, path: List[str]) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in sorted(boundary_graph.get(node, set())):
            if neighbor not in visited:
                dfs(neighbor, path)
            elif neighbor in rec_stack:
                # Cycle detected
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles_found.append(cycle)

        path.pop()
        rec_stack.discard(node)

    for node in sorted(boundary_graph.keys()):
        if node not in visited:
            dfs(node, [])

    # Deduplicate cycles (normalize rotation)
    seen_cycles: Set[str] = set()
    for cycle in cycles_found:
        # Normalize: mulai dari node terkecil secara leksikografis
        min_idx = cycle.index(min(cycle[:-1]))
        normalized = cycle[min_idx:] + cycle[1:min_idx + 1]
        cycle_key = " -> ".join(normalized)

        if cycle_key not in seen_cycles:
            seen_cycles.add(cycle_key)
            findings.append({
                "type": "circular_boundary",
                "severity": "high",
                "cycle": normalized,
                "cycle_length": len(normalized) - 1,
                "observation": (
                    f"Circular dependency detected across {len(normalized) - 1} "
                    f"module boundaries: {cycle_key}"
                ),
                "invariant": "H1_coboundary_cycle",
            })

    findings.sort(key=lambda f: f["cycle_length"])
    return findings


def detect_section_conflicts(
    boundaries: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    H^0 Obstruction: Section Conflict.

    Type dengan nama yang sama didefinisikan di boundary berbeda
    dengan himpunan properti yang berbeda (tidak isomorfik).
    """
    findings: List[Dict[str, Any]] = []

    # Kumpulkan semua type shapes per nama lintas boundary
    type_registry: Dict[str, List[Dict[str, Any]]] = {}

    for bpath, bdata in boundaries.items():
        for tname, tinfo in bdata.get("type_shapes", {}).items():
            if tname not in type_registry:
                type_registry[tname] = []
            type_registry[tname].append({
                "boundary": bpath,
                "file": tinfo["file"],
                "properties": tinfo["properties"],
            })

    # Cek konflik: nama sama, shape berbeda
    for tname, entries in sorted(type_registry.items()):
        if len(entries) < 2:
            continue

        # Bandingkan semua pasangan
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                props_i = entries[i]["properties"]
                props_j = entries[j]["properties"]

                if props_i != props_j:
                    only_in_i = props_i - props_j
                    only_in_j = props_j - props_i

                    findings.append({
                        "type": "section_conflict",
                        "severity": "medium",
                        "type_name": tname,
                        "boundary_a": entries[i]["boundary"],
                        "file_a": entries[i]["file"],
                        "boundary_b": entries[j]["boundary"],
                        "file_b": entries[j]["file"],
                        "properties_a": sorted(props_i),
                        "properties_b": sorted(props_j),
                        "properties_only_in_a": sorted(only_in_i),
                        "properties_only_in_b": sorted(only_in_j),
                        "observation": (
                            f"Type '{tname}' defined in '{entries[i]['boundary']}' and "
                            f"'{entries[j]['boundary']}' with different property sets. "
                            f"Local sections cannot be glued into a consistent global section."
                        ),
                        "invariant": "H0_section_conflict",
                    })

    findings.sort(key=lambda f: (f["type_name"], f["boundary_a"], f["boundary_b"]))
    return findings


def detect_missing_barrel_exports(
    boundaries: Dict[str, Dict[str, Any]],
    file_to_boundary: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    H^1 Obstruction: Missing Restriction.

    Simbol diimpor dari luar boundary, tetapi tidak ada di
    export surface barrel boundary target.
    """
    findings: List[Dict[str, Any]] = []

    for src_boundary, bdata in boundaries.items():
        barrel_of_src = bdata.get("barrel")

        for fp in bdata["files"]:
            if fp == barrel_of_src:
                continue

            content = _read_file(fp)
            if content is None:
                continue

            imports = _extract_imported_symbols(content)

            for imp in imports:
                if not imp["is_relative"] or not imp["symbols"]:
                    continue

                resolved = _resolve_import_target(fp, imp["path"])
                actual_target, tgt_boundary = _find_target_boundary(resolved, file_to_boundary)

                if tgt_boundary is None or tgt_boundary == src_boundary:
                    continue

                tgt_barrel = boundaries[tgt_boundary].get("barrel")
                if not tgt_barrel:
                    continue

                # Cek apakah import via barrel
                barrel_no_ext = os.path.splitext(tgt_barrel)[0]
                target_to_check = actual_target or resolved
                is_via_barrel = (
                    target_to_check == tgt_barrel
                    or target_to_check == barrel_no_ext
                    or resolved == tgt_barrel
                    or resolved == barrel_no_ext
                    or resolved == tgt_boundary
                )

                if not is_via_barrel:
                    continue  # Sudah ditangani boundary_violation

                # Import via barrel: cek apakah simbol ada di export barrel
                barrel_content = _read_file(tgt_barrel)
                if barrel_content is None:
                    continue

                barrel_exports = _extract_exported_names(barrel_content)

                for sym in imp["symbols"]:
                    if sym and sym not in barrel_exports and sym != "default":
                        findings.append({
                            "type": "missing_barrel_export",
                            "severity": "medium",
                            "source_file": fp,
                            "source_boundary": src_boundary,
                            "target_boundary": tgt_boundary,
                            "barrel_file": tgt_barrel,
                            "missing_symbol": sym,
                            "import_path": imp["path"],
                            "observation": (
                                f"Symbol '{sym}' imported from '{tgt_boundary}' via barrel, "
                                f"but not found in barrel's export surface. "
                                f"Restriction map is incomplete."
                            ),
                            "invariant": "H1_missing_restriction",
                        })

    findings.sort(key=lambda f: (f["source_boundary"], f["missing_symbol"]))
    return findings


# ============================================================
# Main Orchestrator
# ============================================================

def analyze_boundaries(
    scan_root: str = ".",
    ignore_dirs: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Orkestrasi penuh Sheaf Cohomology Observer.

    1. Deteksi boundaries
    2. Bangun file-to-boundary mapping
    3. Jalankan semua obstruction detector
    4. Susun output deterministik
    """
    if ignore_dirs is None:
        ignore_dirs = set(DEFAULT_IGNORE_DIRS)

    scan_root_norm = _normalize_path(scan_root)

    # Step 1: Detect boundaries
    boundaries = detect_boundaries(scan_root_norm, ignore_dirs)

    # Step 2: Build file-to-boundary mapping
    file_to_boundary: Dict[str, str] = {}
    for bpath, bdata in boundaries.items():
        for fp in bdata["files"]:
            file_to_boundary[fp] = bpath

    # Step 3: Run obstruction detectors
    all_findings: List[Dict[str, Any]] = []

    violations, no_public_api = detect_boundary_violations(
        boundaries, file_to_boundary
    )
    all_findings.extend(violations)
    all_findings.extend(no_public_api)

    all_findings.extend(
        detect_circular_boundaries(boundaries, file_to_boundary)
    )
    all_findings.extend(
        detect_section_conflicts(boundaries)
    )
    all_findings.extend(
        detect_missing_barrel_exports(boundaries, file_to_boundary)
    )

    # Sort deterministik
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_findings.sort(
        key=lambda f: (
            severity_order.get(f.get("severity", "low"), 3),
            f.get("type", ""),
            f.get("source_file", f.get("boundary", f.get("boundary_a", ""))),
        )
    )

    # Step 4: Build boundary summary (tanpa set agar JSON-serializable)
    boundary_summary: List[Dict[str, Any]] = []
    for bpath in sorted(boundaries.keys()):
        bdata = boundaries[bpath]
        boundary_summary.append({
            "path": bpath,
            "barrel": bdata.get("barrel"),
            "file_count": len(bdata["files"]),
            "exported_name_count": len(bdata.get("exported_names", set())),
            "type_shape_count": len(bdata.get("type_shapes", {})),
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "scan_root": scan_root_norm,
        "boundaries": boundary_summary,
        "obstructions": all_findings,
        "summary": {
            "total_boundaries": len(boundaries),
            "total_files_assigned": len(file_to_boundary),
            "total_obstructions": len(all_findings),
            "by_type": {
                "boundary_violation": sum(
                    1 for f in all_findings if f["type"] == "boundary_violation"
                ),
                "boundary_without_public_api": sum(
                    1 for f in all_findings if f["type"] == "boundary_without_public_api"
                ),
                "circular_boundary": sum(
                    1 for f in all_findings if f["type"] == "circular_boundary"
                ),
                "section_conflict": sum(
                    1 for f in all_findings if f["type"] == "section_conflict"
                ),
                "missing_barrel_export": sum(
                    1 for f in all_findings if f["type"] == "missing_barrel_export"
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

    print(json.dumps(analyze_boundaries(root), indent=2))
