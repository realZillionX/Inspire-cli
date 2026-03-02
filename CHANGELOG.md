# Changelog

## Unreleased

### Breaking Changes

- Removed deprecated `inspire bridge exec --no-tunnel` flag. SSH tunnel is now the default execution path for command execution; workflow path is selected by artifact options.
- Removed deprecated `inspire sync --via-action` flag. Use `--transport workflow` explicitly when workflow transport is required.

### Fixed

- Added first-class `[proxy]` config support (`requests_http`, `requests_https`, `playwright`, `rtunnel`) with matching `INSPIRE_*_PROXY` environment variables.
- Unified runtime proxy resolution priority across requests, Playwright, and rtunnel: explicit env vars, then layered TOML `[proxy]`, then system `http_proxy`/`https_proxy`.
- `inspire notebook ssh` now resolves numeric notebook list IDs (e.g., `189181`) to canonical notebook IDs before SSH setup.
- SSH preflight failure hints now include explicit diagnostics when notebook runtime reports `start_config.allow_ssh=false`.
- `inspire image list --source all` now tolerates per-source failures, returns partial results with warnings, and still fails only when all sources fail.
- `inspire hpc create` now retries with backend-compatible payload fallbacks when clusters reject `task_priority`/`priority` fields or require string-typed `cpus_per_task` and `memory_per_cpu`.

## v0.2.4 (2025-01-01)

### Features

- Job management commands (create, status, logs, list, stop, wait)
- Notebook management commands (list, create, start, stop, ssh)
- Resource availability listing (GPUs, nodes)
- Quick job submission with auto-resource selection (`run`)
- Code sync to Bridge runner (`sync`)
- Bridge remote execution (`bridge exec`, `bridge ssh`)
- SSH tunnel management (add, remove, status, list, ssh-config)
- Configuration management (show, check, env) with TOML + env var loading
- Project initialization with environment detection
- Dual execution paths: SSH tunnel (fast) and Gitea/GitHub Actions (fallback)
- Human-readable and JSON output formatting
- Remote environment variable injection via `[remote_env]` config
