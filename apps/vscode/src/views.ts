import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';

/**
 * Escape a value before it enters the result webview, which is created with `enableScripts: true`.
 *
 * The evidence claim, its id and source type come out of the analysed file and the model's text, so an
 * unescaped `<img src=x onerror=...>` is not a rendering glitch but code running with whatever the extension
 * host can reach. Everything interpolated below goes through here, including the run id and status, so the
 * rule is one function rather than a per-field judgement.
 */
function esc(value: unknown): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export class DatasetTreeProvider implements vscode.TreeDataProvider<DatasetItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<DatasetItem | undefined>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
  private datasets: string[] = [];
  private context: vscode.ExtensionContext;

  constructor(context: vscode.ExtensionContext) {
    this.context = context;
    this.scanWorkspace();
  }

  scanWorkspace(): void {
    this.datasets = [];
    const folders = vscode.workspace.workspaceFolders;
    if (!folders) return;
    for (const f of folders) {
      const patterns = ['**/*.csv', '**/*.parquet'];
      // sync scan for MVP — show workspace root files
      const root = f.uri.fsPath;
      try {
        const files = fs.readdirSync(root);
        for (const file of files) {
          if (file.endsWith('.csv') || file.endsWith('.parquet')) {
            this.datasets.push(path.join(root, file));
          }
        }
        // also check examples
        const ex = path.join(root, 'benchmarks', 'v2', 'datasets');
        if (fs.existsSync(ex)) {
          for (const file of fs.readdirSync(ex).slice(0, 20)) {
            if (file.endsWith('.csv')) this.datasets.push(path.join(ex, file));
          }
        }
      } catch {}
    }
    // also check examples/datasets
    const cwd = folders[0].uri.fsPath;
    const extra = path.join(cwd, 'examples', 'datasets');
    if (fs.existsSync(extra)) {
      for (const file of fs.readdirSync(extra)) {
        if (file.endsWith('.csv')) this.datasets.push(path.join(extra, file));
      }
    }
    this.datasets = [...new Set(this.datasets)].slice(0, 30);
    this._onDidChangeTreeData.fire(undefined);
  }

  refresh(): void {
    this.scanWorkspace();
  }

  getTreeItem(element: DatasetItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: DatasetItem): Thenable<DatasetItem[]> {
    if (!element) {
      return Promise.resolve(
        this.datasets.map(p => new DatasetItem(path.basename(p), p, vscode.TreeItemCollapsibleState.None))
      );
    }
    return Promise.resolve([]);
  }

  getDatasetPaths(): string[] {
    return this.datasets;
  }
}

class DatasetItem extends vscode.TreeItem {
  constructor(label: string, public readonly datasetPath: string, collapsible: vscode.TreeItemCollapsibleState) {
    super(label, collapsible);
    this.tooltip = datasetPath;
    this.description = datasetPath;
    this.command = { command: 'dsa.viewResult', title: 'Open', arguments: [datasetPath] };
    this.contextValue = 'dataset';
    this.iconPath = new vscode.ThemeIcon('table');
  }
}

export class EvidenceTreeProvider implements vscode.TreeDataProvider<EvidenceItem> {
  private _onDidChange = new vscode.EventEmitter<EvidenceItem | undefined>();
  readonly onDidChangeTreeData = this._onDidChange.event;
  private evidence: any[] = [];

  setEvidence(ev: any[]): void {
    this.evidence = ev;
    this._onDidChange.fire(undefined);
    vscode.commands.executeCommand('setContext', 'dsa:hasResult', ev.length > 0);
  }

  getTreeItem(el: EvidenceItem): vscode.TreeItem {
    return el;
  }

  getChildren(el?: EvidenceItem): Thenable<EvidenceItem[]> {
    if (!el) {
      return Promise.resolve(
        this.evidence.slice(0, 20).map((e, i) => new EvidenceItem(e.claim || e.id || `ev-${i}`, e, vscode.TreeItemCollapsibleState.None))
      );
    }
    return Promise.resolve([]);
  }
}

class EvidenceItem extends vscode.TreeItem {
  constructor(label: string, public readonly ev: any, collapsible: vscode.TreeItemCollapsibleState) {
    super(label, collapsible);
    this.tooltip = JSON.stringify(ev, null, 2).slice(0, 500);
    this.description = ev.source_type || '';
    this.iconPath = new vscode.ThemeIcon('verified');
  }
}

export class ResultPanel {
  private panel: vscode.WebviewPanel | undefined;
  private lastResult: any | undefined;
  private lastDataset: string | undefined;

  constructor(private context: vscode.ExtensionContext) {}

  show(dataset: string, result: any): void {
    this.lastDataset = dataset;
    this.lastResult = result;
    if (!this.panel) {
      this.panel = vscode.window.createWebviewPanel('dsaResult', `DSA Result: ${path.basename(dataset)}`, vscode.ViewColumn.One, { enableScripts: true });
      this.panel.onDidDispose(() => (this.panel = undefined));
    }
    this.panel.title = `DSA: ${path.basename(dataset)} → ${result.run_id?.slice(0, 8) || 'result'}`;
    this.panel.webview.html = this.getHtml(dataset, result);
    this.panel.reveal();
  }

  getHtml(dataset: string, result: any): string {
    const report = result.report_markdown || result.report || 'No report';
    const evCount = result.evidence?.length ?? result.raw?.evidence ?? 0;
    const status = result.status || 'UNKNOWN';
    const runId = result.run_id || 'unknown';
    const evidences = result.evidence || [];
    const evRows = evidences
      .slice(0, 10)
      .map((e: any) => `<tr><td>${esc(e.id)}</td><td>${esc((e.claim || '').slice(0, 120))}</td><td>${esc(e.source_type)}</td></tr>`)
      .join('');
    return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body{font-family:var(--vscode-font-family); padding:16px;}
h2{margin-top:0}
.badge{padding:2px 6px; border-radius:4px; background:#0a0; color:white;}
table{border-collapse:collapse; width:100%; margin:8px 0;}
th,td{border:1px solid var(--vscode-panel-border); padding:6px; text-align:left;}
pre{white-space:pre-wrap; background:var(--vscode-textCodeBlock-background); padding:12px; border-radius:6px;}
a{color:var(--vscode-textLink-foreground)}
</style></head><body>
<h2>🔬 Analysis ${esc(runId)} <span class="badge">${esc(status)}</span></h2>
<p><b>Dataset:</b> ${esc(dataset)} | <b>Evidence:</b> ${esc(String(evCount))}</p>
<h3>📄 Report</h3><pre>${esc(report.slice(0, 3000))}</pre>
<h3>🔗 Evidence</h3><table><tr><th>id</th><th>claim</th><th>source</th></tr>${evRows || '<tr><td colspan=3>No evidence</td></tr>'}</table>
<p><button onclick="vscode.postMessage({command:'openReport'})">Open Report</button> <button onclick="vscode.postMessage({command:'viewEvidence'})">View Evidence</button></p>
<script>const vscode=acquireVsCodeApi(); window.addEventListener('message', e=>{});</script>
</body></html>`;
  }

  getLastResult(): any | undefined {
    return this.lastResult;
  }
  getLastDataset(): string | undefined {
    return this.lastDataset;
  }
}
