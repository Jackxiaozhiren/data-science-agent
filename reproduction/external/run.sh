#!/usr/bin/env bash
# Blind reproduction run — no developer cache, no secrets
set -e
set -o pipefail

START=$(date +%s)
echo "=== External Blind Reproduction Run ==="
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "PWD: $(pwd)"
echo "Git: $(git rev-parse --short HEAD 2>&1 | head -n 1)"
echo "Python: $(python --version 2>&1 | head -n 1 || python3 --version 2>&1 | head -n 1)"
echo "uv: $(uv --version 2>&1 | head -n 1 || echo 'uv not found')"
echo "Node: $(node --version 2>&1 | head -n 1 || echo 'node not found')"
echo "Docker: $(docker --version 2>&1 | head -n 1 || echo 'docker not found')"
echo ""

# Helper to time and capture
run_step() {
  local name="$1"
  shift
  echo "--- $name ---"
  local s=$(date +%s)
  if "$@" 2>&1 | tail -n 20; then
    local e=$(date +%s)
    echo "✓ $name: $(($e-$s))s"
    return 0
  else
    local e=$(date +%s)
    echo "✗ $name: FAILED after $(($e-$s))s"
    return 1
  fi
}

# 1. Install
run_step "uv sync --dev" uv sync --dev

# 2. Doctor
run_step "dsa doctor --json" bash -c "uv run dsa doctor --json | head -n 30"

# 3. Demo
run_step "dsa demo" bash -c "uv run dsa demo 2>&1 | tail -n 30"

# 4. Benchmark smoke
run_step "dsa --limit 1" bash -c "uv run dsa --limit 1 2>&1 | tail -n 20"

# 5. SDK
run_step "SDK Agent.analyze" bash -c "uv run python -c \"import asyncio; from data_science_agent import Agent; r=asyncio.run(Agent().analyze('benchmarks/v2/datasets/sales.csv','Analyze revenue')); print('SDK:', r.status, len(r.evidence))\""

# 6. CLI
run_step "CLI dsa analyze" bash -c "uv run dsa analyze benchmarks/v2/datasets/sales.csv --task 'Analyze revenue' --json 2>&1 | tail -n 20"

# 7. Plugin
run_step "Plugin list" bash -c "uv run dsa plugin list --json 2>&1 | head -n 20"

# 8. MCP
run_step "MCP tools" bash -c "uv run dsa mcp --json 2>&1 | head -n 20"

# 9. Jupyter
run_step "Jupyter import" bash -c "uv run python -c 'import dsa_jupyter; print(\"jupyter\", dsa_jupyter.__version__)'"

# 10. Case Study CS01
run_step "Case Study CS01" bash -c "uv run python -c \"from data_science_agent import Agent; r=Agent().analyze_sync('benchmarks/v2/datasets/sales.csv','Analyze revenue trends by region and category'); print('CS01:', r.status, len(r.evidence), 'report', len(r.report_markdown or ''))\""

END=$(date +%s)
echo ""
echo "=== Done in $((END-START))s ==="
echo "If all ✓, then Install/SDK/CLI/Plugin/MCP/Jupyter/CaseStudy all PASS"
