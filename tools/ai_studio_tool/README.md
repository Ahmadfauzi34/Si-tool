# README.md — Updated for HoTT Kernel Architecture (3.0.0-kernel)

```markdown
# AI Studio Codebase Harness & HoTT Kernel

Tool Python ini berfungsi sebagai **harness analisis codebase terpadu** untuk AI Studio & LLM Agent (`schema_version: 3.0.0-kernel`). Melalui **satu entry point** (`hott_kernel.py`), tool ini menjalankan **12 analyzer terintegrasi** dalam **1 filesystem scan**, menghasilkan analisis topologi, performa, dan integritas topologis secara menyeluruh (< 50ms overhead).

Arsitektur kernel mengkonsolidasikan seluruh tool terpisah ke dalam **SharedGraph + Analyzer Registry + Synthesizer** pattern, mereduksi 13 tool calls menjadi 1, dan 9 filesystem scans menjadi 1.

---

## 📌 Peran & Invariant Tool

### 1. Peran Utama

| Komponen | Fungsi |
|---|---|
| **SharedGraph Builder** | Membangun dependency graph dalam 1 pass (vertices, edges, boundaries, type shapes, node metadata) |
| **Analyzer Registry** | 12 analyzer terintegrasi (4 topo, 4 perf, 4 hott) yang mengonsumsi SharedGraph |
| **Targeted Queries** | Impact analysis, outline extraction, dan brief untuk file spesifik |
| **Synthesizer** | Fingerprint computation, health score, cross-analyzer correlations |
| **Decoder Steering** | Baseline management, drift detection, steering signal generation |

### 2. Analyzer Suite (12 Total)

| Prefix | Analyzer | Fungsi |
|---|---|---|
| `topo.orphan` | Orphan Detection | File unreferenced (fan_in=0, bukan entrypoint/test) |
| `topo.entrypoint` | Entrypoint Detection | Identifikasi entrypoints (main.ts, server.ts, dll.) |
| `topo.circular` | Circular Dependency | Deteksi semua circular dependencies via DFS |
| `topo.risk` | Change Risk Advisory | Risk level per file (high/medium/low) |
| `perf.async` | Async Waterfall | Sequential await, await in loop, sync I/O |
| `perf.deopt` | V8 Deopt | delete operator, eval, new Function |
| `perf.gc` | GC Pressure | Allocation in loop, JSON in loop, timer/event listener leaks |
| `perf.cache` | Cache Audit | Nondeterministic keys, collision risk, missing TTL |
| `hott.isomorphism` | Type Isomorphism | Pasangan type/interface isomorfik (Univalence) |
| `hott.sheaf` | Boundary Sheaf | Boundary violations, missing public API, circular boundaries |
| `hott.homotopy` | Homotopy Paths | Diamond dependencies, multi-importer hubs |
| `hott.manifold` | Topological Manifold | Betti numbers (β₀, β₁, β₂), archetype, complexity score |

### 3. Invarian Sistem (Aturan Mutlak)

| Aturan | Penjelasan |
|---|---|
| **Read-Only / Non-Destructive** | Pemindaian bersifat read-only; file sumber tidak pernah diubah |
| **Non-Blocking** | Tool tidak pernah melarang perubahan; keputusan ada pada agent |
| **Informational** | Semua output adalah observasi; bukan rekomendasi atau perintah |
| **Deterministic Output** | Output selalu konsisten untuk input yang sama |
| **Single Scan** | 1 filesystem scan untuk 12 analyzer (tidak ada redundant I/O) |
| **Zero-Dependency** | Menggunakan stdlib Python 3 (`os`, `re`, `json`, `sys`, `math`, `hashlib`, `datetime`) |
| **Relative Paths** | Selalu gunakan relative workspace path (misal `src/app/app.ts`) |
| **Fixture Safety** | Jalankan `fixture_check.py` setelah perubahan pada tool |

---

## 🛠 Aturan Penggunaan & Protokol Eksekusi

### 1. Unified Kernel CLI (PRIMARY)

**Gunakan `hott_kernel.py` untuk semua analisis.** Ini adalah single entry point.

#### A. Analyze Mode — Full Analysis

```bash
# Semua 12 analyzer, output ringkas
python3 tools/ai_studio_tool/hott_kernel.py analyze src --output summary

# Semua 12 analyzer, output lengkap
python3 tools/ai_studio_tool/hott_kernel.py analyze src --output full

