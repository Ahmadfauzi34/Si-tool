import {
  AngularNodeAppEngine,
  createNodeRequestHandler,
  isMainModule,
  writeResponseToNodeResponse,
} from '@angular/ssr/node';
import express, {type Request, type Response} from 'express';
import {access} from 'node:fs/promises';
import {execFile} from 'node:child_process';
import {basename, isAbsolute, join, relative, resolve, sep} from 'node:path';
import {promisify} from 'node:util';

const execFilePromise = promisify(execFile);
const browserDistFolder = join(import.meta.dirname, '../browser');
const kernelScript = 'tools/ai_studio_tool/hott_kernel.py';
const kernelMaxBuffer = 10 * 1024 * 1024;

type JsonRecord = Record<string, unknown>;

class InvalidProjectPathError extends Error {}

function asRecord(value: unknown): JsonRecord {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as JsonRecord
    : {};
}

function queryString(value: unknown): string | undefined {
  if (typeof value === 'string' && value.trim()) {
    return value.trim();
  }
  if (Array.isArray(value) && typeof value[0] === 'string' && value[0].trim()) {
    return value[0].trim();
  }
  return undefined;
}

function projectRelativePath(cwd: string, requestedPath: string): string {
  const absolutePath = resolve(cwd, requestedPath);
  const relativePath = relative(cwd, absolutePath);
  if (
    relativePath === '..'
    || relativePath.startsWith(`..${sep}`)
    || isAbsolute(relativePath)
  ) {
    throw new InvalidProjectPathError(`Path berada di luar project root: ${requestedPath}`);
  }
  return (relativePath || '.').split(sep).join('/');
}

async function getKernelScript(cwd: string): Promise<string> {
  await access(join(cwd, kernelScript));
  return kernelScript;
}

async function runKernel(cwd: string, args: string[]): Promise<JsonRecord> {
  const script = await getKernelScript(cwd);
  const {stdout} = await execFilePromise(
    'python3',
    [script, ...args],
    {cwd, encoding: 'utf8', maxBuffer: kernelMaxBuffer},
  );
  const stdoutText = typeof stdout === 'string' ? stdout : stdout.toString('utf8');
  let result: JsonRecord;
  try {
    result = asRecord(JSON.parse(stdoutText));
  } catch (error: unknown) {
    const err = error as Error;
    throw new Error(`Kernel mengembalikan JSON tidak valid: ${err.message}`);
  }
  if (typeof result['error'] === 'string') {
    throw new Error(result['error']);
  }
  return result;
}

function sendKernelError(res: Response, message: string, error: unknown): void {
  const err = error as Error;
  const status = error instanceof InvalidProjectPathError ? 400 : 500;
  res.status(status).json({error: message, details: err.message || String(err)});
}

function topologyForUi(kernelResult: JsonRecord): JsonRecord {
  const graph = asRecord(kernelResult['shared_graph']);
  const metadata = asRecord(graph['node_metadata']);
  const vertices = Array.isArray(graph['vertices']) ? graph['vertices'] : [];
  const rawEdges = Array.isArray(graph['edges']) ? graph['edges'] : [];

  const nodes = vertices
    .filter((value): value is string => typeof value === 'string')
    .map((path) => {
      const node = asRecord(metadata[path]);
      const filename = basename(path).replace(/\.(tsx?|jsx?)$/, '');
      return {
        id: path,
        path,
        label: filename,
        type: typeof node['type'] === 'string' ? node['type'] : 'Other',
        is_entrypoint: Boolean(node['is_entrypoint']),
        entrypoint_kind: node['entrypoint_kind'] ?? 'none',
        entrypoint_confidence: node['entrypoint_confidence'] ?? 0,
        is_test: Boolean(node['is_test']),
        fan_in: node['fan_in'] ?? 0,
        fan_out: node['fan_out'] ?? 0,
        direct_dependents_count: node['fan_in'] ?? 0,
      };
    });

  const edges = rawEdges.flatMap((edge) => {
    if (
      Array.isArray(edge)
      && typeof edge[0] === 'string'
      && typeof edge[1] === 'string'
    ) {
      return [{source: edge[0], target: edge[1]}];
    }
    return [];
  });

  return {
    schema_version: graph['schema_version'],
    meta: {
      root: graph['scan_root'],
      source: 'hott_kernel',
      mode: 'canonical_shared_graph',
    },
    nodes,
    edges,
    diagnostics: {
      unresolved_imports: graph['unresolved_imports'] ?? [],
      external_imports: graph['external_imports'] ?? [],
    },
    summary: graph['summary'] ?? {},
  };
}

