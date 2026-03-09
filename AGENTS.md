# Repository Guidelines

## Project Structure & Module Organization
- `inspire/` is the main Python package.
- CLI entry point: `inspire/cli/main.py`; top-level command registration is in `inspire/cli/commands/__init__.py`.
- CLI command modules live in `inspire/cli/commands/`:
  - Group packages: `bridge/`, `config/`, `hpc/`, `image/`, `init/`, `job/`, `notebook/`, `project/`, `resources/`, `tunnel/`
  - Top-level command modules: `run.py`, `sync.py`
- Command package conventions:
  - Most groups use thin `__init__.py` files (Click group + `add_command` calls), with implementation in submodules.
  - `init` is the exception: command implementation is in `init/init_cmd.py`; `init/__init__.py` is a stable import surface used by tests.
- Current command implementation map:
  - `bridge/`: `exec_cmd.py`, `ssh_cmd.py`, `scp_cmd.py`
  - `tunnel/`: `add.py`, `remove.py`, `status.py`, `list_cmd.py`, `update.py`, `set_default.py`, `ssh_config.py`, `test_cmd.py`
  - `config/`: `check.py`, `show.py`, `env_cmd.py`
  - `hpc/`: `hpc_commands.py`
  - `init/`: `init_cmd.py`, `discover.py`, `templates.py`, `env_detect.py`, `toml_helpers.py`, `errors.py`, `json_report.py`
  - `image/`: `image_commands.py` (list, detail, register, save, delete, set-default)
  - `job/`: `job_commands.py`, `job_create.py`, `job_logs.py`, `job_deps.py`
  - `notebook/`: `notebook_commands.py`, `notebook_create_flow.py`, `notebook_lookup.py`, `notebook_presenters.py`, `notebook_ssh_flow.py`, `top.py`
  - `project/`: `project_commands.py`
  - `resources/`: `resources_list.py`, `resources_nodes.py`, `resources_specs.py`, `resources_predict.py`
- Formatters: `inspire/cli/formatters/human_formatter.py` (human-readable) and `json_formatter.py` (machine-readable).
- Debug logging helpers live in `inspire/cli/logging_setup.py`.
- Domain packages (preferred for shared logic used by CLI):
  - `inspire/config/`: config models, TOML/env loading, schema/options, runtime helpers.
  - Config loading is split across `load.py` (compat facade), `load_common.py`, `load_layers.py`, `load_runtime.py`, and `load_accounts.py`.
  - `inspire/config/options/`: option groups in `api.py`, `forge.py`, `infra.py`, `project.py`.
  - `inspire/platform/openapi/`: OpenAPI client/auth/jobs/nodes/resources.
  - `inspire/platform/web/`: web session (SSO) + browser-only APIs (`session/`, `browser_api/`, `resources.py`).
  - `inspire/platform/web/browser_api/`: split domain modules including `availability/`, `jobs.py`, `notebooks.py`, `images.py`, `projects.py`, `workspaces.py`, `playwright_notebooks.py`, `rtunnel.py`.
  - `inspire/bridge/tunnel/`: tunnel config/models + rtunnel/ssh/scp/sync helpers.
  - `inspire/bridge/forge/`: Forge/Gitea workflow, logs, artifacts, and API helpers.
- `tests/` contains pytest suites across CLI, bridge/tunnel, openapi, web session, notebook flows, and recent regressions (for example, `tests/test_cli_commands.py`, `tests/test_cli_smoke.py`, `tests/test_openapi_proxy_config.py`, `tests/test_resources_specs_command.py`, `tests/test_cpu_compute_group_fixes.py`).
- `examples/` holds workflow YAML examples for Gitea/Forgejo usage.
- `scripts/` is mostly ignored, but `scripts/bootstrap_inspire_env.sh` is intentionally tracked.
- `docs/` includes `inspire.env.template` and OpenAPI reference notes (`启智 高性能计算/分布式训练/模型部署 OpenAPI 文档.md`); `README.md` is the user-facing command guide; `bin/inspire` is a repo-local wrapper.

## Build, Test, and Development Commands
- Prefer `uv` for all Python/CLI invocations (`uv run ...`, `uv tool run ...`); avoid system `python`/`pip`.
- `uv tool install -e .` installs the CLI in editable mode without activating a venv.
- `uv venv .venv && uv pip install -e .` creates a local venv and installs the package for development.
- `uv run inspire --help` validates the entry point (works without a global install).
- `uv run pytest` runs the test suite.
- If `uv run pytest` cannot find the pytest entrypoint in your local environment, use `uv run --with pytest python -m pytest`.
- `uv run pytest -m integration` runs integration tests that require live API access.
- `uv run ruff check inspire tests` and `uv run black --check inspire tests` match CI lint/format checks.
- `uv tool run black .` formats the repo when needed.
- `uv` may update `uv.lock` during runs; avoid committing it unless dependencies were intentionally changed.

## CI/CD and Release Process
- CI runs on Codeberg Forgejo Actions (`.forgejo/workflows/`) on push/PR to `main`.
- CI jobs run in parallel:
  - `lint`: `uv run ruff check inspire tests` and `uv run black --check inspire tests`
  - `test`: `uv run pytest -x -q --tb=short`
