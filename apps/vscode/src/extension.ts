/* VS Code Real Integration — W5 MVP (§33-35) */

import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import * as dsa from './dsa';
import { DatasetTreeProvider, EvidenceTreeProvider, ResultPanel } from './views';

let datasetProvider: DatasetTreeProvider;
let evidenceProvider: EvidenceTreeProvider;
let resultPanel: ResultPanel;
let lastDataset: string | undefined;
let lastResult: any | undefined;

export function activate(context: vscode.ExtensionContext): void {
  console.log('DSA extension activated (§33)');

  datasetProvider = new DatasetTreeProvider(context);
  evidenceProvider = new EvidenceTreeProvider();
  resultPanel = new ResultPanel(context);

  vscode.window.registerTreeDataProvider('dsa.datasetExplorer', datasetProvider);
  vscode.window.registerTreeDataProvider('dsa.evidenceExplorer', evidenceProvider);
  vscode.commands.executeCommand('setContext', 'dsa:hasResult', false);

  // Open Dataset (§33)
  context.subscriptions.push(
    vscode.commands.registerCommand('dsa.openDataset', async () => {
      const uris = await vscode.window.showOpenDialog({
        canSelectMany: false,
        filters: { Datasets: ['csv', 'parquet', 'tsv'] },
        title: 'Open Dataset (§33)',
      });
      if (!uris || !uris[0]) return;
      lastDataset = uris[0].fsPath;
      vscode.window.showInformationMessage(`Dataset selected: ${path.basename(lastDataset)}`);
      // Auto profile (§33)
      try {
        const prof = await dsa.runProfile(lastDataset);
        vscode.window.showInformationMessage(`Profile: ${prof.rows} rows, ${prof.columns.length} cols`);
      } catch (e: any) {
        // §35 Dataset missing / Python unavailable already handled in dsa.ts
        vscode.window.showErrorMessage(e.message);
      }
      datasetProvider.refresh();
    })
  );

  // Ask DSA (§33) — input task then run
  context.subscriptions.push(
    vscode.commands.registerCommand('dsa.askAnalysis', async (datasetArg?: string) => {
      const dataset = datasetArg || lastDataset || (await pickDataset());
      if (!dataset) {
        const picked = await pickDataset();
        if (!picked) return;
        lastDataset = picked;
      } else {
        lastDataset = dataset;
      }
      const task = await vscode.window.showInputBox({
        prompt: 'Ask DSA — natural language question (§33)',
        placeHolder: 'Analyze correlation between price and revenue',
        value: 'Analyze revenue trend',
      });
      if (!task) return;
      await runAnalysisFlow(lastDataset, task);
    })
  );

  // Run Analysis (§33) — uses last dataset + last task or prompts
  context.subscriptions.push(
    vscode.commands.registerCommand('dsa.runAnalysis', async () => {
      if (!lastDataset) {
        lastDataset = await pickDataset();
        if (!lastDataset) return;
      }
      const task = await vscode.window.showInputBox({
        prompt: 'Task for analysis',
        placeHolder: 'Analyze revenue',
        value: 'Analyze revenue',
      });
      if (!task) return;
      await runAnalysisFlow(lastDataset, task);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('dsa.viewResult', async (datasetArg?: string) => {
      const ds = datasetArg || lastDataset;
      if (!lastResult || !ds) {
        vscode.window.showInformationMessage('No result yet — run DSA: Ask Analysis (§33).');
        return;
      }
      resultPanel.show(ds, lastResult);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('dsa.viewEvidence', async () => {
      if (!lastResult) {
        vscode.window.showInformationMessage('No evidence — run analysis first.');
        return;
      }
      // Evidence Explorer already shows evidence; also show webview
      if (lastDataset) resultPanel.show(lastDataset, lastResult);
      vscode.commands.executeCommand('workbench.view.extension.dsaExplorer');
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('dsa.openReport', async () => {
      if (!lastResult) {
        vscode.window.showInformationMessage('No report — run analysis first.');
        return;
      }
      const report = lastResult.report_markdown || lastResult.raw?.report || lastResult.report;
      if (!report) {
        vscode.window.showInformationMessage('Report not available.');
        return;
      }
      const doc = await vscode.workspace.openTextDocument({ content: report, language: 'markdown' });
      await vscode.window.showTextDocument(doc);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('dsa.doctor', async () => {
      try {
        const rep = await dsa.runDoctor();
        const msg = `dsa doctor: ${rep.status}\n` + (rep.checks || []).map((c: any) => `${c.name}: ${c.status}`).join('\n');
        const doc = await vscode.workspace.openTextDocument({ content: msg, language: 'plaintext' });
        await vscode.window.showTextDocument(doc);
      } catch (e: any) {
        vscode.window.showErrorMessage(`dsa doctor failed: ${e.message}. Suggestion: run \`uv run dsa doctor\` (§35).`);
      }
    })
  );

  // Auto-check §35 on activate
  (async () => {
    const py = await dsa.checkPython();
    if (!py.ok) vscode.window.showWarningMessage(`${py.message}. ${py.suggestion}`);
    const backend = await dsa.checkBackend();
    if (!backend.ok) {
      // not fatal — CLI mode fallback (§35)
      console.log(`Backend check: ${backend.message}`);
    }
  })();
}

async function pickDataset(): Promise<string | undefined> {
  const picks = datasetProvider.getDatasetPaths();
  if (picks.length === 0) {
    vscode.window.showInformationMessage('No datasets found in workspace. Use DSA: Open Dataset (§33).');
    return undefined;
  }
  const sel = await vscode.window.showQuickPick(picks.map(p => ({ label: path.basename(p), detail: p, dataset: p })), {
    placeHolder: 'Pick dataset (§33)',
  });
  return (sel as any)?.dataset;
}

async function runAnalysisFlow(dataset: string, task: string): Promise<void> {
  // Show progress (§29)
  await vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title: `DSA: Analyzing ${path.basename(dataset)}`, cancellable: false },
    async progress => {
      progress.report({ message: 'Planner → Scientist → Critic → Report (§29)…' });
      try {
        const result = await dsa.runAnalysis(dataset, task);
        lastResult = result;
        lastDataset = dataset;
        // Update Evidence Explorer
        evidenceProvider.setEvidence(result.evidence || result.raw?.evidence || []);
        vscode.commands.executeCommand('setContext', 'dsa:hasResult', true);
        // Show Result (§33)
        resultPanel.show(dataset, result);
        vscode.window.showInformationMessage(`Analysis ${result.status}: ${result.run_id} (${(result.evidence || []).length} evidence)`);
      } catch (e: any) {
        // §35 failure handling with clear suggestions
        const msg = e.message || String(e);
        if (msg.includes('Python unavailable')) {
          vscode.window.showErrorMessage(`${msg}. Suggestion: Install Python 3.12+ (§35).`, 'Open Doctor').then(s => {
            if (s) vscode.commands.executeCommand('dsa.doctor');
          });
        } else if (msg.includes('Dataset not found') || msg.includes('Dataset missing')) {
          vscode.window.showErrorMessage(`${msg}`, 'Open Dataset').then(s => {
            if (s) vscode.commands.executeCommand('dsa.openDataset');
          });
        } else if (msg.includes('LLM')) {
          vscode.window.showErrorMessage(msg, 'Doctor').then(s => {
            if (s) vscode.commands.executeCommand('dsa.doctor');
          });
        } else if (msg.includes('Plugin')) {
          vscode.window.showErrorMessage(msg, 'Validate Plugin').then(async s => {
            if (s) {
              try {
                const cp = await import('child_process');
                cp.execSync('uv run dsa plugin validate --json', { timeout: 5000 });
              } catch {}
            }
          });
        } else if (msg.includes('Backend')) {
          vscode.window.showErrorMessage(msg);
        } else {
          vscode.window.showErrorMessage(msg);
        }
      }
    }
  );
}

export function deactivate(): void {}