function analyzerResult(
  kernelResult: JsonRecord,
  analyzerName: string,
  targetFile?: string,
): JsonRecord {
  const analyzers = asRecord(kernelResult['analyzers']);
  const results = asRecord(analyzers['results']);
  const selected = asRecord(results[analyzerName]);
  if (!Object.keys(selected).length) {
    throw new Error(`Analyzer tidak tersedia pada output kernel: ${analyzerName}`);
  }
  if (!targetFile || !Array.isArray(selected['findings'])) {
    return selected;
  }
  const findings = selected['findings'].filter((finding) => {
    const item = asRecord(finding);
    return item['file'] === targetFile || item['file_b'] === targetFile;
  });
  return {
    ...selected,
    findings,
    summary: {
      ...asRecord(selected['summary']),
      total_findings: findings.length,
      filtered_file: targetFile,
    },
  };
}

async function handleAnalyzer(
  req: Request,
  res: Response,
  analyzerName: string,
  errorMessage: string,
): Promise<void> {
  const cwd = process.cwd();
  try {
    const fileQuery = queryString(req.query['file']);
    const mode = queryString(req.query['mode']) || (fileQuery ? 'file' : 'scan');
    if (mode !== 'file' && mode !== 'scan') {
      res.status(400).json({error: "Parameter 'mode' harus 'file' atau 'scan'"});
      return;
    }
    const requestedRoot = queryString(req.query['root'])
      || (mode === 'scan' ? fileQuery : undefined)
      || 'src';
    const rootPath = projectRelativePath(cwd, requestedRoot);
    const targetFile = mode === 'file'
      ? projectRelativePath(cwd, fileQuery || 'src/app/app.ts')
      : undefined;
    const result = await runKernel(cwd, [
      'analyze', rootPath,
      '--analyzers', analyzerName,
      '--output', 'findings',
    ]);
    res.json(analyzerResult(result, analyzerName, targetFile));
  } catch (error: unknown) {
    sendKernelError(res, errorMessage, error);
  }
}

const app = express();
const angularApp = new AngularNodeAppEngine();

app.use(express.json());

// REST adapter untuk canonical HoTT Kernel.
app.get('/api/python-info', async (req, res) => {
  try {
    const cwd = process.cwd();
    const script = await getKernelScript(cwd);
    const {stdout: versionOut} = await execFilePromise(
      'python3',
      ['--version'],
      {encoding: 'utf8'},
    );
    const versionText = typeof versionOut === 'string'
      ? versionOut.trim()
      : versionOut.toString('utf8').trim();
    const analyzerInfo = await runKernel(cwd, ['analyzers']);
    const availableAnalyzers = Array.isArray(analyzerInfo['available_analyzers'])
      ? analyzerInfo['available_analyzers'].length
      : 0;
    res.json({
      supported: true,
      runtime: 'Python 3',
      version: versionText,
      script,
      status: 'active',
      available_analyzers: availableAnalyzers,
    });
  } catch (error: unknown) {
    const err = error as Error;
    res.json({
      supported: false,
      error: err.message || String(err)
    });
  }
});

app.get('/api/topology', async (req, res) => {
  try {
    const cwd = process.cwd();
    const rootPath = projectRelativePath(cwd, queryString(req.query['root']) || 'src');
    const result = await runKernel(cwd, ['analyze', rootPath, '--output', 'graph']);
    res.json(topologyForUi(result));
  } catch (error: unknown) {
    sendKernelError(res, 'Failed to scan topology', error);
  }
});

app.get('/api/impact', async (req, res) => {
  try {
    const cwd = process.cwd();
    const filePath = projectRelativePath(cwd, queryString(req.query['file']) || 'src/app/app.ts');
    const rootPath = projectRelativePath(cwd, queryString(req.query['root']) || '.');
    res.json(await runKernel(cwd, ['impact', filePath, rootPath]));
  } catch (error: unknown) {
    sendKernelError(res, 'Failed to calculate impact', error);
  }
});

app.get('/api/outline', async (req, res) => {
  const requestedFile = queryString(req.query['file']);
  if (!requestedFile) {
    res.status(400).json({ error: "Parameter 'file' wajib diisi. Contoh: ?file=src/app/app.ts" });
    return;
  }
  try {
    const cwd = process.cwd();
    const filePath = projectRelativePath(cwd, requestedFile);
    const rootPath = projectRelativePath(cwd, queryString(req.query['root']) || '.');
    res.json(await runKernel(cwd, ['outline', filePath, rootPath]));
  } catch (error: unknown) {
    sendKernelError(res, 'Failed to extract outline', error);
  }
});

