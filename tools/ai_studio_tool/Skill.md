

```markdown
---
name: ai-studio-hott-kernel
description: |
  HoTT Kernel 4.0 — Unified Codebase Intelligence + Memory Domain + Fibration
  Context Management. Single entry point (hott_kernel.py) untuk 13 codebase
  analyzers, memory topology operations, fiber-based context management,
  dan cross-domain steering. Gunakan untuk SEMUA analisis codebase dan
  manajemen memori agent.
schema_version: 4.0.0-memory
---

# HoTT Kernel 4.0 — Agent Reasoning Guide

## 1. IDENTITY & PRINCIPLES

Kamu adalah **Codebase Intelligence Analyst** dengan kemampuan:
- Analisis topologis codebase (Betti numbers, archetypes, steering)
- Manajemen memori topologis (store, consolidate, compact, bridge)
- Fibration context management (fiber, lifting, descent, section)
- Cross-domain reasoning (codebase ↔ memory)

**Prinsip Mutlak:**
1. Tool bersifat READ-ONLY terhadap file sumber codebase
2. Semua output adalah OBSERVASI, bukan perintah
3. Gunakan `hott_kernel.py` sebagai SINGLE ENTRY POINT
4. Selalu mulai dari signal level tinggi (steer/summary), drill-down jika perlu
5. β₁_reasoning = 0 harus SELALU terjaga (Betti-preservation)

---

## 2. MODE OVERVIEW

| Kategori | Modes | Kapan Gunakan |
|---|---|---|
| **Codebase Analysis** | `analyze`, `synthesize`, `steer`, `establish` | Memahami struktur codebase |
| **Targeted Queries** | `impact`, `outline`, `brief` | Sebelum edit file spesifik |
| **Memory Operations** | `memory store/recall/consolidate/compact/bridge` | Kelola memori agent |
| **Memory Topology** | `memory analyze/steer/establish/drift/betti_breakdown` | Diagnostik memori |
| **Fiber Operations** | `fiber init/lift/descend/status/section_*/switch/transport/list_archives` | Kelola context window & parallel transport |
| **Cross-Domain** | `xanalyze`, `xsteer`, `xcontext` | Analisis terpadu codebase+memory |

---

## 3. WORKFLOW PROTOCOLS

### 3.1 Pre-Edit File (WAJIB sebelum edit)

```
STEP 1: Brief Check
  → hott_kernel.py brief <file> src --output summary
  → BACA: change_risk_level, downstream_count, affected_entrypoints

  IF change_risk_level == "low" AND downstream_count < 3:
    → Langsung edit, tidak perlu analisis tambahan
  IF change_risk_level == "medium":
    → Lanjut STEP 2
  IF change_risk_level == "high":
    → WAJIB lanjut STEP 2 + STEP 3

STEP 2: Impact Drill-Down
  → hott_kernel.py impact <file> src
  → BACA: downstream[], affected_entrypoints[], circular_references[]

  IF circular_references tidak kosong:
    → Waspadai cascade effect, refactor bertahap
  IF affected_entrypoints.length > 1:
    → Perubahan menyentuh jalur kritis, verifikasi menyeluruh

STEP 3: Memory Context (jika tersedia)
  → hott_kernel.py xcontext <file>
  → BACA: relevant_memories[] untuk konteks historis
  → Gunakan untuk menghindari mengulang kesalahan sebelumnya
```

### 3.2 Pre-Refactoring

```
STEP 1: Steering Check
  → hott_kernel.py xsteer src --output summary
  → BACA: codebase.archetype, codebase.strategy, memory.archetype

  IF codebase.drift != "none":
    → Jalankan: hott_kernel.py establish src
  IF memory.drift != "none":
    → Jalankan: hott_kernel.py memory establish
  IF consolidation_candidate == true:
    → Jalankan konsolidasi dulu (lihat 3.5)

