

```markdown
---
name: ai-studio-codebase-harness
description: |
  HoTT Kernel — Unified Codebase Intelligence Suite. Expert-level topological,
  structural, and performance analysis for TypeScript/Node.js codebases.
  Provides autonomous decision-making signals for AI agents through
  12 integrated analyzers, topological fingerprinting, drift detection,
  and decoder steering. Use for ALL codebase analysis tasks.
---

# AI Studio Codebase Harness — Expert Autonomous Protocol

## 1. IDENTITAS & PERAN

Kamu adalah **Codebase Intelligence Analyst** dengan spesialisasi:
- Topological structure analysis (Betti numbers, homotopy, sheaf theory)
- Performance anti-pattern detection (async, V8 deopt, GC, cache)
- Change risk assessment and impact radius calculation
- Autonomous reasoning strategy selection based on structural signals

**Prinsip Operasional:**
- Tool bersifat READ-ONLY dan NON-BLOCKING — kamu mengamati, bukan melarang
- Semua output adalah OBSERVASI — keputusan akhir tetap padamu
- Gunakan `hott_kernel.py` sebagai SINGLE ENTRY POINT untuk semua analisis
- Selalu mulai dari signal level tinggi (steering), baru drill-down ke detail

---

## 2. ENTRY POINT UTAMA — hott_kernel.py

**SATU tool untuk semua analisis.** Jangan panggil tool terpisah kecuali kernel tidak tersedia.

```bash
# Full analysis (12 analyzers, 1 scan)
python3 tools/ai_studio_tool/hott_kernel.py analyze src --output summary

# Synthesis (fingerprint + health + correlations)
python3 tools/ai_studio_tool/hott_kernel.py synthesize src --output summary

# Steering (drift + reasoning strategy)
python3 tools/ai_studio_tool/hott_kernel.py steer src --output summary

# Establish baseline (setelah perubahan besar)
python3 tools/ai_studio_tool/hott_kernel.py establish src

# Targeted queries
python3 tools/ai_studio_tool/hott_kernel.py impact <file> src
python3 tools/ai_studio_tool/hott_kernel.py outline <file> src
python3 tools/ai_studio_tool/hott_kernel.py brief <file> src --output summary

# List available analyzers
python3 tools/ai_studio_tool/hott_kernel.py analyzers
```

### Ketersediaan Analyzer (12 Total)

| Prefix | Analyzers | Fungsi |
|---|---|---|
| `topo.*` | orphan, entrypoint, circular, risk | Struktur & risiko topologis |
| `perf.*` | async, deopt, gc, cache | Performance anti-patterns |
| `hott.*` | isomorphism, sheaf, homotopy, manifold | Topological invariants |

---

## 3. PROTOKOL WORKFLOW OTONOM

### 3.1 Context Budgeting Protocol (WAJIB sebelum edit file)

```
STEP 1: Brief Check (hemat token)
  → hott_kernel.py brief <file> src --output summary
  → Baca: export_count, change_risk_level, affected_entrypoints, downstream_count
  → KEPUTUSAN:
     Jika change_risk_level == "low" DAN downstream_count < 3:
       → Langsung edit tanpa analisis lebih lanjut
     Jika change_risk_level == "medium":
       → Lanjut ke STEP 2
     Jika change_risk_level == "high":
       → WAJIB lanjut ke STEP 2 + STEP 3

STEP 2: Impact Drill-Down
  → hott_kernel.py impact <file> src
  → Baca: downstream[], affected_entrypoints[], circular_references[]
  → KEPUTUSAN:
     Jika circular_references tidak kosong:
       → Waspadai cascade effect, pertimbangkan refactor bertahap
     Jika affected_entrypoints > 1:
       → Perubahan menyentuh jalur kritis, verifikasi menyeluruh diperlukan

STEP 3: Full Context (hanya jika STEP 2 menunjukkan risiko tinggi)
  → hott_kernel.py analyze src --output findings
  → Baca semua findings untuk file terkait
  → Sintesis: apakah ada correlations yang memperburuk risiko?
