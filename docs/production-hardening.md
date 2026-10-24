# Production Persistence Hardening

This document defines the recommended persistence path for the hosted Data Science Agent demo.

## Recommendation

For the current single-instance public demo, use the smallest durable architecture that removes the failure mode already observed in production:

```text
Vercel web
   ↓
Render API (single paid instance)
   ↓
Render persistent disk mounted at /var/data
   ├── /var/data/datasets
   └── /var/data/dsa.db
```

This is the recommended **Stage 1** architecture because the application already supports both configuration points without adding a new storage SDK or database driver:

```bash
DSA_DATASET_DIR=/var/data/datasets
DSA_DATABASE_URL=sqlite+aiosqlite:////var/data/dsa.db
```

The existing API can therefore preserve uploaded datasets and SQLite metadata across normal deploys/restarts as soon as `/var/data` is backed by a persistent disk.

## Billing gate

Do not change the active root `render.yaml` from `plan: free` until the repository owner explicitly chooses
to incur paid Render compute and disk charges.

Money involved, read from Render's pricing page on 2026-10-13: the web service row matching
`0.5c-512mb` (0.5 CPU / 512 MB) lists **$7/month**, and persistent storage is billed at
**$0.25/GB/month**, so the Stage-1 shape above is roughly **$7.25/month**. Treat those as a quote, not a
contract -- one read of the same page put this plan at $25/month by conflating it with the 1c/2GB tier, so
confirm the number in the dashboard before paying. Render documents disks on **paid** web services only,
which is why no free configuration exists: persistence on the free instance is not a setting, it is
unavailable.

The repository includes a non-active reference configuration at:

```text
deploy/render-persistent.example.yaml
```

It uses Render's smallest current paid Web Service compute plan (`0.5c-512mb`) and a 1 GB persistent disk mounted at `/var/data`. The file is an example only. Do **not** attach it as a second Blueprint to the existing service. When upgrading, copy the relevant `plan`, `disk`, and persistence environment settings into the existing Blueprint or make the equivalent changes in the Render Dashboard.

This keeps the free public demo unchanged until the billing decision is intentional.

## Why not jump directly to Postgres + object storage?

Postgres plus S3-compatible object storage is the better multi-instance architecture, but it adds several moving parts at once:

- an async Postgres driver and migration path;
- object-storage credentials and SDK/client behavior;
- upload/download lifecycle and cleanup policy;
- artifact URL serving or signed URLs;
- more failure modes during the public-demo stabilization phase.

The current product is intentionally single-instance and already has a working local-file abstraction through `DSA_DATASET_DIR`. A persistent disk therefore removes the immediate durability risk with the smallest code and operational surface.

## Stage 1 — durable single-instance demo

### Render service

Upgrade the API Web Service from the free instance to a paid instance that supports persistent disks, then attach a disk:

```text
Compute: 0.5c-512mb (smallest current paid Web Service plan)
Disk name: dsa-data
Mount path: /var/data
Disk size: 1 GB to start
```

Set these environment variables:

```bash
DSA_DATASET_DIR=/var/data/datasets
DSA_DATABASE_URL=sqlite+aiosqlite:////var/data/dsa.db
DSA_ARTIFACT_ROOT=/var/data/artifacts
DSA_CORS_ORIGINS=https://data-science-agent-web.vercel.app
DSA_CORS_ORIGIN_REGEX=https://.*\.vercel\.app
DSA_LLM_MODE=heuristic
DSA_LLM_FALLBACK=heuristic
```

Three roots, not two. `DSA_ARTIFACT_ROOT` is the knob `dsa_datasets.artifact_paths.artifact_root()` reads,
and with it unset the process writes charts to `<cwd>/artifacts`, which inside the API container is
`/app/artifacts` -- outside the mount, and gone on the next deploy. A run would then survive with its
metadata and its dataset while every chart path in its report 404s, which is harder to diagnose than total
loss. `tests/contract/test_persistence_blueprint_covers_writable_roots.py` refuses a Stage-1 configuration
whose writable roots are not all under `disk.mountPath`.

The two CORS values above are the live service's, read from the root `render.yaml`: an explicit production
origin plus a regex covering Vercel preview hostnames. Copying an older origin from this page's history
silently drops preview support.

Do not remove the existing health check or Docker configuration.

### Pre-flight: is the mount writable by the process?

