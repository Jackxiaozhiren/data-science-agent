"""MCP App — Real Integration (W6 §36) — Dataset→Question→Analysis→Evidence→Viz→Report.

R-14: the report a client sees here is rendered by the product's one report renderer
(``dsa_agent.report_export.export_html``) over the run's stored state -- the same bytes
the web's download button hands over. This page assembles no report HTML of its own;
its job is the flow (dataset → question → evidence) and staying inside a client's UI
budget by embedding, not re-implementing.

One renderer is only half of "the same run result". The state behind it used to come from
``dsa_mcp.resources._STATE_STORE`` alone -- the runs this process produced by being *asked* --
so a run the product had already stored and the web could show answered 404 here. Measured on
``dsa ui``: ``run-65becae7af`` returned 32,755 bytes at ``/api/v1/analysis/{id}/report`` and
``No stored analysis for this run_id`` at ``/mcp-app/report/{id}``, from the same process. The
loader below is how the host that owns the database hands that reading to the App.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from dsa_agent.report_export import document_security_headers, export_html
from dsa_mcp.resources import get_state


def _served(document: str, *, allow_self_frame: bool = False) -> HTMLResponse:
    """Hand a document to a browser with a policy its own bytes satisfy.

    The host's hardening middleware says ``default-src 'none'``, which is correct for JSON and fatal for this page:
    measured, the App offered zero dataset options against a server publishing thirty, because the inline script was
    refused. The hashes come from ``document_security_headers``, so a page that changes its own script changes its
    policy too -- and a page that gains an unnamed block stops rendering in a browser instead of gaining reach.
    """
    return HTMLResponse(
        content=document,
        headers=document_security_headers(document, allow_self_frame=allow_self_frame),
    )


app = FastAPI(title="DSA MCP App", version="0.1.0")

_stored_run: Callable[[str], Awaitable[dict[str, Any] | None]] | None = None


def set_stored_run_loader(loader: Callable[[str], Awaitable[dict[str, Any] | None]]) -> None:
    """Let the embedding application hand this App a way to read a stored run (R-14).

    The direction is deliberate: ``dsa_api`` imports this module and never the reverse, so the App asks its
    host how to read a run instead of reaching into someone else's session factory. A second implementation of
    "load this run" is the defect R-02 was about -- two owners reading one fact and disagreeing.
    """
    global _stored_run
    _stored_run = loader


HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSA MCP App — Dataset→Question→Analysis→Evidence→Viz→Report (§36)</title>
<style>
body{font-family:system-ui,-apple-system,sans-serif; max-width:900px; margin:20px auto; padding:0 16px;}
h1{font-size:22px} h2{font-size:16px; margin:18px 0 8px;}
.card{border:1px solid #ddd; border-radius:8px; padding:12px; margin:8px 0;}
label{font-weight:600} select,input,textarea{width:100%; padding:6px; margin:4px 0;}
button{padding:8px 14px; border-radius:6px; border:1px solid #0a0; background:#0a0; color:white; cursor:pointer;}
button:disabled{opacity:0.5}
pre{white-space:pre-wrap; background:#fafafa; padding:10px; border-radius:6px; max-height:300px; overflow:auto;}
.badge{padding:2px 6px; border-radius:4px; background:#0a0; color:white; font-size:12px;}
.small{color:#666; font-size:12px}
table{border-collapse:collapse; width:100%;}
th,td{border:1px solid #ddd; padding:6px; text-align:left; font-size:13px;}
#reportFrame{width:100%;height:420px;border:1px solid #ddd;border-radius:6px;}
</style></head><body>
<h1>🔬 Data Science Agent — MCP App (§36)</h1>
<p class="small">Flow: <b>Dataset</b> → <b>Question</b> → <b>Analysis</b> → <b>Evidence</b> → <b>Visualization</b> → <b>Report</b> — stateless with explicit handles (§38)</p>

<div class="card"><h2>1. Dataset <span class="small">dataset://</span></h2>
<label>Select dataset:</label><select id="dataset"></select>
<div id="profile" class="small"></div></div>

<div class="card"><h2>2. Question</h2>
<textarea id="question" rows="2" placeholder="Analyze correlation between price and revenue">Analyze revenue trend</textarea>
<button id="analyzeBtn">▶ Run Analysis</button>
<span id="progress" class="small"></span>
<div id="analysisMeta" class="small"></div></div>

<div class="card"><h2>3. Evidence <span class="small">evidence://{run_id}</span></h2>
<div id="evidence"></div>
<button id="openEvidenceBtn" disabled>Open evidence:// resource</button>
</div>

<div class="card"><h2>4. Visualization <span class="small">artifact://{run_id}/...</span></h2>
<div id="viz"></div></div>

<div class="card"><h2>5. Report <span class="small">report://{run_id}</span></h2>
<p class="small">Rendered by the same report renderer the web app uses — charts inlined, drill-down in page.</p>
<iframe id="reportFrame" title="Rendered analysis report" hidden></iframe>
<p id="reportEmpty" class="small">Run an analysis to see its report here.</p>
<button id="openReportBtn" disabled>Open report:// resource</button>
</div>

<div class="card small">Handles: <code>run_id</code> / <code>analysis_id</code> / <code>dataset</code> — explicit in URL (?run_id=...) and resource URIs (§38). Stateless MCP 2026-07-28 — no session.</div>

<script>
// Everything these touch arrives over the wire -- a dataset's own name/description, and an evidence
// claim that quotes the user's question and the CSV's header row -- so none of it is markup until esc() says so.
const esc = (v) => String(v ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const renderOptions = (ds) => ds.map(x=>`<option value="${esc(x.uri)}">${esc(x.name)} — ${esc((x.description ?? '').slice(0,60))}</option>`).join('');
const renderEvidence = (ev) => '<table><tr><th>id</th><th>claim</th><th>source</th></tr>'
  + ev.slice(0,5).map(e=>`<tr><td>${esc(e.id)}</td><td>${esc((e.claim ?? '').slice(0,80))}</td><td>${esc(e.source_type)}</td></tr>`).join('') + '</table>';

let lastRunId = new URLSearchParams(location.search).get('run_id') || '';
let lastDataset = '';

async function jrpc(method, params){
  const r = await fetch('/mcp', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({jsonrpc:'2.0', id: Date.now(), method, params})});
  return r.json();
}
async function loadDatasets(){
  const sel = document.getElementById('dataset');
  try{
    const res = await jrpc('resources/list', {});
    const resources = (res.result && res.result.resources) || [];
    const ds = resources.filter(x=>x.uri.startsWith('dataset://'));
    sel.innerHTML = renderOptions(ds) || '<option value="dataset://sales">dataset://sales (fallback)</option>';
    if(ds[0]) { lastDataset = ds[0].uri; document.getElementById('profile').textContent = ds[0].description; }
    sel.onchange = ()=>{ lastDataset = sel.value; fetchProfile(); };
    fetchProfile();
    // Also list tools for discover
    const tools = await jrpc('tools/list', {});
    console.log('tools', tools.result && tools.result.tools && tools.result.tools.length);
  }catch(e){ sel.innerHTML='<option>failed to load</option>'; }
}
async function fetchProfile(){
  if(!lastDataset) return;
  const dsId = lastDataset.replace('dataset://','');
  const path = `benchmarks/v2/datasets/${dsId}.csv`;
  // Use profile_dataset tool
  try{
    const r = await jrpc('tools/call', {name:'profile_dataset', arguments:{path: path}});
    if(r.result && r.result.output){
      const p = r.result.output.profile || r.result.output;
      document.getElementById('profile').textContent = `Profile: ${JSON.stringify(p).slice(0,300)}`;
    }
  }catch(e){}
}
async function runAnalysis(){
  const q = document.getElementById('question').value.trim();
  if(!q){ alert('Enter question'); return; }
  const btn = document.getElementById('analyzeBtn');
  btn.disabled = true;
  document.getElementById('progress').textContent = 'Planner→Scientist→Critic→Report …';
  // Resolve dataset path: dataset://sales → benchmarks/v2/datasets/sales.csv
  let dsPath = lastDataset;
  if(dsPath.startsWith('dataset://')){
    const id = dsPath.replace('dataset://','');
    dsPath = `benchmarks/v2/datasets/${id}.csv`;
  }
  try{
    const r = await jrpc('tools/call', {name:'analyze', arguments:{dataset: dsPath, task: q}});
    if(r.error){ document.getElementById('progress').textContent = 'Error: '+(r.error.message||JSON.stringify(r.error)); btn.disabled=false; return; }
    const out = r.result && r.result.output ? r.result.output : r.result;
    lastRunId = out.run_id || out.analysis_id || Date.now().toString();
    history.replaceState(null,'','?run_id='+lastRunId);
    document.getElementById('progress').textContent = `COMPLETED ${lastRunId} (${(out.evidence||[]).length} evidence)`;
    document.getElementById('analysisMeta').textContent = `run_id=${lastRunId} status=${out.status}`;
    // Evidence
    const evDiv = document.getElementById('evidence');
    const ev = out.evidence || [];
    evDiv.innerHTML = ev.length ? renderEvidence(ev) : 'No evidence';
    document.getElementById('openEvidenceBtn').disabled=false;
    document.getElementById('openEvidenceBtn').onclick=()=> openResource('evidence://'+lastRunId);
    // Report — rendered by the single owner (R-14), embedded rather than re-implemented
    const frame = document.getElementById('reportFrame');
    frame.src = '/mcp-app/report/' + encodeURIComponent(lastRunId);
    frame.hidden = false;
    document.getElementById('reportEmpty').hidden = true;
    document.getElementById('openReportBtn').disabled=false;
    document.getElementById('openReportBtn').onclick=()=> openResource('report://'+lastRunId);
    // Viz — if artifact exists, try to show
    if(out.artifacts && out.artifacts[0] && out.artifacts[0].path){
      document.getElementById('viz').textContent = 'Artifact: '+out.artifacts[0].path;
    } else {
      document.getElementById('viz').textContent = 'Visualization via create_visualization tool (call manually if needed)';
    }
  }catch(e){ document.getElementById('progress').textContent='Failed: '+e; }
  btn.disabled=false;
}
async function openResource(uri){
  const r = await jrpc('resources/read', {uri});
  if(r.result) alert(uri+'\\n\\n'+ (r.result.text||JSON.stringify(r.result)).slice(0,2000));
  else alert('Error: '+JSON.stringify(r.error).slice(0,1000));
}
document.getElementById('analyzeBtn').onclick=runAnalysis;
document.getElementById('openEvidenceBtn').onclick=()=> openResource('evidence://'+lastRunId);
document.getElementById('openReportBtn').onclick=()=> openResource('report://'+lastRunId);
loadDatasets();
// If URL has run_id, load its resources
if(lastRunId){
  setTimeout(()=> openResource('evidence://'+lastRunId), 800);
  const frame = document.getElementById('reportFrame');
  frame.src = '/mcp-app/report/' + encodeURIComponent(lastRunId);
  frame.hidden = false;
  document.getElementById('reportEmpty').hidden = true;
  document.getElementById('openReportBtn').disabled=false;
}
</script>
</body></html>
"""


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    return _served(HTML)


@app.get("/report/{run_id}", response_class=HTMLResponse)
async def report_view(run_id: str) -> HTMLResponse:
    """One run's report through the product's single renderer (R-14).

    Asked for in this order on purpose: a run the client drove through the tools is already in memory, and a
    run the product stored is read through the host's loader -- which is scoped to what the instance publishes,
    so an unidentified client surface cannot reach a visitor's private rows (R-08).
    """
    state: Any = get_state(run_id)
    if state is None and _stored_run is not None:
        row = await _stored_run(run_id)
        state = (row or {}).get("state") if row else None
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No stored analysis for this run_id. Run the analyze tool first, then reopen -- or ask for a "
                "report the instance itself publishes."
            ),
        )
    return _served(export_html(state), allow_self_frame=True)


@app.get("/app", response_class=JSONResponse)
async def app_info() -> dict[str, str]:
    return {
        "app": "mcp-data-science",
        "version": "0.1.0",
        "levels": "Tools/Resources/Apps/Tasks",
        "flow": "Dataset→Question→Analysis→Evidence→Viz→Report (§36)",
        "handles": "run_id, analysis_id, dataset (§38 stateless)",
    }
