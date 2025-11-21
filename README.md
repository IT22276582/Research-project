# cog_py_est (Python CLE microservice)

Lightweight, on-device microservice that follows the documented CLE architecture and sequence diagrams without the extra Rust-only complexity. It runs a background loop that ingests sanitized input metadata, fuses features into 60 s windows (15 s hop), normalizes them with a rolling z-score + Huber clipping, updates a scalar Kalman filter with RLS-adapted observation weights, and triggers EMA prompts when uncertainty or residuals are high. All state stays local in SQLite to respect the privacy boundary.

## What it implements (mapping to diagrams)
- Permission guard drops disallowed sources or privacy-pause traffic (`OS Input Hooks -> Guard -> Buffer`).
- Event ring buffer with 60 s span / 15 s hop (`Sliding Window Manager` in the passive-sensing sequence).
- Keystroke/pointer feature fusion (IKI stats, error/backspace rate, pointer speed/accel, idle fraction) and quality scoring with simple imputation when an input channel is missing.
- Rolling normalization (EWMA mean/variance + Huber clipping) before estimation.
- Context-aware window manager fed by the OS hook daemon (focus app, lock status, idle seconds, DND) so the policy guard can suppress prompts per diagram.
- Consent & policy guard loads blocklists, logs consent history, and wires retention pruning all the way to SQLite (via `Storage.prune_retention`).
- Cold-start calibrator streams residual diagnostics, persists a mean feature profile, and drives onboarding banners until the variance target is met.
- EMA fusion layer replays labelled windows into the estimator immediately (RLS update + Kalman assimilation) and emits residual/variance telemetry for the overlay and console/SSE feeds.
- Scalar Kalman filter + RLS adapter for observation weights; emits posterior, variance, and residual per hop.
- EMA scheduler paired with a policy actor/log that enforces DND/blocklists/privacy toggles and surfaces suppression decisions through `/policy/events`.
- Cold-start baseline: 5 minutes of passive collection, then an initial baseline prompt as shown in the cold-start sequence.
- Local-only SQLite persistence aligned with the ERD (sessions, events, feature windows, EMA prompts/responses, model snapshots, telemetry metrics). No network egress.

## Quick start
1) Create a virtual environment and install the service (Python 3.10+):
   ```powershell
   cd cog_py_est
   python -m venv .venv
   .\.venv\Scripts\activate
   python -m pip install --upgrade pip
   python -m pip install .
   ```
2) (Optional) Copy and tweak the config: `copy config\\policy.example.toml policy.toml`.
3) Run the microservice (binds to localhost only by default):
   ```powershell
   .\.venv\Scripts\cog-py-est.exe --config policy.toml
   ```

## Configuration
- Defaults live in `config/policy.example.toml` and mirror the diagrams: `window_seconds=60`, `hop_seconds=15`, baseline_minutes=5, RLS forgetting factor, EMA cadence thresholds, and on-device host/port.
- Sensitivity profiles live under `[sensitivity]`. Choose `current_profile` (`conservative`, `balanced`, `responsive`, `sensitive`, `very_sensitive`, or `v_very_sensitive`) to automatically tune EMA thresholds and estimator noise terms.
- Override with `--config <path>` or host/port flags. Storage path parents are auto-created; retention pruning is left simple (hours cap only).

## API surface (localhost)
- `POST /events` – ingest sanitized events. Body: `{"source": "keyboard|pointer|system", "payload": {...}, "timestamp": "<iso8601, optional>"}`. Returns `{accepted: bool}` after permission guard.
- `GET /estimate` – latest posterior (mean, variance, ci95, residual) plus hop index, quality, baseline flag, onboarding state, context flags, scheduler state, and any pending prompt payload.
- `POST /ema/response` – submit EMA outcome. Body: `{"prompt_id": <int>, "rating": 1-7, "disposition": "completed|dismissed|timeout|snoozed", "note": "optional"}`. Ratings feed the RLS + Kalman assimilation path; snoozes trigger adaptive cooldowns per the EMA policy state machine.
- `GET /telemetry` – residual, variance, suppression reason, scheduler timers, context flags, onboarding percent, and privacy/consent status for the overlay.
- `GET /telemetry/feed` – NDJSON feed of `telemetry_metrics` for the local console/CLI.
- `GET /stream/state` – Server-Sent Events stream that combines `/telemetry` + `/estimate` snapshots for the overlay (used by the Next.js dashboard instead of 5 s polling).
- `POST /privacy` / `POST /consent` – toggle privacy pause or consent entirely on-device (mirrors the "hard suppressed" state in the diagrams) and log the history to `data/consent_log.jsonl`.
- `GET /permissions` – current guard status (helpful when rendering the UI toggles).
- `GET /policy/consent` / `GET /policy/events` – audit feeds for consent history and policy suppression decisions (backed by SQLite + surfaced in the console UI).
- Aggregated export workflow: `POST /export/request` (creates a pending export and summary), optional `POST /export/{id}/approve` with a review token, then `GET /export/{id}/download` to retrieve the approved JSON summary stored under `data/exports/`.

