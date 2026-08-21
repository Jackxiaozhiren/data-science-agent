/* DSA CLI wrapper — Extension → Public SDK/CLI → Core Engine (§34) */

import * as cp from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as util from 'util';
import * as vscode from 'vscode';

const exec = util.promisify(cp.exec);

export interface CheckResult {
  ok: boolean;
  message?: string;
  suggestion?: string;
}

export async function checkPython(): Promise<CheckResult> {
  const cfg = vscode.workspace.getConfiguration('dsa');
  const py = cfg.get<string>('pythonPath', 'python');
  try {
    const { stdout } = await exec(`${py} --version`);
    if (stdout.includes('Python')) return { ok: true };
    return { ok: true };
  } catch {
    try {
      await exec('uv run python --version');
      return { ok: true };
    } catch (e: any) {
      return {
        ok: false,
        message: 'Python unavailable',
        suggestion: 'Install Python 3.12+ and run `uv sync --dev`. Check `dsa doctor`. (§35)',
      };
    }
  }
}

export async function checkLLM(): Promise<CheckResult> {
  const keys = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY', 'OPENROUTER_API_KEY'];
  const hasKey = keys.some(k => !!process.env[k]);
  if (hasKey) return { ok: true };
  return {
    ok: true, // stub mode is ok, but warn
    message: 'LLM unavailable — running in stub/Ollama fallback',
    suggestion: 'Set OPENAI_API_KEY / ANTHROPIC_API_KEY / GOOGLE_API_KEY or run Ollama. See `dsa doctor` (§35).',
  };
}

export async function checkDataset(datasetPath: string): Promise<CheckResult> {
  if (!datasetPath) return { ok: false, message: 'Dataset missing', suggestion: 'Use DSA: Open Dataset to pick a CSV (§35).' };
  if (!fs.existsSync(datasetPath)) {
    return { ok: false, message: `Dataset not found: ${datasetPath}`, suggestion: 'Check file exists or use DSA: Open Dataset (§35).' };
  }
  const ext = path.extname(datasetPath).toLowerCase();
  if (!['.csv', '.parquet', '.tsv'].includes(ext)) {
    return { ok: false, message: `Unsupported dataset type: ${ext}`, suggestion: 'Use CSV/Parquet (§35).' };
  }
  return { ok: true };
}

export async function checkPlugin(): Promise<CheckResult> {
  try {
    const { stdout } = await exec('uv run dsa plugin --json', { timeout: 5000 });
    const arr = JSON.parse(stdout);
    if (Array.isArray(arr) && arr.some((p: any) => p.name === 'dsa-time-series')) return { ok: true };
    return { ok: true, message: 'Plugin dsa-time-series not found', suggestion: 'Run `dsa plugin validate` (§35).' };
  } catch (e: any) {
    return { ok: false, message: 'Plugin failure', suggestion: `dsa plugin validate failed: ${e.message}. Try \`uv sync\` (§35).` };
  }
}

export async function checkBackend(): Promise<CheckResult> {
  const cfg = vscode.workspace.getConfiguration('dsa');
  const url = cfg.get<string>('apiUrl', 'http://127.0.0.1:8000');
  try {
    const res = await fetch(`${url}/health`, { signal: AbortSignal.timeout(2000) });
    if (res.ok) return { ok: true };
    return { ok: false, message: `Backend unavailable at ${url} — status ${res.status}`, suggestion: 'Start API: `uv run uvicorn dsa_api.main:app --app-dir apps/api/src --port 8000` (§35).' };
  } catch {
    return { ok: false, message: `Backend unavailable at ${url}`, suggestion: 'Start API: `uv run uvicorn dsa_api.main:app --app-dir apps/api/src` or use CLI mode (§35).' };
  }
}

export interface AnalysisResult {
  run_id: string;
  status: string;
  evidence: any[];
  report_markdown?: string;
  error?: string;
  raw: any;
}

export async function runAnalysis(dataset: string, task: string): Promise<AnalysisResult> {
  // Pre-checks §35 with clear suggestions
  const checks: CheckResult[] = [];
  checks.push(await checkPython());
  checks.push(await checkDataset(dataset));
  if (checks.some(c => !c.ok)) {
    const failed = checks.filter(c => !c.ok)[0];
    throw new Error(`${failed.message}. Suggestion: ${failed.suggestion}`);
  }
  // LLM and plugin are soft warnings
  const llm = await checkLLM();
  if (llm.message) {
    vscode.window.showWarningMessage(`${llm.message}. ${llm.suggestion}`);
  }
  const plugin = await checkPlugin();
  if (!plugin.ok && plugin.message) {
    vscode.window.showWarningMessage(`${plugin.message}. ${plugin.suggestion}`);
  }
  // Backend is optional — CLI mode can run without it
  const backend = await checkBackend();
  if (!backend.ok) {
    vscode.window.showInformationMessage(`Backend unavailable — running via CLI (local-first). ${backend.suggestion}`);
  }

  // Execute via Public CLI (§34) — not duplicating Agent logic
  const cmd = `uv run dsa analyze ${JSON.stringify(dataset)} --task ${JSON.stringify(task)} --json`;
  try {
    const { stdout, stderr } = await exec(cmd, { timeout: 30000, maxBuffer: 5 * 1024 * 1024 });
    if (stderr && stderr.includes('Usage:')) throw new Error(stderr);
    const parsed = JSON.parse(stdout);
    if (parsed.error) throw new Error(parsed.error);
    // Fetch full state via dsa CLI? For now return parsed
    return {
      run_id: parsed.run_id,
      status: parsed.status,
      evidence: [],
      report_markdown: parsed.report,
      error: parsed.error,
      raw: parsed,
    };
  } catch (e: any) {
    // Try to parse stdout if exec threw but produced JSON
    if (e.stdout) {
      try {
        const p = JSON.parse(e.stdout);
        return { run_id: p.run_id || 'unknown', status: p.status || 'FAILED', evidence: [], error: p.error || e.message, raw: p };
      } catch {}
    }
    throw new Error(`Analysis failed: ${e.message}. Try \`dsa doctor\` (§35).`);
  }
}

export async function runProfile(dataset: string): Promise<any> {
  const chk = await checkDataset(dataset);
  if (!chk.ok) throw new Error(`${chk.message}. ${chk.suggestion}`);
  const cmd = `uv run dsa profile ${JSON.stringify(dataset)} --json`;
  const { stdout } = await exec(cmd, { timeout: 10000 });
  return JSON.parse(stdout);
}

export async function runDoctor(): Promise<any> {
  const { stdout } = await exec('uv run dsa doctor --json', { timeout: 8000 });
  return JSON.parse(stdout);
}