# Hanya analyzer tertentu
python3 tools/ai_studio_tool/hott_kernel.py analyze src --analyzers perf.async,perf.deopt --output findings

# Hanya graph (tanpa analyzer)
python3 tools/ai_studio_tool/hott_kernel.py analyze src --output graph

# List semua analyzer yang tersedia
python3 tools/ai_studio_tool/hott_kernel.py analyzers
```

#### B. Synthesize Mode — Fingerprint + Health + Correlations

```bash
# Synthesis ringkas
python3 tools/ai_studio_tool/hott_kernel.py synthesize src --output summary

# Synthesis lengkap (dengan semua analyzer results)
python3 tools/ai_studio_tool/hott_kernel.py synthesize src --output full
```

#### C. Steer Mode — Drift Detection + Steering Signals

```bash
# Steering ringkas
python3 tools/ai_studio_tool/hott_kernel.py steer src --output summary

# Steering lengkap (dengan synthesis + prompt block)
python3 tools/ai_studio_tool/hott_kernel.py steer src --output full
```

#### D. Establish Mode — Baseline Management

```bash
# Establish baseline baru
python3 tools/ai_studio_tool/hott_kernel.py establish src
```

#### E. Targeted Queries — Per-File Analysis

```bash
# Impact analysis untuk file spesifik
python3 tools/ai_studio_tool/hott_kernel.py impact src/app/app.ts src

# Outline extraction untuk file spesifik
python3 tools/ai_studio_tool/hott_kernel.py outline src/app/app.ts src

