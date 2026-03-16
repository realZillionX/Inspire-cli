[**中文**](README.md) | English

# Inspire CLI

Command-line interface for the Inspire HPC training platform. Supports notebook instance management, distributed training job submission, code sync, SSH tunneling, image management, and more.

> 📖 **Full operational guide:** [Inspire Skill - Platform Operations Manual](https://fudan-nlp.feishu.cn/wiki/D2RXwnZcQiUQadkadJgcC1aEnLh) (Feishu, team access required)

## Installation

```bash
# Via SSH (recommended)
uv tool install git+ssh://git@github.com/realZillionX/Inspire-cli.git

# Or via HTTPS
uv tool install git+https://github.com/realZillionX/Inspire-cli.git
```

### Local Development

```bash
uv tool install -e .
inspire --help
```

---

## Quick Start

### 1. Auto-discover platform resources

```bash
inspire init --discover -u <username> --base-url https://qz.sii.edu.cn
```

This opens a browser for CAS Web SSO login, then automatically discovers your projects, workspaces, compute groups, and shared filesystem paths. It writes sensitive account data such as passwords and base URL to the global config (`~/.config/inspire/config.toml`), while project-specific resource mappings and compute-group catalogs are written to the project config (`.inspire/config.toml`).
When the account can access multiple workspaces, discovery attempts to aggregate visible projects across them. Project-local workspace mappings use the platform's actual workspace names rather than abstract aliases such as `cpu`, `gpu`, or `internet`.

Set password as an env var to avoid repeated prompts:

```bash
export INSPIRE_PASSWORD="your_password"
```

### 2. Verify configuration

```bash
inspire config show    # View all config values and their sources
inspire config check   # Validate API authentication
```

### 3. Start using

```bash
inspire resources list                          # View GPU availability
inspire notebook create --name dev -r 4CPU --wait  # Create a CPU instance
inspire notebook ssh <id>                       # SSH into instance (auto-establishes tunnel)
```

---

## Command Reference

### Configuration & Initialization

| Command                   | Description                                             |
| ------------------------- | ------------------------------------------------------- |
| `inspire init --discover` | Auto-discover projects, workspaces, compute groups      |
| `inspire init`            | Generate config from env vars (template / smart mode)   |
| `inspire config show`     | View merged config with value sources                   |
| `inspire config check`    | Validate config + API auth status                       |
| `inspire config env`      | Generate config template (`.env` format, with comments) |

### Notebook Instance Management

| Command                                      | Description                                                        |
| -------------------------------------------- | ------------------------------------------------------------------ |
| `inspire notebook list`                      | List instances in current workspace (add `-A` for all workspaces)  |
| `inspire notebook create`                    | Create instance (`--workspace`, `--resource`, `--image`, `--wait`) |
| `inspire notebook status <id>`               | View instance details                                              |
| `inspire notebook start/stop <id>`           | Start / stop instance                                              |
| `inspire notebook ssh <id>`                  | SSH into instance (auto-installs rtunnel + establishes tunnel)     |
| `inspire notebook ssh <id> --save-as <name>` | SSH and save as Bridge Profile                                     |
| `inspire notebook top`                       | Show GPU utilization for all tunneled instances (`--watch`)        |

### Training Jobs

| Command                    | Description                                              |
| -------------------------- | -------------------------------------------------------- |
| `inspire job create`       | Submit distributed training job (fine-grained control)   |
| `inspire run "<cmd>"`      | Quick submit (auto resource selection, `--sync --watch`) |
| `inspire job list`         | List locally cached jobs (shows all by default; use `--limit` to cap) |
| `inspire job status <id>`  | Query job status                                         |
| `inspire job logs <id>`    | View job logs (`--tail`, `--follow`, `--head`)           |
| `inspire job wait <id>`    | Block until job finishes                                 |
| `inspire job stop <id>`    | Stop a job                                               |
| `inspire job update`       | Refresh cached active job statuses (refreshes all active cached jobs by default) |
| `inspire job command <id>` | View the submitted command                               |

### HPC Jobs

| Command                   | Description            |
| ------------------------- | ---------------------- |
| `inspire hpc create`      | Create HPC job (Slurm) |
| `inspire hpc list`        | List HPC jobs          |
| `inspire hpc status <id>` | View HPC job details   |
| `inspire hpc stop <id>`   | Stop HPC job           |

> **Note:** `hpc create`'s `--spec-id` must use the HPC `predef_quota_id`. Prefer `inspire resources specs --usage hpc`, or extract it from `inspire --json hpc status <job_id>` → `slurm_cluster_spec.predef_quota_id`. The default `resources specs` mode is now `auto`, which prefers HPC specs; use `--usage notebook` when you explicitly want notebook/DSW quota data. `--image` must be a full docker address.

### Image Management

| Command                            | Description                                                     |
| ---------------------------------- | --------------------------------------------------------------- |
| `inspire image list`               | Browse images (`--source private/public/official/all`)          |
| `inspire image detail <id>`        | View image details                                              |
| `inspire image save <notebook_id>` | Save image from a running instance                              |
| `inspire image register`           | Register external image (`--method address` or `--method push`) |
| `inspire image delete <id>`        | Delete image                                                    |
| `inspire image set-default`        | Set default image (`--job` and/or `--notebook`)                 |

### Code Sync & Remote Operations

| Command                          | Description                                                          |
| -------------------------------- | -------------------------------------------------------------------- |
| `inspire sync`                   | Sync code to shared filesystem (SSH default, `--transport workflow`) |
| `inspire bridge exec "<cmd>"`    | Execute command on remote `INSPIRE_TARGET_DIR`                       |
| `inspire bridge ssh`             | Open interactive SSH shell                                           |
| `inspire bridge scp <src> <dst>` | Upload/download files (`-r` recursive, `-d` download direction)      |

### Tunnel Management

| Command                               | Description                       |
| ------------------------------------- | --------------------------------- |
| `inspire tunnel add <name> <url>`     | Add tunnel Profile                |
| `inspire tunnel list`                 | List all Profiles (with status)   |
| `inspire tunnel status`               | Check all Bridge SSH connectivity |
| `inspire tunnel test`                 | Test default Profile latency      |
| `inspire tunnel ssh-config --install` | Write to `~/.ssh/config`          |
| `inspire tunnel set-default <name>`   | Set default Profile               |
| `inspire tunnel remove <name>`        | Remove Profile                    |

### Resources & Projects

| Command                   | Description                          |
| ------------------------- | ------------------------------------ |
| `inspire resources list`  | View real-time compute-group availability (GPU by default, optional CPU totals) |
| `inspire resources nodes` | View full-free GPU nodes (supports cross-workspace queries) |
| `inspire resources specs` | Query compute group specs (`--json`) |
| `inspire project list`    | View projects and quotas             |

---

## Examples

```bash
# Submit a training job
inspire job create --name "train-v1" --resource "4xH200" --command "bash train.sh"

# Quick submit with auto code sync and log tracking
inspire run "python train.py --epochs 100" --sync --watch

# Sync code and verify
inspire sync && inspire bridge exec "git log -1"

# Set up SSH tunnel and save as Bridge Profile
inspire notebook ssh <notebook-id> --save-as mybridge
ssh mybridge

# Monitor GPU usage
inspire notebook top --watch

# Transfer files via Bridge
inspire bridge scp ./model.py /tmp/model.py --bridge mybridge
inspire bridge scp -d /tmp/checkpoints/ ./checkpoints/ -r --bridge mybridge

# Check GPU availability in the current workspace
inspire resources list

# Check GPU groups across all visible workspaces
inspire resources list --all

# Check GPU + CPU-only groups across all visible workspaces
inspire resources list --all --include-cpu

# Target a specific workspace explicitly
inspire resources list --workspace-name 分布式训练空间

# Check full-free 8-GPU nodes across workspaces
inspire resources nodes --all

inspire project list

# Query default specs (auto: prefer HPC, fall back to notebook)
inspire resources specs --workspace CPU资源空间 --group CPU资源-2 --json

# Query HPC specs
inspire resources specs --workspace CPU资源空间 --group HPC-可上网区资源-2 --usage hpc --json

# Query notebook/DSW specs
inspire resources specs --workspace CPU资源空间 --group CPU资源-2 --usage notebook --json
```

---

## Configuration

### Layered Config Model

Config is loaded in priority order (later overrides earlier):

1. **Global config**: `~/.config/inspire/config.toml`
2. **Project config**: `./.inspire/config.toml`
3. **Environment variables**

Use `inspire init --discover` for auto-generation, or `inspire config show` to inspect the merged result. In the default split, global config stores account-level secrets and project config stores resource mappings and defaults.
You can override the default global config location with `INSPIRE_GLOBAL_CONFIG_PATH`.

Legacy `[auth].password` is still supported, but `[accounts."<username>"].password` takes precedence when both are present.

### Multi-account Support

Configure passwords for different accounts in TOML:

```toml
[accounts."username_a"]
password = "password_a"

[accounts."username_b"]
password = "password_b"
```

Lookup order: `[accounts."<username>"].password` (global → project) → `INSPIRE_PASSWORD` (fallback).

### Example Config

```toml
[auth]
username = "your_username"

[api]
base_url = "https://qz.sii.edu.cn"
force_proxy = true

[proxy]
# Proxy config is optional. Skip this section if your network can reach *.sii.edu.cn directly.
# requests_http = "http://127.0.0.1:7897"
# requests_https = "http://127.0.0.1:7897"
# playwright = "http://127.0.0.1:7897"
# rtunnel = "http://127.0.0.1:7897"

[workspaces]
# Project-local workspace mappings using the platform's actual names.
"CPU资源空间" = "ws-..."
"分布式训练空间" = "ws-..."
"可上网GPU资源" = "ws-..."

[[compute_groups]]
# Project-local compute-group catalog discovered for this repo.
name = "H100 Cluster"
id = "lcg-..."
gpu_type = "H100"

[bridge]
action_timeout = 600

[ssh]
# rtunnel_bin = "/inspire/shared/tools/rtunnel"
# apt_mirror_url = "http://nexus.example.com/repository/ubuntu/"
# rtunnel_upload_policy = "auto"  # auto | never | always
```

---

## Proxy Configuration

### Proxy is Optional

If your network can reach `*.sii.edu.cn` directly (e.g., campus network), **no proxy configuration is needed** — the CLI connects directly.

### When Proxy is Needed

Use the local `Clash Verge` / `verge-mihomo` `7897` mixed port. Domain rules send `*.sii.edu.cn` to `Sii-Proxy`, while public traffic reuses the same local entrypoint:

```toml
[proxy]
requests_http = "http://127.0.0.1:7897"    # Clash Verge mixed port
requests_https = "http://127.0.0.1:7897"
playwright = "http://127.0.0.1:7897"
rtunnel = "http://127.0.0.1:7897"
```

If a tool only supports `SOCKS5`, switch to `socks5://127.0.0.1:7897`; the local entrypoint is still the same `7897` mixed port.

### Proxy Precedence

1. Explicit env vars (`INSPIRE_*_PROXY`)
2. TOML `[proxy]` values
3. System `http_proxy` / `https_proxy`

### Auto Split-routing

`Clash Verge` now handles domain-based routing on `7897`; the CLI no longer carries legacy compatibility or auto-rewrites for local `1080/8888` ports.

---

## Environment Variables

### Core

| Variable              | Description                  | Default     |
| --------------------- | ---------------------------- | ----------- |
| `INSPIRE_USERNAME`    | Platform username            | —           |
| `INSPIRE_PASSWORD`    | Platform password (fallback) | —           |
| `INSPIRE_BASE_URL`    | API base URL                 | From config |
| `INSPIRE_FORCE_PROXY` | Force OpenAPI through proxy  | `false`     |
| `INSPIRE_GLOBAL_CONFIG_PATH` | Override global config path | —      |
| `INSPIRE_TARGET_DIR`  | Bridge shared directory path | —           |

### Proxy

| Variable                       | Description                  |
| ------------------------------ | ---------------------------- |
| `INSPIRE_REQUESTS_HTTP_PROXY`  | HTTP proxy for OpenAPI       |
| `INSPIRE_REQUESTS_HTTPS_PROXY` | HTTPS proxy for OpenAPI      |
| `INSPIRE_PLAYWRIGHT_PROXY`     | Proxy for browser automation |
| `INSPIRE_RTUNNEL_PROXY`        | Proxy for SSH tunneling      |
| `INSPIRE_RTUNNEL_UPLOAD_POLICY` | Rtunnel upload fallback policy: `auto`, `never`, or `always` |

### Workspaces & Projects

| Variable                        | Description                |
| ------------------------------- | -------------------------- |
| `INSPIRE_PROJECT_ID`            | Default project ID         |
| `INSPIRE_WORKSPACE_CPU_ID`      | CPU workspace ID           |
| `INSPIRE_WORKSPACE_GPU_ID`      | GPU workspace ID           |
| `INSPIRE_WORKSPACE_INTERNET_ID` | Internet-enabled workspace |

### Jobs & Notebooks

| Variable                    | Description               | Default  |
| --------------------------- | ------------------------- | -------- |
| `INSP_IMAGE`                | Default image             | —        |
| `INSP_PRIORITY`             | Default priority (1-10)   | `10`     |
| `INSPIRE_NOTEBOOK_RESOURCE` | Default notebook resource | `1xH200` |
| `INSPIRE_NOTEBOOK_POST_START` | Default notebook post-start action | — |

### Debugging

| Variable                    | Description                         |
| --------------------------- | ----------------------------------- |
| `INSPIRE_DEBUG_LOG_DIR`     | Directory for `inspire --debug` logs |
| `INSPIRE_RTUNNEL_TIMING`    | Emit per-step rtunnel timing         |

---

## SSH / Tunnel Mechanics

### Key Points

- **There is no `inspire tunnel start` command.** Create or refresh Profiles with `inspire notebook ssh <id> --save-as <name>`.
- **`allow_ssh=false` is the platform default.** SSH requires `sshd` + `rtunnel` pre-installed in the container — connection failure typically means the image lacks the SSH toolchain.
- On first bootstrap, `notebook ssh` opens JupyterLab, prefers uploading `rtunnel` via Jupyter Contents API, then dispatches the setup script via terminal REST API + terminal WebSocket. Only if that path fails does it fall back to Playwright terminal automation. The terminal WebSocket path now waits for an explicit remote completion marker before starting rtunnel / SSH readiness checks, so "command accepted" is no longer treated as "bootstrap finished". If `/tmp/rtunnel`, `sshd`, or `dropbear` is still missing in the container, continue with the manual Web-terminal install flow.
- If the notebook already has the same `rtunnel` binary, the CLI now reuses it through a `.sha256` sidecar check instead of uploading again. To force or disable the upload fallback explicitly, use `--rtunnel-upload-policy auto|never|always` or set `ssh.rtunnel_upload_policy`.
- On non-`Linux` hosts, the default `auto` policy no longer uploads `~/.local/bin/rtunnel` blindly to the notebook. If no explicitly remote-compatible binary is configured, the CLI skips that bad fallback and lets the container download the Linux build itself.
- For offline notebooks, once the flow is using uploaded binaries or dropbear/apt-mirror bootstrap, the CLI skips doomed `curl` download fallbacks.
- Images saved from instances with SSH installed will retain sshd — no need to reinstall.
- `bridge exec` and `bridge ssh` auto-reconnect dropped tunnels for notebook-backed Profiles; `bridge scp` only checks availability without rebuilding.
- rtunnel install script uses dynamic platform detection (`uname -s/-m`), independent of local host architecture.
- `inspire --debug` writes a redacted debug report under `~/.cache/inspire-cli/logs/`, which is useful for tracing upload, terminal, and proxy failures.

### Manual SSH Setup

```bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq openssh-server
curl -fsSL "https://github.com/Sarfflow/rtunnel/releases/download/nightly/rtunnel-linux-amd64.tar.gz" \
  -o /tmp/rtunnel.tgz && tar -xzf /tmp/rtunnel.tgz -C /tmp && chmod +x /tmp/rtunnel
mkdir -p /run/sshd && ssh-keygen -A >/dev/null 2>&1
/usr/sbin/sshd -p 22222 -o ListenAddress=127.0.0.1 -o PermitRootLogin=yes \
  -o PasswordAuthentication=no -o PubkeyAuthentication=yes
nohup /tmp/rtunnel 22222 31337 >/tmp/rtunnel-server.log 2>&1 &
```

---

## HPC Job Notes

- `--spec-id` must use the HPC `predef_quota_id`. Prefer `inspire resources specs --usage hpc`, or read it from `inspire --json hpc status <job_id>` → `slurm_cluster_spec.predef_quota_id`.
- `inspire resources specs` now defaults to `auto`: it prefers HPC `predef_node_specs` and falls back to notebook/DSW quotas only when no HPC spec exists.
- Use `--usage notebook` when you explicitly want notebook/DSW quota data.
- `--image` must be a full docker address (e.g., `docker.sii.shaipower.online/inspire-studio/<name>:<version>`).
- `memory_per_cpu` is sent as a string with `G` suffix; `cpus_per_task` as a string — matching OpenAPI spec.
- Built-in exponential backoff retry on `429 Too Many Requests`.

---

## Authentication

Three independent auth chains (cannot substitute for each other):

1. **OpenAPI**: Bearer Token (`POST /auth/token`) — for `job`/`run`/`hpc`/`config check`.
2. **Web SSO**: Browser CAS Cookie Session — for `notebook`/`image`/`resources`/`project`.
3. **Git Platform**: GitHub/Gitea Token — for `job logs`/`sync --transport workflow`.

`config check` passing does not guarantee Web Session or Git Platform are functional.

---

## Exit Codes

| Code | Meaning                    |
| ---- | -------------------------- |
| `0`  | Success                    |
| `1`  | General error              |
| `10` | Config error               |
| `11` | Auth failure               |
| `12` | Parameter validation error |
| `13` | API error (incl. 429)      |
| `14` | Timeout                    |
| `15` | Log not found              |
| `16` | Job not found              |

---

## Development & Contributing

```bash
# Set up dev environment
uv venv .venv && uv pip install -e .

# Run tests
uv run python -m pytest tests/ -x -q

# Format code
uv tool run black .

# Lint
uv run ruff check inspire tests
```

Commit convention: use [Conventional Commits](https://www.conventionalcommits.org/) prefixes (`feat:`, `fix:`, `docs:`, `chore:`).

---

## License

See [LICENSE](LICENSE) file.
