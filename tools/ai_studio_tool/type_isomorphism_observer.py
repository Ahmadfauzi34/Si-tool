"""
Type Isomorphism Observer (Proto-HoTT Stage 1)
Schema Version: 2.0.0-hott

Mengobservasi isomorfisme struktural antar type/interface TypeScript.

Konsep HoTT yang diaproksimasi:
- Types as Spaces: setiap interface/type adalah ruang struktural
- Structural Bijection: dua ruang dianggap isomorfik jika properti
  dan tipe propertinya ekuivalen secara bijektif
- Univalence Approximation: A ≅ B diobservasi sebagai kesetaraan struktural

Output bersifat informational dan tidak memberikan rekomendasi perubahan.
"""

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

SCHEMA_VERSION = "2.0.0-hott"

SOURCE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")

DEFAULT_IGNORE_DIRS = {
    "node_modules", ".git", "dist", ".angular",
    ".Jules", "coverage", ".next", "out",
    "fixtures_min"
}

# Regex untuk menangkap interface dan type alias sederhana
INTERFACE_REGEX = re.compile(
    r"(?:export\s+)?(?:declare\s+)?(?:abstract\s+)?interface\s+"
    r"([A-Za-z0-9_$]+)"
    r"(?:\s+extends\s+[^{]+)?"
    r"\s*\{([^}]*)\}",
    re.DOTALL
)