- Release workflow triggers on `v*` tag push and validates version consistency across `pyproject.toml`, `inspire/__init__.py`, and the git tag.
- Dependency checks run weekly (Monday 09:00 UTC) via `deps-check`.
- Release process:
  1. `uv run cz bump --patch` (or `--minor` / `--major`) updates `pyproject.toml`, `inspire/__init__.py`, `CHANGELOG.md`, and creates a git tag.
  2. `git push origin main --tags` triggers release validation CI.
  3. Sync to GitHub public with the existing file-copy process (see `CLAUDE.md`).
- New clones should run `uv run pre-commit install` to install hooks.
- Manual dependency update: `uv lock --upgrade`.

## Coding Style & Naming Conventions
- Python 3.10+ codebase; follow Black and Ruff defaults with 100-character line length.
- Use `snake_case` for functions/variables, `CapWords` for classes, and `test_*.py` for test files.
- Keep Click group wiring and implementation separated; avoid putting business logic in command registration modules.

## Testing Guidelines
- Tests live under `tests/` and use pytest.
- Integration tests are marked with `@pytest.mark.integration`; keep them isolated from unit tests and avoid requiring live credentials in standard runs.
- `tests/test_cli_smoke.py` validates `--help` output and key command presence; update it when adding/removing top-level command groups in `inspire/cli/main.py` (including `hpc`).
- For proxy/config changes, run `tests/test_openapi_proxy_config.py`, `tests/test_web_session_proxy.py`, and `tests/test_web_config_resolution.py`.
- For OpenAPI config/transport changes, also run `tests/test_openapi_client_config.py`.
- For image-source behavior changes, run `tests/test_image_commands.py` (covers `private`/`my-private`/`all` semantics and image-id resolution).
- For resource selection changes, run `tests/test_resources_specs_command.py`, `tests/test_cpu_compute_group_fixes.py`, and `tests/test_notebook_create_flow.py`.
- For notebook command surface or SSH changes, run `tests/test_notebook_commands.py`, `tests/test_notebook_rtunnel_commands.py`, and `tests/test_notebook_post_start.py`.
- For debug logging changes, run `tests/test_debug_logging.py`.

## Commit & Pull Request Guidelines
- Prefer concise, imperative commit subjects. Conventional-commit prefixes are acceptable when useful.
- PRs should include a short behavior summary, testing notes, and any config/environment changes; include CLI output snippets for user-visible behavior changes.

## Configuration & Security Tips
- Config is layered from:
  1. `~/.config/inspire/config.toml` (global)
  2. `./.inspire/config.toml` (project)
  3. Environment variables
- `INSPIRE_GLOBAL_CONFIG_PATH` overrides the default global config path for both reads and writes (`init`, `discover`, template generation, and normal runtime loading).
- Default conflict precedence is env-over-TOML; `inspire config show` surfaces value sources and precedence.
- Typical required inputs for authenticated commands are `INSPIRE_USERNAME`, `INSPIRE_PASSWORD` (or `[accounts."<username>"].password`), and `INSPIRE_TARGET_DIR`.
- Account-scoped passwords in `[accounts."<username>"].password` override legacy `[auth].password` when both are present.
- Gitea/Forge workflow sync and remote logs rely on `INSP_GITEA_REPO`, `INSP_GITEA_TOKEN`, and `INSP_GITEA_SERVER`.
- Optional: `INSPIRE_SHM_SIZE` (or `job.shm_size` in config) sets default shared memory (GiB) for job and notebook creation.
- Optional: `INSPIRE_NOTEBOOK_POST_START` (or `notebook.post_start`) configures a post-start shell action for notebook create/start flows.
- Optional: `INSPIRE_BRIDGE_ACTION_TIMEOUT` (or `bridge.action_timeout` in config) sets default timeout (seconds) for `inspire bridge exec`.
- Optional: `INSPIRE_BROWSER_API_PREFIX` overrides the default browser API path prefix.
- Optional: `INSPIRE_DEBUG_LOG_DIR` overrides the per-run debug report directory used by `inspire --debug`.
- Proxy precedence is unified as: explicit `INSPIRE_*_PROXY` env vars > layered TOML `[proxy]` > system `http_proxy`/`https_proxy`.
- `INSPIRE_FORCE_PROXY` / `[api].force_proxy` disables `requests.Session.trust_env` for OpenAPI calls to prevent `no_proxy` or system bypass.
- For `.sii.edu.cn` deployments, when request-side proxy resolves to `http://127.0.0.1:8888`, Playwright/rtunnel auto-fallback to `socks5://127.0.0.1:1080`.
- `inspire config check` now validates placeholder hosts, required credentials, required Docker registry, and API authentication in one pass.
- Never commit credentials/tokens. Prefer local env exports or local config; run `inspire config check` to validate setup.

