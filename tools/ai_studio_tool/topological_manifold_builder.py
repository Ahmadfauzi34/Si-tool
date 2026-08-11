"""
Topological Manifold Builder (Proto-HoTT Stage 5)
Schema Version: 2.4.0-manifold

Membangun topological manifold dari dependency graph dan menghitung:
- Betti numbers (β₀: components, β₁: cycles, β₂: voids)
- Persistence diagram (fitur topologis lintas skala)
- Topological invariant vector (fingerprint untuk decoder steering)

Konsep:
- Vertex (0-simplex) = file
- Edge (1-simplex) = import
- Triangle (2-simplex) = dependency cycle tertutup
- Betti numbers = jumlah "lubang" di setiap dimensi

Output bersifat informational dan tidak memberikan rekomendasi perubahan.
"""

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

SCHEMA_VERSION = "2.4.0-manifold"

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


# ============================================================
# Graph Construction
# ============================================================

def build_graph(
    scan_root: str,
    ignore_dirs: Optional[Set[str]] = None,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Bangun graph: vertices (files) dan edges (imports)."""
    if ignore_dirs is None:
        ignore_dirs = set(DEFAULT_IGNORE_DIRS)

    all_files: Set[str] = set()
    file_imports: Dict[str, List[str]] = {}

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
            file_imports[full_path] = IMPORT_REGEX.findall(content)

    vertices = sorted(all_files)
    edges: List[Tuple[str, str]] = []

    for src, raw_imports in file_imports.items():
        for raw in raw_imports:
            if not raw.startswith("."):
                continue
            resolved_base = _resolve_import_path(src, raw)
            for cand in _candidate_targets(resolved_base):
                if cand in all_files and cand != src:
                    edges.append((src, cand))
                    break

    edges = sorted(set(edges))
    return vertices, edges


# ============================================================
# Topological Computation
# ============================================================

class UnionFind:
    """Union-Find untuk melacak connected components."""

    def __init__(self, items: List[str]):
        self.parent = {x: x for x in items}
        self.rank = {x: 0 for x in items}

    def find(self, x: str) -> str:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: str, y: str) -> bool:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1
        return True


def compute_betti_numbers(
    vertices: List[str],
    edges: List[Tuple[str, str]],
) -> Dict[str, int]:
    """
    Hitung Betti numbers.

    β₀ = jumlah connected components
    β₁ = jumlah independent cycles (cyclomatic number)
         = E - V + β₀
    β₂ = jumlah enclosed voids (dari triangles)
    """
    if not vertices:
        return {"beta_0": 0, "beta_1": 0, "beta_2": 0, "total_cycles": 0}

    # β₀ via union-find
    uf = UnionFind(vertices)
    for src, tgt in edges:
        uf.union(src, tgt)

    components = len(set(uf.find(v) for v in vertices))
    beta_0 = components

    # β₁ = cyclomatic number = E - V + β₀
    beta_1 = len(edges) - len(vertices) + beta_0
    beta_1 = max(0, beta_1)

    # β₂ via triangles (2-simplices)
    triangles = _find_triangles(edges)
    beta_2 = _count_enclosed_voids(vertices, edges, triangles)

    return {
        "beta_0": beta_0,
        "beta_1": beta_1,
        "beta_2": beta_2,
        "total_cycles": beta_1,
    }


def _find_triangles(edges: List[Tuple[str, str]]) -> List[Tuple[str, str, str]]:
    """Deteksi triangles (2-simplices) dalam graph."""
    adjacency: Dict[str, Set[str]] = {}
    for src, tgt in edges:
        adjacency.setdefault(src, set()).add(tgt)
        adjacency.setdefault(tgt, set()).add(src)

    triangles: Set[Tuple[str, str, str]] = set()
    for src, tgt in edges:
        common = adjacency.get(src, set()) & adjacency.get(tgt, set())
        for third in common:
            triangle = tuple(sorted([src, tgt, third]))
            triangles.add(triangle)

    return sorted(triangles)


def _count_enclosed_voids(
    vertices: List[str],
    edges: List[Tuple[str, str]],
    triangles: List[Tuple[str, str, str]],
) -> int:
    """
    Hitung enclosed voids (β₂) menggunakan rank boundary matrix.
    β₂ = dim(ker ∂₂) - dim(im ∂₃)
    """
    if not triangles:
        return 0

    edge_index = {e: i for i, e in enumerate(sorted(set(edges)))}
    n_edges = len(edge_index)
    n_triangles = len(triangles)

    if n_triangles == 0:
        return 0

    boundary_matrix = [[0] * n_triangles for _ in range(n_edges)]

    for j, triangle in enumerate(triangles):
        a, b, c = triangle
        for e in [(a, b), (b, c), (a, c)]:
            e_norm = tuple(sorted(e))
            if e_norm in edge_index:
                boundary_matrix[edge_index[e_norm]][j] = 1

    rank = _rank_mod2(boundary_matrix)
    beta_2 = n_triangles - rank
    return max(0, beta_2)


def _rank_mod2(matrix: List[List[int]]) -> int:
    """Hitung rank matrix atas GF(2) menggunakan Gaussian elimination."""
    if not matrix or not matrix[0]:
        return 0

    m = [row[:] for row in matrix]
    n_rows = len(m)
    n_cols = len(m[0])
    rank = 0

    for col in range(n_cols):
        pivot_row = None
        for row in range(rank, n_rows):
            if m[row][col] == 1:
                pivot_row = row
                break

        if pivot_row is None:
            continue

        m[rank], m[pivot_row] = m[pivot_row], m[rank]

        for row in range(n_rows):
            if row != rank and m[row][col] == 1:
                for c in range(n_cols):
                    m[row][c] ^= m[rank][c]

        rank += 1

    return rank


def compute_persistence_diagram(
    vertices: List[str],
    edges: List[Tuple[str, str]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Hitung persistence diagram melalui filtration.
    """
    if not vertices:
        return {"h0": [], "h1": []}

    uf = UnionFind(vertices)
    h0_diagram: List[Dict[str, Any]] = []
    h1_diagram: List[Dict[str, Any]] = []

    birth_time = {v: 0 for v in vertices}

    for t, (src, tgt) in enumerate(edges):
        if uf.find(src) != uf.find(tgt):
            root_src = uf.find(src)
            root_tgt = uf.find(tgt)

            if birth_time.get(root_src, 0) >= birth_time.get(root_tgt, 0):
                dying = root_src
                surviving = root_tgt
            else:
                dying = root_tgt
                surviving = root_src

            h0_diagram.append({
                "birth": birth_time.get(dying, 0),
                "death": t + 1,
                "persistence": (t + 1) - birth_time.get(dying, 0),
            })

            uf.union(src, tgt)
            new_root = uf.find(src)
            birth_time[new_root] = min(
                birth_time.get(root_src, 0),
                birth_time.get(root_tgt, 0),
            )
        else:
            h1_diagram.append({
                "birth": t + 1,
                "death": float("inf"),
                "persistence": float("inf"),
            })

    final_components = set(uf.find(v) for v in vertices)
    for comp in final_components:
        h0_diagram.append({
            "birth": birth_time.get(comp, 0),
            "death": float("inf"),
            "persistence": float("inf"),
        })

    def _sanitize(diagram):
        result = []
        for point in diagram:
            result.append({
                "birth": point["birth"],
                "death": point["death"] if point["death"] != float("inf") else -1,
                "persistence": point["persistence"] if point["persistence"] != float("inf") else -1,
            })
        return result

    return {
        "h0": _sanitize(h0_diagram),
        "h1": _sanitize(h1_diagram),
    }


def compute_invariant_vector(
    betti: Dict[str, int],
    persistence: Dict[str, List[Dict[str, Any]]],
    vertices: List[str],
    edges: List[Tuple[str, str]],
) -> Dict[str, float]:
    """
    Encode topological invariants menjadi vector fingerprint.
    """
    n_vertices = len(vertices)
    n_edges = len(edges)

    beta_0_norm = betti["beta_0"] / max(1, n_vertices)
    beta_1_norm = betti["beta_1"] / max(1, n_edges)

    h1_finite = [p for p in persistence["h1"] if p["persistence"] != -1]
    h1_persistences = [p["persistence"] for p in h1_finite] if h1_finite else [0]
    h1_mean = sum(h1_persistences) / len(h1_persistences) if h1_persistences else 0.0

    h0_finite = [p for p in persistence["h0"] if p["persistence"] != -1]
    h0_persistences = [p["persistence"] for p in h0_finite] if h0_finite else [0]
    h0_mean = sum(h0_persistences) / len(h0_persistences) if h0_persistences else 0.0

    max_edges = n_vertices * (n_vertices - 1) / 2 if n_vertices > 1 else 1
    density = n_edges / max(1, max_edges)
    avg_degree = (2.0 * n_edges / n_vertices) if n_vertices > 0 else 0.0

    return {
        "beta_0": float(betti["beta_0"]),
        "beta_1": float(betti["beta_1"]),
        "beta_2": float(betti["beta_2"]),
        "beta_0_normalized": round(beta_0_norm, 4),
        "beta_1_normalized": round(beta_1_norm, 4),
        "h0_mean_persistence": round(h0_mean, 4),
        "h1_mean_persistence": round(h1_mean, 4),
        "edge_density": round(density, 4),
        "avg_degree": round(avg_degree, 4),
        "vertex_count": float(n_vertices),
        "edge_count": float(n_edges),
    }


def compute_topological_drift(
    invariant_before: Dict[str, float],
    invariant_after: Dict[str, float],
) -> Dict[str, Any]:
    """
    Hitung topological drift antara dua invariant vectors.
    """
    keys = [
        "beta_0_normalized", "beta_1_normalized",
        "h0_mean_persistence", "h1_mean_persistence",
        "edge_density",
    ]

    distances = {}
    total = 0.0

    for key in keys:
        before = invariant_before.get(key, 0.0)
        after = invariant_after.get(key, 0.0)
        dist = abs(after - before)
        distances[key] = round(dist, 4)
        total += dist

    drift_score = round(total / len(keys), 4) if keys else 0.0

    return {
        "drift_score": drift_score,
        "per_dimension": distances,
        "interpretation": (
            "low" if drift_score < 0.1 else
            "medium" if drift_score < 0.3 else
            "high"
        ),
    }


# ============================================================
# Main Orchestrator
# ============================================================

def build_topological_manifold(
    scan_root: str = ".",
    ignore_dirs: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Orkestrasi penuh Topological Manifold Builder.
    """
    scan_root_norm = _normalize_path(scan_root)

    vertices, edges = build_graph(scan_root_norm, ignore_dirs)
    betti = compute_betti_numbers(vertices, edges)
    persistence = compute_persistence_diagram(vertices, edges)
    invariant_vector = compute_invariant_vector(betti, persistence, vertices, edges)

    return {
        "schema_version": SCHEMA_VERSION,
        "scan_root": scan_root_norm,
        "manifold": {
            "vertex_count": len(vertices),
            "edge_count": len(edges),
            "betti_numbers": betti,
            "persistence_diagram": persistence,
        },
        "invariant_vector": invariant_vector,
        "summary": {
            "connected_components": betti["beta_0"],
            "independent_cycles": betti["beta_1"],
            "enclosed_voids": betti["beta_2"],
            "topological_dimension": 2 if betti["beta_2"] > 0 else 1 if betti["beta_1"] > 0 else 0,
        },
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = "."

    print(json.dumps(build_topological_manifold(root), indent=2))
