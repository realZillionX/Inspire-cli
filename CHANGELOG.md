# Changelog

## Unreleased

### Breaking Changes

- Removed deprecated `inspire bridge exec --no-tunnel` flag. SSH tunnel is now the default execution path for command execution; workflow path is selected by artifact options.
- Removed deprecated `inspire sync --via-action` flag. Use `--transport workflow` explicitly when workflow transport is required.

### Added

- Added `inspire resources specs` command to discover per-workspace/per-compute-group spec entries for notebook/HPC creation, including `logic_compute_group_id`, `spec_id` (`quota_id`), CPU/memory/GPU fields, and price metadata.
- Added `docs/inspire.env.template` and `scripts/bootstrap_inspire_env.sh` for reproducible local environment bootstrap without committing plaintext credentials.

### Fixed

- Added first-class `[proxy]` config support (`requests_http`, `requests_https`, `playwright`, `rtunnel`) with matching `INSPIRE_*_PROXY` environment variables.
- Unified runtime proxy resolution priority across requests, Playwright, and rtunnel: explicit env vars, then layered TOML `[proxy]`, then system `http_proxy`/`https_proxy`.
- OpenAPI client now consistently honors config-backed `force_proxy` plus TOML `[proxy].requests_http/requests_https` without requiring shell-level `http_proxy/https_proxy`.
- `inspire notebook ssh` now resolves numeric notebook list IDs (e.g., `189181`) to canonical notebook IDs before SSH setup.
- SSH preflight failure hints now include explicit diagnostics when notebook runtime reports `start_config.allow_ssh=false`.
- `inspire image list --source all` now tolerates per-source failures, returns partial results with warnings, and still fails only when all sources fail.
- `inspire image list --source private` now matches UI "个人可见镜像" semantics (`visibility=VISIBILITY_PRIVATE` with combined private/public source list), and new `--source my-private` preserves direct `SOURCE_PRIVATE` queries for backward compatibility.
- `inspire image list --source all` now aggregates `official/public/private/my-private` and deduplicates by `image_id`; partial image-ID resolution for `detail/delete` now scans the same source set to avoid lookup gaps.
- Web-session request stack now supports `DELETE` in both requests and Playwright fallback clients, fixing `inspire image delete` failures caused by unsupported HTTP methods.
- `inspire hpc create` now retries with backend-compatible payload fallbacks when clusters reject `task_priority`/`priority` fields or require string-typed `cpus_per_task` and `memory_per_cpu`.
- CPU notebook compute-group selection now prefers `CPU资源-2` and `HPC-可上网区资源-2` when `gpu_count == 0`, avoiding accidental binding to generic `CPU资源`.
- Job subcommands (`list/status/stop/wait/update/command`) now load layered config from files and env vars (instead of env-only), aligning runtime behavior with other command groups.

### Docs

- Rewrote `docs/GUIDE.md` into an execution-first flow aligned with real CLI behavior and validated write-path outcomes.
- Updated image-source documentation to map UI categories (官方／公开可见／个人可见) to CLI `--source` values, with troubleshooting examples for `wanvideo:1.0`.

### Tests

- Added `tests/test_openapi_proxy_config.py` to prevent proxy-resolution regressions for OpenAPI paths.
- Added `tests/test_resources_specs_command.py` for the new `resources specs` command.
- Expanded `tests/test_web_session.py` coverage for `DELETE` request handling in both requests and Playwright fallback paths.
- Expanded `tests/test_cpu_compute_group_fixes.py` for CPU-only compute-group preference and selection flow stability.

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
