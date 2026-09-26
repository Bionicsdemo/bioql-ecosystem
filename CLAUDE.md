# BioQL — Quantum Drug Discovery Platform

## Mission
A real quantum drug-discovery platform: real-hardware execution on IBM Quantum Heron r2 (156q) with CUDA-Q GPU (cuStateVec/MPS) simulation behind it, defaulting to simulation to conserve scarce IBM hardware minutes — and every result labeled with its true backend (is_real_hardware + IBM job id, real-or-null).

## Runtime (CURRENT — local-only)
The live stack runs entirely on this machine. `src/backend/` IS the live source; there is no deploy step.

| Service | Port | Bind | Started by |
|---|---|---|---|
| vMLX LLM engine (Qwen2.5-Coder-7B-MLX) | 8001 | 127.0.0.1 | `start_all_local.sh` |
| Marie speech (Whisper + Kokoro) | 8002 | 127.0.0.1 | `start_all_local.sh` |
| Marie coordinator (FastAPI + SQLite WAL) | 8003 | 127.0.0.1 | `start_all_local.sh` |
| Flask backend | 5035 | 127.0.0.1 | `start_backend.sh` |
| Vite frontend | 3000 | all interfaces | `start_frontend_local.sh` |
| TargetRadar | 4000 | all interfaces | `start_targetradar_local.sh` |

`start_all_local.sh` is idempotent — it skips any port already listening, so it is safe to re-run. Three LaunchAgents bring the stack up at login and keep it alive: `com.bioql.localstack`, `com.bioql.watchdog` (runs `watchdog_local.sh`, every 30 s), `com.bioql.llm-watchdog`. The scripts' own logs land in `.local_stack_logs/`.

**The agents do not call the repo scripts directly.** All three run `~/.bioql/runtime/agents/launch.sh <repo script>`, and their launchd-level stdout/stderr go to `~/.bioql/runtime/logs/`, not into the repo. This repo lives under `~/Documents`, which iCloud manages: at login the provider may not be ready, a launchd-spawned bash handed a script there fails with `Resource deadlock avoided` (EDEADLK), and the job dies — which is what filled `.local_stack_logs/*.launchd.err.log` through July 2026 and left nothing bringing the stack up. `launch.sh` waits (up to 180 s, reading a real byte, since a `stat` succeeds on a file that is not yet materialised) and then `exec`s the script, so the repo stays the single source of truth and no second copy can drift from it. It notes any wait in `~/.bioql/runtime/logs/launch.log`; an empty file means the repo was readable first try. Edit `start_all_local.sh`, `watchdog_local.sh` and `llm_watchdog.sh` in the repo as normal — nothing needs copying for those. `launch.sh` is the one exception, and it is the only file here that must be installed rather than read in place, because the reason it exists is that launchd cannot be trusted to read this directory at login. Its source of record is `src/infrastructure/scripts/launch_agent_shim.sh`; edit it there and reinstall:

```bash
install -m 755 src/infrastructure/scripts/launch_agent_shim.sh ~/.bioql/runtime/agents/launch.sh
```

After editing a plist: `launchctl bootout gui/$(id -u)/<label>`, then `launchctl enable …` and `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/<label>.plist`. Originals are backed up under `~/.bioql/runtime/agents/plist-backup-*/`.

To pick up a backend edit: clear the stale `.pyc`, then kill the backend and let the watchdog restart it. A kickstart of the LaunchAgent will not do it.

## Critical Rules
- **ALL timeouts = 43200s** (12 hours) — every endpoint, nginx, gunicorn, frontend
- **NEVER use --max-requests** in Gunicorn — kills in-flight quantum pipelines
- **Streaming keepalive** required for endpoints >30s (`streaming_pipeline_response()`)
- **proxy_buffering off** + `X-Accel-Buffering: no` for streaming nginx blocks
- **IBM channel = `ibm_quantum_platform`** (not `ibm_quantum`)
- **Qiskit Runtime 0.44+**: `EstimatorV2(mode=backend)` not `EstimatorV2(backend=backend)`
- **Protenix v1.0.5**: entity type `"proteinChain"`, must include `"count": 1`