# Brief (outline + impact combined) untuk file spesifik
python3 tools/ai_studio_tool/hott_kernel.py brief src/app/app.ts src --output summary
```

### 2. Output Modes

| Mode | Konten | Use Case |
|---|---|---|
| `full` | Semua data termasuk shared_graph | Deep analysis, debugging |
| `summary` | Hanya unified_summary + counts | Quick overview, agent decision |
| `findings` | Findings + summary, tanpa shared_graph | Review issues tanpa graph noise |
| `graph` | Hanya shared_graph (tanpa file_map) | Topology inspection |

### 3. Uji Baseline Fixtures (27 Test Cases)

```bash
python3 tools/ai_studio_tool/fixture_check.py
```

Expected output: `PASS: 27 fixture minimal baseline aman`

---

## 🔌 REST API Endpoints (via Express Backend)

Di `src/server.ts`, tool suite diintegrasikan melalui REST API endpoints berikut:

| Endpoint | Fungsi |
|---|---|
| `GET /api/python-info` | Status ketersediaan runtime Python 3 & versi script |
| `GET /api/topology` | Topologi codebase (nodes, edges, summary) |
| `GET /api/impact?file=src/app/app.ts` | Analisis dampak upstream & downstream |
| `GET /api/outline?file=src/app/app.ts` | Ekstrak outline permukaan file |
| `GET /api/brief?file=src/app/app.ts` | Context budgeting brief (outline + impact) |
| `GET /api/async-detector?root=src` | Deteksi async waterfalls dan synchronous I/O |
| `GET /api/deopt-checker?root=src` | Deteksi V8 deoptimization anti-patterns |
| `GET /api/gc-pressure?root=src` | Deteksi GC pressure, memory leaks |
| `GET /api/cache-auditor?root=src` | Audit cache patterns |
| `GET /api/type-isomorphism?root=src` | Observasi type isomorphism |
| `GET /api/boundary-sheaf?root=src` | Observasi boundary sheaf obstructions |
| `GET /api/homotopy-paths?root=src` | Observasi homotopy paths |
| `GET /api/topological-integrity?root=src` | Synthesis terpadu dengan health score |
| `GET /api/topological-manifold?root=src` | Betti numbers & invariant vector |
| `GET /api/topological-fingerprint?root=src` | Topological fingerprint & archetype |
| `GET /api/decoder-steering?mode=steer&root=src` | Steering signals & drift detection |

---

## 📊 Interpretasi Output Kunci

### Health Score Thresholds

| Score | Interpretasi | Action |
|---|---|---|
| `> 0.7` | Codebase sehat | Perubahan aman |
| `0.4 - 0.7` | Moderate | Hati-hati, verifikasi |
| `< 0.4` | Bermasalah | Prioritaskan perbaikan |

### Structural Archetypes

| Archetype | Karakteristik | Strategi Reasoning |
|---|---|---|
| `tree_like` | Connected acyclic | hierarchical_traversal |
| `modular` | Disconnected acyclic | isolated_analysis |
| `sparse_cyclic` | Connected with sparse cycles | cycle_aware_traversal |
| `mixed_cyclic` | Moderate cycles | path_enumeration |
| `dense_mesh` | Highly interconnected | conservative_edit |
| `fragmented_sparse_cyclic` | Fragmented with sparse cycles | component_localized_traversal |
| `fragmented_cyclic` | Fragmented with cycles | component_boundary_mapping |

### Cross-Analyzer Correlations

| Correlation Type | Severity | Interpretasi |
|---|---|---|
| `orphan_with_issues` | medium-high | File orphan dengan issues → cleanup candidate |
| `circular_with_deopt` | high | Circular dependency + deopt → critical refactor |
| `entrypoint_high_risk` | high | Entrypoint rentan → proteksi ekstra |
| `boundary_isomorphism` | low | Type duplikat di boundary → consolidation opportunity |

---

## 📁 Struktur Direktori Tool

```
tools/ai_studio_tool/
├── hott_kernel.py                  # UNIFIED ENTRY POINT (PRIMARY)
├── shared_graph.py                 # SharedGraph builder (1-pass scan)
├── analyzer_registry.py            # 12 analyzer registry
├── performance_analyzers.py        # perf.* analyzers (async, deopt, gc, cache)
├── hott_analyzers.py               # hott.* analyzers (isomorphism, sheaf, homotopy, manifold)
├── topology_analyzers.py           # topo.* analyzers + targeted queries (impact, outline, brief)
├── synthesizer.py                  # Synthesis engine (fingerprint, health, correlations, steering)
├── deprecation.py                  # Deprecation layer untuk standalone tools
├── baseline/                       # Topological baseline storage
│   └── kernel_baseline.json
├── fixture_check.py                # 27 baseline fixtures
├── tools_schema.json               # AI Agent tool declarations
├── SKILL.md                        # AI Agent skill guide
├── README.md                       # This file
│
├── file_scanner.py                 # [LEGACY] → hott_kernel analyze/impact/outline/brief
├── async_waterfall_detector.py     # [LEGACY] → perf.async
├── deopt_checker.py                # [LEGACY] → perf.deopt
├── gc_pressure_analyzer.py         # [LEGACY] → perf.gc
├── cache_auditor.py                # [LEGACY] → perf.cache
├── type_isomorphism_observer.py    # [LEGACY] → hott.isomorphism
├── boundary_sheaf_checker.py       # [LEGACY] → hott.sheaf
├── homotopy_path_observer.py       # [LEGACY] → hott.homotopy
├── topological_manifold_builder.py # [LEGACY] → hott.manifold
├── topological_integrity_orchestrator.py # [LEGACY] → hott_kernel synthesize
├── invariant_encoder.py            # [LEGACY] → hott_kernel synthesize
└── decoder_steering.py             # [LEGACY] → hott_kernel steer/establish
```

---

## 🧩 Tool Function Schema Declarations (`tools_schema.json`)

```json
[
  {
    "name": "hott_kernel",
    "description": "Unified HoTT Kernel: single entry point untuk seluruh analisis codebase. Menjalankan 12 analyzer (topo, perf, hott) dalam 1 filesystem scan. Mode 'analyze' untuk findings, 'synthesize' untuk fingerprint + health score + correlations, 'steer' untuk drift detection + steering signals, 'establish' untuk baseline, 'impact'/'outline'/'brief' untuk targeted file analysis. Gunakan ini sebagai pengganti semua tool analisis terpisah.",
    "parameters": {
      "type": "OBJECT",
      "properties": {
        "mode": {
          "type": "STRING",
          "description": "Mode operasi: analyze | synthesize | steer | establish | impact | outline | brief | analyzers"
        },
        "scan_root": {
          "type": "STRING",
          "description": "Root directory untuk scan. Default: 'src'. Untuk mode impact/outline/brief, ini adalah root proyek."
        },
        "target_file": {
          "type": "STRING",
          "description": "Path relatif file target untuk mode impact/outline/brief, contoh: 'src/app/app.ts'"
        },
        "analyzers": {
          "type": "STRING",
          "description": "Comma-separated daftar analyzer untuk mode analyze (optional, default: semua 12). Contoh: 'perf.async,perf.deopt,topo.circular'"
        },
        "output": {
          "type": "STRING",
          "description": "Format output: full | summary | findings | graph. Default: full"
        }
      },
      "required": ["mode"]
    }
  },
  {
    "name": "scan_topology",
    "description": "[DEPRECATED: gunakan hott_kernel mode=analyze] Memindai struktur direktori TS/JS/TSX/JSX dan menghasilkan topology graph. Tetap tersedia untuk backward compatibility.",
    "parameters": {
      "type": "OBJECT",
      "properties": {
        "path": {
          "type": "STRING",
          "description": "Lokasi root direktori proyek. Default adalah '.'"
        }
      }
    }
  },
  {
    "name": "get_impacted_files",
    "description": "[DEPRECATED: gunakan hott_kernel mode=impact] Melacak dampak perubahan file secara transitif. Tetap tersedia untuk backward compatibility.",
    "parameters": {
      "type": "OBJECT",
      "properties": {
        "file_path": {
          "type": "STRING",
          "description": "Path relatif file yang ingin dianalisis dampaknya, contoh: 'src/app/app.ts'"
        },
        "path": {
          "type": "STRING",
          "description": "Root proyek opsional. Default adalah '.'"
        }
      },
      "required": ["file_path"]
    }
  },
  {
    "name": "get_file_outline",
    "description": "[DEPRECATED: gunakan hott_kernel mode=outline] Ekstrak outline ringkas dari file TS/JS/TSX/JSX. Tetap tersedia untuk backward compatibility.",
    "parameters": {
      "type": "OBJECT",
      "properties": {
        "file_path": {
          "type": "STRING",
          "description": "Path relatif file yang ingin diekstrak outlinenya, contoh: 'src/app/app.ts'"
        }
      },
      "required": ["file_path"]
    }
  }
]
```

---

## 📈 Migration Path (Standalone → Kernel)

| Tool Lama | Kernel Equivalent |
|---|---|
| `file_scanner.py public/topology.json src` | `hott_kernel.py analyze src --output graph` |
| `file_scanner.py impact src/app/app.ts` | `hott_kernel.py impact src/app/app.ts src` |
| `file_scanner.py outline src/app/app.ts` | `hott_kernel.py outline src/app/app.ts src` |
| `file_scanner.py brief src/app/app.ts` | `hott_kernel.py brief src/app/app.ts src` |
| `async_waterfall_detector.py scan src` | `hott_kernel.py analyze src --analyzers perf.async --output findings` |
| `deopt_checker.py scan src` | `hott_kernel.py analyze src --analyzers perf.deopt --output findings` |
| `gc_pressure_analyzer.py scan src` | `hott_kernel.py analyze src --analyzers perf.gc --output findings` |
| `cache_auditor.py scan src` | `hott_kernel.py analyze src --analyzers perf.cache --output findings` |
| `type_isomorphism_observer.py scan src` | `hott_kernel.py analyze src --analyzers hott.isomorphism --output findings` |
| `boundary_sheaf_checker.py src` | `hott_kernel.py analyze src --analyzers hott.sheaf --output findings` |
| `homotopy_path_observer.py src` | `hott_kernel.py analyze src --analyzers hott.homotopy --output findings` |
| `topological_manifold_builder.py src` | `hott_kernel.py analyze src --analyzers hott.manifold --output findings` |
| `topological_integrity_orchestrator.py src` | `hott_kernel.py synthesize src --output summary` |
| `invariant_encoder.py src` | `hott_kernel.py synthesize src --output summary` |
| `decoder_steering.py establish src` | `hott_kernel.py establish src` |
| `decoder_steering.py steer src` | `hott_kernel.py steer src --output summary` |
```

---

## Ringkasan Perubahan dari README Lama

| Aspek | README Lama | README Baru |
|---|---|---|
| Schema version | 2.6.0-steering | **3.0.0-kernel** |
| Entry point | Multiple standalone tools | **hott_kernel.py (unified)** |
| Analyzers | 12 tools terpisah | **12 analyzers dalam 1 registry** |
| Filesystem scans | 9x per full analysis | **1x per full analysis** |
| Output modes | Tidak ada | **full / summary / findings / graph** |
| Synthesis | Tidak terintegrasi | **synthesize mode dengan correlations** |
| Steering | Standalone decoder_steering.py | **steer mode terintegrasi** |
| File structure | 12 files flat | **7 kernel files + 12 legacy files** |
| Fixture count | 25 | **27** |
| tools_schema.json | 4 declarations | **1 kernel + 3 deprecated** |
| Migration path | Tidak ada | **Complete mapping table** |