`docker/Dockerfile.api` runs `chown -R appuser:appuser /app` at build time and then switches with
`USER appuser`. A disk mounted at `/var/data` is created by Render at runtime, so it is **not** covered by
that chown, and the build-time layer cannot cover it either -- the path does not exist yet when the image is
built. If it arrives root-owned, the symptom is not a clear permission error: SQLite reports
`unable to open database file` at startup, or `attempt to write a readonly database` on the first insert,
and the dataset upload can fail while `/health` still answers.

Check it once, in the service's Shell, before running the acceptance test:

```bash
id -un                                  # expect appuser
touch /var/data/.write-check && rm /var/data/.write-check && echo writable
```

If that fails, prefer moving the mount under the directory the image already owns (for example
`/app/data` with the three variables pointed there) over adding a startup chown, and record whichever you
chose here -- the guard test only enforces that all three roots sit under the declared mount path, so any
mount path is acceptable as long as it is the same one in all three places.

### Acceptance test

After the disk is attached and the service is live:

1. Upload `dsa_acceptance_60.csv`.
2. Run the canonical multi-tool analysis.
3. Confirm the report reaches `COMPLETED` with no tool errors.
4. Trigger a manual redeploy.
5. Return to `/datasets` and confirm the uploaded dataset is still present.
6. Run the same analysis again without re-uploading the file.
7. Open the **pre-redeploy** run and confirm every path listed by
   `GET /api/v1/analysis/{run_id}/artifacts` still resolves to a file, and that the report's
   `experiment.json` / `reproduce.sh` / chart PNGs are present on the mount.

The persistence hardening is accepted only if steps 5-7 work after a redeploy.

Step 7 is the one that catches a half-durable configuration, and it is not the same failure as step 5-6.
`GET /api/v1/analysis/{run_id}/report` renders from the state stored in the database, so the report **text**
survives a redeploy on a free instance even when nothing else does; the artifact list is the part that
points at files. A run can therefore look perfectly healthy in the UI while its reproducibility bundle and
charts are gone.

## Stage 2 — scalable persistence

Move to this architecture only when the public demo needs multiple API instances, stronger retention guarantees, or independent lifecycle management:

```text
Vercel web
   ↓
Render API
   ├── Managed Postgres — metadata, runs, evidence indexes
   └── Object storage — datasets, charts, reports, notebooks, reproducibility bundles
```

Recommended changes for Stage 2:

- add an async PostgreSQL driver and normalize Render's database URL for SQLAlchemy async use;
- introduce a storage interface with local and S3-compatible implementations;
- store object keys rather than container-local paths in database records;
- use signed URLs or an authenticated API route for artifact retrieval;
- define retention, deletion, size, and abuse policies;
- add migrations before switching the production database.

Do not mix the Stage 2 migration with unrelated planner/statistics changes.

## Operational notes

The current free hosted demo must still be treated as ephemeral until Stage 1 is actually configured in Render. The application-level checks that hide stale dataset records and reject missing backing files should remain in place even after persistent storage is enabled; they are useful corruption and recovery guards.

Generated report/chart artifacts are now part of Stage 1 rather than a later refinement: `DSA_ARTIFACT_ROOT`
belongs on the mount alongside the database and the dataset directory, for the reason given in Stage 1.
Dataset, database and artifact durability are the gate because they jointly decide whether a run a visitor
created before an instance lifecycle event is still readable afterwards.

One detection gap to know about: `dsa_api.core.database.is_ephemeral_database()` -- the function behind the
startup warning "use a persistent volume or managed DB for anything beyond demos" -- inspects only the
database URL. A configuration that puts the database on `/var/data` while charts stay in `/app/artifacts`
therefore starts up with no warning at all. The guard test closes that hole at the configuration level; the
runtime check remains DB-scoped.

Render persistent disks are single-instance storage. Attaching one prevents multi-instance scaling for that service and introduces a brief deploy gap because the old instance must release the disk before the new instance mounts it. That tradeoff is acceptable for the current demo, but it is another reason to move to managed Postgres + object storage before horizontal scaling.

## Decision record

**Chosen first step:** persistent disk + SQLite on the existing single Render API instance.

**Billing policy:** keep the active service on Free until paid infrastructure is explicitly approved.

**Deferred:** managed Postgres + object storage, until scale or retention requirements justify the added operational complexity.
