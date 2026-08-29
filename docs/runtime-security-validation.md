# Web runtime security validation

This document records the validation intent for the current hosted-demo web runtime.

The production web stack is expected to pass the repository's full CI after coordinated framework/runtime security upgrades, including:

- Next.js 16.3.3
- React 19.2.8
- ReactDOM 19.2.8
- Sharp 0.35.4
- PostCSS >= 8.5.23

The CI pipeline must verify dependency installation, high-severity npm audit policy, Python quality gates and tests, API and Web Docker builds, the standalone Next.js production build, Docker Compose configuration, and strict MkDocs documentation build.

This page is intentionally small: the pull request that introduces it exists primarily to validate the exact current `main` runtime tree through the normal pull-request CI path after the runtime upgrade landed directly on `main`.
