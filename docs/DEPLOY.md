# Deploying to Render

Two Docker web services: `agritwin-rwanda-api` (FastAPI, `infra/Dockerfile.api`) and
`agritwin-rwanda-web` (static React build served by nginx, `infra/Dockerfile.web`).
Both Dockerfiles and the `render.yaml` Blueprint at the repo root have been built and
smoke-tested locally with real `docker build` / `docker run` (see `docs/decisions.md`
2026-09-25): correct image builds, `$PORT` binding via shell-expanded `CMD` (API) and
nginx's `envsubst` templating (web), the web's client-side routing (`/districts/12`
refresh) falling back to `index.html` correctly, and the build-time `VITE_API_BASE` arg
actually reaching the compiled JS bundle.

**What I can't do for you:** connecting this repo to Render requires logging into (or
creating) a Render account and authorizing it against GitHub — an account action only
you can take. Everything up to that point is done and tested.

## One-time setup

1. Push this branch to GitHub (`git push origin main`) if you haven't already — Render
   builds from the GitHub repo, not from your local disk.
2. Go to [dashboard.render.com](https://dashboard.render.com) and sign in (or create an
   account).
3. **New +** → **Blueprint** → connect the `agritwin-rwanda` GitHub repo. Render reads
   `render.yaml` from the repo root automatically and proposes both services.
4. Click **Apply**. Render builds both Docker images and deploys them. First build takes
   a few minutes (installing Python/npm dependencies from scratch).

## If Render rejects `render.yaml`'s syntax

Render has changed its Blueprint schema field names before (e.g. `env:` → `runtime:`
for the service's build type). `render.yaml` here uses `runtime: docker`, current as of
this writing, but this file was authored and tested locally (Docker builds, not against
Render's actual Blueprint parser, since that needs a live account). If Render's UI
reports a schema error on `runtime: docker`, try `env: docker` instead — the underlying
`dockerfilePath`/`dockerContext`/`envVars` fields are stable either way. Everything else
in this doc (the Dockerfiles, the env vars needed, the smoke-test steps) holds regardless
of that one field name.

## Service name collisions

`render.yaml` names the two services `agritwin-rwanda-api` and `agritwin-rwanda-web`,
and cross-references them by that name (`ALLOWED_ORIGINS` on the API includes the web
service's expected URL; `VITE_API_BASE` on the web build points at the API's expected
URL). Render service names must be globally unique across *all* of Render, not just
your account. If either name is taken:

1. Edit `render.yaml`, change both occurrences of the taken name to something else
   (e.g. `agritwin-rwanda-api-<yourname>`), keeping the API and web cross-references
   consistent with each other.
2. Commit and push; re-apply the Blueprint, or fix the two env vars
   (`ALLOWED_ORIGINS` on the API service, `VITE_API_BASE` on the web service) directly
   in the Render dashboard after the first deploy and trigger a manual redeploy of the
   web service (it needs to rebuild, since `VITE_API_BASE` is baked in at build time,
   not read at runtime).

## After the first deploy: smoke-test it

Per the project's own development method (`CLAUDE.md`: "manually smoke-test the
deployed URL after each deploy"), not just this first one:

1. Open the web service's URL (`https://agritwin-rwanda-web.onrender.com` or whatever
   you named it). The map should load with real district colors, not a blank page or a
   stuck "Loading district data…".
2. Switch crop, season, and year; click a district; confirm the detail panel populates
   with real numbers.
3. Click "View full district profile"; confirm the district page loads with real yield
   trend, drivers, an early estimate, and a working "Download PDF brief" link.
4. Open the API service's URL directly at `/health` — should return
   `{"status": "ok", "data_version": "..."}`. At `/docs` you get the full interactive
   OpenAPI documentation for all 11 endpoints.
5. Check the browser console for CORS errors. If you see one, the web service's actual
   URL doesn't match what's in the API's `ALLOWED_ORIGINS` env var — fix it in the
   Render dashboard (API service → Environment) and the API service restarts
   automatically, no rebuild needed (this one's read at runtime, unlike
   `VITE_API_BASE`).

## Known limitations of the free plan

- Free web services on Render spin down after inactivity and take 30-60 seconds to
  wake up on the next request (a real cold start, not a bug in this app). Fine for a
  hackathon demo you're driving live; if judges will hit the link cold, consider
  visiting it yourself a minute before they do, or upgrading the API service to a paid
  plan (`plan: starter` in `render.yaml`) for always-on.
- Data refresh: this app has no scheduled jobs. To ship a newer `data/public/` (after
  re-running `make all` locally), commit and push it, then either wait for
  Render's auto-deploy-on-push (enabled by default) or trigger a manual deploy from the
  dashboard.

## Rolling back

Render keeps every previous deploy. If a deploy breaks something, use the dashboard's
"Rollback to this deploy" on the last known-good build rather than reverting git commits
under pressure.
