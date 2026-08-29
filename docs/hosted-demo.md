# Hosted Demo Deployment

The repository contains a Next.js web app (`apps/web`) and FastAPI service (`apps/api`). The hosted demo should expose both through public HTTPS URLs.

## Required configuration

### Web

Set this **at web build time**:

```bash
NEXT_PUBLIC_API_URL=https://api.example.com
```

`NEXT_PUBLIC_API_URL` must be a URL the visitor's browser can reach. Do not use a Docker-only hostname such as `http://api:8000` for a public build.

### API

Allow the public web origin:

```bash
DSA_CORS_ORIGINS=https://demo.example.com
```

Multiple origins may be comma-separated:

```bash
DSA_CORS_ORIGINS=https://demo.example.com,https://preview.example.com
```

Keep provider/API credentials in the hosting platform's secret store. Never expose them through `NEXT_PUBLIC_*` variables.

## Local Docker check

Copy the environment template and start the stack:

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- Web: `http://localhost:3000`
- API health: `http://localhost:8000/health`

The expected visitor path is:

```text
Landing page
  → upload dataset
  → inspect profile
  → ask a natural-language question
  → inspect tool trace and evidence
  → open/download report
```

## Recommended hosted shape

Use two independently deployable services:

1. **API service** — persistent filesystem/volume for uploaded datasets and generated artifacts.
2. **Web service** — Next.js application built with the public API URL.

For a public trial, add platform-level controls for maximum request/file size, rate limits, log retention, and provider spending limits.

## Launch checklist

- [ ] API is reachable over HTTPS.
- [ ] `/health` returns successfully.
- [ ] Web build uses the public API URL.
- [ ] API CORS allows the public web origin only.
- [ ] Uploading a small CSV succeeds.
- [ ] A canonical analysis question completes successfully.
- [ ] Analysis trace shows tool calls, evidence, validation, and artifacts.
- [ ] Report download works.
- [ ] Provider spending/rate limits are configured.
- [ ] README gets a `Try Live Demo` link only after the public URL passes this checklist.

The public demo should optimize for one reliable happy path rather than exposing every internal surface.