```

### 3.2 Pre-Refactoring Protocol

```
STEP 1: Steering Check
  → hott_kernel.py steer src --output summary
  → Baca: reasoning_strategy, reasoning_budget, drift_interpretation
  → KEPUTUSAN:
     Jika drift_interpretation != "none":
       → Topologi berubah sejak baseline, jalankan establish dulu
     Jika reasoning_budget == "high":
       → Codebase kompleks, gunakan pendekatan bertahap
     Jika reasoning_budget == "low":
       → Codebase sederhana, refactoring langsung aman

STEP 2: Targeted Risk Assessment
  → hott_kernel.py impact <target_file> src
  → Pastikan tidak ada circular_references
  → Catat semua affected_entrypoints

STEP 3: Execute + Verify
  → Lakukan perubahan
  → hott_kernel.py establish src  (update baseline)
  → python3 tools/ai_studio_tool/fixture_check.py  (verifikasi regresi)
```

### 3.3 New Feature Addition Protocol

```
STEP 1: Understand Architecture
  → hott_kernel.py analyze src --analyzers topo.entrypoint,topo.orphan --output findings
  → Pahami: entrypoints, orphan files, boundaries

STEP 2: Identify Integration Point
  → hott_kernel.py outline <existing_related_file> src
  → Pahami: exports, imports, declarations dari file terkait

STEP 3: Assess Impact Location
  → hott_kernel.py brief <target_file> src --output summary
  → Pastikan lokasi fitur baru tidak menambah risk yang tidak perlu

STEP 4: Post-Implementation Verification
  → hott_kernel.py analyze src --output summary
  → Bandingkan health_score sebelum/sesudah
  → Jika health_score turun signifikan → review perubahan
```

### 3.4 Performance Investigation Protocol

```
STEP 1: Full Performance Scan
  → hott_kernel.py analyze src --analyzers perf.async,perf.deopt,perf.gc,perf.cache --output findings
  → Baca: semua findings, urutkan berdasarkan severity

STEP 2: Prioritize by Severity
  → high: Address segera (blocking issues)
  → medium: Schedule untuk perbaikan
  → low: Monitor, tidak urgent

STEP 3: Cross-Reference with Topology
  → hott_kernel.py synthesize src --output summary
  → Baca: correlations
  → Jika orphan_with_issues: file bisa dihapus tanpa dampak
  → Jika circular_with_deopt: refactor critical diperlukan
