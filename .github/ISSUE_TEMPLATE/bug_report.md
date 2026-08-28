---
name: Bug report
about: Report a reproducible defect in DSA
labels: bug
---

## Summary

Describe the bug and the user-visible impact in one or two sentences.

## Minimal reproduction

```bash
# Include the smallest command or code snippet that reproduces the problem.
```

## Expected behavior

What did you expect to happen?

## Actual behavior

What happened instead? Include the exact error message or failed assertion when possible.

## Environment

Please include:

```text
OS:
Python version:
DSA version (`dsa --version`):
Install method (PyPI/source/container):
LLM/provider configuration, if relevant:
```

If available, also paste the output of `uv run dsa doctor`.

## Evidence / artifacts

Attach or link the smallest useful artifacts, for example:

- `experiment.json`
- relevant `evidence_graph.json` fragment
- tool-call error
- dataset schema (not private data)
- reproduction bundle path

## Additional context

Anything else that may help isolate the problem.

> Do not post credentials, API keys, private datasets, or security vulnerabilities here. See `SECURITY.md` for responsible disclosure.