## Public Sync & Ignore Policy
- Treat `.gitignore` as the source of truth for non-public/internal artifacts.
- Paths currently ignored/internal include `.inspire/`, `internal/`, most of `scripts/` (except tracked `scripts/bootstrap_inspire_env.sh`), `API_ENDPOINTS.md`, `CLAUDE.md`, `config.toml.example`, `inspire/Inspire_OpenAPI_Reference.md`, `docs/rtunnel-ssh-setup.md`, and `.playwright-cli/`.
- When preparing `github-public` sync, avoid introducing dependencies on ignored paths in docs, examples, tests, or command instructions.

## Current Runtime Notes (Keep In Sync With Code)
- `inspire resources specs` is the canonical preflight for **notebook** spec discovery; it emits `logic_compute_group_id`, `spec_id`, CPU/memory/GPU fields, and workspace binding. **HPC tasks use a separate `quota_id`** (not the same `spec_id`); obtain it from an existing HPC job via `inspire --json hpc status <job_id>` → `slurm_cluster_spec.predef_quota_id` or `resource_spec_price.quota_id`.
- `inspire image list --source private` now maps to UI "个人可见镜像"; `--source my-private` preserves direct `SOURCE_PRIVATE`; `--source all` aggregates `official/public/private/my-private` and deduplicates by `image_id`.
- Partial image-id resolution for `image detail/delete` scans the same four sources to avoid "list can see but detail cannot resolve" gaps.
- `inspire image set-default` only accepts `--job` / `--notebook` targets (it does not take a positional `<image_id>`).
- `inspire bridge exec` uses SSH tunnel by default; workflow transport is used only when artifact options are requested.
- Deprecated flags are removed: `inspire bridge exec --no-tunnel` and `inspire sync --via-action`.
- `inspire sync` uses explicit `--transport ssh|workflow`; SSH mode supports `--source auto|remote|bundle` and bridge internet-awareness fallback.
- CPU notebook compute-group selection prefers `CPU资源-2` and `HPC-可上网区资源-2` when `gpu_count == 0`, and probes resource prices to avoid empty groups.
- `inspire hpc create` sends `memory_per_cpu` as a string with `G` suffix (e.g. `"4G"`) and `cpus_per_task` as a string, matching the OpenAPI spec. It retries with payload fallbacks when backend rejects `task_priority`/`priority` fields. `--image` must be a full docker address (e.g. `docker.sii.shaipower.online/inspire-studio/<name>:<version>`).
- `make_request_with_retry()` in `inspire/platform/openapi/http.py` retries HTTP 429 (rate limit) responses with exponential backoff, in addition to 5xx errors.
- Job subcommands (`list/status/stop/wait/update/command`) load layered config from files + env (not env-only).
- `notebook ssh` first bootstraps from the web/Jupyter side: it opens JupyterLab with Playwright, uploads the local `rtunnel` binary via Jupyter Contents API when available, then prefers terminal REST API + terminal WebSocket delivery for the setup script. If terminal WS delivery fails, fallback is Playwright UI terminal automation.
- `notebook ssh` skips `curl` fallback when the runtime is clearly offline (Contents API upload succeeded, or dropbear/apt-mirror bootstrap is in use). In those cases a missing `/tmp/rtunnel` is surfaced as an explicit bootstrap error instead of a doomed download attempt.
- rtunnel setup script now uses dynamic platform detection (`uname -s`/`uname -m`) inside the container to determine the correct binary download URL, instead of using the local machine's `platform.system()`/`platform.machine()` values.
- `open_notebook_lab()` now probes `/ide` briefly (short frame probe window) and falls back early to direct `/api/v1/notebook/lab/<id>/` navigation.
- `inspire --debug` writes a redacted per-run report under `~/.cache/inspire-cli/logs/` by default; secrets, cookies, bearer tokens, and Jupyter proxy path tokens are masked before writing.
- Session-expiry handling refreshes credentials in place: `request_json()` re-authenticates once and updates the same `WebSession` object.
- HTTP proxy readiness checks can still report transient failures (`404`, `ECONNREFUSED`) even when SSH succeeds. Treat HTTP probe as advisory; use SSH preflight (`inspire tunnel test`) as authoritative.
- rtunnel proxy state is cached per account under `~/.cache/inspire-cli/rtunnel-proxy-state*.json` with TTL-based reuse.
- Set `INSPIRE_RTUNNEL_TIMING=1` to enable per-step timing output in `_setup_notebook_rtunnel_sync()`.
- `inspire init --discover` now collects projects across discovered workspaces, not only the current workspace. Global per-account catalog data is persisted only when discovery actually spans multiple workspaces; project-level config remains the canonical place for workspace aliases and compute-group catalogs.
- Notebook post-start actions are now first-class. Use `notebook.post_start` / `INSPIRE_NOTEBOOK_POST_START`, `--post-start`, or `--post-start-script`; the old keepalive preset is removed, and `none` is the supported way to disable a configured default.
- Keep tracked tests/docs free of credentials, tokens, and private endpoint values.
- `inspire init` probe controls (`--probe-limit`, `--probe-keep-notebooks`, `--probe-pubkey`/`--pubkey`, `--probe-timeout`) are only effective with `--discover --probe-shared-path`; otherwise they are accepted but ignored.
