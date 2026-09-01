"""Repository-level integration checks for the portable AI Studio tool.

This file intentionally lives outside ``tools/ai_studio_tool``. The Python
tool is the portable product; Angular and REST files are only a target corpus.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TOOL_ROOT = REPOSITORY_ROOT / "tools" / "ai_studio_tool"
KERNEL = TOOL_ROOT / "hott_kernel.py"
FAILURES = []


def expect(condition, message):
    if not condition:
        FAILURES.append(message)


def run_kernel(*args):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(KERNEL), *args],
        cwd=REPOSITORY_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    expect(
        completed.returncode == 0,
        f"KERNEL: {' '.join(args)} gagal ({completed.returncode}): {completed.stderr.strip()}",
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        expect(False, f"KERNEL: {' '.join(args)} bukan JSON valid: {exc}")
        return {}
    expect(not payload.get("error"), f"KERNEL: {payload.get('error')}")
    return payload


def test_portable_tool_bundle():
    """The copied tool directory must pass without repository/Angular files."""
    with tempfile.TemporaryDirectory(prefix="ai-studio-portable-") as temp_dir:
        copied_tool = Path(temp_dir) / "ai_studio_tool"
        shutil.copytree(
            TOOL_ROOT,
            copied_tool,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, "fixture_check.py"],
            cwd=copied_tool,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        expect(
            completed.returncode == 0,
            f"PORTABLE: fixture gagal setelah folder tool disalin: {completed.stdout} {completed.stderr}",
        )
        expect(
            "portable integration smoke aman" in completed.stdout,
            "PORTABLE: fixture bundle tidak mencapai final PASS",
        )


def test_rest_kernel_wiring():
    """REST demo may depend on the kernel, never the other way around."""
    server_source = (REPOSITORY_ROOT / "src" / "server.ts").read_text(encoding="utf-8")
    app_source = (REPOSITORY_ROOT / "src" / "app" / "app.ts").read_text(encoding="utf-8")

    legacy_scripts = {
        "file_scanner.py",
        "async_waterfall_detector.py",
        "deopt_checker.py",
        "gc_pressure_analyzer.py",
        "cache_auditor.py",
        "type_isomorphism_observer.py",
        "boundary_sheaf_checker.py",
        "homotopy_path_observer.py",
        "topological_integrity_orchestrator.py",
        "topological_manifold_builder.py",
        "invariant_encoder.py",
        "decoder_steering.py",
    }
    for script_name in sorted(legacy_scripts):
        expect(script_name not in server_source, f"REST: legacy script tersisa: {script_name}")

    expect("hott_kernel.py" in server_source, "REST: canonical kernel harus digunakan")
    expect("hott_kernel.py" in app_source, "REST: indikator demo harus menyebut canonical kernel")

    routes = {
        "/api/python-info",
        "/api/topology",
        "/api/impact",
        "/api/outline",
        "/api/brief",
        "/api/async-detector",
        "/api/deopt-checker",
        "/api/gc-pressure",
        "/api/cache-auditor",
        "/api/type-isomorphism",
        "/api/boundary-sheaf",
        "/api/homotopy-paths",
        "/api/topological-integrity",
        "/api/topological-manifold",
        "/api/topological-fingerprint",
        "/api/decoder-steering",
    }
    for route in sorted(routes):
        expect(route in server_source, f"REST: route demo hilang: {route}")


def test_angular_cycle_semantics():
    """Angular corpus distinguishes Betti-1 witnesses from circular imports."""
    payload = run_kernel(
        "analyze",
        "src",
        "--analyzers",
        "hott.manifold,topo.circular",
        "--output",
        "findings",
    )
    results = payload.get("analyzers", {}).get("results", {})
    manifold = results.get("hott.manifold", {})
    circular = results.get("topo.circular", {})
    betti = manifold.get("manifold", {}).get("betti_numbers", {})
    basis = manifold.get("cycle_basis", [])

    expect(betti.get("beta_0") == 11, "DEMO: beta_0 harus 11 setelah topology labs ditambahkan")
    expect(betti.get("beta_1") == 3, "DEMO: beta_1 harus 3 setelah cycle lab ditambahkan")
    expect(len(basis) == betti.get("beta_1"), "DEMO: setiap basis cycle harus punya witness")

    directed_paths = [
        set(item.get("vertices", []))
        for item in basis
        if item.get("orientation") == "directed"
    ]
    expected_directed = {
        "src/topology-lab/directed-cycle/a.ts",
        "src/topology-lab/directed-cycle/b.ts",
        "src/topology-lab/directed-cycle/c.ts",
    }
    expect(expected_directed in directed_paths, "DEMO: directed cycle lab harus punya basis witness")

    mixed_paths = [
        set(item.get("vertices", []))
        for item in basis
        if item.get("orientation") == "mixed"
    ]
    expected_diamond = {
        "src/utils/a.ts",
        "src/utils/b.ts",
        "src/utils/c.ts",
        "src/utils/d.ts",
    }
    expect(expected_diamond in mixed_paths, "DEMO: diamond harus tetap menjadi mixed witness")

    circular_findings = circular.get("findings", [])
    expect(len(circular_findings) == 1, "DEMO: hanya cycle lab yang boleh circular berarah")
    expect(
        set(circular_findings[0].get("files", [])) == expected_directed,
        "DEMO: circular finding harus menunjuk tiga file cycle lab",
    )

    model = manifold.get("topological_model", {})
    expect(
        model.get("name") == "dependency_multigraph_1_complex"
        and model.get("edge_orientation_for_betti") == "ignored",
        "DEMO: model harus menjelaskan bahwa Betti mengabaikan orientasi edge",
    )
    expect(
        "not a formal HoTT proof" in model.get("formal_scope", ""),
        "DEMO: batas klaim formal harus dinyatakan",
    )

    steering = run_kernel("steer", "src", "--output", "summary")
    semantics = steering.get("cycle_semantics", {})
    expect(
        semantics.get("directed_basis_witnesses") == 1,
        "DEMO: steering summary harus membawa satu directed basis witness",
    )
    expect(
        semantics.get("mixed_basis_witnesses") == 2,
        "DEMO: steering summary harus membawa dua mixed basis witness",
    )
    expect(
        "Cycle Interpretation:" in steering.get("steering_prompt_block", ""),
        "DEMO: steering prompt harus membawa interpretasi cycle untuk LLM",
    )


def test_angular_test_reachability():
    """Static test paths are evidence for context selection, not coverage."""
    payload = run_kernel(
        "analyze",
        "src",
        "--analyzers",
        "topo.test_reachability",
        "--output",
        "findings",
    )
    result = payload.get("analyzers", {}).get("results", {}).get(
        "topo.test_reachability", {}
    )
    summary = result.get("summary", {})
    expect(summary.get("total_tests") == 2, "DEMO: harus ada dua test file")
    expect(summary.get("total_production_files") == 25, "DEMO: harus ada 25 production source")
    expect(summary.get("directly_tested_files") == 2, "DEMO: dua source harus direct test target")
    expect(summary.get("statically_reachable_files") == 3, "DEMO: tiga source harus reachable")
    expect(summary.get("static_test_reachability_ratio") == 0.12, "DEMO: ratio harus 0.12")
    expect(summary.get("testless_component_count") == 9, "DEMO: harus ada sembilan testless component")
    expect(summary.get("high_influence_without_test_path") == 6, "DEMO: harus ada enam influence gap")

    covered_service = "src/topology-lab/test-reachability/covered.service.ts"
    covered_test = "src/topology-lab/test-reachability/covered.consumer.spec.ts"
    witness = result.get("source_test_witnesses", {}).get(covered_service, [])
    expect(len(witness) == 1, "DEMO: covered service harus punya satu test witness")
    expect(
        witness[0].get("path") == [
            covered_test,
            "src/topology-lab/test-reachability/covered.consumer.ts",
            covered_service,
        ],
        "DEMO: covered service harus punya directional witness path",
    )

    critical_service = "src/topology-lab/test-reachability/critical.service.ts"
    expect(
        critical_service in result.get("unreachable_sources", []),
        "DEMO: critical service harus tidak terjangkau secara statis",
    )
    high_influence_files = {
        item.get("file")
        for item in result.get("findings", [])
        if item.get("type") == "high_influence_without_test_path"
    }
    expect(
        critical_service in high_influence_files,
        "DEMO: critical service harus menjadi high-influence gap",
    )
    expect(
        result.get("model", {}).get("not_runtime_coverage") is True,
        "DEMO: analyzer harus menolak klaim runtime coverage",
    )

    steering = run_kernel("steer", "src", "--output", "summary")
    test_topology = steering.get("test_topology", {})
    expect(
        test_topology.get("summary", {}).get("statically_reachable_files") == 3,
        "DEMO: steering harus membawa test topology summary",
    )
    expect(
        "not runtime coverage" in steering.get("steering_prompt_block", ""),
        "DEMO: steering prompt harus menjaga batas interpretasi coverage",
    )


def test_angular_context_optimizer():
    """Query context must be measured, deterministic, bounded, and target-local."""
    run_kernel("cache", "clear", "src")
    cache_args = (
        "context",
        "nondeterministic cache key",
        "src",
        "--budget-tokens",
        "500",
        "--max-hops",
        "1",
        "--detail",
        "source",
        "--output",
        "prompt",
    )
    cache_context = run_kernel(*cache_args)
    repeated = run_kernel(*cache_args)
    cache_file = "src/services/cache.service.ts"
    first_cache = cache_context.get("graph_cache", {})
    repeated_cache = repeated.get("graph_cache", {})
    first_analyzer_cache = cache_context.get("analyzer_cache", {})
    repeated_analyzer_cache = repeated.get("analyzer_cache", {})
    expect(first_cache.get("status") == "miss", "DEMO: context awal harus cache miss")
    expect(first_cache.get("files_read") == 27, "DEMO: miss harus membaca 27 source")
    expect(repeated_cache.get("status") == "hit", "DEMO: context kedua harus cache hit")
    expect(repeated_cache.get("files_reused") == 27, "DEMO: hit harus reuse 27 source")
    expect(repeated_cache.get("files_read") == 0, "DEMO: hit tidak boleh membaca source")
    expect(first_analyzer_cache.get("status") == "miss", "DEMO: analyzer awal harus miss")
    expect(first_analyzer_cache.get("executed_count") == 13, "DEMO: awal harus eksekusi 13 analyzer")
    expect(repeated_analyzer_cache.get("status") == "hit", "DEMO: analyzer kedua harus hit")
    expect(repeated_analyzer_cache.get("reused_count") == 13, "DEMO: hit harus reuse 13 analyzer")
    expect(repeated_analyzer_cache.get("executed_count") == 0, "DEMO: hit tidak boleh eksekusi analyzer")
    expect(
        cache_context.get("provenance", {}).get("analyzer_cache") == first_analyzer_cache,
        "DEMO: provenance context harus membawa analyzer cache yang sama",
    )
    expect(
        cache_context.get("selection", {}).get("selected_paths") == [cache_file],
        "DEMO: query cache harus memilih cache.service tanpa target eksplisit",
    )
    expect(
        "perf.cache:nondeterministic_cache_key:high"
        in cache_context.get("context_block", ""),
        "DEMO: context harus membawa finding witness yang cocok dengan query",
    )
    expect(
        "Date.now()" in cache_context.get("context_block", ""),
        "DEMO: context harus membawa source excerpt yang relevan",
    )
    budget = cache_context.get("budget", {})
    expect(budget.get("within_budget") is True, "DEMO: context harus mematuhi hard budget")
    expect(
        budget.get("used_chars", 1) <= budget.get("char_budget", 0),
        "DEMO: used chars tidak boleh melewati budget",
    )
    expect(
        cache_context.get("provenance", {}).get("optimizer_additional_filesystem_scans") == 0,
        "DEMO: optimizer harus reuse SharedGraph tanpa scan tambahan",
    )
    memory_retrieval = cache_context.get("memory_context", {}).get("retrieval", {})
    memory_projection = memory_retrieval.get("projection", {})
    repeated_memory_projection = repeated.get("memory_context", {}).get(
        "retrieval", {}
    ).get("projection", {})
    expect(
        memory_retrieval.get("model")
        == "scoped_memory_recall_projection_v3_freshness"
        and memory_projection.get("source_store_loads") == 1
        and memory_projection.get("cache", {}).get("status") == "miss"
        and memory_projection.get("snapshot_consistent") is True,
        "DEMO: context memory harus memakai satu snapshot recall projection",
    )
    expect(
        repeated_memory_projection.get("source_store_loads") == 0
        and repeated_memory_projection.get("cache", {}).get("status") == "hit"
        and repeated_memory_projection.get("cache", {}).get(
            "entries_reused"
        ) == repeated_memory_projection.get("snapshot_memory_count"),
        "DEMO: context kedua harus reuse recall projection tanpa parse store",
    )
    expect(
        memory_projection.get("omitted_semantic_relevance_proven") is False
        and str(memory_projection.get("snapshot_signature", "")).startswith("sha256:"),
        "DEMO: recall projection harus membawa signature dan batas omission",
    )
    expect(
        cache_context.get("context_block") == repeated.get("context_block"),
        "DEMO: context block untuk snapshot dan query yang sama harus deterministik",
    )
    expect(
        memory_projection.get("snapshot_signature")
        == repeated_memory_projection.get("snapshot_signature"),
        "DEMO: memory projection signature harus stabil pada snapshot identik",
    )
    expect(
        cache_context.get("provenance", {}).get("graph_content_signature")
        == repeated.get("provenance", {}).get("graph_content_signature"),
        "DEMO: content provenance harus stabil",
    )

    critical_service = "src/topology-lab/test-reachability/critical.service.ts"
    target_context = run_kernel(
        "context",
        "critical service change risk",
        "src",
        "--target",
        critical_service,
        "--budget-tokens",
        "700",
        "--max-hops",
        "1",
        "--output",
        "summary",
    )
    expect(
        target_context.get("selection", {}).get("graph_seeds") == [critical_service],
        "DEMO: explicit target harus menjadi base projection tunggal",
    )
    expect(
        target_context.get("selection", {}).get("selected_paths") == [
            critical_service,
            "src/topology-lab/test-reachability/critical.consumer-a.ts",
            "src/topology-lab/test-reachability/critical.consumer-b.ts",
        ],
        "DEMO: target context harus memilih target dan neighbor satu hop saja",
    )
    expect(
        target_context.get("quotient_summary", {}).get("original_vertex_count") == 27,
        "DEMO: quotient harus berasal dari snapshot Angular lengkap",
    )
    cache_status = run_kernel("cache", "status", "src").get("cache", {})
    expect(
        cache_status.get("memory_recall_cache", {}).get("status") == "valid",
        "DEMO: cache status harus mencakup scoped memory recall projection",
    )
    cleared = run_kernel("cache", "clear", "src").get("cache", {})
    expect(
        cleared.get("memory_recall_cache", {}).get("status") == "cleared",
        "DEMO: cache clear harus menghapus derived recall cache",
    )


def main():
    for test in (
        test_portable_tool_bundle,
        test_rest_kernel_wiring,
        test_angular_cycle_semantics,
        test_angular_test_reachability,
        test_angular_context_optimizer,
    ):
        try:
            test()
        except Exception as exc:
            FAILURES.append(f"{test.__name__}: exception {exc}")

    if FAILURES:
        print("FAIL")
        for failure in FAILURES:
            print(f"- {failure}")
        raise SystemExit(1)

    print("PASS: portable tool + Angular demo integration aman")


if __name__ == "__main__":
    main()