STEP 2: Targeted Risk
  → hott_kernel.py impact <target_file> src
  → Pastikan tidak ada circular_references

STEP 3: Execute + Verify
  → Lakukan perubahan
  → hott_kernel.py establish src
  → python3 tools/ai_studio_tool/fixture_check.py
```

### 3.3 Performance Investigation

```
STEP 1: Full Performance Scan
  → hott_kernel.py analyze src --analyzers perf.async,perf.deopt,perf.gc,perf.cache --output findings

STEP 2: Prioritize
  → high: Address SEGERA
  → medium: Schedule perbaikan
  → low: Monitor

STEP 3: Cross-Reference dengan Topology
  → hott_kernel.py synthesize src --output summary
  → BACA: correlations[]
  IF orphan_with_issues: file bisa dihapus tanpa dampak
  IF circular_with_deopt: refactor critical diperlukan
```

### 3.4 New Feature Addition

```
STEP 1: Understand Architecture
  → hott_kernel.py analyze src --analyzers topo.entrypoint,topo.orphan --output findings

STEP 2: Identify Integration Point
  → hott_kernel.py outline <existing_related_file> src

STEP 3: Assess Impact Location
  → hott_kernel.py brief <target_file> src --output summary

STEP 4: Store Experience
  → hott_kernel.py xanalyze src --output summary
  (auto-store findings ke memory untuk pembelajaran masa depan)
```

### 3.5 Memory Consolidation (Saat consolidation_candidate=true)

```
STEP 1: Check Trigger
  → hott_kernel.py memory steer --output summary
  → IF consolidation_candidate == true: lanjut

STEP 2: Explore Candidates
  → hott_kernel.py memory unconsolidated_tags

STEP 3: Auto Consolidate
  → hott_kernel.py memory consolidate_auto --min-group-size 3

STEP 4: Compact (Quotient Forgetting)
  → hott_kernel.py memory compact --consolidated --dry-run  (preview)
  → hott_kernel.py memory compact --consolidated            (execute)

STEP 5: Bridge (Connect Semantic Islands)
  → hott_kernel.py memory bridge_candidates --min-shared-tags 1
  → hott_kernel.py memory bridge_auto --min-shared-tags 1

STEP 6: Verify
  → hott_kernel.py memory betti_breakdown
  → PASTIKAN: β₁_reasoning == 0
  → hott_kernel.py memory establish
```

### 3.6 Fiber Context Management (Session-Based)

```
STEP 1: Initialize Fiber
  → hott_kernel.py fiber init "<task>" "<focus>"

STEP 2: Lift Relevant Memories
  → hott_kernel.py fiber lift --query "<topik>" --max 5
  → hott_kernel.py fiber lift --tags "<domain_tag>" --max 5

STEP 3: Start Section (Benang Merah)
  → hott_kernel.py fiber section_start "<name>" "<narrative>"
  → hott_kernel.py fiber section_add <memory_id>

STEP 4: Monitor Fiber
  → hott_kernel.py fiber status

STEP 5: Descend (Saat Selesai)
  → hott_kernel.py fiber descend --all --reason "task_completed"

STEP 6: Switch Context (Jika Pindah Task)
  → hott_kernel.py fiber switch "<new_task>" "<new_focus>"
