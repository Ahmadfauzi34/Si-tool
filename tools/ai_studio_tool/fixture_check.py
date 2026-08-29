#!/usr/bin/env python3
"""
Fixture check minimal untuk mengunci baseline file_scanner.

Fixture yang dikunci:
- F01 basic relative import
- F02 extensionless import
- F04 tsx/jsx support
- F05 unresolved import tidak menjadi edge utama
- F09 circular dependency aman

Script ini:
- membuat fixture otomatis
- menjalankan scan_topology
- menjalankan get_impacted_files
- melakukan assertion minimal
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codebase import file_scanner

FIXTURES = {
    # F01 basic relative import
    Path("fixtures_min/f01_basic/project/src/a.ts"): (
        "export const a = 'a';\n"
    ),
    Path("fixtures_min/f01_basic/project/src/b.ts"): (
        "import { a } from './a.ts';\n"
        "export const b = a;\n"
    ),

    # F02 extensionless import
    Path("fixtures_min/f02_extensionless/project/src/logger.ts"): (
        "export function log() { return true; }\n"
    ),
    Path("fixtures_min/f02_extensionless/project/src/app.ts"): (
        "import { log } from './logger';\n"
        "export const app = log;\n"
    ),

    # F04 tsx/jsx support
    Path("fixtures_min/f04_tsx_jsx/project/src/Button.tsx"): (
        "export const Button = () => null;\n"
    ),
    Path("fixtures_min/f04_tsx_jsx/project/src/Card.jsx"): (
        "export const Card = () => null;\n"
    ),
    Path("fixtures_min/f04_tsx_jsx/project/src/app.tsx"): (
        "import { Button } from './Button';\n"
        "import { Card } from './Card';\n"
        "export const App = () => null;\n"
    ),

    # F05 unresolved import
    Path("fixtures_min/f05_unresolved/project/src/app.ts"): (
        "import { missing } from './missing';\n"
        "export const app = true;\n"
    ),

    # F09 circular dependency
    Path("fixtures_min/f09_circular/project/src/a.ts"): (
        "import './b';\n"
        "export const a = 'a';\n"
    ),
    Path("fixtures_min/f09_circular/project/src/b.ts"): (
        "import './c';\n"
        "export const b = 'b';\n"
    ),
    Path("fixtures_min/f09_circular/project/src/c.ts"): (
        "import './a';\n"
        "export const c = 'c';\n"
    ),

    # F08 entrypoint detection
    Path("fixtures_min/f08_entrypoint/project/src/main.ts"): (
        "import './app';\n"
        "export const main = true;\n"
    ),
    Path("fixtures_min/f08_entrypoint/project/src/app.ts"): (
        "import './util';\n"
        "export const app = true;\n"
    ),
    Path("fixtures_min/f08_entrypoint/project/src/util.ts"): (
        "export const util = true;\n"
    ),

    # F10 graph metrics
    Path("fixtures_min/f10_graph_metrics/project/src/a.ts"): (
        "import './d';\n"
        "export const a = 'a';\n"
    ),
    Path("fixtures_min/f10_graph_metrics/project/src/b.ts"): (
        "import './a';\n"
        "export const b = 'b';\n"
    ),
    Path("fixtures_min/f10_graph_metrics/project/src/c.ts"): (
        "import './a';\n"
        "export const c = 'c';\n"
    ),
    Path("fixtures_min/f10_graph_metrics/project/src/d.ts"): (
        "export const d = 'd';\n"
    ),

    # F11 change risk advisory
    Path("fixtures_min/f11_change_risk_advisory/project/src/main.ts"): (
        "import './app';\n"
        "export const main = true;\n"
    ),
    Path("fixtures_min/f11_change_risk_advisory/project/src/server.ts"): (
        "import './app';\n"
        "export const server = true;\n"
    ),
    Path("fixtures_min/f11_change_risk_advisory/project/src/app.ts"): (
        "import './util';\n"
        "export const app = true;\n"
    ),
    Path("fixtures_min/f11_change_risk_advisory/project/src/util.ts"): (
        "export const util = true;\n"
    ),
    Path("fixtures_min/f11_change_risk_advisory/project/src/isolated.ts"): (
        "export const isolated = true;\n"
    ),

    # F12 unreferenced files observation
    Path("fixtures_min/f12_unreferenced_files/project/src/main.ts"): (
        "import './app';\n"
        "export const main = true;\n"
    ),
    Path("fixtures_min/f12_unreferenced_files/project/src/app.ts"): (
        "import './util';\n"
        "export const app = true;\n"
    ),
    Path("fixtures_min/f12_unreferenced_files/project/src/util.ts"): (
        "export const util = true;\n"
    ),
    Path("fixtures_min/f12_unreferenced_files/project/src/unused.ts"): (
        "export const unused = true;\n"
    ),
    Path("fixtures_min/f12_unreferenced_files/project/src/app.spec.ts"): (
        "export const spec = true;\n"
    ),
    Path("fixtures_min/f13_multi_root/root_a/a.ts"): (
        "import '../root_b/b';\n"
        "export const a = true;\n"
    ),
    Path("fixtures_min/f13_multi_root/root_b/b.ts"): (
        "export const b = true;\n"
    ),
    Path("fixtures_min/f13_multi_root/root_b/c.ts"): (
        "import './b';\n"
        "export const c = true;\n"
    ),
    # F14 file outline
    Path("fixtures_min/f14_outline/project/src/sample.ts"): (
        "import './util';\n"
        "import { externalThing } from 'some-lib';\n"
        "\n"
        "export interface Sample {\n"
        "  id: string;\n"
        "}\n"
        "\n"
        "export type SampleId = string;\n"
        "\n"
        "export const sampleName = 'sample';\n"
        "\n"
        "export function sampleFunction(value: string) {\n"
        "  return value;\n"
        "}\n"
        "\n"
        "export class SampleClass {\n"
        "  run() {\n"
        "    return true;\n"
        "  }\n"
        "}\n"
    ),
    Path("fixtures_min/f14_outline/project/src/util.ts"): (
        "export const util = true;\n"
    ),
    # F15 alias paths
    Path("fixtures_min/f15_alias_paths/project/tsconfig.json"): (
        "{\n"
        "  \"compilerOptions\": {\n"
        "    \"baseUrl\": \".\",\n"
        "    \"paths\": {\n"
        "      \"@app/*\": [\"src/app/*\"],\n"
        "      \"@core/*\": [\"src/core/*\"]\n"
        "    }\n"
        "  }\n"
        "}\n"
    ),
    Path("fixtures_min/f15_alias_paths/project/src/core/logger.ts"): (
        "export const logger = true;\n"
    ),
    Path("fixtures_min/f15_alias_paths/project/src/app/app.ts"): (
        "import { logger } from '@core/logger';\n"
        "import { externalThing } from 'some-lib';\n"
        "export const app = logger;\n"
    ),
    # F16 file brief context budgeting
    Path("fixtures_min/f16_file_brief/project/src/main.ts"): (
        "import './app';\n"
        "export const main = true;\n"
    ),
    Path("fixtures_min/f16_file_brief/project/src/app.ts"): (
        "import './util';\n"
        "export function runApp() { return true; }\n"
        "export class AppService {}\n"
    ),
    Path("fixtures_min/f16_file_brief/project/src/util.ts"): (
        "export const util = true;\n"
    ),
    # F17 async waterfall detection
    Path("fixtures_min/f17_async_waterfall/project/src/service.ts"): (
        "import { Injectable } from '@angular/core';\n"
        "\n"
        "@Injectable()\n"
        "export class DataService {\n"
        "  async loadData() {\n"
        "    const users = await this.fetchUsers();\n"
        "    const orders = await this.fetchOrders();\n"
        "    const config = await this.fetchConfig();\n"
        "    return { users, orders, config };\n"
        "  }\n"
        "\n"
        "  async processItems(ids: string[]) {\n"
        "    for (const id of ids) {\n"
        "      const item = await this.fetchItem(id);\n"
        "      console.log(item);\n"
        "    }\n"
        "  }\n"
        "}\n"
    ),
    # F18 deopt checker
    Path("fixtures_min/f18_deopt_checker/project/src/service.ts"): (
        "export class DataService {\n"
        "  processConfig() {\n"
        "    const config = { host: 'localhost', port: 3000 };\n"
        "    config.timeout = 5000;\n"
        "    delete config.port;\n"
        "    return config;\n"
        "  }\n"
        "\n"
        "  dynamicEval(code: string) {\n"
        "    return eval(code);\n"
        "  }\n"
        "}\n"
    ),
    # F19 gc pressure
    Path("fixtures_min/f19_gc_pressure/project/src/processor.ts"): (
        "export class DataProcessor {\n"
        "  private cache = new Map();\n"
        "\n"
        "  processItems(items: any[]) {\n"
        "    const results = [];\n"
        "    for (const item of items) {\n"
        "      const parsed = JSON.parse(item.data);\n"
        "      const result = { id: parsed.id, value: parsed.value };\n"
        "      results.push(result);\n"
        "    }\n"
        "    return results;\n"
        "  }\n"
        "\n"
        "  setupPolling() {\n"
        "    const timer = setInterval(() => {\n"
        "      this.poll();\n"
        "    }, 5000);\n"
        "  }\n"
        "\n"
        "  attachListener(el: HTMLElement) {\n"
        "    el.addEventListener('resize', this.handleResize);\n"
        "  }\n"
        "}\n"
    ),
    # F20 cache auditor
    Path("fixtures_min/f20_cache_audit/project/src/cache.service.ts"): (
        "export class CacheService {\n"
        "  private dataCache = new Map();\n"
        "  private sessionCache = new Map();\n"
        "\n"
        "  setWithTimestamp(key: string, value: any) {\n"
        "    const cacheKey = key + Date.now();\n"
        "    this.dataCache.set(cacheKey, value);\n"
        "  }\n"
        "\n"
        "  setWithConcat(userId: string, productId: string) {\n"
        "    const key = userId + productId;\n"
        "    this.dataCache.set(key, { userId, productId });\n"
        "  }\n"
        "\n"
        "  setObjectKey(config: any, result: any) {\n"
        "    this.sessionCache.set(config, result);\n"
        "  }\n"
        "\n"
        "  getWithObject(config: any) {\n"
        "    return this.sessionCache.get(config);\n"
        "  }\n"
        "}\n"
    ),
    # F21 type isomorphism observer (proto-HoTT)
    Path("fixtures_min/f21_type_isomorphism/project/src/types.ts"): (
        "export interface UserDTO {\n"
        "  id: string;\n"
        "  name: string;\n"
        "  email: string;\n"
        "}\n"
        "\n"
        "export interface UserViewModel {\n"
        "  id: string;\n"
        "  name: string;\n"
        "  email: string;\n"
        "}\n"
        "\n"
        "export interface Product {\n"
        "  sku: string;\n"
        "  price: number;\n"
        "}\n"
        "\n"
        "export type ProductAlias = {\n"
        "  sku: string;\n"
        "  price: number;\n"
        "};\n"
        "\n"
        "export interface Order {\n"
        "  orderId: string;\n"
        "  total: number;\n"
        "  createdAt: string;\n"
        "}\n"
    ),
    # F22 boundary sheaf checker
    Path("fixtures_min/f22_boundary_sheaf/project/src/core/index.ts"): (
        "export { AuthService } from './services/auth.service';\n"
        "export type { CoreConfig } from './types';\n"
    ),
    Path("fixtures_min/f22_boundary_sheaf/project/src/core/services/auth.service.ts"): (
        "export class AuthService {\n"
        "  login() { return true; }\n"
        "}\n"
    ),
    Path("fixtures_min/f22_boundary_sheaf/project/src/core/types.ts"): (
        "export interface CoreConfig {\n"
        "  apiUrl: string;\n"
        "  timeout: number;\n"
        "}\n"
    ),
    Path("fixtures_min/f22_boundary_sheaf/project/src/app/index.ts"): (
        "export { AppComponent } from './app.component';\n"
    ),
    Path("fixtures_min/f22_boundary_sheaf/project/src/app/app.component.ts"): (
        "import { AuthService } from '../core/services/auth.service';\n"
        "export class AppComponent {\n"
        "  constructor(private auth: AuthService) {}\n"
        "}\n"
    ),
    Path("fixtures_min/f22_boundary_sheaf/project/src/app/models.ts"): (
        "export interface CoreConfig {\n"
        "  apiUrl: string;\n"
        "  retries: number;\n"
        "}\n"
    ),
    # F23 boundary sheaf entrypoint + no-barrel precision
    Path("fixtures_min/f23_sheaf_precision/project/src/main.ts"): (
        "import { App } from './app/app';\n"
        "export function bootstrap() { return new App(); }\n"
    ),
    Path("fixtures_min/f23_sheaf_precision/project/src/app/app.ts"): (
        "export class App {}\n"
    ),
    # F24 homotopy path observer
    Path("fixtures_min/f24_homotopy_path/project/src/a.ts"): (
        "import './b';\n"
        "import './c';\n"
        "import './util';\n"
        "import { helper } from './util';\n"
        "export const a = true;\n"
    ),
    Path("fixtures_min/f24_homotopy_path/project/src/b.ts"): (
        "import './d';\n"
        "export const b = true;\n"
    ),
    Path("fixtures_min/f24_homotopy_path/project/src/c.ts"): (
        "import './d';\n"
        "export const c = true;\n"
    ),
    Path("fixtures_min/f24_homotopy_path/project/src/d.ts"): (
        "export const d = true;\n"
    ),
    Path("fixtures_min/f24_homotopy_path/project/src/util.ts"): (
        "export const helper = true;\n"
    ),
    # F25 topological integrity orchestrator
    Path("fixtures_min/f25_synthesis/project/src/a.ts"): (
        "import './b';\n"
        "import './c';\n"
        "export const a = true;\n"
    ),
    Path("fixtures_min/f25_synthesis/project/src/b.ts"): (
        "import './d';\n"
        "export const b = true;\n"
    ),
    Path("fixtures_min/f25_synthesis/project/src/c.ts"): (
        "import './d';\n"
        "export const c = true;\n"
    ),
    Path("fixtures_min/f25_synthesis/project/src/d.ts"): (
        "export const d = true;\n"
    ),
    # F26 topological manifold builder
    Path("fixtures_min/f26_manifold/project/src/a.ts"): (
        "import './b';\n"
        "import './c';\n"
        "export const a = true;\n"
    ),
    Path("fixtures_min/f26_manifold/project/src/b.ts"): (
        "import './c';\n"
        "export const b = true;\n"
    ),
    Path("fixtures_min/f26_manifold/project/src/c.ts"): (
        "export const c = true;\n"
    ),
    # F27 invariant encoder
    Path("fixtures_min/f27_encoder/project/src/a.ts"): (
        "import './b';\n"
        "import './c';\n"
        "export const a = true;\n"
    ),
    Path("fixtures_min/f27_encoder/project/src/b.ts"): (
        "export const b = true;\n"
    ),
    Path("fixtures_min/f27_encoder/project/src/c.ts"): (
        "export const c = true;\n"
    ),
    # F28 decoder steering
    Path("fixtures_min/f28_steering/project/src/a.ts"): (
        "import './b';\n"
        "import './c';\n"
        "export const a = true;\n"
    ),
    Path("fixtures_min/f28_steering/project/src/b.ts"): (
        "export const b = true;\n"
    ),
    Path("fixtures_min/f28_steering/project/src/c.ts"): (
        "export const c = true;\n"
    ),
    # F29 archetype calibration
    Path("fixtures_min/f29_archetype_calibration/project/src/a.ts"): (
        "import './b';\n"
        "export const a = true;\n"
    ),
    Path("fixtures_min/f29_archetype_calibration/project/src/b.ts"): (
        "import './c';\n"
        "export const b = true;\n"
    ),
    Path("fixtures_min/f29_archetype_calibration/project/src/c.ts"): (
        "import './a';\n"
        "export const c = true;\n"
    ),
    Path("fixtures_min/f29_archetype_calibration/project/src/d.ts"): (
        "import './e';\n"
        "export const d = true;\n"
    ),
    Path("fixtures_min/f29_archetype_calibration/project/src/e.ts"): (
        "export const e = true;\n"
    ),
    # F30 complexity calibration
    Path("fixtures_min/f30_complexity_calibration/project/src/a.ts"): (
        "import './b';\n"
        "export const a = true;\n"
    ),
    Path("fixtures_min/f30_complexity_calibration/project/src/b.ts"): (
        "export const b = true;\n"
    ),
    # F32 reciprocal imports are parallel 1-cells after orientation is forgotten
    Path("fixtures_min/f32_reciprocal_cycle/project/src/a.ts"): (
        "import './b';\n"
        "export const a = true;\n"
    ),
    Path("fixtures_min/f32_reciprocal_cycle/project/src/b.ts"): (
        "import './a';\n"
        "export const b = true;\n"
    ),
    # F33 static test import reachability (not runtime coverage)
    Path("fixtures_min/f33_test_reachability/project/src/app.spec.ts"): (
        "import './app';\n"
        "export const appSpec = true;\n"
    ),
    Path("fixtures_min/f33_test_reachability/project/src/app.ts"): (
        "import './service';\n"
        "export const app = true;\n"
    ),
    Path("fixtures_min/f33_test_reachability/project/src/service.ts"): (
        "import './core';\n"
        "export const service = true;\n"
    ),
    Path("fixtures_min/f33_test_reachability/project/src/core.ts"): (
        "export const core = true;\n"
    ),
    Path("fixtures_min/f33_test_reachability/project/src/critical.ts"): (
        "export const critical = true;\n"
    ),
    Path("fixtures_min/f33_test_reachability/project/src/consumer-a.ts"): (
        "import './critical';\n"
        "export const consumerA = true;\n"
    ),
    Path("fixtures_min/f33_test_reachability/project/src/consumer-b.ts"): (
        "import './critical';\n"
        "export const consumerB = true;\n"
    ),
    Path("fixtures_min/f33_test_reachability/project/src/orphan.spec.ts"): (
        "export const orphanSpec = true;\n"
    ),
    # F34 query-directed context projection and boundary quotient
    Path("fixtures_min/f34_context_optimizer/project/src/orders/pricing.ts"): (
        "export function calculatePricing(quantity: number) {\n"
        "  return quantity * 100;\n"
        "}\n"
    ),
    Path("fixtures_min/f34_context_optimizer/project/src/orders/repository.ts"): (
        "export const orderRepository = new Map<string, number>();\n"
    ),
    Path("fixtures_min/f34_context_optimizer/project/src/orders/order.service.ts"): (
        "import { calculatePricing } from './pricing';\n"
        "import { orderRepository } from './repository';\n"
        "export const createOrder = (id: string, quantity: number) => {\n"
        "  orderRepository.set(id, calculatePricing(quantity));\n"
        "};\n"
    ),
    Path("fixtures_min/f34_context_optimizer/project/src/orders/order.controller.ts"): (
        "import { createOrder } from './order.service';\n"
        "export const submitOrder = createOrder;\n"
    ),
    Path("fixtures_min/f34_context_optimizer/project/src/orders/order.spec.ts"): (
        "import { submitOrder } from './order.controller';\n"
        "export const orderSpec = submitOrder;\n"
    ),
    Path("fixtures_min/f34_context_optimizer/project/src/auth/auth.service.ts"): (
        "export const authenticate = () => true;\n"
    ),
    # F35 persistent SharedGraph cache and file-level invalidation
    Path("fixtures_min/f35_incremental_cache/project/src/a.ts"): (
        "import './b';\n"
        "export const a = true;\n"
    ),
    Path("fixtures_min/f35_incremental_cache/project/src/b.ts"): (
        "export const b = true;\n"
    ),
    Path("fixtures_min/f35_incremental_cache/project/src/c.ts"): (
        "export const c = true;\n"
    ),
}

FAILURES = []


def expect(condition, message):
    if not condition:
        FAILURES.append(message)


def write_fixtures():
    for rel_path, content in FIXTURES.items():
        rel_path.parent.mkdir(parents=True, exist_ok=True)
        rel_path.write_text(content, encoding="utf-8")


def node_ids(topology):
    return {node["id"] for node in topology.get("nodes", [])}


def edge_pairs(topology):
    return {(edge["source"], edge["target"]) for edge in topology.get("edges", [])}


def require_trust_layer(topology, name):
    expect("summary" in topology, f"{name}: topology harus punya summary")
    expect("diagnostics" in topology, f"{name}: topology harus punya diagnostics")


def test_f01_basic_relative():
    name = "F01"
    project = "fixtures_min/f01_basic/project"
    topology = file_scanner.scan_topology(path=project)
    require_trust_layer(topology, name)

    expected_nodes = {
        f"{project}/src/a.ts",
        f"{project}/src/b.ts",
    }

    expected_edges = {
        (f"{project}/src/b.ts", f"{project}/src/a.ts"),
    }

    expect(topology["summary"]["total_nodes"] == 2, f"{name}: total_nodes harus 2")
    expect(topology["summary"]["unresolved_import_count"] == 0, f"{name}: unresolved harus 0")
    expect(node_ids(topology) == expected_nodes, f"{name}: nodes tidak sesuai")
    expect(edge_pairs(topology) == expected_edges, f"{name}: edges tidak sesuai")

    if topology.get("edges"):
        edge = topology["edges"][0]
        expect(edge.get("status") == "resolved", f"{name}: edge harus resolved")
        expect(edge.get("method") == "exact_match", f"{name}: edge harus exact_match")

    impact = file_scanner.get_impacted_files(
        f"{project}/src/a.ts",
        topology=topology
    )

    expect(
        impact["downstream"] == [f"{project}/src/b.ts"],
        f"{name}: downstream a.ts harus b.ts"
    )
    expect(
        impact["upstream"] == [],
        f"{name}: upstream a.ts harus kosong"
    )


def test_f02_extensionless():
    name = "F02"
    project = "fixtures_min/f02_extensionless/project"
    topology = file_scanner.scan_topology(path=project)
    require_trust_layer(topology, name)

    expected_nodes = {
        f"{project}/src/logger.ts",
        f"{project}/src/app.ts",
    }

    expected_edges = {
        (f"{project}/src/app.ts", f"{project}/src/logger.ts"),
    }

    expect(topology["summary"]["total_nodes"] == 2, f"{name}: total_nodes harus 2")
    expect(topology["summary"]["unresolved_import_count"] == 0, f"{name}: unresolved harus 0")
    expect(node_ids(topology) == expected_nodes, f"{name}: nodes tidak sesuai")
    expect(edge_pairs(topology) == expected_edges, f"{name}: edges tidak sesuai")

    if topology.get("edges"):
        edge = topology["edges"][0]
        expect(
            edge.get("status") == "resolved_with_assumption",
            f"{name}: extensionless import harus resolved_with_assumption"
        )
        expect(
            edge.get("method") == "extension_match",
            f"{name}: extensionless import harus extension_match"
        )

    impact = file_scanner.get_impacted_files(
        f"{project}/src/logger.ts",
        topology=topology
    )

    expect(
        impact["downstream"] == [f"{project}/src/app.ts"],
        f"{name}: downstream logger.ts harus app.ts"
    )


def test_f04_tsx_jsx():
    name = "F04"
    project = "fixtures_min/f04_tsx_jsx/project"
    topology = file_scanner.scan_topology(path=project)
    require_trust_layer(topology, name)

    expected_nodes = {
        f"{project}/src/Button.tsx",
        f"{project}/src/Card.jsx",
        f"{project}/src/app.tsx",
    }

    expected_edges = {
        (f"{project}/src/app.tsx", f"{project}/src/Button.tsx"),
        (f"{project}/src/app.tsx", f"{project}/src/Card.jsx"),
    }

    expect(topology["summary"]["total_nodes"] == 3, f"{name}: total_nodes harus 3")
    expect(topology["summary"]["total_edges"] == 2, f"{name}: total_edges harus 2")
    expect(topology["summary"]["unresolved_import_count"] == 0, f"{name}: unresolved harus 0")
    expect(node_ids(topology) == expected_nodes, f"{name}: nodes tidak sesuai")
    expect(edge_pairs(topology) == expected_edges, f"{name}: edges tidak sesuai")

    impact_button = file_scanner.get_impacted_files(
        f"{project}/src/Button.tsx",
        topology=topology
    )

    impact_card = file_scanner.get_impacted_files(
        f"{project}/src/Card.jsx",
        topology=topology
    )

    expect(
        impact_button["downstream"] == [f"{project}/src/app.tsx"],
        f"{name}: downstream Button.tsx harus app.tsx"
    )

    expect(
        impact_card["downstream"] == [f"{project}/src/app.tsx"],
        f"{name}: downstream Card.jsx harus app.tsx"
    )


def test_f05_unresolved():
    name = "F05"
    project = "fixtures_min/f05_unresolved/project"
    topology = file_scanner.scan_topology(path=project)
    require_trust_layer(topology, name)

    expected_nodes = {
        f"{project}/src/app.ts",
    }

    expect(topology["summary"]["total_nodes"] == 1, f"{name}: total_nodes harus 1")
    expect(topology["summary"]["total_edges"] == 0, f"{name}: unresolved tidak boleh jadi edge utama")
    expect(topology["summary"]["unresolved_import_count"] == 1, f"{name}: unresolved harus 1")
    expect(node_ids(topology) == expected_nodes, f"{name}: nodes tidak sesuai")
    expect(edge_pairs(topology) == set(), f"{name}: edges utama harus kosong")

    unresolved = topology["diagnostics"]["unresolved_imports"]
    expect(len(unresolved) == 1, f"{name}: diagnostics unresolved harus 1 item")

    if unresolved:
        item = unresolved[0]
        expect(item.get("importer") == f"{project}/src/app.ts", f"{name}: importer unresolved salah")
        expect(item.get("raw_import") == "./missing", f"{name}: raw_import unresolved salah")
        expect("attempted_candidates" in item, f"{name}: unresolved harus punya attempted_candidates")

    impact = file_scanner.get_impacted_files(
        f"{project}/src/app.ts",
        topology=topology
    )

    expect(
        impact["downstream"] == [],
        f"{name}: downstream app.ts harus kosong"
    )

    expect(
        len(impact.get("unresolved_dependency_warnings", [])) == 1,
        f"{name}: impact harus membawa unresolved_dependency_warnings"
    )


def test_f09_circular():
    name = "F09"
    project = "fixtures_min/f09_circular/project"
    topology = file_scanner.scan_topology(path=project)
    require_trust_layer(topology, name)

    expected_nodes = {
        f"{project}/src/a.ts",
        f"{project}/src/b.ts",
        f"{project}/src/c.ts",
    }

    expected_edges = {
        (f"{project}/src/a.ts", f"{project}/src/b.ts"),
        (f"{project}/src/b.ts", f"{project}/src/c.ts"),
        (f"{project}/src/c.ts", f"{project}/src/a.ts"),
    }

    expect(topology["summary"]["total_nodes"] == 3, f"{name}: total_nodes harus 3")
    expect(topology["summary"]["total_edges"] == 3, f"{name}: total_edges harus 3")
    expect(topology["summary"]["unresolved_import_count"] == 0, f"{name}: unresolved harus 0")
    expect(node_ids(topology) == expected_nodes, f"{name}: nodes tidak sesuai")
    expect(edge_pairs(topology) == expected_edges, f"{name}: edges tidak sesuai")

    impact = file_scanner.get_impacted_files(
        f"{project}/src/a.ts",
        topology=topology
    )

    expected_downstream = {
        f"{project}/src/b.ts",
        f"{project}/src/c.ts",
    }

    expect(
        set(impact["downstream"]) == expected_downstream,
        f"{name}: downstream a.ts harus mencakup b.ts dan c.ts"
    )

    expect(
        len(impact["circular_references"]) > 0,
        f"{name}: circular_references harus terdeteksi"
    )


def test_f08_entrypoint():
    name = "F08"
    project = "fixtures_min/f08_entrypoint/project"
    topology = file_scanner.scan_topology(path=project)
    require_trust_layer(topology, name)

    expected_nodes = {
        f"{project}/src/main.ts",
        f"{project}/src/app.ts",
        f"{project}/src/util.ts",
    }

    expect(topology["summary"]["total_nodes"] == 3, f"{name}: total_nodes harus 3")
    expect(topology["summary"]["unresolved_import_count"] == 0, f"{name}: unresolved harus 0")
    expect(node_ids(topology) == expected_nodes, f"{name}: nodes tidak sesuai")

    expect(
        topology["summary"].get("entrypoint_count") == 1,
        f"{name}: entrypoint_count harus 1"
    )

    nodes_by_id = {node["id"]: node for node in topology.get("nodes", [])}
    main_id = f"{project}/src/main.ts"

    main_node = nodes_by_id.get(main_id, {})
    expect(
        main_node.get("is_entrypoint") is True,
        f"{name}: main.ts harus ditandai sebagai entrypoint"
    )
    expect(
        main_node.get("entrypoint_kind") == "browser_bootstrap",
        f"{name}: main.ts harus punya entrypoint_kind browser_bootstrap"
    )
    expect(
        main_node.get("entrypoint_confidence", 0) >= 0.8,
        f"{name}: confidence entrypoint main.ts harus cukup tinggi"
    )

    impact_util = file_scanner.get_impacted_files(
        f"{project}/src/util.ts",
        topology=topology
    )

    expect(
        impact_util.get("affected_entrypoints") == [main_id],
        f"{name}: perubahan util.ts harus berdampak ke main.ts"
    )

    impact_main = file_scanner.get_impacted_files(
        main_id,
        topology=topology
    )

    expect(
        impact_main.get("target_is_entrypoint") is True,
        f"{name}: main.ts harus ditandai sebagai target entrypoint"
    )

    expect(
        impact_main.get("affected_entrypoints") == [main_id],
        f"{name}: impact main.ts harus menyertakan dirinya sebagai affected_entrypoints"
    )


def test_f10_graph_metrics():
    name = "F10"
    project = "fixtures_min/f10_graph_metrics/project"
    topology = file_scanner.scan_topology(path=project)
    require_trust_layer(topology, name)

    expected_nodes = {
        f"{project}/src/a.ts",
        f"{project}/src/b.ts",
        f"{project}/src/c.ts",
        f"{project}/src/d.ts",
    }

    expect(topology["summary"]["total_nodes"] == 4, f"{name}: total_nodes harus 4")
    expect(topology["summary"]["total_edges"] == 3, f"{name}: total_edges harus 3")
    expect(topology["summary"]["unresolved_import_count"] == 0, f"{name}: unresolved harus 0")
    expect(node_ids(topology) == expected_nodes, f"{name}: nodes tidak sesuai")

    expect(
        topology["summary"].get("max_fan_in") == 2,
        f"{name}: max_fan_in harus 2"
    )

    expect(
        topology["summary"].get("max_fan_out") == 1,
        f"{name}: max_fan_out harus 1"
    )

    nodes_by_id = {node["id"]: node for node in topology.get("nodes", [])}

    a_id = f"{project}/src/a.ts"
    b_id = f"{project}/src/b.ts"
    c_id = f"{project}/src/c.ts"
    d_id = f"{project}/src/d.ts"

    a_node = nodes_by_id.get(a_id, {})
    b_node = nodes_by_id.get(b_id, {})
    c_node = nodes_by_id.get(c_id, {})
    d_node = nodes_by_id.get(d_id, {})

    expect(a_node.get("fan_in") == 2, f"{name}: fan_in a.ts harus 2")
    expect(a_node.get("fan_out") == 1, f"{name}: fan_out a.ts harus 1")
    expect(
        a_node.get("direct_dependents_count") == 2,
        f"{name}: direct_dependents_count a.ts harus 2"
    )

    expect(d_node.get("fan_in") == 1, f"{name}: fan_in d.ts harus 1")
    expect(d_node.get("fan_out") == 0, f"{name}: fan_out d.ts harus 0")

    expect(b_node.get("fan_in") == 0, f"{name}: fan_in b.ts harus 0")
    expect(b_node.get("fan_out") == 1, f"{name}: fan_out b.ts harus 1")

    expect(c_node.get("fan_in") == 0, f"{name}: fan_in c.ts harus 0")
    expect(c_node.get("fan_out") == 1, f"{name}: fan_out c.ts harus 1")

    impact_a = file_scanner.get_impacted_files(a_id, topology=topology)

    expect(
        impact_a.get("target_fan_in") == 2,
        f"{name}: target_fan_in a.ts harus 2"
    )

    expect(
        impact_a.get("target_fan_out") == 1,
        f"{name}: target_fan_out a.ts harus 1"
    )

    expect(
        impact_a.get("target_direct_dependents_count") == 2,
        f"{name}: target_direct_dependents_count a.ts harus 2"
    )


def test_f11_change_risk_advisory():
    name = "F11"
    project = "fixtures_min/f11_change_risk_advisory/project"
    topology = file_scanner.scan_topology(path=project)
    require_trust_layer(topology, name)

    expected_nodes = {
        f"{project}/src/main.ts",
        f"{project}/src/server.ts",
        f"{project}/src/app.ts",
        f"{project}/src/util.ts",
        f"{project}/src/isolated.ts",
    }

    expect(topology["summary"]["total_nodes"] == 5, f"{name}: total_nodes harus 5")
    expect(topology["summary"]["total_edges"] == 3, f"{name}: total_edges harus 3")
    expect(node_ids(topology) == expected_nodes, f"{name}: nodes tidak sesuai")

    app_id = f"{project}/src/app.ts"
    util_id = f"{project}/src/util.ts"
    isolated_id = f"{project}/src/isolated.ts"
    main_id = f"{project}/src/main.ts"
    server_id = f"{project}/src/server.ts"

    impact_app = file_scanner.get_impacted_files(app_id, topology=topology)

    expect(
        impact_app.get("change_risk_level") == "high",
        f"{name}: app.ts harus berisiko high"
    )

    expect(
        set(impact_app.get("change_risk_reasons", [])) == {
            "impacts_entrypoints",
            "high_fan_in",
        },
        f"{name}: alasan risiko app.ts harus impacts_entrypoints dan high_fan_in"
    )

    expect(
        set(impact_app.get("affected_entrypoints", [])) == {main_id, server_id},
        f"{name}: app.ts harus berdampak ke main.ts dan server.ts"
    )

    impact_util = file_scanner.get_impacted_files(util_id, topology=topology)

    expect(
        impact_util.get("change_risk_level") == "medium",
        f"{name}: util.ts harus berisiko medium"
    )

    expect(
        "impacts_entrypoints" in impact_util.get("change_risk_reasons", []),
        f"{name}: util.ts harus memiliki alasan impacts_entrypoints"
    )

    impact_isolated = file_scanner.get_impacted_files(isolated_id, topology=topology)

    expect(
        impact_isolated.get("change_risk_level") == "low",
        f"{name}: isolated.ts harus berisiko low"
    )

    expect(
        impact_isolated.get("change_risk_reasons") == ["isolated"],
        f"{name}: isolated.ts harus memiliki alasan isolated"
    )

    expect(
        impact_isolated.get("affected_entrypoints") == [],
        f"{name}: isolated.ts tidak boleh berdampak ke entrypoint"
    )


def test_f12_unreferenced_files():
    name = "F12"
    project = "fixtures_min/f12_unreferenced_files/project"
    topology = file_scanner.scan_topology(path=project)
    require_trust_layer(topology, name)

    expected_nodes = {
        f"{project}/src/main.ts",
        f"{project}/src/app.ts",
        f"{project}/src/util.ts",
        f"{project}/src/unused.ts",
        f"{project}/src/app.spec.ts",
    }

    expect(topology["summary"]["total_nodes"] == 5, f"{name}: total_nodes harus 5")
    expect(topology["summary"]["total_edges"] == 2, f"{name}: total_edges harus 2")
    expect(topology["summary"]["unresolved_import_count"] == 0, f"{name}: unresolved harus 0")
    expect(node_ids(topology) == expected_nodes, f"{name}: nodes tidak sesuai")

    policy = topology.get("meta", {}).get("policy", {})
    expect(
        policy.get("mode") == "informational_only",
        f"{name}: policy mode harus informational_only"
    )
    expect(
        policy.get("blocking") is False,
        f"{name}: tool tidak boleh blocking"
    )
    expect(
        policy.get("provides_change_recommendations") is False,
        f"{name}: tool tidak boleh memberikan rekomendasi perubahan"
    )

    expect(
        topology["summary"].get("test_file_count") == 1,
        f"{name}: test_file_count harus 1"
    )

    expect(
        topology["summary"].get("unreferenced_file_count") == 1,
        f"{name}: unreferenced_file_count harus 1"
    )

    unreferenced = topology.get("diagnostics", {}).get("unreferenced_files", [])
    unreferenced_ids = [item.get("id") for item in unreferenced]

    expect(
        unreferenced_ids == [f"{project}/src/unused.ts"],
        f"{name}: hanya unused.ts yang boleh masuk unreferenced_files"
    )

    nodes_by_id = {node["id"]: node for node in topology.get("nodes", [])}

    expect(
        nodes_by_id.get(f"{project}/src/app.spec.ts", {}).get("is_test") is True,
        f"{name}: app.spec.ts harus ditandai sebagai test"
    )

    expect(
        nodes_by_id.get(f"{project}/src/main.ts", {}).get("is_entrypoint") is True,
        f"{name}: main.ts harus ditandai sebagai entrypoint"
    )

    impact_unused = file_scanner.get_impacted_files(
        f"{project}/src/unused.ts",
        topology=topology
    )

    expect(
        impact_unused.get("change_risk_level") == "low",
        f"{name}: unused.ts harus memiliki change_risk_level low"
    )

    expect(
        impact_unused.get("target_is_test") is False,
        f"{name}: unused.ts bukan file test"
    )

    expect(
        impact_unused.get("affected_entrypoints") == [],
        f"{name}: unused.ts tidak berdampak ke entrypoint"
    )


def test_f13_multi_root():
    name = "F13"
    base = "fixtures_min/f13_multi_root"
    root_a = f"{base}/root_a"
    root_b = f"{base}/root_b"

    topology = file_scanner.scan_topology(path=[root_a, root_b])
    require_trust_layer(topology, name)

    expected_nodes = {
        f"{base}/root_a/a.ts",
        f"{base}/root_b/b.ts",
        f"{base}/root_b/c.ts",
    }

    expected_edges = {
        (f"{base}/root_a/a.ts", f"{base}/root_b/b.ts"),
        (f"{base}/root_b/c.ts", f"{base}/root_b/b.ts"),
    }

    expect(topology["summary"]["total_nodes"] == 3, f"{name}: total_nodes harus 3")
    expect(topology["summary"]["total_edges"] == 2, f"{name}: total_edges harus 2")
    expect(topology["summary"]["unresolved_import_count"] == 0, f"{name}: unresolved harus 0")
    expect(node_ids(topology) == expected_nodes, f"{name}: nodes tidak sesuai")
    expect(edge_pairs(topology) == expected_edges, f"{name}: edges tidak sesuai")

    expect(
        topology.get("meta", {}).get("scan_mode") == "multi-root",
        f"{name}: scan_mode harus multi-root"
    )

    expect(
        topology.get("meta", {}).get("roots") == [root_a, root_b],
        f"{name}: roots harus berisi root_a dan root_b"
    )

    nodes_by_id = {node["id"]: node for node in topology.get("nodes", [])}
    b_node = nodes_by_id.get(f"{base}/root_b/b.ts", {})

    expect(b_node.get("fan_in") == 2, f"{name}: fan_in b.ts harus 2")

    topology_csv = file_scanner.scan_topology(path=f"{root_a},{root_b}")
    expect(
        node_ids(topology_csv) == expected_nodes,
        f"{name}: comma-separated roots harus menghasilkan nodes yang sama"
    )
    expect(
        topology_csv["summary"]["unresolved_import_count"] == 0,
        f"{name}: comma-separated roots harus tetap resolve"
    )


def test_f14_file_outline():
    name = "F14"
    project = "fixtures_min/f14_outline/project"
    target = f"{project}/src/sample.ts"

    outline = file_scanner.get_file_outline(target)

    expect(outline.get("exists") is True, f"{name}: outline harus exists")

    expect(
        "./util" in outline.get("imports", []),
        f"{name}: import ./util harus terlihat"
    )

    expect(
        "some-lib" in outline.get("external_imports", []),
        f"{name}: external import harus terlihat"
    )

    expected_exports = {
        "Sample",
        "SampleId",
        "sampleName",
        "sampleFunction",
        "SampleClass",
    }

    expect(
        set(outline.get("exports", [])) == expected_exports,
        f"{name}: exports tidak sesuai"
    )

    kinds = {item.get("kind") for item in outline.get("outline", [])}

    expect(
        {"interface", "type", "const", "function", "class"} <= kinds,
        f"{name}: kinds outline tidak lengkap"
    )


def test_f15_alias_paths():
    name = "F15"
    project = "fixtures_min/f15_alias_paths/project"

    topology = file_scanner.scan_topology(path=project)
    require_trust_layer(topology, name)

    expected_nodes = {
        f"{project}/src/core/logger.ts",
        f"{project}/src/app/app.ts",
    }

    expected_edges = {
        (f"{project}/src/app/app.ts", f"{project}/src/core/logger.ts"),
    }

    expect(topology["summary"]["total_nodes"] == 2, f"{name}: total_nodes harus 2")
    expect(topology["summary"]["total_edges"] == 1, f"{name}: total_edges harus 1")
    expect(topology["summary"]["unresolved_import_count"] == 0, f"{name}: unresolved harus 0")
    expect(node_ids(topology) == expected_nodes, f"{name}: nodes tidak sesuai")
    expect(edge_pairs(topology) == expected_edges, f"{name}: edges tidak sesuai")

    expect(
        topology.get("meta", {}).get("alias_rules_count", 0) >= 1,
        f"{name}: alias_rules_count harus >= 1"
    )

    if topology.get("edges"):
        edge = topology["edges"][0]
        expect(
            edge.get("method") == "alias_match",
            f"{name}: edge alias harus punya method alias_match"
        )

    external_raw_imports = {
        item.get("raw_import")
        for item in topology.get("diagnostics", {}).get("external_imports", [])
    }

    expect(
        "some-lib" in external_raw_imports,
        f"{name}: some-lib harus tetap dicatat sebagai external"
    )


def test_f16_file_brief():
    name = "F16"
    project = "fixtures_min/f16_file_brief/project"
    target_app = f"{project}/src/app.ts"
    target_util = f"{project}/src/util.ts"

    brief_app = file_scanner.get_file_brief(target_app, path=project)

    expect(brief_app.get("exists") is True, f"{name}: brief app.ts harus exists")
    expect(brief_app.get("outline") is not None, f"{name}: outline harus ada")
    expect(brief_app.get("impact") is not None, f"{name}: impact harus ada")

    # Validasi Outline
    expect(
        "runApp" in brief_app["outline"].get("exports", []),
        f"{name}: exports harus memuat runApp"
    )

    # Validasi Impact (app.ts diimpor main.ts -> entrypoint)
    expect(
        brief_app["impact"]["change_risk_level"] in ("medium", "high"),
        f"{name}: risk level app.ts harus medium/high"
    )
    expect(
        len(brief_app["impact"]["affected_entrypoints"]) > 0,
        f"{name}: app.ts harus berdampak ke entrypoint"
    )

    brief_util = file_scanner.get_file_brief(target_util, path=project)

    # Validasi Downstream Count (util diimpor app, app diimpor main)
    expect(
        brief_util["impact"]["downstream_count"] == 2,
        f"{name}: downstream_count util.ts harus 2 (app dan main)"
    )


def test_f17_async_waterfall():
    name = "F17"
    project = "fixtures_min/f17_async_waterfall/project"
    from core.shared_graph import build_shared_graph
    from codebase.performance_analyzers import analyze_async_waterfall

    sg = build_shared_graph(project)
    result = analyze_async_waterfall(sg)

    expect(result["summary"]["total_findings"] >= 1, f"{name}: harus ada findings")
    expect(
        result["summary"]["by_type"]["sequential_await"] >= 1 or result["summary"]["by_type"]["await_in_loop"] >= 1,
        f"{name}: harus deteksi sequential await atau await in loop"
    )


def test_f18_deopt_checker():
    name = "F18"
    project = "fixtures_min/f18_deopt_checker/project"
    from core.shared_graph import build_shared_graph
    from codebase.performance_analyzers import analyze_deopt

    sg = build_shared_graph(project)
    result = analyze_deopt(sg)

    expect(result["summary"]["total_findings"] >= 2, f"{name}: harus ada minimal 2 findings (delete, eval)")
    expect(result["summary"]["by_type"]["delete_operator"] >= 1, f"{name}: harus deteksi delete operator")
    expect(result["summary"]["by_type"]["eval_usage"] >= 1, f"{name}: harus deteksi eval usage")


def test_f19_gc_pressure():
    name = "F19"
    project = "fixtures_min/f19_gc_pressure/project"
    from core.shared_graph import build_shared_graph
    from codebase.performance_analyzers import analyze_gc_pressure

    sg = build_shared_graph(project)
    result = analyze_gc_pressure(sg)

    expect(result["summary"]["total_findings"] >= 3, f"{name}: harus ada minimal 3 findings")
    expect(result["summary"]["by_type"]["json_in_loop"] >= 1, f"{name}: harus deteksi JSON.parse di loop")
    expect(result["summary"]["by_type"]["uncleared_timer"] >= 1, f"{name}: harus deteksi uncleared timer")


def test_f20_cache_audit():
    name = "F20"
    project = "fixtures_min/f20_cache_audit/project"
    from core.shared_graph import build_shared_graph
    from codebase.performance_analyzers import analyze_cache

    sg = build_shared_graph(project)
    result = analyze_cache(sg)

    expect(result["summary"]["total_findings"] >= 3, f"{name}: harus ada minimal 3 findings")
    expect(
        result["summary"]["by_type"]["nondeterministic_cache_key"] >= 1,
        f"{name}: harus deteksi nondeterministic key (Date.now)"
    )
    expect(
        result["summary"]["by_type"]["unbounded_cache"] >= 1,
        f"{name}: harus deteksi unbounded cache"
    )


def test_f21_type_isomorphism():
    name = "F21"
    project = "fixtures_min/f21_type_isomorphism/project"
    from core.shared_graph import build_shared_graph
    from codebase.hott_analyzers import analyze_isomorphism

    sg = build_shared_graph(project)
    result = analyze_isomorphism(sg)

    expect(
        result["summary"]["isomorphic_pair_count"] == 2,
        f"{name}: harus ada 2 pasangan isomorfik"
    )

    pair_names = set()
    for pair in result.get("findings", []):
        if pair.get("type") == "structural_isomorphism":
            pair_names.add(
                (pair["space_a"]["name"], pair["space_b"]["name"])
            )

    expect(
        ("UserDTO", "UserViewModel") in pair_names,
        f"{name}: UserDTO dan UserViewModel harus isomorfik"
    )

    expect(
        ("Product", "ProductAlias") in pair_names,
        f"{name}: Product dan ProductAlias harus isomorfik"
    )

    # Order tidak boleh isomorfik dengan yang lain
    for pair in result.get("findings", []):
        if pair.get("type") == "structural_isomorphism":
            expect(
                pair["space_a"]["name"] != "Order"
                and pair["space_b"]["name"] != "Order",
                f"{name}: Order tidak boleh isomorfik dengan type lain"
            )


def test_f22_boundary_sheaf():
    name = "F22"
    project = "fixtures_min/f22_boundary_sheaf/project"
    scan_root = f"{project}/src"
    from core.shared_graph import build_shared_graph
    from codebase.hott_analyzers import analyze_sheaf

    sg = build_shared_graph(scan_root)
    result = analyze_sheaf(sg)

    expect(
        result["summary"]["total_boundaries"] >= 2,
        f"{name}: harus ada minimal 2 boundaries"
    )

    expect(
        result["summary"]["total_findings"] >= 1,
        f"{name}: harus ada minimal 1 finding"
    )

    # Cek boundary violation: app.component.ts bypass barrel core
    violations = [
        f for f in result["findings"]
        if f["type"] == "boundary_violation"
    ]
    expect(
        len(violations) >= 1,
        f"{name}: harus deteksi boundary violation (bypass barrel)"
    )


def test_f23_sheaf_precision():
    name = "F23"
    project = "fixtures_min/f23_sheaf_precision/project"
    scan_root = f"{project}/src"
    from core.shared_graph import build_shared_graph
    from codebase.hott_analyzers import analyze_sheaf

    sg = build_shared_graph(scan_root)
    result = analyze_sheaf(sg)

    # Entrypoint main.ts mengimpor src/app/app.ts TANPA barrel.
    # Ini harus TIDAK dilaporkan sebagai boundary_violation.
    violations = [
        f for f in result["findings"]
        if f["type"] == "boundary_violation"
    ]
    expect(
        len(violations) == 0,
        f"{name}: entrypoint + no-barrel tidak boleh jadi boundary_violation"
    )

    # Tapi boundary tanpa public API tetap dicatat sebagai observasi low.
    no_api = [
        f for f in result["findings"]
        if f["type"] == "boundary_without_public_api"
    ]
    expect(
        len(no_api) >= 1,
        f"{name}: boundary tanpa barrel harus dicatat sebagai observasi"
    )


def test_f24_homotopy_path():
    name = "F24"
    project = "fixtures_min/f24_homotopy_path/project"
    scan_root = f"{project}/src"
    from core.shared_graph import build_shared_graph
    from codebase.hott_analyzers import analyze_homotopy

    sg = build_shared_graph(scan_root)
    result = analyze_homotopy(sg)

    # Cek diamond: a -> b -> d dan a -> c -> d
    diamonds = [
        f for f in result["findings"]
        if f["type"] == "diamond_dependency"
    ]
    expect(
        len(diamonds) >= 1,
        f"{name}: harus deteksi diamond dependency (a->b->d, a->c->d)"
    )

    if diamonds:
        diamond = diamonds[0]
        expect(
            diamond["convergence"].endswith("d.ts"),
            f"{name}: diamond harus berkonvergensi di d.ts"
        )
        expect(
            diamond["source"].endswith("a.ts"),
            f"{name}: diamond harus bersumber dari a.ts"
        )

    # Cek mergeable import: a.ts mengimpor ./util dua kali
    mergeable = [
        f for f in result["findings"]
        if f["type"] == "mergeable_import"
    ]
    expect(
        len(mergeable) >= 1,
        f"{name}: harus deteksi mergeable import (./util diimpor 2x)"
    )


def test_f25_topological_synthesis():
    name = "F25"
    project = "fixtures_min/f25_synthesis/project"
    scan_root = f"{project}/src"
    from core.synthesizer import synthesize_topological_integrity

    result = synthesize_topological_integrity(scan_root)

    # Verifikasi struktur dasar
    expect(
        result.get("schema_version") == "3.0.0-kernel",
        f"{name}: schema_version harus 3.0.0-kernel"
    )

    expect(
        "unified_summary" in result,
        f"{name}: harus ada unified_summary"
    )

    # Verifikasi health score ada dan dalam rentang valid
    health = result["unified_summary"].get("topological_health_score")
    expect(
        health is not None and 0.0 <= health <= 1.0,
        f"{name}: health score harus dalam rentang [0, 1]"
    )

    # Fixture ini punya diamond (a->b->d, a->c->d)
    expect(
        result["unified_summary"]["total_findings"] >= 1,
        f"{name}: harus ada minimal 1 finding (diamond dari fixture)"
    )

    # Verifikasi total_files terisi
    expect(
        result["unified_summary"]["total_files"] == 4,
        f"{name}: total_files harus 4"
    )


def test_f26_topological_manifold():
    name = "F26"
    project = "fixtures_min/f26_manifold/project"
    scan_root = f"{project}/src"
    from core.shared_graph import build_shared_graph
    from codebase.hott_analyzers import analyze_manifold
    from codebase.topology_analyzers import analyze_circular

    sg = build_shared_graph(scan_root)
    result = analyze_manifold(sg)

    expect(
        result["manifold"]["vertex_count"] == 3,
        f"{name}: harus ada 3 vertices"
    )
    expect(
        result["manifold"]["edge_count"] == 3,
        f"{name}: harus ada 3 edges"
    )

    betti = result["manifold"]["betti_numbers"]
    expect(
        betti["beta_0"] == 1,
        f"{name}: β₀ harus 1 (terhubung penuh)"
    )
    expect(
        betti["beta_1"] == 1,
        f"{name}: β₁ harus 1 untuk triangle DAG pada underlying undirected graph"
    )

    basis = result.get("cycle_basis", [])
    expect(len(basis) == 1, f"{name}: harus ada satu cycle-basis witness")
    expect(
        basis[0].get("orientation") == "mixed",
        f"{name}: triangle DAG bukan circular import berarah",
    )
    circular = analyze_circular(sg)
    expect(
        circular.get("summary", {}).get("total_cycles") == 0,
        f"{name}: β₁ undirected tidak boleh dianggap circular import",
    )
    model = result.get("topological_model", {})
    expect(
        model.get("name") == "dependency_multigraph_1_complex",
        f"{name}: model topologi harus dinyatakan eksplisit",
    )
    expect(
        model.get("edge_orientation_for_betti") == "ignored",
        f"{name}: orientasi edge harus dinyatakan diabaikan untuk Betti",
    )

    expect(
        "invariant_vector" in result,
        f"{name}: harus ada invariant_vector"
    )
    expect(
        "summary" in result,
        f"{name}: harus ada summary"
    )


def test_f27_invariant_encoder():
    name = "F27"
    project = "fixtures_min/f27_encoder/project"
    scan_root = f"{project}/src"
    from core.synthesizer import encode_topological_invariants

    result = encode_topological_invariants(scan_root)

    expect(result.get("available") is True, f"{name}: encoder harus available")

    fingerprint = result.get("topological_fingerprint", {})

    hash1 = fingerprint.get("signature_hash", "")
    result2 = encode_topological_invariants(scan_root)
    hash2 = result2.get("topological_fingerprint", {}).get("signature_hash", "")
    expect(hash1 == hash2 and hash1 != "", f"{name}: signature hash harus deterministik")
    expect(hash1.startswith("sha256:"), f"{name}: hash harus prefix sha256")

    for key, value in fingerprint.get("normalized_vector", {}).items():
        expect(0.0 <= value <= 1.0, f"{name}: {key} harus dalam [0,1]")

    complexity = fingerprint.get("complexity_score", -1)
    expect(0.0 <= complexity <= 1.0, f"{name}: complexity harus dalam [0,1]")

    expect(
        fingerprint.get("structural_archetype") == "tree_like",
        f"{name}: archetype harus tree_like untuk struktur pohon"
    )

    context_block = result.get("context_block", "")
    expect("[TOPOLOGICAL FINGERPRINT]" in context_block, f"{name}: context block harus ada")
    expect(hash1 in context_block, f"{name}: context block harus berisi signature")
    expect("Cycle Semantics:" in context_block, f"{name}: context block harus menjelaskan cycle semantics")
    expect(
        result.get("cycle_semantics", {}).get("model") == "dependency_multigraph_1_complex",
        f"{name}: encoder harus meneruskan model topologi",
    )


def test_f28_decoder_steering():
    name = "F28"
    project = "fixtures_min/f28_steering/project"
    scan_root = f"{project}/src"
    baseline_path = f"{project}/baseline/topological_baseline.json"
    from core.synthesizer import establish_baseline, steer_decoder

    # Step 1: Establish baseline
    establish_result = establish_baseline(scan_root, baseline_path)
    expect(
        establish_result.get("available") is True,
        f"{name}: establish baseline harus berhasil"
    )

    # Step 2: Steer dengan baseline yang baru dibuat
    steer_result = steer_decoder(scan_root, baseline_path)
    expect(
        steer_result.get("available") is True,
        f"{name}: steer harus available"
    )

    # Baseline harus terdeteksi
    expect(
        steer_result["baseline"]["exists"] is True,
        f"{name}: baseline harus terdeteksi"
    )

    # Tidak ada drift karena belum ada perubahan
    drift = steer_result.get("drift_analysis")
    expect(drift is not None, f"{name}: drift_analysis harus ada")
    expect(
        drift["has_drift"] is False,
        f"{name}: tidak boleh ada drift setelah establish"
    )
    expect(
        drift["topology_changed"] is False,
        f"{name}: topologi tidak boleh berubah"
    )

    # Steering signals harus ada
    signals = steer_result.get("steering_signals")
    expect(signals is not None, f"{name}: steering_signals harus ada")
    expect(
        signals["reasoning_strategy"] == "hierarchical_traversal",
        f"{name}: fixture tree harus dapat strategi hierarchical_traversal"
    )
    expect(
        signals["reasoning_budget"] in ("low", "medium", "high"),
        f"{name}: reasoning_budget harus valid"
    )
    expect(
        signals["regrounding_needed"] is False,
        f"{name}: tidak perlu regrounding saat topologi stabil"
    )

    # Steering prompt block harus ada dan berisi signature
    prompt_block = steer_result.get("steering_prompt_block", "")
    expect(
        "[TOPOLOGICAL STEERING SIGNAL]" in prompt_block,
        f"{name}: prompt block harus ada"
    )
    expect(
        steer_result["current_fingerprint"]["signature_hash"] in prompt_block,
        f"{name}: prompt block harus berisi signature"
    )
    expect(
        "Cycle Interpretation:" in prompt_block,
        f"{name}: steering prompt harus mencegah penyamaan β₁ dengan circular import",
    )

    # Cleanup baseline
    import os as _os
    if _os.path.isfile(baseline_path):
        _os.remove(baseline_path)


def test_f29_archetype_calibration():
    name = "F29"
    project = "fixtures_min/f29_archetype_calibration/project"
    scan_root = f"{project}/src"
    from core.synthesizer import encode_topological_invariants

    result = encode_topological_invariants(scan_root)
    fingerprint = result.get("topological_fingerprint", {})
    archetype = fingerprint.get("structural_archetype", "")

    expect(
        archetype != "dense_mesh",
        f"{name}: fragmented sparse cyclic harus BUKAN dense_mesh"
    )
    expect(
        archetype == "fragmented_sparse_cyclic",
        f"{name}: archetype harus fragmented_sparse_cyclic, dapat '{archetype}'"
    )

    betti = result.get("summary", {}).get("betti_numbers", {})
    expect(betti.get("beta_0") == 2, f"{name}: beta_0 harus 2 (dua komponen)")
    expect(betti.get("beta_1") == 1, f"{name}: beta_1 harus 1 (satu cycle)")

    from core.shared_graph import build_shared_graph
    from codebase.hott_analyzers import analyze_manifold
    from codebase.topology_analyzers import analyze_circular

    graph = build_shared_graph(scan_root)
    manifold = analyze_manifold(graph)
    basis = manifold.get("cycle_basis", [])
    expect(len(basis) == 1, f"{name}: harus ada satu cycle-basis witness")
    expect(
        basis[0].get("orientation") == "directed",
        f"{name}: a->b->c->a harus dikenali sebagai directed witness",
    )
    circular = analyze_circular(graph)
    expect(
        circular.get("summary", {}).get("total_cycles") == 1,
        f"{name}: directed witness harus cocok dengan satu circular import",
    )


def test_f30_complexity_calibration():
    name = "F30"
    project = "fixtures_min/f30_complexity_calibration/project"
    scan_root = f"{project}/src"
    from core.synthesizer import encode_topological_invariants

    result = encode_topological_invariants(scan_root)
    fingerprint = result.get("topological_fingerprint", {})
    normalized = fingerprint.get("normalized_vector", {})

    # n_avg_degree harus ada dan dalam [0,1]
    expect(
        "n_avg_degree" in normalized,
        f"{name}: n_avg_degree harus ada di normalized_vector"
    )
    expect(
        0.0 <= normalized.get("n_avg_degree", -1) <= 1.0,
        f"{name}: n_avg_degree harus dalam [0,1]"
    )

    # n_edge_density harus sudah dihapus (digantikan n_avg_degree)
    expect(
        "n_edge_density" not in normalized,
        f"{name}: n_edge_density harus sudah digantikan n_avg_degree"
    )

    # complexity_score harus dalam [0,1]
    complexity = fingerprint.get("complexity_score", -1)
    expect(
        0.0 <= complexity <= 1.0,
        f"{name}: complexity_score harus dalam [0,1]"
    )

    # signature_hash harus tetap ada
    signature = fingerprint.get("signature_hash", "")
    expect(
        signature.startswith("sha256:"),
        f"{name}: signature_hash harus tetap ada"
    )


def test_f32_reciprocal_cycle_basis():
    name = "F32"
    scan_root = "fixtures_min/f32_reciprocal_cycle/project/src"
    from core.shared_graph import build_shared_graph
    from codebase.hott_analyzers import analyze_manifold
    from codebase.topology_analyzers import analyze_circular

    graph = build_shared_graph(scan_root)
    manifold = analyze_manifold(graph)
    betti = manifold.get("manifold", {}).get("betti_numbers", {})
    basis = manifold.get("cycle_basis", [])

    expect(betti.get("beta_0") == 1, f"{name}: dua file reciprocal harus terhubung")
    expect(betti.get("beta_1") == 1, f"{name}: dua import reciprocal harus membentuk β₁=1")
    expect(len(basis) == 1, f"{name}: reciprocal cycle harus punya satu witness")
    expect(basis[0].get("length") == 2, f"{name}: witness harus berupa cycle dua edge")
    expect(basis[0].get("orientation") == "directed", f"{name}: reciprocal cycle harus directed")
    expect(
        manifold.get("manifold", {}).get("cycle_basis_complete") is True,
        f"{name}: cycle basis harus lengkap untuk multigraph",
    )
    expect(
        analyze_circular(graph).get("summary", {}).get("total_cycles") == 1,
        f"{name}: reciprocal import harus terdeteksi circular",
    )


def test_f33_static_test_reachability():
    name = "F33"
    scan_root = "fixtures_min/f33_test_reachability/project/src"
    from core.shared_graph import build_shared_graph
    from codebase.topology_analyzers import analyze_test_reachability

    result = analyze_test_reachability(build_shared_graph(scan_root))
    summary = result.get("summary", {})
    expect(summary.get("total_tests") == 2, f"{name}: harus ada dua test file")
    expect(summary.get("total_production_files") == 6, f"{name}: harus ada enam source file")
    expect(summary.get("directly_tested_files") == 1, f"{name}: hanya app.ts yang direct target")
    expect(summary.get("statically_reachable_files") == 3, f"{name}: app/service/core harus reachable")
    expect(summary.get("statically_unreachable_files") == 3, f"{name}: tiga source harus unreachable")
    expect(summary.get("static_test_reachability_ratio") == 0.5, f"{name}: ratio harus 0.5")
    expect(summary.get("testless_component_count") == 1, f"{name}: harus ada satu testless component")
    expect(summary.get("high_influence_without_test_path") == 1, f"{name}: critical harus high influence gap")
    expect(summary.get("isolated_test_count") == 1, f"{name}: orphan.spec harus isolated")

    core_file = f"{scan_root}/core.ts"
    app_test = f"{scan_root}/app.spec.ts"
    witness = result.get("source_test_witnesses", {}).get(core_file, [])
    expect(len(witness) == 1, f"{name}: core.ts harus punya satu test witness")
    expect(
        witness[0].get("path") == [
            app_test,
            f"{scan_root}/app.ts",
            f"{scan_root}/service.ts",
            core_file,
        ],
        f"{name}: path test ke core harus lengkap dan directional",
    )
    expect(
        result.get("model", {}).get("not_runtime_coverage") is True,
        f"{name}: output harus menolak klaim runtime coverage",
    )
    expect(
        f"{scan_root}/critical.ts" in result.get("unreachable_sources", []),
        f"{name}: critical.ts harus tidak terjangkau test",
    )


def test_f34_context_optimizer():
    name = "F34"
    scan_root = "fixtures_min/f34_context_optimizer/project/src"
    pricing = f"{scan_root}/orders/pricing.ts"
    order_service = f"{scan_root}/orders/order.service.ts"
    auth_service = f"{scan_root}/auth/auth.service.ts"

    from core.analyzer_registry import run_analyzers
    from core.context_optimizer import build_context_pack
    from core.shared_graph import build_shared_graph

    graph = build_shared_graph(scan_root)
    analyzer_output = run_analyzers(graph)
    kwargs = {
        "query": "pricing calculation",
        "budget_tokens": 600,
        "max_hops": 2,
        "detail": "source",
        "analyzer_output": analyzer_output,
    }
    result = build_context_pack(graph, **kwargs)
    repeated = build_context_pack(graph, **kwargs)

    selected = result.get("selection", {}).get("selected_paths", [])
    expect(selected and selected[0] == pricing, f"{name}: pricing.ts harus semantic seed pertama")
    expect(order_service in selected, f"{name}: neighbor order.service harus masuk context")
    expect(auth_service not in selected, f"{name}: boundary auth yang tidak relevan harus diomit")
    expect(
        selected == repeated.get("selection", {}).get("selected_paths", []),
        f"{name}: ranking file harus deterministik",
    )
    expect(
        result.get("context_block") == repeated.get("context_block"),
        f"{name}: prompt context harus deterministik",
    )
    expect(
        result.get("provenance", {}).get("graph_content_signature")
        == repeated.get("provenance", {}).get("graph_content_signature"),
        f"{name}: content signature harus deterministik",
    )
    budget = result.get("budget", {})
    expect(budget.get("within_budget") is True, f"{name}: hard budget harus dipatuhi")
    expect(
        budget.get("used_chars", 1) <= budget.get("char_budget", 0),
        f"{name}: context_block tidak boleh melewati character budget",
    )
    expect(
        result.get("provenance", {}).get("optimizer_additional_filesystem_scans") == 0,
        f"{name}: optimizer harus reuse SharedGraph tanpa rescan",
    )
    quotient = result.get("quotient_graph", {}).get("summary", {})
    expect(quotient.get("quotient_vertex_count") == 2, f"{name}: quotient harus punya orders+auth")
    expect(
        quotient.get("relevant_boundary_count") == 1,
        f"{name}: hanya boundary orders yang relevan",
    )
    context_block = result.get("context_block", "")
    expect("0.45L+0.25P+0.20C+0.10F" in context_block, f"{name}: formula harus transparan")
    expect("calculatePricing" in context_block, f"{name}: source witness harus masuk context")
    expect(
        result.get("model", {}).get("claim_boundary", "").startswith("Ranking is deterministic"),
        f"{name}: batas klaim ranking harus eksplisit",
    )


def test_f35_incremental_graph_cache():
    name = "F35"
    source_project = ROOT / "fixtures_min/f35_incremental_cache/project/src"

    from core.graph_cache import (
        LEGACY_CACHE_SCHEMA_VERSIONS,
        _cache_identity,
        _cache_key,
        build_cached_shared_graph,
        clear_graph_cache,
        get_graph_cache_status,
    )

    with tempfile.TemporaryDirectory() as temporary_root:
        project = Path(temporary_root) / "project"
        cache_dir = Path(temporary_root) / "cache"
        shutil.copytree(source_project, project)

        legacy_identity = _cache_identity(
            str(project),
            None,
            cache_schema_version=LEGACY_CACHE_SCHEMA_VERSIONS[0],
        )
        legacy_path = cache_dir / f"shared_graph_{_cache_key(legacy_identity)}.json"
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text("legacy-cache", encoding="utf-8")

        first = build_cached_shared_graph(str(project), cache_dir=str(cache_dir))
        first_cache = first.get("cache", {})
        expect(first_cache.get("status") == "miss", f"{name}: build awal harus miss")
        expect(first_cache.get("files_read") == 3, f"{name}: build awal harus baca 3 file")
        expect(first_cache.get("files_added") == 3, f"{name}: build awal harus catat 3 file baru")
        expect(first_cache.get("contains_source_content") is True, f"{name}: disclosure source wajib")
        expect(not legacy_path.exists(), f"{name}: cache schema lama harus dibersihkan setelah migrasi")
        expect(
            first_cache.get("legacy_entries_removed"),
            f"{name}: cleanup cache lama harus terlihat di provenance",
        )

        second = build_cached_shared_graph(str(project), cache_dir=str(cache_dir))
        second_cache = second.get("cache", {})
        expect(second_cache.get("status") == "hit", f"{name}: build kedua harus hit")
        expect(second_cache.get("files_reused") == 3, f"{name}: 3 file harus dipakai ulang")
        expect(second_cache.get("files_read") == 0, f"{name}: cache hit tidak boleh baca source")
        for key in (
            "vertices",
            "edges",
            "node_metadata",
            "resolved_imports",
            "unresolved_imports",
            "external_imports",
            "boundaries",
            "file_to_boundary",
            "type_shapes",
            "summary",
        ):
            expect(first.get(key) == second.get(key), f"{name}: cache hit mengubah {key}")

        b_path = project / "b.ts"
        b_path.write_text(
            "import './c';\nexport const b = true;\n",
            encoding="utf-8",
        )
        changed = build_cached_shared_graph(str(project), cache_dir=str(cache_dir))
        changed_cache = changed.get("cache", {})
        expect(changed_cache.get("status") == "partial", f"{name}: mutation harus partial")
        expect(changed_cache.get("files_changed") == 1, f"{name}: hanya b.ts berubah")
        expect(changed_cache.get("files_read") == 1, f"{name}: hanya b.ts dibaca ulang")
        expect(changed_cache.get("files_reused") == 2, f"{name}: dua file harus reuse")
        expect(changed.get("summary", {}).get("total_edges") == 2, f"{name}: edge baru harus terbentuk")

        extra_path = project / "extra.ts"
        extra_path.write_text("export const extra = true;\n", encoding="utf-8")
        added = build_cached_shared_graph(str(project), cache_dir=str(cache_dir))
        added_cache = added.get("cache", {})
        expect(added_cache.get("files_added") == 1, f"{name}: extra.ts harus terdeteksi")
        expect(added_cache.get("files_read") == 1, f"{name}: hanya extra.ts dibaca")
        expect(added_cache.get("files_reused") == 3, f"{name}: tiga file harus reuse")

        (project / "c.ts").unlink()
        deleted = build_cached_shared_graph(str(project), cache_dir=str(cache_dir))
        deleted_cache = deleted.get("cache", {})
        expect(deleted_cache.get("files_deleted") == 1, f"{name}: delete harus terdeteksi")
        expect(deleted_cache.get("files_read") == 0, f"{name}: delete tak perlu baca source")
        expect(deleted_cache.get("files_reused") == 3, f"{name}: file tersisa harus reuse")
        expect(deleted.get("summary", {}).get("total_unresolved") == 1, f"{name}: import c jadi unresolved")

        status = get_graph_cache_status(str(project), cache_dir=str(cache_dir))
        expect(status.get("status") == "valid", f"{name}: cache pascahapus harus valid")
        expect(status.get("files_reusable") == 3, f"{name}: status harus lapor 3 reusable")

        refreshed = build_cached_shared_graph(
            str(project),
            cache_dir=str(cache_dir),
            mode="refresh",
        )
        refresh_cache = refreshed.get("cache", {})
        expect(refresh_cache.get("status") == "refreshed", f"{name}: refresh harus eksplisit")
        expect(refresh_cache.get("files_read") == 3, f"{name}: refresh harus baca semua file")

        cache_path = Path(refresh_cache.get("cache_path", ""))
        cache_path.write_text("{cache-rusak", encoding="utf-8")
        recovered = build_cached_shared_graph(str(project), cache_dir=str(cache_dir))
        recovered_cache = recovered.get("cache", {})
        expect(recovered_cache.get("status") == "recovered", f"{name}: corrupt harus recovery")
        expect(recovered_cache.get("files_read") == 3, f"{name}: recovery harus rebuild")
        expect(
            str(recovered_cache.get("recovery_reason", "")).startswith("cache_read_error:"),
            f"{name}: alasan recovery harus transparan",
        )

        cleared = clear_graph_cache(str(project), cache_dir=str(cache_dir))
        expect(cleared.get("status") == "cleared", f"{name}: clear harus menghapus entry")
        missing = get_graph_cache_status(str(project), cache_dir=str(cache_dir))
        expect(missing.get("status") == "missing", f"{name}: status setelah clear harus missing")

        disabled = build_cached_shared_graph(
            str(project),
            cache_dir=str(cache_dir),
            mode="off",
        )
        expect(disabled.get("cache", {}).get("status") == "disabled", f"{name}: mode off harus bypass")

        write_failed = build_cached_shared_graph(
            str(project),
            cache_dir=str(project / "a.ts"),
        )
        expect(
            write_failed.get("cache", {}).get("status") == "write_failed",
            f"{name}: cache path tak dapat ditulis tidak boleh menggagalkan graph",
        )
        expect(
            write_failed.get("summary", {}).get("total_files") == 3,
            f"{name}: write failure tetap harus menghasilkan graph lengkap",
        )


def test_f36_analyzer_evidence_cache():
    name = "F36"
    source_project = ROOT / "fixtures_min/f35_incremental_cache/project/src"

    from core.analyzer_cache import (
        clear_analyzer_cache,
        get_analyzer_cache_status,
        run_cached_analyzers,
    )
    from core.graph_cache import build_cached_shared_graph

    with tempfile.TemporaryDirectory() as temporary_root:
        project = Path(temporary_root) / "project"
        graph_cache_dir = Path(temporary_root) / "graph-cache"
        analyzer_cache_dir = Path(temporary_root) / "analyzer-cache"
        shutil.copytree(source_project, project)

        graph = build_cached_shared_graph(
            str(project),
            cache_dir=str(graph_cache_dir),
        )
        first = run_cached_analyzers(
            graph,
            cache_dir=str(analyzer_cache_dir),
        )
        first_cache = first.get("cache", {})
        expect(first_cache.get("status") == "miss", f"{name}: analyzer awal harus miss")
        expect(first_cache.get("executed_count") == 13, f"{name}: awal harus eksekusi 13 analyzer")
        expect(first_cache.get("reused_count") == 0, f"{name}: awal tidak boleh reuse")
        expect(
            first_cache.get("contains_full_source_content") is False,
            f"{name}: cache analyzer tidak boleh menyimpan source penuh",
        )
        expect(
            first_cache.get("contains_derived_source_evidence") is True,
            f"{name}: derived evidence harus diungkapkan",
        )
        analyzer_cache_path = Path(first_cache.get("cache_path", ""))
        expect(analyzer_cache_path.exists(), f"{name}: entry analyzer harus persisten")
        if analyzer_cache_path.exists():
            expect(
                analyzer_cache_path.stat().st_mode & 0o777 == 0o600,
                f"{name}: permission cache analyzer harus 0600",
            )

        second = run_cached_analyzers(
            graph,
            cache_dir=str(analyzer_cache_dir),
        )
        second_cache = second.get("cache", {})
        expect(second_cache.get("status") == "hit", f"{name}: analyzer kedua harus hit")
        expect(second_cache.get("reused_count") == 13, f"{name}: 13 analyzer harus reuse")
        expect(second_cache.get("executed_count") == 0, f"{name}: hit tidak boleh eksekusi")
        expect(first.get("results") == second.get("results"), f"{name}: evidence hit harus identik")

        source_key = first_cache.get("source_cache_key", "")
        cleared_for_partial = clear_analyzer_cache(
            source_key,
            cache_dir=str(analyzer_cache_dir),
        )
        expect(cleared_for_partial.get("status") == "cleared", f"{name}: setup partial harus clear")
        subset_names = ["perf.cache", "topo.circular"]
        subset = run_cached_analyzers(
            graph,
            subset_names,
            cache_dir=str(analyzer_cache_dir),
        )
        expect(subset.get("cache", {}).get("executed_count") == 2, f"{name}: subset harus eksekusi 2")
        partial = run_cached_analyzers(
            graph,
            cache_dir=str(analyzer_cache_dir),
        )
        partial_cache = partial.get("cache", {})
        expect(partial_cache.get("status") == "partial", f"{name}: cache subset harus partial")
        expect(partial_cache.get("reused_count") == 2, f"{name}: partial harus reuse subset")
        expect(partial_cache.get("executed_count") == 11, f"{name}: partial harus eksekusi sisanya")

        old_signature = partial_cache.get("graph_content_signature")
        (project / "b.ts").write_text(
            "import './c';\nexport const b = true;\n",
            encoding="utf-8",
        )
        changed_graph = build_cached_shared_graph(
            str(project),
            cache_dir=str(graph_cache_dir),
        )
        changed = run_cached_analyzers(
            changed_graph,
            cache_dir=str(analyzer_cache_dir),
        )
        changed_cache = changed.get("cache", {})
        expect(changed_cache.get("status") == "invalidated", f"{name}: source change harus invalidate")
        expect(
            "graph_content_changed" in changed_cache.get("invalidation_reasons", []),
            f"{name}: alasan invalidasi graph harus eksplisit",
        )
        expect(changed_cache.get("executed_count") == 13, f"{name}: graph baru harus hitung ulang")
        expect(
            changed_cache.get("graph_content_signature") != old_signature,
            f"{name}: mutation harus mengubah graph signature",
        )

        semantic_graph = json.loads(json.dumps(changed_graph))
        semantic_vertex = sorted(semantic_graph.get("vertices", []))[0]
        semantic_graph["node_metadata"][semantic_vertex]["type"] = "SemanticMutation"
        semantic_invalidated = run_cached_analyzers(
            semantic_graph,
            cache_dir=str(analyzer_cache_dir),
        )
        expect(
            semantic_invalidated.get("cache", {}).get("status") == "invalidated",
            f"{name}: perubahan metadata graph harus invalidate",
        )
        expect(
            "graph_content_changed"
            in semantic_invalidated.get("cache", {}).get("invalidation_reasons", []),
            f"{name}: signature harus mencakup semantic graph, bukan source saja",
        )
        restored_graph = run_cached_analyzers(
            changed_graph,
            cache_dir=str(analyzer_cache_dir),
        )
        expect(
            restored_graph.get("cache", {}).get("status") == "invalidated",
            f"{name}: graph canonical harus mengganti synthetic evidence",
        )

        analyzer_cache_path = Path(restored_graph.get("cache", {}).get("cache_path", ""))
        payload = json.loads(analyzer_cache_path.read_text(encoding="utf-8"))
        payload["engine_signature"] = "sha256:stale-engine"
        analyzer_cache_path.write_text(json.dumps(payload), encoding="utf-8")
        engine_invalidated = run_cached_analyzers(
            changed_graph,
            cache_dir=str(analyzer_cache_dir),
        )
        engine_cache = engine_invalidated.get("cache", {})
        expect(engine_cache.get("status") == "invalidated", f"{name}: engine change harus invalidate")
        expect(
            "analyzer_engine_changed" in engine_cache.get("invalidation_reasons", []),
            f"{name}: alasan invalidasi engine harus eksplisit",
        )
        expect(engine_cache.get("executed_count") == 13, f"{name}: engine baru harus hitung ulang")

        analyzer_cache_path.write_text("{cache-rusak", encoding="utf-8")
        recovered = run_cached_analyzers(
            changed_graph,
            cache_dir=str(analyzer_cache_dir),
        )
        recovered_cache = recovered.get("cache", {})
        expect(recovered_cache.get("status") == "recovered", f"{name}: corrupt harus recovery")
        expect(recovered_cache.get("executed_count") == 13, f"{name}: recovery harus hitung ulang")
        expect(
            str(recovered_cache.get("recovery_reason", "")).startswith("analyzer_cache_read_error:"),
            f"{name}: alasan recovery harus transparan",
        )

        refreshed = run_cached_analyzers(
            changed_graph,
            cache_dir=str(analyzer_cache_dir),
            mode="refresh",
        )
        expect(refreshed.get("cache", {}).get("status") == "refreshed", f"{name}: refresh eksplisit")
        expect(refreshed.get("cache", {}).get("executed_count") == 13, f"{name}: refresh hitung ulang")
        status = get_analyzer_cache_status(
            source_key,
            changed_cache.get("graph_content_signature"),
            cache_dir=str(analyzer_cache_dir),
        )
        expect(status.get("status") == "valid", f"{name}: status analyzer harus valid")
        expect(status.get("analyzer_count") == 13, f"{name}: status harus lapor 13 analyzer")

        disabled = run_cached_analyzers(
            changed_graph,
            subset_names,
            cache_dir=str(analyzer_cache_dir),
            mode="off",
        )
        expect(disabled.get("cache", {}).get("status") == "disabled", f"{name}: mode off harus bypass")
        expect(disabled.get("cache", {}).get("executed_count") == 2, f"{name}: off tetap eksekusi subset")

        error_cache_dir = Path(temporary_root) / "error-cache"
        first_error = run_cached_analyzers(
            changed_graph,
            ["tidak.ada"],
            cache_dir=str(error_cache_dir),
        )
        second_error = run_cached_analyzers(
            changed_graph,
            ["tidak.ada"],
            cache_dir=str(error_cache_dir),
        )
        expect(first_error.get("analyzers_failed") == 1, f"{name}: analyzer error harus terlihat")
        expect(second_error.get("cache", {}).get("executed_count") == 1, f"{name}: error tidak boleh dicache")
        expect(second_error.get("cache", {}).get("reused_count") == 0, f"{name}: error tidak boleh reuse")

        cleared = clear_analyzer_cache(
            source_key,
            cache_dir=str(analyzer_cache_dir),
        )
        expect(cleared.get("status") == "cleared", f"{name}: clear harus menghapus evidence")
        missing = get_analyzer_cache_status(
            source_key,
            cache_dir=str(analyzer_cache_dir),
        )
        expect(missing.get("status") == "missing", f"{name}: status setelah clear harus missing")

        write_failed = run_cached_analyzers(
            changed_graph,
            cache_dir=str(project / "a.ts"),
        )
        expect(
            write_failed.get("cache", {}).get("status") == "write_failed",
            f"{name}: write failure tidak boleh menggagalkan analyzer",
        )
        expect(
            len(write_failed.get("results", {})) == 13,
            f"{name}: write failure tetap harus menghasilkan 13 evidence",
        )

        from hott_kernel import kernel_cache

        kernel_cache("clear", str(project))
        kernel_refresh = kernel_cache("refresh", str(project))
        expect(
            kernel_refresh.get("cache", {}).get("analyzer_cache", {}).get("status")
            == "refreshed",
            f"{name}: kernel refresh harus mengisi dua lapis cache",
        )
        (project / "a.ts").write_text(
            "import './b';\nexport const a = 'changed-after-refresh';\n",
            encoding="utf-8",
        )
        stale_status = kernel_cache("status", str(project)).get("cache", {})
        expect(stale_status.get("status") == "stale", f"{name}: source mutation harus stale")
        expect(
            stale_status.get("analyzer_cache", {}).get("status") == "stale",
            f"{name}: analyzer status harus mengikuti source stale",
        )
        expect(
            "source_snapshot_stale"
            in stale_status.get("analyzer_cache", {}).get("stale_reasons", []),
            f"{name}: alasan stale source harus eksplisit",
        )
        kernel_cache("clear", str(project))


def test_f31_memory_topology_betti():
    name = "F31"
    from memory.graph import build_memory_graph_from_data
    from memory.analyzers import analyze_betti_breakdown, analyze_circular
    from memory.synthesizer import generate_memory_steering_signals

    # Test case 1: In-memory memory graph
    memories = [
        {"id": "m1", "type": "episodic", "importance": 0.8},
        {"id": "m2", "type": "episodic", "importance": 0.8},
        {"id": "m3", "type": "episodic", "importance": 0.8},
        {"id": "m4", "type": "semantic", "importance": 0.9},
    ]
    associations = [
        {"id": "a1", "from": "m1", "to": "m2", "type": "temporal"},
        {"id": "a2", "from": "m2", "to": "m3", "type": "temporal"},
        {"id": "a3", "from": "m3", "to": "m1", "type": "temporal"},
        {"id": "a4", "from": "m1", "to": "m4", "type": "consolidation"},
    ]

    graph = build_memory_graph_from_data(memories, associations)
    expect("edge_types" in graph, f"{name}: edge_types must be in memory graph")
    expect(graph["summary"]["total_memories"] == 4, f"{name}: 4 memories expected")
    expect(
        graph.get("model", {}).get("name")
        == "memory_association_multigraph_1_complex",
        f"{name}: memory graph model harus eksplisit",
    )

    # Test Betti breakdown
    breakdown = analyze_betti_breakdown(graph)
    betti = breakdown.get("betti_numbers", {})
    expect(betti.get("beta_0") == 1, f"{name}: beta_0 should be 1")
    expect(betti.get("beta_1_total") == 1, f"{name}: beta_1_total should be 1")
    expect(betti.get("beta_1_reasoning") == 0, f"{name}: beta_1_reasoning should be 0 for temporal loop")
    expect(betti.get("beta_1_structural") == 1, f"{name}: beta_1_structural should be 1 for temporal loop")

    # Parallel reasoning associations are distinct 1-cells. They increase the
    # undirected cycle rank but do not form a directed circular-reasoning path.
    parallel_graph = build_memory_graph_from_data(
        [
            {"id": "p1", "type": "semantic"},
            {"id": "p2", "type": "semantic"},
        ],
        [
            {"id": "pa1", "from": "p1", "to": "p2", "type": "inferential"},
            {"id": "pa2", "from": "p1", "to": "p2", "type": "causal"},
        ],
    )
    expect(len(parallel_graph.get("edges", [])) == 2, f"{name}: edge multiplicity harus terjaga")
    expect(
        parallel_graph.get("summary", {}).get("by_edge_type")
        == {"inferential": 1, "causal": 1},
        f"{name}: parallel edge types tidak boleh saling menimpa",
    )
    parallel_breakdown = analyze_betti_breakdown(parallel_graph)
    expect(
        parallel_breakdown.get("topological_model", {}).get("name")
        == "memory_association_multigraph_1_complex",
        f"{name}: breakdown harus membawa model ke consumer/LLM",
    )
    expect(
        parallel_breakdown.get("betti_numbers", {}).get("beta_1_reasoning") == 1,
        f"{name}: parallel 1-cells harus memberi reasoning cycle rank 1",
    )
    expect(
        parallel_breakdown.get("interpretation", {}).get(
            "directed_reasoning_cycle_witness_count"
        ) == 0,
        f"{name}: parallel edge searah bukan directed circular reasoning",
    )
    parallel_signals = generate_memory_steering_signals(
        {
            "memory_archetype": "memory_sparse_cyclic",
            "betti_numbers": {"beta_0": 1, "beta_1": 1, "beta_2": 0},
        },
        {"topology_changed": False, "interpretation": "none"},
        0.8,
        directed_reasoning_cycle_witness_count=0,
    )
    expect(
        "association_cycle_rank_present" in parallel_signals.get("attention_priorities", []),
        f"{name}: steering harus membawa cycle rank sebagai sinyal struktur",
    )
    expect(
        "directed_circular_reasoning_witness_present"
        not in parallel_signals.get("attention_priorities", []),
        f"{name}: steering tidak boleh mengubah parallel edge menjadi reasoning loop",
    )

    directed_graph = build_memory_graph_from_data(
        [
            {"id": "r1", "type": "semantic"},
            {"id": "r2", "type": "semantic"},
            {"id": "r3", "type": "semantic"},
        ],
        [
            {"id": "ra1", "from": "r1", "to": "r2", "type": "inferential"},
            {"id": "ra2", "from": "r2", "to": "r3", "type": "causal"},
            {"id": "ra3", "from": "r3", "to": "r1", "type": "inferential"},
        ],
    )
    directed = analyze_circular(directed_graph, edge_type_filter={"inferential", "causal"})
    expect(
        directed.get("summary", {}).get("directed_cycle_witness_count") == 1,
        f"{name}: directed reasoning loop harus punya path witness",
    )
    expect(
        directed.get("summary", {}).get("beta_1") == 1,
        f"{name}: directed loop harus tetap konsisten dengan cycle rank",
    )
    expect(
        "not all elementary cycles"
        in directed.get("summary", {}).get("directed_cycle_witness_semantics", ""),
        f"{name}: batas enumerasi witness harus eksplisit",
    )
    directed_signals = generate_memory_steering_signals(
        {
            "memory_archetype": "memory_sparse_cyclic",
            "betti_numbers": {"beta_0": 1, "beta_1": 1, "beta_2": 0},
        },
        {"topology_changed": False, "interpretation": "none"},
        0.8,
        directed_reasoning_cycle_witness_count=1,
    )
    expect(
        "directed_circular_reasoning_witness_present"
        in directed_signals.get("attention_priorities", []),
        f"{name}: directed witness harus mencapai steering signal",
    )


def _run_scoped_kernel(
    state_dir: Path,
    project_root: Path,
    *args: str,
    expect_success: bool = True,
):
    """Run one isolated CLI invocation against a project-scoped runtime."""
    env = dict(os.environ)
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "AI_STUDIO_STATE_DIR": str(state_dir),
        "AI_STUDIO_PROJECT_ROOT": str(project_root),
    })
    completed = subprocess.run(
        [sys.executable, str(ROOT / "hott_kernel.py"), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        expect(False, f"SCOPED KERNEL: {' '.join(args)} bukan JSON valid: {exc}")
        return completed, {}
    if expect_success:
        expect(
            completed.returncode == 0 and not payload.get("error"),
            (
                f"SCOPED KERNEL: {' '.join(args)} gagal "
                f"({completed.returncode}): {payload.get('error') or completed.stderr.strip()}"
            ),
        )
    return completed, payload


def test_f37_memory_runtime_integrity():
    """Project scope, deduplication, locking, recovery, and permissions."""
    name = "F37"
    with tempfile.TemporaryDirectory(prefix="ai-studio-memory-runtime-") as tmp:
        root = Path(tmp)
        state_dir = root / "state"
        project_a = root / "project-a"
        project_b = root / "project-b"
        project_race = root / "project-race"
        project_broken = root / "project-broken"
        for project in (project_a, project_b, project_race, project_broken):
            project.mkdir(parents=True)
        (project_a / "app.ts").write_text("export const projectA = true;\n", encoding="utf-8")
        (project_b / "app.ts").write_text("export const projectB = true;\n", encoding="utf-8")

        # State location alone must not collapse different scan roots into one scope.
        auto_env = dict(os.environ)
        auto_env.update({
            "PYTHONDONTWRITEBYTECODE": "1",
            "AI_STUDIO_STATE_DIR": str(state_dir),
        })
        auto_env.pop("AI_STUDIO_PROJECT_ROOT", None)
        auto_env.pop("AI_STUDIO_MEMORY_SCOPE", None)
        auto_scope_ids = []
        for project in (project_a, project_b):
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "hott_kernel.py"),
                    "context", "project app", str(project),
                    "--target", "app.ts", "--budget-tokens", "256", "--output", "prompt",
                ],
                cwd=ROOT,
                env=auto_env,
                text=True,
                capture_output=True,
                check=False,
            )
            payload = json.loads(completed.stdout)
            expect(completed.returncode == 0, f"{name}: auto-scope context harus sukses")
            auto_scope_ids.append(
                payload.get("provenance", {}).get("memory_scope", {}).get("scope_id")
            )
        expect(
            all(auto_scope_ids) and len(set(auto_scope_ids)) == 2,
            f"{name}: scan root berbeda harus otomatis mendapat memory scope berbeda",
        )

        _, stored_a = _run_scoped_kernel(
            state_dir,
            project_a,
            "memory", "store", "episodic",
            "Project A evidence for src/services/cache.service.ts",
            "--source", "f37-project-a", "--tags", "cache,src.services",
        )
        _, stored_b = _run_scoped_kernel(
            state_dir,
            project_b,
            "memory", "store", "episodic",
            "Project B evidence for src/services/cache.service.ts",
            "--source", "f37-project-b", "--tags", "cache,src.services",
        )
        expect(stored_a.get("status") == "stored", f"{name}: project A harus tersimpan")
        expect(stored_b.get("status") == "stored", f"{name}: project B harus tersimpan")

        _, context_a = _run_scoped_kernel(
            state_dir,
            project_a,
            "xcontext", "src/services/cache.service.ts",
        )
        contents_a = [item.get("content", "") for item in context_a.get("memories", [])]
        expect(any("Project A" in item for item in contents_a), f"{name}: scope A harus recall A")
        expect(not any("Project B" in item for item in contents_a), f"{name}: scope A tidak boleh bocor ke B")
        expect(
            context_a.get("memory_scope", {}).get("scope_id"),
            f"{name}: xcontext harus membawa provenance scope",
        )

        # Direct association command must not bypass directed-cycle safety.
        _, second_a = _run_scoped_kernel(
            state_dir,
            project_a,
            "memory", "store", "semantic", "Project A second reasoning node",
            "--source", "f37-cycle-safety",
        )
        first_a_id = stored_a.get("memory", {}).get("id")
        second_a_id = second_a.get("memory", {}).get("id")
        _, forward_association = _run_scoped_kernel(
            state_dir,
            project_a,
            "memory", "associate", first_a_id, second_a_id, "inferential",
        )
        expect(
            forward_association.get("status") == "associated",
            f"{name}: reasoning edge acyclic harus diterima",
        )
        completed, rejected_reverse = _run_scoped_kernel(
            state_dir,
            project_a,
            "memory", "associate", second_a_id, first_a_id, "causal",
            expect_success=False,
        )
        expect(completed.returncode == 2, f"{name}: direct reasoning loop harus exit 2")
        expect(
            rejected_reverse.get("error_code") == "would_create_reasoning_cycle",
            f"{name}: direct association harus memakai safety error stabil",
        )
        _, memory_summary = _run_scoped_kernel(
            state_dir,
            project_a,
            "memory", "analyze", "--output", "summary",
        )
        expect(
            memory_summary.get("topological_model", {}).get("name")
            == "memory_association_multigraph_1_complex",
            f"{name}: CLI summary harus membawa model memory graph",
        )
        expect(
            memory_summary.get("cycle_semantics", {}).get(
                "directed_reasoning_cycle_witness_count"
            ) == 0,
            f"{name}: edge reasoning acyclic tidak boleh dilabeli circular",
        )

        # Identical analyzer evidence must be observed again, not duplicated.
        fixture_project = ROOT / "fixtures_min/f20_cache_audit/project"
        _, first = _run_scoped_kernel(
            state_dir,
            fixture_project,
            "xanalyze", str(fixture_project), "--output", "summary",
        )
        _, second = _run_scoped_kernel(
            state_dir,
            fixture_project,
            "xanalyze", str(fixture_project), "--output", "summary",
        )
        first_store = first.get("memory_store_result", {})
        second_store = second.get("memory_store_result", {})
        expect(first_store.get("stored_count", 0) > 0, f"{name}: analisis pertama harus store evidence")
        expect(second_store.get("stored_count") == 0, f"{name}: analisis identik tidak boleh duplicate")
        expect(
            second_store.get("reused_count") == first_store.get("stored_count"),
            f"{name}: evidence identik harus direuse seluruhnya",
        )
        _, deduplicated = _run_scoped_kernel(
            state_dir,
            fixture_project,
            "memory", "recall", "--limit", "100",
        )
        expect(
            deduplicated.get("count") == first_store.get("stored_count"),
            f"{name}: total node harus tetap sama setelah analisis identik",
        )
        expect(
            all(
                item.get("context", {}).get("observation_count") == 2
                for item in deduplicated.get("results", [])
            ),
            f"{name}: re-observation harus menaikkan counter node yang sama",
        )

        # All successful concurrent writers must survive the read-modify-write cycle.
        env = dict(os.environ)
        env.update({
            "PYTHONDONTWRITEBYTECODE": "1",
            "AI_STUDIO_STATE_DIR": str(state_dir),
            "AI_STUDIO_PROJECT_ROOT": str(project_race),
        })
        processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "hott_kernel.py"),
                    "memory", "store", "episodic", f"parallel write {index:02d}",
                    "--source", "f37-race", "--tags", "concurrency",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for index in range(16)
        ]
        for process in processes:
            stdout, stderr = process.communicate(timeout=30)
            expect(process.returncode == 0, f"{name}: parallel writer gagal: {stderr or stdout}")
        _, race_stats = _run_scoped_kernel(state_dir, project_race, "memory", "stats")
        expect(race_stats.get("total_memories") == 16, f"{name}: 16/16 parallel writes harus persisten")

        runtime = race_stats.get("runtime", {})
        store_path = Path(runtime.get("store_path", ""))
        expect(store_path.is_file(), f"{name}: runtime harus mengekspos store path aktual")
        if os.name != "nt":
            expect(store_path.stat().st_mode & 0o777 == 0o600, f"{name}: store permission harus 0600")

        # One more valid write creates a last-known-good backup. Corruption must recover.
        _run_scoped_kernel(
            state_dir,
            project_race,
            "memory", "store", "episodic", "backup checkpoint", "--source", "f37-recovery",
        )
        store_path.write_text("{corrupt-json", encoding="utf-8")
        _, recovered = _run_scoped_kernel(state_dir, project_race, "memory", "stats")
        expect(recovered.get("total_memories") == 16, f"{name}: backup harus memulihkan last-known-good state")
        expect(
            recovered.get("runtime", {}).get("recovery", {}).get("status") == "recovered_from_backup",
            f"{name}: recovery harus terlihat dalam provenance",
        )

        # Missing primary with a valid backup is a recoverable interrupted-state case.
        store_path.unlink()
        _, missing_primary_recovered = _run_scoped_kernel(
            state_dir, project_race, "memory", "stats"
        )
        expect(
            missing_primary_recovered.get("total_memories") == 16,
            f"{name}: primary hilang harus dipulihkan dari backup valid",
        )
        expect(
            missing_primary_recovered.get("runtime", {}).get("recovery", {}).get("status")
            == "recovered_missing_primary_from_backup",
            f"{name}: recovery primary hilang harus terlihat dalam provenance",
        )

        # Missing primary plus invalid backup must block instead of becoming empty.
        backup_path = Path(f"{store_path}.bak")
        backup_path.write_text("{invalid-backup", encoding="utf-8")
        store_path.unlink()
        completed, missing_and_broken = _run_scoped_kernel(
            state_dir,
            project_race,
            "memory", "stats",
            expect_success=False,
        )
        expect(completed.returncode == 2, f"{name}: missing+invalid harus exit 2")
        expect(
            missing_and_broken.get("error_code") == "memory_store_corrupt",
            f"{name}: missing+invalid backup harus menjadi stop condition",
        )
        expect(
            missing_and_broken.get("primary_error") == "primary_missing",
            f"{name}: provenance harus membedakan primary hilang",
        )

        # Without a valid backup, corruption must block both reads and writes.
        _, first_broken = _run_scoped_kernel(
            state_dir,
            project_broken,
            "memory", "store", "episodic", "only checkpoint", "--source", "f37-broken",
        )
        broken_scope = first_broken.get("memory_scope", {})
        if not broken_scope:
            _, broken_stats = _run_scoped_kernel(state_dir, project_broken, "memory", "stats")
            broken_scope = broken_stats.get("runtime", {})
        broken_path = Path(broken_scope.get("store_path", ""))
        broken_path.write_text("{unrecoverable", encoding="utf-8")
        completed, broken_read = _run_scoped_kernel(
            state_dir,
            project_broken,
            "memory", "stats",
            expect_success=False,
        )
        expect(completed.returncode == 2, f"{name}: corrupt tanpa backup harus exit 2")
        expect(
            broken_read.get("error_code") == "memory_store_corrupt",
            f"{name}: corrupt tanpa backup harus punya error code stabil",
        )
        completed, broken_write = _run_scoped_kernel(
            state_dir,
            project_broken,
            "memory", "store", "episodic", "must not overwrite",
            expect_success=False,
        )
        expect(completed.returncode == 2, f"{name}: write setelah corrupt harus tetap diblok")
        expect(
            broken_write.get("error_code") == "memory_store_corrupt",
            f"{name}: write tidak boleh mengganti corrupt store dengan state kosong",
        )
        expect(
            broken_path.read_text(encoding="utf-8") == "{unrecoverable",
            f"{name}: primary corrupt harus dipertahankan sampai perbaikan eksplisit",
        )


def test_f38_memory_augmented_context_budget():
    """The primary context command must include scoped memory within its hard budget."""
    name = "F38"
    with tempfile.TemporaryDirectory(prefix="ai-studio-memory-context-") as tmp:
        root = Path(tmp)
        state_dir = root / "state"
        project = ROOT / "fixtures_min/f16_file_brief/project"
        target = "src/app.ts"
        memory_text = "Historical invariant: src/app.ts requires deterministic startup ordering."
        _run_scoped_kernel(
            state_dir,
            project,
            "memory", "store", "semantic", memory_text,
            "--source", "f38", "--importance", "0.95", "--tags", "startup,src",
        )
        _, result = _run_scoped_kernel(
            state_dir,
            project,
            "context", "historical startup invariant", str(project),
            "--target", target,
            "--budget-tokens", "400",
            "--output", "prompt",
        )
        memory_context = result.get("memory_context", {})
        expect(memory_context.get("selected_count") == 1, f"{name}: satu memory evidence harus dipilih")
        expect(memory_text in result.get("context_block", ""), f"{name}: isi memory harus mencapai prompt LLM")
        expect(
            "[PROJECT MEMORY EVIDENCE]" in result.get("context_block", ""),
            f"{name}: memory harus dibedakan eksplisit dari source evidence",
        )
        expect(result.get("budget", {}).get("within_budget") is True, f"{name}: hard budget harus terjaga")
        expect(
            any(
                str(path).replace("\\", "/").endswith(target)
                for path in result.get("selection", {}).get("selected_paths", [])
            ),
            f"{name}: memory evidence tidak boleh menggusur explicit source target",
        )
        expect(
            result.get("provenance", {}).get("memory_scope", {}).get("scope_id"),
            f"{name}: prompt harus membawa memory-scope provenance",
        )
        expect(
            result.get("provenance", {}).get("memory_retrieval", {}).get("claim_boundary")
            == "deterministic lexical-and-path retrieval; not semantic embedding proof",
            f"{name}: batas klaim retrieval harus eksplisit",
        )

        oversized = "Oversized sentinel historical evidence: " + ("x" * 2000)
        _run_scoped_kernel(
            state_dir,
            project,
            "memory", "store", "semantic", oversized,
            "--source", "f38-large", "--importance", "0.99", "--tags", "sentinel",
        )
        _, bounded = _run_scoped_kernel(
            state_dir,
            project,
            "context", "oversized sentinel", str(project),
            "--target", target, "--budget-tokens", "400", "--output", "prompt",
        )
        selected_memory = bounded.get("memory_context", {}).get("selected", [])
        expect(selected_memory, f"{name}: memory panjang tetap harus punya bounded witness")
        expect(
            selected_memory[0].get("content_truncated") is True,
            f"{name}: truncation memory harus transparan",
        )
        expect(
            oversized not in bounded.get("context_block", ""),
            f"{name}: full memory tidak boleh membypass context budget",
        )
        expect(
            bounded.get("budget", {}).get("within_budget") is True,
            f"{name}: memory panjang tetap harus mematuhi hard budget",
        )


def _run_kernel(*args):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(ROOT / "hott_kernel.py"), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    expect(
        completed.returncode == 0,
        f"KERNEL: {' '.join(args)} gagal: {completed.stderr.strip()}",
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        expect(False, f"KERNEL: {' '.join(args)} bukan JSON valid: {exc}")
        return {}
    expect(
        not result.get("error"),
        f"KERNEL: {' '.join(args)} mengembalikan error: {result.get('error')}",
    )
    return result


def test_kernel_wiring_smoke():
    """Kunci jalur CLI read-only yang rentan rusak setelah reorganisasi modul."""
    analyzers = _run_kernel("analyzers").get("available_analyzers", [])
    expect(len(analyzers) == 13, "KERNEL: semua 13 codebase analyzer harus aktif")
    expect("topo.circular" in analyzers, "KERNEL: topo.circular harus terdaftar")
    expect("topo.risk" in analyzers, "KERNEL: topo.risk harus terdaftar")
    expect(
        "topo.test_reachability" in analyzers,
        "KERNEL: topo.test_reachability harus terdaftar",
    )

    project = "fixtures_min/f16_file_brief/project"
    target = f"{project}/src/app.ts"
    for command in ("impact", "outline", "brief"):
        result = _run_kernel(command, target, project)
        expect(result.get("exists") is True, f"KERNEL: {command} harus menemukan target")

    _run_kernel("cache", "clear", project)
    context_result = _run_kernel(
        "context",
        "app dependency change",
        project,
        "--target",
        target,
        "--budget-tokens",
        "400",
        "--output",
        "prompt",
    )
    expect(context_result.get("mode") == "context", "KERNEL: mode context harus terhubung")
    expect(
        target in context_result.get("selection", {}).get("selected_paths", []),
        "KERNEL: context harus membawa explicit target",
    )
    expect(
        context_result.get("budget", {}).get("within_budget") is True,
        "KERNEL: context CLI harus mematuhi budget",
    )
    first_cache = context_result.get("graph_cache", {})
    expect(first_cache.get("status") == "miss", "KERNEL: context awal harus cache miss")
    expect(first_cache.get("files_read") == 3, "KERNEL: context awal harus baca 3 source")
    first_analyzer_cache = context_result.get("analyzer_cache", {})
    expect(first_analyzer_cache.get("status") == "miss", "KERNEL: analyzer awal harus cache miss")
    expect(first_analyzer_cache.get("executed_count") == 13, "KERNEL: awal harus eksekusi 13 analyzer")
    expect(
        context_result.get("provenance", {}).get("analyzer_cache") == first_analyzer_cache,
        "KERNEL: provenance context harus membawa analyzer cache yang sama",
    )

    repeated_context = _run_kernel(
        "context",
        "app dependency change",
        project,
        "--target",
        target,
        "--budget-tokens",
        "400",
        "--output",
        "prompt",
    )
    repeated_cache = repeated_context.get("graph_cache", {})
    expect(repeated_cache.get("status") == "hit", "KERNEL: context kedua harus cache hit")
    expect(repeated_cache.get("files_reused") == 3, "KERNEL: context kedua harus reuse 3 source")
    expect(repeated_cache.get("files_read") == 0, "KERNEL: context kedua tidak boleh baca source")
    repeated_analyzer_cache = repeated_context.get("analyzer_cache", {})
    expect(repeated_analyzer_cache.get("status") == "hit", "KERNEL: analyzer kedua harus cache hit")
    expect(repeated_analyzer_cache.get("reused_count") == 13, "KERNEL: 13 analyzer harus reuse")
    expect(repeated_analyzer_cache.get("executed_count") == 0, "KERNEL: analyzer hit tidak boleh eksekusi")
    expect(
        context_result.get("context_block") == repeated_context.get("context_block"),
        "KERNEL: cache tidak boleh mengubah context block",
    )
    cache_status = _run_kernel("cache", "status", project).get("cache", {})
    expect(cache_status.get("status") == "valid", "KERNEL: cache status harus valid")
    expect(
        cache_status.get("analyzer_cache", {}).get("status") == "valid",
        "KERNEL: cache status harus mencakup analyzer evidence",
    )
    expect(
        cache_status.get("analyzer_cache", {}).get("analyzer_count") == 13,
        "KERNEL: cache status harus lapor 13 analyzer",
    )

    steer = _run_kernel("steer", project, "--output", "summary")
    expect(
        steer.get("analyzer_cache", {}).get("status") == "hit",
        "KERNEL: steer harus reuse evidence yang relevan",
    )

    for args in (
        ("memory", "steer", "--output", "summary"),
        ("memory", "drift"),
        ("memory", "betti_breakdown"),
        ("memory", "unconsolidated_tags"),
        ("memory", "bridge_candidates"),
        ("fiber", "list_archives"),
    ):
        _run_kernel(*args)

    xsteer = _run_kernel("xsteer", project, "--output", "full")
    memory_archetype = xsteer.get("memory_steering", {}).get("archetype")
    expect(
        memory_archetype not in (None, "unknown"),
        "KERNEL: xsteer harus meneruskan memory_archetype yang terhitung",
    )
    _run_kernel("cache", "clear", project)


def test_kernel_cli_contract():
    """Kunci validasi input dan status analyzer untuk pemanggil Bash/API."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    def run_raw(*args):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "hott_kernel.py"), *args],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            expect(False, f"CLI: {' '.join(args)} bukan JSON valid: {exc}")
            return completed, {}
        return completed, payload

    completed, help_payload = run_raw("--help")
    expect(completed.returncode == 0, "CLI: --help harus sukses")
    expect(not help_payload.get("error"), "CLI: --help tidak boleh menjadi error")
    expect("analyze" in help_payload.get("usage", {}), "CLI: help harus memuat analyze")
    expect("context" in help_payload.get("usage", {}), "CLI: help harus memuat context")
    expect("cache" in help_payload.get("usage", {}), "CLI: help harus memuat cache")
    expect(
        "cache_mode" in help_payload.get("global_options", {}),
        "CLI: help harus memuat cache mode global",
    )
    for option in ("memory_project_root", "memory_scope", "memory_state_dir"):
        expect(
            option in help_payload.get("global_options", {}),
            f"CLI: help harus memuat {option}",
        )

    completed, invalid_memory_type = run_raw(
        "memory", "store", "bukan-tipe", "invalid memory",
    )
    expect(completed.returncode == 2, "CLI: memory input error harus exit code 2")
    expect(
        "Invalid memory type" in invalid_memory_type.get("error", ""),
        "CLI: memory input error harus terlihat untuk Bash",
    )

    project = "fixtures_min/f16_file_brief/project"
    completed, invalid_analyzer = run_raw(
        "analyze",
        project,
        "--analyzers",
        "tidak.ada",
        "--output",
        "summary",
    )
    summary = invalid_analyzer.get("unified_summary", {})
    expect(completed.returncode == 3, "CLI: partial analyzer result harus memakai exit code 3")
    expect(summary.get("analyzers_failed") == 1, "CLI: analyzer invalid harus dihitung gagal")
    expect(summary.get("analysis_status") == "partial", "CLI: analyzer gagal harus berstatus partial")
    expect(
        "tidak.ada" in summary.get("analyzer_errors", {}),
        "CLI: alasan analyzer gagal harus tersedia untuk pemanggil",
    )

    completed, missing_root = run_raw("synthesize", "direktori-yang-tidak-ada", "--output", "summary")
    expect(completed.returncode == 2, "CLI: input error harus memakai exit code 2")
    expect(
        missing_root.get("error_code") == "scan_root_not_found",
        "CLI: root yang tidak ada harus ditolak eksplisit",
    )

    completed, invalid_output = run_raw("synthesize", project, "--output", "bukan-mode")
    expect(completed.returncode == 2, "CLI: output mode invalid harus memakai exit code 2")
    expect(
        invalid_output.get("error_code") == "invalid_output_mode",
        "CLI: output mode invalid harus ditolak eksplisit",
    )

    completed, invalid_cache_mode = run_raw(
        "analyze",
        project,
        "--output",
        "summary",
        "--cache-mode",
        "bukan-mode",
    )
    expect(completed.returncode == 2, "CLI: cache mode invalid harus memakai exit code 2")
    expect(
        invalid_cache_mode.get("error_code") == "invalid_graph_cache_mode",
        "CLI: cache mode invalid harus punya error code stabil",
    )

    completed, invalid_cache_action = run_raw("cache", "bukan-aksi", project)
    expect(completed.returncode == 2, "CLI: cache action invalid harus memakai exit code 2")
    expect(
        invalid_cache_action.get("error_code") == "invalid_cache_action",
        "CLI: cache action invalid harus punya error code stabil",
    )

    completed, cache_off = run_raw(
        "analyze",
        project,
        "--output",
        "summary",
        "--cache-mode",
        "off",
    )
    expect(completed.returncode == 0, "CLI: cache mode off harus tetap sukses")
    expect(
        cache_off.get("graph_cache", {}).get("status") == "disabled",
        "CLI: mode off harus terlihat dalam provenance",
    )
    expect(
        cache_off.get("analyzer_cache", {}).get("status") == "disabled",
        "CLI: mode off harus membypass analyzer cache juga",
    )

    completed, invalid_budget = run_raw(
        "context",
        "app dependency",
        project,
        "--budget-tokens",
        "12",
    )
    expect(completed.returncode == 2, "CLI: context budget terlalu kecil harus exit code 2")
    expect(
        invalid_budget.get("error_code") == "invalid_context_budget",
        "CLI: context budget invalid harus ditolak eksplisit",
    )

    completed, missing_target = run_raw(
        "context",
        "app dependency",
        project,
        "--target",
        "src/tidak-ada.ts",
    )
    expect(completed.returncode == 2, "CLI: explicit target yang hilang harus exit code 2")
    expect(
        missing_target.get("error_code") == "context_target_not_found",
        "CLI: target context yang hilang harus punya error code stabil",
    )

    _, empty_analysis = run_raw("analyze", ".", "--output", "summary")
    empty_summary = empty_analysis.get("unified_summary", {})
    expect(empty_summary.get("analysis_status") == "empty", "CLI: domain tanpa TS/JS harus ditandai empty")
    expect(
        ".py" not in empty_summary.get("supported_source_extensions", []),
        "CLI: dukungan Python tidak boleh aktif secara implisit",
    )

    completed, _ = run_raw("analyze", project, "--output", "summary")
    expect(
        "DeprecationWarning" not in completed.stderr,
        "CLI: analisis tidak boleh menghasilkan warning datetime deprecated",
    )
    run_raw("cache", "clear", project)
    run_raw("cache", "clear", ".")


