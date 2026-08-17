# CLI — V4 W5 (§34–37)

Every command has `--help`, clear error, exit code, `--json` structured output (§37):

- `dsa doctor` — checks Python/Node/Docker/LLM/Disk (§34)
- `dsa init my-project` — scaffold `datasets/analyses/reports/notebooks/config.yaml/README.md` (§36)
- `dsa analyze <dataset> --task "..." --json` — SDK analyze
- `dsa profile <dataset> --json`
- `dsa benchmark --limit 5 --json`
- `dsa plugin` — list plugins
- `dsa mcp` — list MCP tools
- `dsa demo` / `dsa reproduce` / `dsa verify-release` / `dsa research`
