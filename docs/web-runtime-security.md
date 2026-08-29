# Web runtime security baseline

The hosted Web UI follows a conservative runtime dependency policy:

- production dependency review continues to fail on **high** or **critical** vulnerabilities;
- the Web subproject lockfile is the source of truth for `npm --prefix apps/web ci`;
- framework security upgrades must pass the production Web build and Web Docker build before merge;
- transitive runtime licenses are reviewed explicitly rather than bypassing dependency review.

## Current baseline

The security upgrade in PR #26 moves the Web runtime to:

- Next.js 16.3.3
- React 19.0.8
- React DOM 19.0.8
- Sharp 0.35.4

An isolated install of this dependency set reported zero npm audit vulnerabilities before the pull request was opened.

The dependency-review allowlist includes `LGPL-3.0-or-later` for Sharp/libvips runtime artifacts and `CC-BY-4.0` for browser compatibility data. The vulnerability threshold remains unchanged.