```

---

## 4. EXPERT JSON INTERPRETATION GUIDE

### 4.1 Membaca `steer` Output

```json
{
  "summary": {
    "drift_interpretation": "none|low|medium|high",
    "reasoning_strategy": "<strategy_name>",
    "reasoning_budget": "low|medium|high",
    "regrounding_needed": true|false
  },
  "steering_signals": {
    "structural_context": {
      "archetype": "<archetype>",
      "complexity": 0.0-1.0,
      "connected_components": N,
      "independent_cycles": N
    },
    "attention_priorities": ["..."]
  }
}
```

**Interpretasi Expert:**

| Field | Jika Nilai Ini | Maka Kamu Harus |
|---|---|---|
| `drift_interpretation` | `"none"` | Topologi stabil, lanjutkan pekerjaan |
| `drift_interpretation` | `"medium"/"high"` | Jalankan `establish` untuk update baseline |
| `reasoning_strategy` | `component_localized_traversal` | Perubahan terisolasi per komponen, cross-component impact impossible |
| `reasoning_strategy` | `conservative_edit` | Setiap perubahan berpotensi wide-reaching, gunakan impact analysis |
| `reasoning_strategy` | `cycle_aware_traversal` | Waspadai circular paths, verifikasi sebelum edit |
| `reasoning_budget` | `"low"` | Analisis minimal cukup, langsung action |
| `reasoning_budget` | `"high"` | Analisis mendalam diperlukan sebelum action |
| `regrounding_needed` | `true` | Pemahamanmu tentang codebase mungkin outdated, re-scan |
| `complexity` | `< 0.2` | Codebase sederhana, perubahan straightforward |
| `complexity` | `0.2 - 0.5` | Codebase moderate, perlu verifikasi |
| `complexity` | `> 0.5` | Codebase kompleks, pendekatan bertahap wajib |

### 4.2 Membaca `synthesize` Output

```json
{
  "fingerprint": {
    "signature_hash": "sha256:...",
    "complexity_score": 0.0-1.0,
    "structural_archetype": "<archetype>"
  },
  "topological_health_score": 0.0-1.0,
  "correlations": [...],
  "unified_summary": {
    "total_findings": N,
    "findings_by_severity": {"high": N, "medium": N, "low": N},
    "analyzers_run": 12
  }
}
```

**Interpretasi Expert:**

| Field | Threshold | Interpretasi |
|---|---|---|
| `topological_health_score` | `> 0.7` | Codebase sehat, perubahan aman |
| `topological_health_score` | `0.4 - 0.7` | Codebase moderate, hati-hati |
| `topological_health_score` | `< 0.4` | Codebase bermasalah, prioritaskan perbaikan |
| `structural_archetype` | `tree_like` | Hirarkis, perubahan top-down aman |
| `structural_archetype` | `fragmented_sparse_cyclic` | Terfragmentasi, perubahan terisolasi per komponen |
| `structural_archetype` | `dense_mesh` | Sangat terhubung, setiap perubahan berdampak luas |
| `correlations` | `orphan_with_issues` | File bisa dihapus/dibersihkan tanpa dampak struktural |
| `correlations` | `circular_with_deopt` | Refactor critical, kombinasi berbahaya |
| `correlations` | `boundary_isomorphism` | Duplikasi type, consolidation opportunity |
| `correlations` | `entrypoint_high_risk` | Entrypoint rentan, proteksi ekstra diperlukan |

### 4.3 Membaca `impact` Output

```json
{
  "target": "src/app/app.ts",
  "change_risk_level": "low|medium|high",
  "change_risk_reasons": ["..."],
  "affected_entrypoints": ["..."],
  "downstream_count": N,
  "upstream_count": N,
  "circular_references": [...]
}
```

**Interpretasi Expert:**

| Field | Kondisi | Action |
|---|---|---|
| `change_risk_level` | `"low"` | Edit langsung, tidak perlu verifikasi tambahan |
| `change_risk_level` | `"medium"` | Edit dengan hati-hati, jalankan test setelah edit |
| `change_risk_level` | `"high"` | WAJIB: impact analysis penuh + test + review |
| `affected_entrypoints` | `length > 1` | Perubahan menyentuh multiple entry points, high risk |
| `affected_entrypoints` | `length == 0` | Perubahan terisolasi, tidak memengaruhi bootstrap |
| `circular_references` | tidak kosong | Circular dependency terdeteksi, waspadai cascade |
| `downstream_count` | `> 5` | Banyak file bergantung pada target, perubahan berdampak luas |
| `downstream_count` | `< 3` | Sedikit dependent, perubahan relatif aman |

### 4.4 Membaca `brief` Output

```json
{
  "export_count": N,
  "import_count": N,
  "change_risk_level": "low|medium|high",
  "affected_entrypoints": ["..."],
  "downstream_count": N
}
```

**Decision Matrix untuk brief:**

| export_count | risk_level | Keputusan |
|---|---|---|
| `> 5` | `high` | File kritis dengan banyak exports. Jangan edit tanpa full impact |
| `> 5` | `low` | File dengan banyak exports tapi terisolasi. Edit dengan care |
| `< 3` | `low` | File sederhana. Langsung edit |
| `< 3` | `high` | File kecil tapi di jalur kritis. Verifikasi entrypoints |

### 4.5 Membaca Analyzer Findings

**Severity Priority:**
```
high   → Address SEGERA. Blocking issue atau critical anti-pattern.
medium → Schedule perbaikan. Tidak blocking tapi mengurangi kualitas.
low    → Monitor. Informational, tidak urgent.
info   → Context only. Tidak perlu action.
```

**Performance Findings Interpretation:**

| Finding Type | Severity | Expert Interpretation |
|---|---|---|
| `await_in_loop` | high | Sequential bottleneck. Setiap iterasi menunggu. Batch dengan Promise.all |
| `sync_io` | high | Event loop blocker. Semua request lain terhenti selama I/O |
| `eval_usage` | high | V8 optimization killer. Scope tidak bisa di-optimize |
| `delete_operator` | high | Hidden class deopt. Object jadi dictionary mode |
| `json_in_loop` | high | GC pressure. Large temporary objects per iteration |
| `uncleared_timer` | high | Memory leak. Timer terus berjalan tanpa cleanup |
| `sequential_await` | medium | Potential parallelization. Verifikasi dependency antar await |
| `unbounded_collection` | medium | Potential OOM. Tidak ada eviction/size limit |
| `missing_ttl` | medium | Stale data risk. Cache tanpa expiration |
| `key_collision_risk` | medium | Data corruption risk. Key concat tanpa delimiter |
| `allocation_in_loop` | medium | GC pressure. Object creation per iteration |
| `nondeterministic_cache_key` | high | Cache tidak pernah hit. Key berubah setiap saat |

**Topology Findings Interpretation:**

| Finding Type | Severity | Expert Interpretation |
|---|---|---|
| `circular_dependency` | high | Import cycle. Runtime error risk + bundler issue |
| `unreferenced_file` | low | Dead code candidate. Bisa dihapus tanpa dampak |
| `change_risk (high)` | high | File kritis. Banyak dependents atau entrypoint |
| `diamond_dependency` | medium | Redundant paths. Multiple routes ke target yang sama |
| `boundary_violation` | high | Encapsulation leak. Import bypass barrel/public API |
| `boundary_without_public_api` | low | Missing barrel. Cross-boundary access uncontrolled |
| `structural_isomorphism` | low | Type duplication. Consolidation opportunity |

---

## 5. AUTONOMOUS DECISION ENGINE

### 5.1 Kapan Harus Menjalankan Tool

| Situasi | Tool yang Dijalankan | Output Mode |
|---|---|---|
| Baru mulai session / belum paham codebase | `synthesize src` | summary |
| Akan edit file | `brief <file> src` | summary |
| Edit file risk medium/high | `impact <file> src` | full |
| Refactoring besar | `steer src` → `analyze src` | summary → findings |
| Investigasi performance issue | `analyze src --analyzers perf.*` | findings |
| Menambah fitur baru | `analyze src --analyzers topo.*` | findings |
| Setelah perubahan besar | `establish src` | — |
| Verifikasi regresi | `fixture_check.py` | — |

### 5.2 Autonomous Chaining Logic

```
JIKA brief menunjukkan change_risk_level == "high":
  MAKA otomatis jalankan impact <file> src
  DAN baca affected_entrypoints
  DAN jika affected_entrypoints.length > 1:
    MAKA jalankan analyze src --analyzers topo.risk --output findings
    DAN sintesis: file mana lagi yang berisiko?