def main():
    write_fixtures()

    tests = [
        test_f01_basic_relative,
        test_f02_extensionless,
        test_f04_tsx_jsx,
        test_f05_unresolved,
        test_f09_circular,
        test_f08_entrypoint,
        test_f10_graph_metrics,
        test_f11_change_risk_advisory,
        test_f12_unreferenced_files,
        test_f13_multi_root,
        test_f14_file_outline,
        test_f15_alias_paths,
        test_f16_file_brief,
        test_f17_async_waterfall,
        test_f18_deopt_checker,
        test_f19_gc_pressure,
        test_f20_cache_audit,
        test_f21_type_isomorphism,
        test_f22_boundary_sheaf,
        test_f23_sheaf_precision,
        test_f24_homotopy_path,
        test_f25_topological_synthesis,
        test_f26_topological_manifold,
        test_f27_invariant_encoder,
        test_f28_decoder_steering,
        test_f29_archetype_calibration,
        test_f30_complexity_calibration,
        test_f31_memory_topology_betti,
        test_f32_reciprocal_cycle_basis,
        test_f33_static_test_reachability,
        test_f34_context_optimizer,
        test_f35_incremental_graph_cache,
        test_f36_analyzer_evidence_cache,
        test_f37_memory_runtime_integrity,
        test_f38_memory_augmented_context_budget,
        test_kernel_wiring_smoke,
        test_kernel_cli_contract,
    ]

    for test in tests:
        try:
            test()
        except Exception as exc:
            FAILURES.append(f"{test.__name__}: exception {exc}")

    if FAILURES:
        print("FAIL")
        for failure in FAILURES:
            print(f"- {failure}")
        sys.exit(1)

    print("PASS: 35 fixture minimal + 2 portable integration smoke aman")


if __name__ == "__main__":
    main()