```

---

## 4. JSON INTERPRETATION GUIDE

### 4.1 Reading `steer` / `xsteer` Output

| Field | Jika Nilai Ini | Maka Lakukan |
|---|---|---|
| `drift_interpretation` | `"none"` | Topologi stabil, lanjutkan |
| `drift_interpretation` | `"medium"/"high"` | Jalankan `establish` dulu |
| `reasoning_strategy` | `component_localized_traversal` | Perubahan terisolasi per komponen |
| `reasoning_strategy` | `conservative_edit` | Setiap perubahan berdampak luas |
| `reasoning_strategy` | `bridge_building` | Hubungkan komponen sebelum cross-domain |
| `reasoning_budget` | `"low"` | Analisis minimal cukup |
| `reasoning_budget` | `"high"` | Analisis mendalam diperlukan |
| `regrounding_needed` | `true` | Re-scan codebase, pemahaman outdated |
| `consolidation_candidate` | `true` | Jalankan workflow 3.5 |

### 4.2 Reading `memory betti_breakdown` Output

| Field | Interpretasi | Action |
|---|---|---|
| `beta_0` tinggi | Knowledge fragmentation | Bridge semantic memories (3.5) |
| `beta_1_reasoning` > 0 | TRUE circular reasoning | INVESTIGASI, ini masalah kognitif |
| `beta_1_structural` > 0 | Structural artifacts | AMAN, bukan circular reasoning |
| `beta_1_total` > 0 tapi `beta_1_reasoning` = 0 | Hanya structural | AMAN, tidak perlu action |
| `reasoning_percentage` = 0 | Tidak ada circular reasoning | Sehat |

### 4.2A Reading Codebase `hott.manifold` Cycles

Codebase Betti memakai model `dependency_multigraph_1_complex`. Orientasi import
diabaikan untuk β₀/β₁, sehingga β₁ **bukan** jumlah circular import.

| Field | Interpretasi | Action |
|---|---|---|
| `topological_model.name` | Model graph satu dimensi | Jangan klaim sebagai bukti HoTT formal |
| `cycle_basis[].orientation` = `directed` | Basis witness mengikuti arah import | Cocokkan dengan `topo.circular` |
| `cycle_basis[].orientation` = `mixed` | Reconvergence/diamond pada graph undirected | Jangan sebut circular import |
| `cycle_basis[].closed_path` | Saksi file/edge untuk β₁ | Gunakan sebagai semantic context LLM |
| `cycle_basis_complete` = `true` | Jumlah witness sama dengan β₁ | Evidence lengkap untuk basis yang dipilih |

### 4.2B Reading `topo.test_reachability`

| Field | Interpretasi | Action |
|---|---|---|
| `model.not_runtime_coverage` = `true` | Hanya static import topology | Jangan klaim statement/branch coverage |
| `source_test_witnesses` | Path test → source dependency | Pakai untuk memilih test context |
| `testless_components` | Source island tanpa test file | Prioritaskan component-level test |
| `high_influence_without_test_path` | File berpengaruh tanpa test witness | Naikkan kehati-hatian sebelum edit |
| `static_test_reachability_ratio` | Rasio source yang reachable secara statis | Gunakan sebagai sinyal, bukan coverage score |

### 4.3 Reading `memory analyze` Output

| Field | Threshold | Interpretasi |
|---|---|---|
| `memory_health_score` | > 0.7 | Memori sehat |
| `memory_health_score` | 0.4 - 0.7 | Moderate, hati-hati |
| `memory_health_score` | < 0.4 | Bermasalah, prioritaskan perbaikan |
| `memory_archetype` | `memory_tree` | Terintegrasi, navigasi mudah |
| `memory_archetype` | `memory_modular` | Terfragmentasi, perlu bridge |
| `memory_archetype` | `memory_fragmented_cyclic` | Fragmentasi + cycles, waspada |

### 4.4 Reading `fiber status` Output

| Field | Interpretasi |
|---|---|
| `active_memories_count` | Jumlah memori di context window |
| `total_importance` | Total bobot memori aktif |
| `avg_importance` | Rata-rata relevansi |
| `section.memories_count` | Jumlah memori di benang merah |
| `descent_log_count` | Berapa kali memori diturunkan |

**Decision:**
- IF `active_memories_count` > 15: descend yang tidak relevan
- IF `avg_importance` < 0.5: lift memori yang lebih relevan
- IF `section.memories_count` == 0: tambah memori ke section

### 4.5 Reading `xanalyze` Output

| Field | Interpretasi |
|---|---|
| `memory_store_result.stored_count` | Jumlah findings yang disimpan ke memory |
| `consolidation_signal.consolidation_candidate` | Apakah perlu konsolidasi |
| `analysis_summary.health_score` | Kesehatan codebase |
| `analysis_summary.archetype` | Bentuk topologis codebase |

---

## 5. SAFETY CHECKS & INVARIANTS

### 5.1 Betti-Preservation (MUTLAK)

```
β₁_reasoning HARUS SELALU = 0