app.get('/api/brief', async (req, res) => {
  const requestedFile = queryString(req.query['file']);
  if (!requestedFile) {
    res.status(400).json({ error: "Parameter 'file' wajib diisi. Contoh: ?file=src/app/app.ts" });
    return;
  }
  try {
    const cwd = process.cwd();
    const filePath = projectRelativePath(cwd, requestedFile);
    const rootPath = projectRelativePath(cwd, queryString(req.query['root']) || '.');
    res.json(await runKernel(cwd, ['brief', filePath, rootPath]));
  } catch (error: unknown) {
    sendKernelError(res, 'Failed to generate file brief', error);
  }
});

const analyzerRoutes = [
  ['/api/async-detector', 'perf.async', 'Failed to analyze async issues'],
  ['/api/deopt-checker', 'perf.deopt', 'Failed to check deopt patterns'],
  ['/api/gc-pressure', 'perf.gc', 'Failed to analyze GC pressure'],
  ['/api/cache-auditor', 'perf.cache', 'Failed to audit cache patterns'],
  ['/api/type-isomorphism', 'hott.isomorphism', 'Failed to observe type isomorphisms'],
  ['/api/boundary-sheaf', 'hott.sheaf', 'Failed to observe boundary sheaf obstructions'],
  ['/api/homotopy-paths', 'hott.homotopy', 'Failed to observe homotopy paths'],
] as const;

for (const [route, analyzerName, errorMessage] of analyzerRoutes) {
  app.get(route, (req, res) => handleAnalyzer(req, res, analyzerName, errorMessage));
}

app.get('/api/topological-integrity', async (req, res) => {
  try {
    const cwd = process.cwd();
    const safeRoot = projectRelativePath(cwd, queryString(req.query['root']) || 'src');
    res.json(await runKernel(cwd, ['synthesize', safeRoot, '--output', 'full']));
  } catch (error: unknown) {
    sendKernelError(res, 'Failed to synthesize topological integrity', error);
  }
});

app.get('/api/topological-manifold', (req, res) => handleAnalyzer(
  req,
  res,
  'hott.manifold',
  'Failed to build topological manifold',
));

app.get('/api/topological-fingerprint', async (req, res) => {
  try {
    const cwd = process.cwd();
    const rootPath = projectRelativePath(cwd, queryString(req.query['root']) || 'src');
    const result = await runKernel(cwd, ['synthesize', rootPath, '--output', 'summary']);
    res.json({...result, topological_fingerprint: result['fingerprint']});
  } catch (error: unknown) {
    sendKernelError(res, 'Failed to encode topological invariants', error);
  }
});

app.get('/api/decoder-steering', async (req, res) => {
  const mode = queryString(req.query['mode']) || 'steer';
  if (mode !== 'steer' && mode !== 'establish') {
    res.status(400).json({error: "Parameter 'mode' harus 'steer' atau 'establish'"});
    return;
  }
  try {
    const cwd = process.cwd();
    const rootPath = projectRelativePath(cwd, queryString(req.query['root']) || 'src');
    res.json(await runKernel(cwd, [mode, rootPath, '--output', 'full']));
  } catch (error: unknown) {
    sendKernelError(res, 'Failed to execute decoder steering', error);
  }
});

/**
 * Serve static files from /browser
 */
app.use(
  express.static(browserDistFolder, {
    maxAge: '1y',
    index: false,
    redirect: false,
  }),
);

/**
 * Handle all other requests by rendering the Angular application.
 */
app.use((req, res, next) => {
  angularApp
    .handle(req)
    .then((response) =>
      response ? writeResponseToNodeResponse(response, res) : next(),
    )
    .catch(next);
});

/**
 * Start the server if this module is the main entry point, or it is ran via PM2.
 * The server listens on the port defined by the `PORT` environment variable, or defaults to 4000.
 */
if (isMainModule(import.meta.url) || process.env['pm_id']) {
  const port = process.env['PORT'] || 4000;
  app.listen(port, (error) => {
    if (error) {
      throw error;
    }

    console.log(`Node Express server listening on http://localhost:${port}`);
  });
}

/**
 * Request handler used by the Angular CLI (for dev-server and during build) or Firebase Cloud Functions.
 */
export const reqHandler = createNodeRequestHandler(app);