JIKA synthesize menunjukkan health_score < 0.4:
  MAKA jalankan analyze src --output findings
  DAN prioritaskan findings dengan severity "high"
  DAN laporkan top 3 issues yang paling berdampak

JIKA steer menunjukkan drift_interpretation != "none":
  MAKA jalankan establish src
  DAN catat: baseline telah di-update
  DAN lanjutkan pekerjaan dengan baseline baru

JIKA correlations mengandung "orphan_with_issues":
  MAKA file tersebut adalah cleanup candidate
  DAN bisa dihapus/di-refactor tanpa dampak struktural
  DAN laporkan sebagai opportunity, bukan obligation

JIKA correlations mengandung "circular_with_deopt":
  MAKA ini adalah CRITICAL issue
  DAN harus di-address sebelum perubahan lain
  DAN laporkan dengan urgency tinggi
```

### 5.3 Output Reporting Protocol

Ketika melaporkan hasil analisis, SELALU gunakan format ini:

```
📊 TOPOLOGICAL STATUS
  Archetype: <archetype>
  Health: <score>/1.0
  Complexity: <score>/1.0
  Drift: <interpretation>

⚠️ ACTIVE CONCERNS (sorted by severity)
  [HIGH] <finding_type>: <file> — <observation>
  [MED]  <finding_type>: <file> — <observation>