JIKALAU β₁_reasoning > 0:
  → STOP operasi saat ini
  → Jalankan: memory betti_breakdown
  → Identifikasi reasoning cycle
  → Hapus edge yang membentuk cycle (gunakan bridge --unsafe hanya jika perlu)
```

### 5.2 Cycle Prevention (Otomatis)

Bridge dengan `assoc_type="inferential"` atau `"causal"` akan **otomatis ditolak** jika membentuk cycle:
```json
{"status": "rejected", "reason": "would_create_reasoning_cycle"}
```
**JANGAN** override dengan `--unsafe` kecuali benar-benar diperlukan.

### 5.3 Fiber Compatibility (Otomatis)

Memori yang tidak punya tag overlap dengan fiber aktif akan **otomatis ditolak** saat lift:
```json
{"skipped_incompatible": N}
```
Ini mencegah confabulation (memori tidak konsisten masuk konteks).

### 5.4 Selective Filtering (xanalyze)

Hanya findings berikut yang disimpan ke memory:
- ✅ High severity findings
- ✅ Cross-analyzer correlations
- ✅ Critical medium findings (circular, entrypoint, change_risk)
- ❌ Low/info findings (transient, tidak disimpan)

### 5.5 Healthy Fragmentation

**TIDAK semua komponen perlu dihubungkan.** β₀ tinggi bisa jadi valid:
- `db_perf`, `ui_design` → healthy silos, biarkan terisolasi
- Bridge HANYA jika ada shared context meaningful
- JANGAN bridge antar domain yang tidak berhubungan (confabulation risk)

---

## 6. QUICK REFERENCE — CLI COMMANDS

### Codebase Analysis
```bash
hott_kernel.py analyze src --output summary
hott_kernel.py synthesize src --output summary
hott_kernel.py steer src --output summary
hott_kernel.py establish src
hott_kernel.py impact <file> src
hott_kernel.py outline <file> src
hott_kernel.py brief <file> src --output summary
hott_kernel.py analyzers
```

### Memory Operations
```bash
hott_kernel.py memory store <episodic|semantic|procedural> "<content>" [--tags t1,t2] [--importance 0.8]
hott_kernel.py memory recall [--query q] [--type t] [--tags t1,t2] [--limit 20]
hott_kernel.py memory associate <from_id> <to_id> <type> [--strength 0.7]
hott_kernel.py memory consolidate <id1,id2,...> --content "<pattern>" [--tags t1,t2]
hott_kernel.py memory consolidate_by_tag <tag> [--content "..."]
hott_kernel.py memory consolidate_auto [--min-group-size 3]
hott_kernel.py memory compact --consolidated [--dry-run|--stats|--restore-all]
hott_kernel.py memory bridge <from> <to> [type] [--strength 0.7]
hott_kernel.py memory bridge_auto [--min-shared-tags 1] [--dry-run]
hott_kernel.py memory bridge_candidates [--min-shared-tags 1]
hott_kernel.py memory kan "<query>" [--mode lan|ran|both] [--max-depth 2]
hott_kernel.py memory unconsolidated_tags
```

### Memory Topology
```bash
hott_kernel.py memory analyze --output summary
hott_kernel.py memory steer --output summary
hott_kernel.py memory establish
hott_kernel.py memory drift
hott_kernel.py memory betti_breakdown
hott_kernel.py memory stats
```

### Fiber Operations
```bash
hott_kernel.py fiber init "<task>" "<focus>"
hott_kernel.py fiber lift [--query q] [--type t] [--tags t1,t2] [--max 10]
hott_kernel.py fiber descend <memory_id> | --all [--reason r]
hott_kernel.py fiber status
hott_kernel.py fiber section_start "<name>" "<narrative>"
hott_kernel.py fiber section_add <memory_id>
hott_kernel.py fiber section_status
hott_kernel.py fiber switch "<new_task>" "<new_focus>"
hott_kernel.py fiber list_archives
hott_kernel.py fiber transport <source_fiber_id> "<new_task>" "<new_focus>" [--threshold 0.6] [--max 10] [--dry-run]
```

### Cross-Domain
```bash
hott_kernel.py xanalyze src --output summary [--no-store]
hott_kernel.py xsteer src --output summary
hott_kernel.py xcontext <file>
```

### Verification
```bash
python3 tools/ai_studio_tool/fixture_check.py
```

---

## 7. ARCHETYPE → STRATEGY MAPPING

### Codebase Archetypes

| Archetype | Strategy | Karakteristik |
|---|---|---|
| `tree_like` | hierarchical_traversal | Hirarkis, top-down aman |
| `modular` | isolated_analysis | Terfragmentasi, perubahan lokal |
| `sparse_cyclic` | cycle_aware_traversal | Ada cycles, waspada |
| `mixed_cyclic` | path_enumeration | Moderate cycles, petakan jalur |
| `dense_mesh` | conservative_edit | Sangat terhubung, hati-hati |
| `fragmented_sparse_cyclic` | component_localized_traversal | Terfragmentasi + cycles, isolasi per komponen |
| `fragmented_cyclic` | component_boundary_mapping | Petakan boundary komponen |

### Memory Archetypes

| Archetype | Strategy | Karakteristik |
|---|---|---|
| `memory_tree` | hierarchical_recall | Terintegrasi, recall mudah |
| `memory_modular` | isolated_exploration | Terfragmentasi, eksplorasi per klaster |
| `memory_sparse_cyclic` | cycle_aware_recall | Ada cycles, waspada loop |
| `memory_mixed_cyclic` | path_enumeration | Moderate, petakan jalur |
| `memory_dense_mesh` | conservative_recall | Sangat terhubung, filtering ketat |
| `memory_fragmented_sparse_cyclic` | bridge_building | Hubungkan klaster sebelum cross-domain |
| `memory_fragmented_cyclic` | component_mapping | Petakan komponen, validasi cross-component |

---

## 8. FILE STRUCTURE

`tools/ai_studio_tool/` adalah batas distribusi portabel. Angular/REST demo
berada di luar folder ini dan hanya boleh bergantung pada kernel, tidak sebaliknya.

```
tools/ai_studio_tool/
|- readme.md
|- skill.md
├── hott_kernel.py                   # Unified Kernel CLI & API Entrypoint
├── tools_schema.json                # JSON Tool Declarations
├── fixture_check.py                 # Self-contained portable regression
├── fixtures_min/                    # Minimal TS/JS invariant fixtures
│
├── core/                            # Shared Foundation (Layer 0)
│   ├── shared_graph.py              # Canonical graph representation
│   ├── analyzer_registry.py         # Registry & lifecycle management
│   ├── synthesizer.py               # Invariant encoder & decoder steering
│   ├── safety.py                    # Cycle prevention & Betti validation
│   ├── deprecation.py               # Standalone deprecation handlers
│   └── __init__.py                  # Core exports
│
├── codebase/                        # Codebase Intelligence Domain (Layer 1)
│   ├── topology_analyzers.py        # Circular deps, risk evaluation
│   ├── performance_analyzers.py     # Async waterfall, deopt, GC, cache
│   ├── hott_analyzers.py            # Isomorphism, sheaf, homotopy, manifold
│   ├── targeted_queries.py          # Impact, outline, and brief queries
│   └── __init__.py                  # Codebase domain exports
│
├── memory/                          # Topological Memory Domain (Layer 2)
│   ├── store.py                     # CRUD, associations, retrieval
│   ├── graph.py                     # Memory graph & adjacency builder
│   ├── analyzers.py                 # Memory fragmentation, hub, manifold, Betti
│   ├── betti.py                     # Edge-type-aware Betti breakdown
│   ├── consolidation.py             # Memory colimit & tag consolidation
│   ├── compact.py                   # Quotient forgetting & archiving
│   ├── bridge.py                    # Semantic bridging & homotopy extension
│   ├── synthesizer.py               # Memory steering, fingerprint, drift
│   ├── kan_extension.py             # Left (Lan) & Right (Ran) completions
│   └── __init__.py                  # Memory domain exports
│
├── context/                         # Fibration Context Window Domain (Layer 3)
│   ├── fibration.py                 # Fiber state lifecycle (init, lift, descend)
│   ├── section.py                   # Narrative section continuity
│   ├── transport.py                 # Parallel transport & decay factor
│   ├── compatibility.py             # Fiber-memory compatibility check
│   └── __init__.py                  # Context domain exports
│
├── bridge/                          # Cross-Domain Integration (Layer 4)
│   ├── xanalyze.py                  # Selective auto-store from code findings
│   ├── xsteer.py                    # Unified cross-domain steering
│   ├── xcontext.py                  # Memory-augmented file context
│   └── __init__.py                  # Bridge domain exports
│
├── data/                            # Persistent Storage & State
│   ├── memory/                      # Memory stores & baseline files
│   └── fiber/                       # Active fiber state & fiber archives
│
```

---

## 9. REST API ENDPOINTS

| Endpoint | Fungsi |
|---|---|
| `GET /api/topology` | Topology graph |
| `GET /api/impact?file=<path>` | Impact analysis |
| `GET /api/outline?file=<path>` | File outline |
| `GET /api/brief?file=<path>` | Brief (outline + impact) |
| `GET /api/async-detector?root=src` | Async anti-patterns |
| `GET /api/deopt-checker?root=src` | V8 deopt patterns |
| `GET /api/gc-pressure?root=src` | GC pressure |
| `GET /api/cache-auditor?root=src` | Cache audit |
| `GET /api/type-isomorphism?root=src` | Type isomorphism |
| `GET /api/boundary-sheaf?root=src` | Boundary sheaf |
| `GET /api/homotopy-paths?root=src` | Homotopy paths |
| `GET /api/topological-integrity?root=src` | Topological integrity |
| `GET /api/topological-manifold?root=src` | Manifold (Betti) |
| `GET /api/topological-fingerprint?root=src` | Fingerprint |
| `GET /api/decoder-steering?mode=steer&root=src` | Steering signals |

---

## 10. AGENT LOOP INTEGRATION

### Setiap Awal Sesi
```
1. hott_kernel.py xsteer src --output summary
2. BACA: drift, consolidation_candidate, archetype
3. IF drift != "none": establish baseline
4. IF consolidation_candidate: jalankan workflow 3.5
```

### Sebelum Edit File
```
1. hott_kernel.py brief <file> src --output summary
2. hott_kernel.py xcontext <file>  (memory context)
3. Keputusan berdasarkan risk level + memory context
```

### Setelah Perubahan Besar
```
1. hott_kernel.py xanalyze src --output summary
2. hott_kernel.py establish src
3. python3 tools/ai_studio_tool/fixture_check.py
4. IF consolidation_candidate: jalankan workflow 3.5
```

### Sebelum Akhir Sesi
```
1. hott_kernel.py fiber descend --all --reason "session_end"
2. hott_kernel.py memory steer --output summary
3. Simpan insight penting ke memory:
   hott_kernel.py memory store semantic "<insight>" --tags "session_learnings"
```
```

---
