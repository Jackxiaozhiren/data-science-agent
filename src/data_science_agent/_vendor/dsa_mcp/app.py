"""MCP App — Real Integration (W6 §36) — Dataset→Question→Analysis→Evidence→Viz→Report.

R-14: the report a client sees here is rendered by the product's one report renderer
(``dsa_agent.report_export.export_html``) over the run's stored state -- the same bytes
the web's download button hands over. This page assembles no report HTML of its own;
its job is the flow (dataset → question → evidence) and staying inside a client's UI
budget by embedding, not re-implementing.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from dsa_agent.report_export import export_html
from dsa_mcp.resources import get_state

app = FastAPI(title="DSA MCP App", version="0.1.0")

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
<iframe id="reportFrame" title="Rendered analysis report" style="width:100%;height:420px;border:1px solid #ddd;border-radius:6px;" hidden></iframe>
<p id="reportEmpty" class="small">Run an analysis to see its report here.</p>
<button id="openReportBtn" disabled>Open report:// resource</button>
</div>

<div class="card small">Handles: <code>run_id</code> / <code>analysis_id</code> / <code>dataset</code> — explicit in URL (?run_id=...) and resource URIs (§38). Stateless MCP 2026-07-28 — no session.</div>

<script>
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
    sel.innerHTML = ds.map(x=>`<option value="${x.uri}">${x.name} — ${x.description.slice(0,60)}</option>`).join('') || '<option value="dataset://sales">dataset://sales (fallback)</option>';
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
    evDiv.innerHTML = ev.length ? '<table><tr><th>id</th><th>claim</th><th>source</th></tr>'+ev.slice(0,5).map(e=>`<tr><td>${e.id}</td><td>${(e.claim||'').slice(0,80)}</td><td>${e.source_type||''}</td></tr>`).join('')+'</table>' : 'No evidence';
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
async def root() -> str:
    return HTML


@app.get("/report/{run_id}", response_class=HTMLResponse)
async def report_view(run_id: str) -> HTMLResponse:
    """One run's report through the product's single renderer (R-14)."""
    state = get_state(run_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail="No stored analysis for this run_id. Run the analyze tool first, then reopen.",
        )
    return HTMLResponse(content=export_html(state))


@app.get("/app", response_class=JSONResponse)
async def app_info() -> dict[str, str]:
    return {
        "app": "mcp-data-science",
        "version": "0.1.0",
        "levels": "Tools/Resources/Apps/Tasks",
        "flow": "Dataset→Question→Analysis→Evidence→Viz→Report (§36)",
        "handles": "run_id, analysis_id, dataset (§38 stateless)",
    }