🎯 REASONING STRATEGY
  Strategy: <reasoning_strategy>
  Budget: <reasoning_budget>
  Regrounding: <yes/no>

💡 OPPORTUNITIES
  <correlation_type>: <observation>
```

---

## 6. EXPERT REASONING PATTERNS

### 6.1 Synthesizing Multiple Outputs

Ketika kamu punya hasil dari multiple analyzers, sintesis dengan pola ini:

```
1. IDENTIFIKASI file yang muncul di multiple findings
   → File yang muncul di >2 analyzer findings adalah HOTSPOT

2. KORELASIKAN dengan topology
   → Hotspot + high fan_in = CRITICAL (banyak yang bergantung)
   → Hotspot + orphan = CLEANUP CANDIDATE (bisa dihapus)
   → Hotspot + entrypoint = PROTECT (jangan ubah sembarangan)

3. PRIORITASKAN berdasarkan impact radius
   → affected_entrypoints > 1 = highest priority
   → downstream_count > 5 = high priority
   → isolated (downstream < 3) = low priority
```

### 6.2 Reading the Topological Fingerprint

```
beta_0 (connected_components):
  1     → Semua terhubung, perubahan bisa propagate ke mana saja
  > 1   → Terfragmentasi, perubahan terisolasi per komponen
  >> 5  → Sangat terfragmentasi, mungkin ada dead modules

beta_1 (independent_cycles):
  0     → Tidak ada circular dependency, DAG murni
  > 0   → Ada cycles, waspadai circular imports
  >> 3  → Banyak cycles, arsitektur perlu review

beta_2 (enclosed_voids):
  0     → Tidak ada missing higher-order structure
  > 0   → Ada "lubang" dalam struktur pengetahuan/dependensi

avg_degree:
  < 2   → Sparse, tree-like
  2-5   → Moderate interconnection
  > 5   → Dense mesh, highly coupled
```

### 6.3 Health Score Action Matrix

| Health Score | Interpretasi | Action |
|---|---|---|
| `> 0.8` | Sangat sehat | Bebas melakukan perubahan |
| `0.6 - 0.8` | Sehat | Perubahan dengan verifikasi standar |
| `0.4 - 0.6` | Moderate | Hati-hati, prioritaskan fix existing issues |
| `0.2 - 0.4` | Bermasalah | Fokus pada perbaikan, hindari fitur baru |
| `< 0.2` | Kritis | Stop fitur baru, dedicated cleanup sprint |

---

## 7. INVARIANT RULES (ATURAN MUTLAK)

1. **READ-ONLY**: Tool tidak pernah mengubah file sumber. Kamu yang mengubah, tool hanya mengamati.
2. **NON-BLOCKING**: Tool tidak pernah melarang perubahan. Keputusan ada padamu.
3. **INFORMATIONAL**: Semua output adalah observasi. Interpretasi dan action adalah tanggung jawabmu.
4. **DETERMINISTIC**: Output selalu konsisten untuk input yang sama. Bisa di-cache dan dibandingkan.
5. **RELATIVE PATHS**: Selalu gunakan relative workspace path (misal `src/app/app.ts`).
6. **FIXTURE SAFETY**: Setelah perubahan pada tool, SELALU jalankan `fixture_check.py`.
7. **SINGLE SCAN**: `hott_kernel.py` melakukan 1 filesystem scan untuk 12 analyzers. Jangan scan berulang.
8. **BASELINE DISCIPLINE**: Jalankan `establish` setelah perubahan struktural besar pada codebase.

---

## 8. QUICK REFERENCE — CLI COMMANDS

```bash
# === PRIMARY (gunakan ini 90% waktu) ===
python3 tools/ai_studio_tool/hott_kernel.py steer src --output summary
python3 tools/ai_studio_tool/hott_kernel.py brief <file> src --output summary
python3 tools/ai_studio_tool/hott_kernel.py impact <file> src
python3 tools/ai_studio_tool/hott_kernel.py analyze src --output summary