TYPE_ALIAS_REGEX = re.compile(
    r"(?:export\s+)?(?:declare\s+)?type\s+"
    r"([A-Za-z0-9_$]+)\s*=\s*\{([^}]*)\}",
    re.DOTALL
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


def _normalize_type(type_str: str) -> str:
    """
    Normalisasi string tipe untuk perbandingan struktural.

    Aturan normalisasi:
    - hapus whitespace berlebih
    - literal string -> string
    - literal number -> number
    - literal boolean -> boolean
    - uraikan union dengan null/undefined menjadi sorted union
    - T[] dan Array<T> dianggap ekuivalen
    """
    t = type_str.strip()

    # Hapus whitespace berlebih
    t = re.sub(r"\s+", " ", t)

    # Hapus trailing semicolon/comma
    t = t.rstrip(";,")

    # Array<T> -> T[]
    array_generic = re.match(r"^Array<(.+)>$", t)
    if array_generic:
        inner = _normalize_type(array_generic.group(1))
        return f"{inner}[]"

    # T[] -> normalize inner
    if t.endswith("[]"):
        inner = _normalize_type(t[:-2])
        return f"{inner}[]"

    # Literal string: 'abc' atau "abc"
    if re.match(r"^['\"].*['\"]$", t):
        return "string"

    # Literal number
    if re.match(r"^-?\d+(\.\d+)?$", t):
        return "number"

    # Literal boolean
    if t in ("true", "false"):
        return "boolean"

    # Union types: urutkan untuk perbandingan deterministik
    if "|" in t:
        parts = [_normalize_type(p.strip()) for p in t.split("|")]
        parts = sorted(set(parts))
        return " | ".join(parts)

    return t


def _split_properties(body: str) -> List[str]:
    """
    Pecah body interface/type menjadi daftar properti,
    dengan menghormati nesting curly braces.
    """
    segments: List[str] = []
    current = ""
    depth = 0

    for char in body:
        if char == "{":
            depth += 1
            current += char
        elif char == "}":
            depth -= 1
            current += char
        elif char in (";", ",") and depth == 0:
            if current.strip():
                segments.append(current.strip())
            current = ""
        else:
            current += char

    if current.strip():
        segments.append(current.strip())

    return segments


def _extract_properties(body: str) -> List[Dict[str, Any]]:
    """
    Ekstrak properti dari body interface/type.

    Setiap properti memiliki:
    - name
    - type (normalized)
    - optional (boolean)
    - readonly (boolean)
    """
    properties: List[Dict[str, Any]] = []

    segments = _split_properties(body)

    prop_regex = re.compile(
        r"^(readonly\s+)?"
        r"([A-Za-z0-9_$]+)"
        r"(\?)?"
        r"\s*:\s*(.+)$"
    )

    for segment in segments:
        segment = segment.strip()

        if not segment:
            continue

        # Lewati index signature seperti [key: string]: T
        if segment.startswith("["):
            continue

        match = prop_regex.match(segment)
        if match:
            readonly = bool(match.group(1))
            name = match.group(2)
            optional = bool(match.group(3))
            type_raw = match.group(4).strip()

            properties.append({
                "name": name,
                "type": _normalize_type(type_raw),
                "optional": optional,
                "readonly": readonly,
            })

    # Deterministik: urutkan berdasarkan nama properti
    properties.sort(key=lambda p: p["name"])

    return properties


def extract_type_shapes(file_path: str) -> Dict[str, Any]:
    """
    Ekstrak semua interface dan type alias sederhana dari satu file.

    Output:
    - file
    - shapes: daftar type spaces dengan properti masing-masing
    """
    path_norm = _normalize_path(file_path)

    result = {
        "schema_version": SCHEMA_VERSION,
        "file": path_norm,
        "exists": False,
        "error": None,
        "shapes": [],
        "shape_count": 0,
    }

    if not os.path.isfile(path_norm):
        result["error"] = "file_not_found"
        return result

    try:
        with open(path_norm, "r", encoding="utf-8", errors="ignore") as f:
            raw_content = f.read()
    except Exception as exc:
        result["error"] = f"read_error: {exc}"
        return result

    result["exists"] = True

    content = _strip_comments(raw_content)

    shapes: List[Dict[str, Any]] = []
    seen_names: Set[Tuple[str, int]] = set()

    # Ekstrak interface
    for match in INTERFACE_REGEX.finditer(content):
        name = match.group(1)
        body = match.group(2)
        line_no = content[:match.start()].count("\n") + 1

        key = (name, line_no)
        if key in seen_names:
            continue
        seen_names.add(key)

        properties = _extract_properties(body)

        shapes.append({
            "name": name,
            "kind": "interface",
            "line": line_no,
            "properties": properties,
            "property_count": len(properties),
        })

    # Ekstrak type alias object
    for match in TYPE_ALIAS_REGEX.finditer(content):
        name = match.group(1)
        body = match.group(2)
        line_no = content[:match.start()].count("\n") + 1

        key = (name, line_no)
        if key in seen_names:
            continue
        seen_names.add(key)

        properties = _extract_properties(body)

        shapes.append({
            "name": name,
            "kind": "type_alias",
            "line": line_no,
            "properties": properties,
            "property_count": len(properties),
        })

    # Deterministik
    shapes.sort(key=lambda s: (s["name"], s["line"]))

    result["shapes"] = shapes
    result["shape_count"] = len(shapes)

    return result


def _shape_signature_key(shape: Dict[str, Any]) -> str:
    """
    Signature utama untuk perbandingan isomorfisme:
    himpunan (nama_properti, tipe_normalisasi, optional).
    """
    parts = []
    for prop in shape.get("properties", []):
        parts.append(f"{prop['name']}:{prop['type']}:{'opt' if prop['optional'] else 'req'}")
    return "|".join(sorted(parts))


def _shape_extended_key(shape: Dict[str, Any]) -> str:
    """
    Signature lebih ketat: termasuk array bracket dan readonly.
    Dipakai untuk confidence tinggi.
    """
    parts = []
    for prop in shape.get("properties", []):
        ro = "ro" if prop.get("readonly") else "mut"
        parts.append(
            f"{prop['name']}:{prop['type']}:{'opt' if prop['optional'] else 'req'}:{ro}"
        )
    return "|".join(sorted(parts))


def _are_isomorphic(shape_a: Dict[str, Any], shape_b: Dict[str, Any]) -> Tuple[bool, float]:
    """
    Cek apakah dua type spaces isomorfik secara struktural.

    Returns:
    - is_isomorphic: bool
    - confidence: float
    """
    props_a = shape_a.get("properties", [])
    props_b = shape_b.get("properties", [])

    # Ruang kosong tidak dianggap isomorfik (terlalu trivial)
    if not props_a or not props_b:
        return False, 0.0

    # Jumlah properti harus sama
    if len(props_a) != len(props_b):
        return False, 0.0

    sig_a = _shape_signature_key(shape_a)
    sig_b = _shape_signature_key(shape_b)

    if sig_a != sig_b:
        return False, 0.0

    ext_a = _shape_extended_key(shape_a)
    ext_b = _shape_extended_key(shape_b)

    if ext_a == ext_b:
        return True, 0.95

    # Signature utama cocok, tetapi readonly berbeda
    return True, 0.85


def observe_isomorphisms_in_file(file_path: str) -> Dict[str, Any]:
    """
    Observasi pasangan type isomorfik di dalam satu file.
    """
    shape_result = extract_type_shapes(file_path)

    findings: List[Dict[str, Any]] = []

    if not shape_result["exists"]:
        return {
            "schema_version": SCHEMA_VERSION,
            "file": shape_result["file"],
            "exists": False,
            "error": shape_result["error"],
            "isomorphic_pairs": [],
            "summary": {
                "total_shapes": 0,
                "isomorphic_pair_count": 0,
            },
        }

    shapes = shape_result["shapes"]

    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            shape_a = shapes[i]
            shape_b = shapes[j]

            is_iso, confidence = _are_isomorphic(shape_a, shape_b)

            if is_iso:
                findings.append({
                    "file": shape_result["file"],
                    "type": "structural_isomorphism",
                    "space_a": {
                        "name": shape_a["name"],
                        "kind": shape_a["kind"],
                        "line": shape_a["line"],
                        "property_count": shape_a["property_count"],
                    },
                    "space_b": {
                        "name": shape_b["name"],
                        "kind": shape_b["kind"],
                        "line": shape_b["line"],
                        "property_count": shape_b["property_count"],
                    },
                    "isomorphism_confidence": confidence,
                    "observation": (
                        f"Type spaces '{shape_a['name']}' and '{shape_b['name']}' "
                        f"are structurally isomorphic ({shape_a['property_count']} properties)."
                    ),
                    "invariant": "univalence_candidate",
                })

    # Deterministik
    findings.sort(
        key=lambda f: (
            f["space_a"]["name"],
            f["space_a"]["line"],
            f["space_b"]["name"],
            f["space_b"]["line"],
        )
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "file": shape_result["file"],
        "exists": True,
        "error": None,
        "isomorphic_pairs": findings,
        "summary": {
            "total_shapes": len(shapes),
            "isomorphic_pair_count": len(findings),
        },
    }


def scan_directory_for_isomorphisms(
    path: str = ".",
    ignore_dirs: Optional[set] = None,
) -> Dict[str, Any]:
    """
    Observasi pasangan type isomorfik lintas file dalam satu direktori.
    """
    if ignore_dirs is None:
        ignore_dirs = set(DEFAULT_IGNORE_DIRS)

    all_shapes: List[Dict[str, Any]] = []
    files_scanned = 0

    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(
            [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
        )

        for file in sorted(files):
            if not _is_source_file(file):
                continue

            full_path = _normalize_path(os.path.join(root, file))
            shape_result = extract_type_shapes(full_path)

            if not shape_result["exists"]:
                continue

            files_scanned += 1

            for shape in shape_result["shapes"]:
                all_shapes.append({
                    "file": full_path,
                    "name": shape["name"],
                    "kind": shape["kind"],
                    "line": shape["line"],
                    "properties": shape["properties"],
                    "property_count": shape["property_count"],
                })

    # Observasi pasangan lintas file
    findings: List[Dict[str, Any]] = []

    for i in range(len(all_shapes)):
        for j in range(i + 1, len(all_shapes)):
            shape_a = all_shapes[i]
            shape_b = all_shapes[j]

            # Hindari membandingkan dua shape dari file dan line yang sama
            if shape_a["file"] == shape_b["file"] and shape_a["line"] == shape_b["line"]:
                continue

            is_iso, confidence = _are_isomorphic(shape_a, shape_b)

            if is_iso:
                findings.append({
                    "file": shape_a["file"],
                    "file_b": shape_b["file"],
                    "type": "structural_isomorphism",
                    "scope": "cross_file",
                    "space_a": {
                        "name": shape_a["name"],
                        "kind": shape_a["kind"],
                        "line": shape_a["line"],
                        "property_count": shape_a["property_count"],
                        "file": shape_a["file"],
                    },
                    "space_b": {
                        "name": shape_b["name"],
                        "kind": shape_b["kind"],
                        "line": shape_b["line"],
                        "property_count": shape_b["property_count"],
                        "file": shape_b["file"],
                    },
                    "isomorphism_confidence": confidence,
                    "observation": (
                        f"Type spaces '{shape_a['name']}' ({shape_a['file']}) and "
                        f"'{shape_b['name']}' ({shape_b['file']}) are structurally "
                        f"isomorphic ({shape_a['property_count']} properties)."
                    ),
                    "invariant": "univalence_candidate",
                })

    # Deterministik
    findings.sort(
        key=lambda f: (
            f["space_a"]["file"],
            f["space_a"]["name"],
            f["space_a"]["line"],
            f["space_b"]["file"],
            f["space_b"]["name"],
            f["space_b"]["line"],
        )
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "scan_root": _normalize_path(path),
        "files_scanned": files_scanned,
        "total_shapes": len(all_shapes),
        "total_isomorphic_pairs": len(findings),
        "isomorphic_pairs": findings,
        "summary": {
            "files_scanned": files_scanned,
            "total_shapes": len(all_shapes),
            "isomorphic_pair_count": len(findings),
            "high_confidence_pairs": sum(
                1 for f in findings if f["isomorphism_confidence"] >= 0.95
            ),
            "medium_confidence_pairs": sum(
                1 for f in findings if 0.85 <= f["isomorphism_confidence"] < 0.95
            ),
        },
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        root = sys.argv[2] if len(sys.argv) > 2 else "."
        print(json.dumps(scan_directory_for_isomorphisms(root), indent=2))
    elif len(sys.argv) > 1:
        file_p = sys.argv[1]
        print(json.dumps(observe_isomorphisms_in_file(file_p), indent=2))
    else:
        print(json.dumps({
            "tool": "type_isomorphism_observer",
            "schema_version": SCHEMA_VERSION,
            "usage": {
                "observe_file": "python3 type_isomorphism_observer.py <file_path>",
                "scan_directory": "python3 type_isomorphism_observer.py scan [root_path]"
            }
        }, indent=2))