## Next.js UI (real-time dashboard + EMA prompt)
- Location: `cog_py_est/web-ui` (Next.js 14, SWR polling).
- Configure API base by copying `.env.local.example` to `.env.local` and adjusting if needed.
- Dev server:
  ```powershell
  cd cog_py_est/web-ui
  npm install   # first run only
  npm run dev   # http://localhost:3000
  ```
- The UI now relies on `/stream/state` (SSE) for live updates—no more 5 s polling. SSE payloads include telemetry + estimate snapshots so charts, badges, and prompts refresh immediately.
- Live diagnostics show scheduler state, context flags, adaptive cooldown timers, onboarding progress, and policy prompt/suppression counters, plus buttons wired to `/privacy` and `/consent` so you can exercise snooze/opt-out flows exactly as the diagrams describe.
- A dedicated telemetry console lives at `http://localhost:3000/console`, backed by `/telemetry/feed`, `/policy/consent`, and `/policy/events` to review NDJSON metrics, consent history, and suppression logs directly from SQLite.
- Prefer a pure local console? Run `python -m cog_py_est.tools.console_cli --config policy.toml` to print live counts, telemetry metrics, and consent history straight from the SQLite store (no HTTP dependencies).

## One-shot starter (backend + UI [+ hooks])
- Script: `cog_py_est/start_all.ps1`
- Usage:
  ```powershell
  cd cog_py_est
  # Optional first-time installs: python -m venv .venv; .\.venv\Scripts\activate; python -m pip install ".[hooks]"
  powershell -ExecutionPolicy Bypass -File start_all.ps1           # backend + UI
  powershell -ExecutionPolicy Bypass -File start_all.ps1 -WithHooks # backend + UI + OS hook streamer
  ```
- The script checks/installs UI deps, starts the Python service, Next dev server, and optionally the OS hook streamer.

## Testing & quality
- Python test deps: `python -m pip install ".[tests,lint]"` before running checks.
- Backend lint: `ruff check .`
- Backend unit/integration/benchmark suite: `python -m unittest discover -s tests -p "test_*.py"` (covers FastAPI ingest, feature vector shape/performance, and Kalman throughput)
- Frontend tests: `cd web-ui && npm test`
- Frontend type-check: `cd web-ui && npm run typecheck`
- Frontend build: `cd web-ui && npm run build`
- CI: GitHub Actions runs lint + backend tests/benchmarks + frontend tests/type-check + build on pushes/PRs.

### Hooking real OS events into `/events`
- Install optional hook deps: `python -m pip install ".[hooks]"`.
- Run the helper that streams keyboard/pointer timing (no content) into the service:
  ```powershell
  .\.venv\Scripts\cle-os-hooks.exe --endpoint http://127.0.0.1:8000/events
  ```
- The helper uses `pynput` to capture timing deltas only and posts sanitized payloads aligned with the feature extractor (IKI latencies and pointer deltas).

### Connecting an EMA UI shell
- Poll `GET /estimate` and watch `pending_prompt` for `{"prompt_id": <id>, "reason": ...}` to know when to render a prompt.
- After the user responds, POST to `/ema/response` with `prompt_id`, `rating (1-7)`, and `disposition` (`completed|dismissed|timeout|snoozed`). Completed prompts replay the labelled window immediately; dismiss/snooze map to the suppression branches from the EMA state diagram.
- Typical flow in a UI loop:
  1. Call `/estimate` every hop (15s) or subscribe via SSE/websocket you host in the overlay.
  2. When `pending_prompt` is present and your overlay isn’t muted, render the micro-EMA form, collect Likert + optional note.
  3. Call `/ema/response` with the same `prompt_id` you received; keep your own UX timers for dismiss/timeout to send the right `disposition`.

## Alignment and constraints
- Runs entirely on-device (localhost bind) to satisfy the privacy boundary in the architecture docs.
- Uses simple stats and a scalar state to keep latency/energy low as per the performance assumptions.
- No extra features beyond what appears in the design + sequence diagrams: no adaptive CPU throttling, no advanced pattern detectors, no network exports.

## File map
- `cog_py_est/config.py` – config models and loader.
- `cog_py_est/events.py` – permission guard + event buffer.
- `cog_py_est/features.py` – keystroke/pointer feature fusion and quality score.
- `cog_py_est/normalization.py` – rolling z-score with Huber clipping.
- `cog_py_est/kalman.py` – scalar Kalman filter with RLS weight adaptation.
- `cog_py_est/ema.py` – cadence/suppression logic for EMA prompts.
- `cog_py_est/storage.py` – local SQLite persistence for sessions, events, windows, EMAs, and model snapshots.
- `cog_py_est/service.py` – background runtime loop (60 s window, 15 s hop).
- `cog_py_est/app.py` – FastAPI wiring and request schemas.
- `cog_py_est/cli.py` – entrypoint (`cog-py-est`) for running the service.


## Console 01
.\.venv\Scripts\cle-os-hooks.exe --endpoint http://127.0.0.1:8000/events

## Console 02
.\.venv\Scripts\cog-py-est.exe --config policy_1.toml

## Console 03
npm run dev