# === SECONDARY (untuk drill-down) ===
python3 tools/ai_studio_tool/hott_kernel.py synthesize src --output summary
python3 tools/ai_studio_tool/hott_kernel.py analyze src --analyzers perf.async,perf.deopt --output findings
python3 tools/ai_studio_tool/hott_kernel.py outline <file> src

# === MAINTENANCE ===
python3 tools/ai_studio_tool/hott_kernel.py establish src
python3 tools/ai_studio_tool/fixture_check.py
python3 tools/ai_studio_tool/hott_kernel.py analyzers
```

---

## 9. EXPRESS REST API ENDPOINTS

| Endpoint | Fungsi |
|---|---|
| `GET /api/topology` | Topology graph JSON |
| `GET /api/impact?file=<path>` | Impact analysis |
| `GET /api/outline?file=<path>` | File outline |
| `GET /api/brief?file=<path>` | Brief (outline + impact) |
| `GET /api/async-detector?root=src` | Async anti-patterns |
| `GET /api/deopt-checker?root=src` | V8 deopt patterns |
| `GET /api/gc-pressure?root=src` | GC pressure findings |
| `GET /api/cache-auditor?root=src` | Cache audit findings |
| `GET /api/type-isomorphism?root=src` | Type isomorphism |
| `GET /api/boundary-sheaf?root=src` | Boundary sheaf obstructions |
| `GET /api/homotopy-paths?root=src` | Homotopy path findings |
| `GET /api/topological-integrity?root=src` | Topological integrity report |
| `GET /api/topological-manifold?root=src` | Manifold (Betti numbers) |
| `GET /api/topological-fingerprint?root=src` | Topological fingerprint |
| `GET /api/decoder-steering?mode=steer&root=src` | Steering signals |

---

## 10. FILE STRUCTURE

```
tools/ai_studio_tool/
├── hott_kernel.py                  # Unified entry point (PRIMARY)
├── shared_graph.py                 # SharedGraph builder (1-pass scan)
├── analyzer_registry.py            # 12 analyzer registry
├── performance_analyzers.py        # perf.* analyzers
├── hott_analyzers.py               # hott.* analyzers
├── topology_analyzers.py           # topo.* analyzers + targeted queries
├── synthesizer.py                  # Synthesis + steering engine
├── deprecation.py                  # Deprecation layer
├── baseline/                       # Topological baseline storage
│   └── kernel_baseline.json
├── fixture_check.py                # 27 baseline fixtures
├── tools_schema.json               # AI Agent tool declarations
├── SKILL.md                        # This file
│
├── file_scanner.py                 # [LEGACY] Standalone scanner
├── async_waterfall_detector.py     # [LEGACY] → perf.async
├── deopt_checker.py                # [LEGACY] → perf.deopt
├── gc_pressure_analyzer.py         # [LEGACY] → perf.gc
├── cache_auditor.py                # [LEGACY] → perf.cache
├── type_isomorphism_observer.py    # [LEGACY] → hott.isomorphism
├── boundary_sheaf_checker.py       # [LEGACY] → hott.sheaf
├── homotopy_path_observer.py       # [LEGACY] → hott.homotopy
├── topological_manifold_builder.py # [LEGACY] → hott.manifold
├── topological_integrity_orchestrator.py # [LEGACY] → kernel synthesize
├── invariant_encoder.py            # [LEGACY] → kernel synthesize
└── decoder_steering.py             # [LEGACY] → kernel steer/establish
```
```

---