## Shadow-path traps (edits that silently do nothing)
- **`/opt/bioql` shadows sibling modules.** `script_executor_server.py:42` runs `sys.path.insert(0, '/opt/bioql')` before anything else, so a module that also exists under `/opt/bioql` is imported from THERE, not from `src/backend/`. Editing the repo copy changes nothing. Copy to `/opt/bioql` and clear the `.pyc`, and verify against the running backend rather than the venv. Four more `/opt/bioql` inserts follow at lines 1788, 1864, 2346 and 2616.
- **NEVER copy a NEW module into `/opt/bioql`.** The trap above only applies to a module that ALREADY exists in both places. A module that exists only in `src/backend/` resolves from the repo correctly, because `src/backend` stays on `sys.path` (the server lives there). Copying a new file to `/opt/bioql` is what CREATES the trap — from then on every repo edit to it silently does nothing. Before any `cp` into `/opt/bioql`, check whether the file is already there; if it is not, do not copy it. Verify resolution instead: `~/.bioql/venv/bin/python -c "import m; print(m.__file__)"`.
- **Before syncing a module that IS in both places, diff it first.** `diff /opt/bioql/m.py src/backend/m.py` and inspect `^<` lines — anything that exists only in `/opt` is about to be lost. Back up, then copy, then clear the `.pyc`. On 2026-09-18 `/opt/bioql/pipeline_finalize.py` (Sep 13) was missing `_attach_efficacious_dose` entirely and `/opt/bioql/pbpk_modeler.py` (Aug 1) was missing the `optimizer` parameter — so the live dose derivation had never run, and when it did it silently used QAOA-PK and returned 51.2/49.3/48.8 mg for identical input instead of a deterministic 7.5 mg.
- **The frontend on :3000 is served from `~/.bioql/runtime/frontend-v2`,** not from the repo. Confirm a change landed by curling the built asset from the running server.
- **TargetRadar on :4000 is served from `~/.bioql/runtime/targetradar`,** rsynced from the repo at startup only. Repo edits after startup do nothing until the next restart.

## Testing
- **Run tests with `~/.bioql/venv/bin/python -m pytest`,** the backend's own interpreter. Homebrew `python3` lacks `flask`, `block2/pyblock2` and other backend deps, so a run there reports failures that are not regressions — on 2026-09-18 six "failures" all passed under the venv.
- **A source-level guard must not read its own explanation.** Three guards written on 2026-09-18 fired on their own docstrings or notes (e.g. a docstring saying "nothing here imports cudaq" read as an import). Strip docstrings via AST before substring checks, and skip prose fields (`note`, `reason`, `description`, …) when matching recorded values.
- **Match field names by token, not substring.** `"kd" in path` matches `score_brea(kd)own`; that inflated a historical audit rate from 60% to 94%.

## Key Files
- `src/backend/script_executor_server.py` — Main Flask monolith (~35K lines)
- `src/mcp/server.py` — MCP tool server (65+ tools)
- `src/frontend/src/` — React UI source

## Retired — GCP production (reference only, do not deploy)
The GCP project `bioql-prod-2026` (us-east1-b) is deprecated. The table and scripts below are kept for historical context; nothing in the current workflow should target them.

| Instance | Role | Key Ports |
|---|---|---|
| bioql-g1-mcp-auth | MCP Server + Auth | 5010, 5001 |
| bioql-g2-workflows | Workflows + Crons | 8080 |
| bioql-g3-frontend-lb | Frontend + Nginx LB + Primary Backend | 3000, 5035 |
| bioql-g4-alphagen | Protenix + Complexa + AlphaGenomics (L4 GPU) | 5020, 5040 |
| bioql-g6-ha-backend-1 | HA Backup Backend | 5035 |
| bioql-g7-ha-backend-2 | HA Backup Backend | 5035 |

- `src/infrastructure/scripts/deploy_sync.sh` — GCP deploy, G3 → G6/G7 (retired)
- `src/infrastructure/scripts/g4_auto_manager.py` — GPU cost optimization (retired)

```bash
# RETIRED — these targeted the GCP replicas, which no longer exist.
# ./src/infrastructure/scripts/deploy_sync.sh
# ./src/infrastructure/scripts/deploy_sync.sh --file module_name.py
```

MOLEVERA / BIOQL
