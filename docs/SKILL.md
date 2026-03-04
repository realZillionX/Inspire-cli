---
name: inspire
description: "Execution-first Inspire platform playbook for agents using Inspire-cli as a black-box tool, with reproducible setup, notebook/image/bridge/tunnel/sync workflows, job and HPC operations, proxy routing, and failure recovery."
---

# Inspire Skill

> **定位。** 本文是使用 `inspire-cli` 完成启智平台全流程（从本地代码开发到多节点训练）的详细说明书。Agent 可将 `inspire-cli` 作为黑盒工具直接使用，无需查阅仓库源码。

---

## 0. 固定前提

主仓库路径固定为 `/Users/zillionx/.codex/skills/inspire/Inspire-cli`。CLI 入口优先使用全局 `inspire`；需锁定仓库版本时用 `cd /Users/zillionx/.codex/skills/inspire/Inspire-cli && uv run inspire`。默认项目为 `CI-情境智能-探索课题`。代理分流规则：`*.sii.edu.cn` 走 `8888`（HTTP）或 `1080`（SOCKS5），公网走 `7897`。启智链路异常时第一步向用户确认 `aTrust` 登录状态。CPU 资源空间下 `CPU资源-2` 无公网、`HPC-可上网区资源-2` 有公网——首次 SSH 配置需联网，必须用后者。当前基础镜像为 `codex-skill-20260304-base:v1`（含 sshd，已设为默认）。**资源调用不要保守**——启智算力充足，可调用上千张 CPU、数百张 H100/H200，按实际需求选择规格即可，不必刻意选小。

---

## 1. 初始化与配置

### 1.1 自动发现与验证

首次使用推荐运行 `inspire init --discover -u <username> --base-url https://qz.sii.edu.cn`，该命令会拉起浏览器完成 CAS Web SSO 登录，自动写入 workspace、project、compute group 元数据到 `~/.config/inspire/config.toml`（全局）和 `./.inspire/config.toml`（项目级）。设置 `export INSPIRE_PASSWORD='<password>'` 可避免重复输入。如需探测共享路径，加 `--probe-shared-path`（可配合 `--probe-limit`、`--probe-timeout`、`--probe-pubkey`）。已知配置场景可直接使用 `inspire init --project --force` 快速生成项目配置，再用 `inspire config env --output .env.inspire.generated` 导出。

初始化完成后，依次验证四个关键步骤：`inspire config check --json`（确认 `auth_ok=true`）→ `inspire config show`（确认 proxy、workspace 来源正确）→ `inspire project list --json`（确认可见目标项目）→ `inspire resources specs --workspace cpu --group CPU资源-2 --json`（确认返回 `logic_compute_group_id` 与 `spec_id`）。最后确认 `INSPIRE_TARGET_DIR` 已配置（`sync` 和 `bridge exec` 都依赖它）。

### 1.2 分层配置模型

配置优先级为 `Defaults < Global TOML (~/.config/inspire/config.toml) < Project TOML (./.inspire/config.toml) < Environment variables`。代理优先级为 `INSPIRE_*_PROXY` env vars → TOML `[proxy]` → 系统 `http_proxy`/`https_proxy`。设置 `INSPIRE_FORCE_PROXY=true` 可强制 OpenAPI 走代理，避免被系统 `no_proxy` 绕过。Playwright 与 rtunnel 使用各自代理配置，不与 OpenAPI 自动混用；但当 `requests_http` 解析到 `http://127.0.0.1:8888`（`.sii.edu.cn`），Playwright 和 rtunnel 会自动降级到 `socks5://127.0.0.1:1080`。

**多账号支持：** 在 TOML 中用 `[accounts."username"].password` 为不同账号配置密码，global 和 project 级均可。密码查找顺序：`[accounts."<username>"].password`（global → project）→ `INSPIRE_PASSWORD`（兜底）。

#### 配置文件示例

```toml
[api]
base_url = "https://qz.sii.edu.cn"
force_proxy = true
docker_registry = "qz.sii.edu.cn"

[auth]
username = "<your_username>"

[proxy]
requests_http = "http://127.0.0.1:8888"
requests_https = "http://127.0.0.1:8888"
playwright = "socks5://127.0.0.1:1080"
rtunnel = "socks5://127.0.0.1:1080"

[workspaces]
cpu = "ws-..."
gpu = "ws-..."
internet = "ws-..."

[[compute_groups]]
name = "H100 Cluster"
id = "lcg-..."
gpu_type = "H100"

[ssh]
# rtunnel_bin = "/inspire/shared/tools/rtunnel"
# apt_mirror_url = "http://nexus.example.com/repository/ubuntu/"
# dropbear_deb_dir = "/inspire/shared/debs/dropbear"

[bridge]
action_timeout = 600
```

---

## 2. CLI 命令速查表

| 命令组 | 子命令 | 说明 | `--json` |
|---|---|---|---|
| `config` | `show`/`check`/`env` | 查看配置、认证检查、导出 env。 | `check` 支持 |
| `init` | `--discover`/普通 | 初始化与资源发现。 | 支持 |
| `project` | `list` | 项目与配额。 | 支持 |
| `resources` | `list`/`nodes`/`specs` | 可用性、节点状态、规格发现。 | 仅 `specs` 支持 |
| `notebook` | `list`/`create`/`status`/`start`/`stop`/`ssh`/`top` | 交互式实例全生命周期管理。 | `list`/`create`/`status` 支持 |
| `image` | `list`/`detail`/`save`/`register`/`delete`/`set-default` | 镜像查询、构建、注册、删除、默认值写入。 | `list`/`detail`/`save`/`register`/`delete` 支持 |
| `bridge` | `exec`/`ssh`/`scp` | 远程命令执行与文件传输（需活跃 tunnel 且已配置 `INSPIRE_TARGET_DIR`）。 | 否 |
| `tunnel` | `add`/`update`/`remove`/`list`/`status`/`set-default`/`ssh-config`/`test` | SSH Profile 管理，`remove` 无 `--force`。 | 否 |
| `sync` | 单命令 | 代码同步到 Bridge 共享目录，`--transport ssh\|workflow`。 | 否 |
| `job` | `create`/`status`/`logs`/`list`/`stop`/`wait`/`update`/`command` | 分布式训练任务完整管理，`logs` 需 Gitea/GitHub 配置。 | `create` 支持 |
| `run` | 快速提交 | 快速任务提交，支持 `--sync --watch`。 | 否 |
| `hpc` | `create`/`status`/`list`/`stop` | HPC 任务链路（OpenAPI，可用），`create` 必须指定 `--project`、`--image`（完整 docker 地址）、`--logic-compute-group-id`、`--spec-id`（实为 `quota_id`）。平台有 APISIX 网关速率限制，密集调用可能触发 429。 | `status` 支持（全局 `--json`） |

#### 实测修正备忘

1. `image set-default` 必须使用 `--job` 和/或 `--notebook`，无位置参数。`image list --source private` 对应网页"个人可见镜像"，`--source my-private` 是旧语义兼容通道（直查 `SOURCE_PRIVATE`），`--source all` 聚合四源按 `image_id` 去重。
2. `tunnel remove` 不支持 `--force`。`bridge exec` 不再支持 `--no-tunnel`。`sync` 不再支持 `--via-action`，改用 `--transport workflow`。
3. `hpc list` 和 `resources nodes` 均不支持 `--json`。`hpc create` 的 `--image` 必须用完整 docker 地址（如 `docker.sii.shaipower.online/inspire-studio/<name>:<version>`），不能仅用镜像名。`hpc create` 的 `--spec-id` 必须用 `quota_id`（从已有 HPC 任务 detail 获取），`resources specs` 返回的 `spec_id` **不适用于 HPC**。
4. `bridge exec` 必须先配置 `INSPIRE_TARGET_DIR`。`notebook list` 支持 `--all-workspaces`（`-A`）跨所有工作空间列出实例。
5. `hpc list` 显示**所有用户**的 HPC 任务（非仅当前用户），`hpc status` 查询他人任务返回 "No permission"。Web UI 默认只显示当前用户的任务。
6. 全局 `--json` 标志位置必须在子命令**之前**：`inspire --json hpc status <id>`（✅），`inspire hpc status --json <id>`（❌）。
7. `image save` 返回的 `image_id` 可能为空——保存成功后用 `image list --source private` 确认实际镜像 ID 和地址。

---

## 3. 开发主流程

> **术语澄清**："分布式训练空间"是工作空间名称，"分布式训练任务"是任务类型（`job create`/`run`），`hpc create` 是另一条任务链路，不等于 `job create`。

### 代码同步（贯穿全流程）

代码同步**不是一次性动作**，而是贯穿开发—调试—训练整个迭代循环的核心操作。典型闭环：本地改代码 → `inspire sync` → `notebook ssh`/`bridge exec` 在实例上调试 → 查看 `job logs`/`job status` 获取反馈 → 回到本地修复 → 再次 `inspire sync`。

**推荐同步路径：** `inspire sync && inspire bridge exec "cd $INSPIRE_TARGET_DIR && git log -1"` 验证同步结果。脏工作区场景使用 `inspire sync --allow-dirty --no-push --source bundle --force` 保守同步。文件级传输使用 `inspire bridge scp ./local.txt /tmp/local.txt`（上传）、`inspire bridge scp -d /tmp/remote.txt ./remote.txt`（下载），加 `-r` 传输目录。安装 `inspire tunnel ssh-config --install` 后可直接使用原生 `scp`/`rsync` 命令。

> **前提。** `sync` 和 `bridge` 命令需要：(1) 已配置 `INSPIRE_TARGET_DIR`；(2) 存在活跃的 SSH tunnel（通过 `inspire notebook ssh --save-as` 或 `inspire tunnel add` 创建）。**SSH 是整个交互式调试流程的核心**，因此阶段 A 中必须确保镜像支持 SSH。

### 阶段 A：CPU 资源空间做容器环境配置

在 CPU 资源空间创建配置实例、安装依赖、**配置 SSH 工具链**后保存基础镜像。CPU 资源空间下有两个计算组：**`CPU资源-2`（无公网）** 和 **`HPC-可上网区资源-2`（有公网）**。首次容器配置必须使用 `HPC-可上网区资源-2`，因为安装 sshd 和下载 rtunnel 需要公网。（`CPU资源` 与 `HPC-可上网区资源` 可能无可用规格，不建议使用。）

> **SSH 前提（关键）。** `allow_ssh=false` 是该平台**所有实例的默认状态**（与镜像类型无关）。SSH 连接需要在容器内手动安装 `openssh-server` 和 `rtunnel`——`notebook ssh` 会通过 Jupyter WebSocket 注入安装脚本，但**此注入机制可能静默失败**。如果 `notebook ssh` 失败（ECONNREFUSED），必须在容器 Web 终端手动安装 SSH 工具链（见下方步骤 3）。从已安装 SSH 工具链的实例保存出的自定义镜像**会保留 sshd**，后续实例无需重复安装。

```bash
# 1. 查看可用规格（必须用 HPC-可上网区资源-2 以获取公网）。
inspire resources specs --workspace cpu --group HPC-可上网区资源-2 --json

# 2. 创建 CPU 实例。
inspire notebook create \
  --workspace cpu --resource 4CPU \
  --name <action-goal-name> \
  --image ubuntu-inspire-base:22.04 \
  --project CI-情境智能-探索课题 --wait --json

# 3. 尝试 SSH 连接；若失败则手动安装 SSH 工具链。
inspire notebook ssh <notebook_id> --command "echo ssh-ok"
# 若报 ECONNREFUSED，在容器 Web 终端执行：
#   export DEBIAN_FRONTEND=noninteractive
#   apt-get update -qq && apt-get install -y -qq openssh-server
#   curl -fsSL "https://github.com/Sarfflow/rtunnel/releases/download/nightly/rtunnel-linux-amd64.tar.gz" \
#     -o /tmp/rtunnel.tgz && tar -xzf /tmp/rtunnel.tgz -C /tmp && chmod +x /tmp/rtunnel
#   mkdir -p /run/sshd && ssh-keygen -A >/dev/null 2>&1
#   /usr/sbin/sshd -p 22222 -o ListenAddress=127.0.0.1 -o PermitRootLogin=yes \
#     -o PasswordAuthentication=no -o PubkeyAuthentication=yes
#   nohup /tmp/rtunnel 22222 31337 >/tmp/rtunnel-server.log 2>&1 &
# 然后重试：
#   inspire notebook ssh <notebook_id> --command "echo ssh-ok"

# 4. SSH 连通后保存 Bridge Profile。
inspire notebook ssh <notebook_id> --save-as cpu-bridge

# 5. 安装项目依赖后，保存为基础镜像（保留 sshd + rtunnel）。
inspire image save <notebook_id> -n <action-goal-name>-base -v v1 --json

# 6. 写入默认镜像配置（后续 job/notebook 均使用此镜像）。
inspire image set-default \
  --job docker.sii.shaipower.online/inspire-studio/<action-goal-name>-base:v1 \
  --notebook docker.sii.shaipower.online/inspire-studio/<action-goal-name>-base:v1
```

> **已建立的基础镜像。** 当前基础镜像为 `codex-skill-20260304-base:v1`（从 `container-config` 实例保存，原始镜像 `dhyu-wan-torch29:0.6`，已预装 `openssh-server`）。已通过 `image set-default` 设为 `.inspire/config.toml` 中 `job.image` 和 `notebook.image` 的默认值。后续创建的实例将自动使用此镜像，仅需下载 rtunnel 即可启用 SSH（sshd 已持久化在镜像中）。

### 阶段 B：CPU 资源做高性能数据处理

用 CPU 分组承载大规模预处理，避免挤占 GPU 主训练资源。**注意**：HPC 的 `--spec-id` 和 notebook 的 `spec_id` **不通用**。HPC 使用的是 `quota_id`，可从已有 HPC 任务的 detail 中获取（`inspire --json hpc status <job_id>` → `slurm_cluster_spec.predef_quota_id` 或 `resource_spec_price.quota_id`）。`--image` 必须使用完整 docker 地址（`docker.sii.shaipower.online/inspire-studio/<name>:<version>`），不能仅用镜像名。`--memory-per-cpu` 的值带单位后缀（如 `4` 会自动补 `G`）。

```bash
inspire hpc create \
  -n <action-goal-name>-hpc-preprocess \
  -c 'bash -lc "python preprocess.py"' \
  --logic-compute-group-id <logic_compute_group_id> \
  --spec-id <quota_id> \
  --workspace cpu \
  --cpus-per-task <cpu_count> --memory-per-cpu <memory_gib> \
  --number-of-tasks 1 --instance-count 1 \
  --project CI-情境智能-探索课题 \
  --image docker.sii.shaipower.online/inspire-studio/<image_name>:<version> \
  --image-type SOURCE_PRIVATE
```

> **已验证的 HPC 参数。**
> | 计算组 | `logic_compute_group_id` | `quota_id`（即 `spec_id`） | 配置 |
> |--------|--------------------------|---------------------------|------|
> | CPU资源-2 | `lcg-d4b51af1-2168-4ee2-920f-4fc50e2aeb69` | `e8da6721-d6b2-43ec-a23b-5406b2d1e7a2` | 120 CPU / 500GiB |
> | HPC-可上网区资源-2 | `lcg-cb2de75c-40ac-4de1-bbb3-11e62b32f424` | `f74b36bc-0c26-4878-beb9-14f4f035834c` | 55 CPU / 500GiB |

`hpc create` 的必填参数包括 `-n`、`-c`、`--logic-compute-group-id`、`--spec-id`、`--cpus-per-task`、`--memory-per-cpu`，以及 `--project`（或 `INSPIRE_PROJECT_ID`）和 `--image`（完整 docker 地址），缺少任何一个会报 `exit code 10`。提交后用 `inspire hpc list --workspace cpu` 查看状态，`inspire hpc status <job_id>` 查看详情，`inspire hpc stop <job_id>` 停止任务。遇到 `429 Too Many Requests` 时 CLI 已内置退避重试；持续 429 是平台级 OpenAPI 频控（APISIX 网关），等待数分钟后重试。

### 阶段 C：可上网 GPU 资源区

可上网 GPU 区适合临时评估与联网依赖拉取，主训练不建议长期绑定该区，CPU 运维任务不要占用可上网 GPU 规格。

### 阶段 D：分布式训练空间执行主训练

**D-1 单节点交互式调试：** 使用 `inspire notebook create --workspace gpu --resource 1xH100 --name <action-goal-name>-gpu-debug --project CI-情境智能-探索课题 --wait --json` 创建实例，然后 `inspire notebook ssh <notebook_id> --command "nvidia-smi"` 验证 GPU 可见性。**SSH 连接后直接操控实例终端**是单节点调试的核心方式——`inspire notebook ssh <notebook_id>` 打开交互式 shell，在远端执行训练脚本、查看日志、调参。

**D-2 多节点分布式训练任务提交：** 使用 `job create` 精细控制或 `run` 快速提交：

```bash
# 方式一：job create（精细控制）。
inspire job create -n <action-goal-name>-train -r 8xH100 --nodes 2 \
  -c 'bash train.sh' --workspace gpu \
  --location 'cuda12.8版本H100' --image '<image_ref>'

# 方式二：run（快速提交，自动选资源）。
inspire run 'bash train.sh' --gpus 8 --type h100 --nodes 2 \
  --workspace gpu --location 'cuda12.8版本H100' \
  --image '<image_ref>' --sync --watch
```

**D-3 迭代调试闭环：** 分布式训练的核心循环是 **本地改代码 → `inspire sync` → 提交任务/SSH 调试 → 获取反馈 → 回到本地修复**。单节点场景下通过 `inspire notebook ssh` 交互式调试；多节点场景下通过 `inspire job status`/`job logs` 获取结果反馈。具体命令：`inspire job list` 列出本地缓存的作业，`inspire job status <job_id>` 查询状态，`inspire job command <job_id>` 查看提交时的命令，`inspire job update` 刷新缓存中活跃作业状态（可加 `--status RUNNING --limit 5` 限定范围），`inspire job logs <job_id> --tail 100` 查看日志尾部（支持 `--follow` 持续追踪、`--head` 查看头部、`--path` 仅输出日志路径、`--refresh` 强制重拉），`inspire job wait <job_id> --timeout 7200` 阻塞等待作业结束，`inspire job stop <job_id>` 停止作业。

> **`job logs` 前提。** `job logs` 通过 Gitea/GitHub workflow 拉取日志，需要在 TOML 中配置 `[gitea]` 块（含 `server`、`repo`、`token`）或对应的 `INSP_GITEA_*` 环境变量。若未配置，会报 `Missing INSPIRE_USERNAME` 或无法拉取日志，此时改用 `job status` + 平台 Web UI 查看日志。

---

## 4. Notebook 生命周期管理

**创建与连接：** `inspire notebook create -n <action-goal-name>-nb --workspace gpu -r 1xH100 --wait` 创建实例。**推荐使用阶段 A 中已预装 sshd+rtunnel 的自定义镜像**，这样 SSH 无需重复配置。`inspire notebook ssh <notebook_id>` 启动交互式 SSH（打开远端终端，可直接执行命令、调试代码）；加 `--save-as <bridge-name>` 将当前 tunnel 保存为 Bridge Profile（后续可用 `ssh <bridge-name>` 直连）；加 `--command "echo ok"` 远程执行单条命令。

**状态管理：** `inspire notebook list` 列出当前工作空间实例，加 `--all-workspaces`（`-A`）跨全部工作空间列出，支持 `-s RUNNING` 按状态过滤、`--name container-config` 按关键字搜索。`inspire notebook status <notebook_id> --json` 查看详情，`inspire notebook stop/start <notebook_id>` 停止/启动实例。**注意 JSON 结构**：实例的镜像信息在嵌套的 `image` 对象中（`image.name`、`image.address`、`image.version`），而**非**顶级的 `image_name`/`image_address` 字段（这些通常为空）。SSH 相关字段在 `start_config.allow_ssh`。

**GPU 监控：** `inspire notebook top` 展示所有 tunnel-backed 实例的 GPU 利用率与显存概览，加 `--watch` 持续监控，加 `-b <bridge_name>` 指定单个 Bridge。若某 Bridge 的 SSH 不响应，对应条目会显示 `error SSH tunnel is not responding`，但不影响其他正常 Bridge 的采集。也可通过 `inspire notebook ssh <notebook_id> --command "watch -n 5 nvidia-smi"` 直接在实例内监控。

**SSH/rtunnel 机制要点：** 没有 `inspire tunnel start` 命令，通过 `inspire notebook ssh <id> --save-as <name>` 创建或刷新 Profile。`allow_ssh=false` 是该平台**所有实例的默认状态**（与镜像无关），SSH 需要容器内预装 sshd + rtunnel（参见阶段 A）。**SSH 失败时应在容器 Web 终端手动安装工具链，而非更换镜像。** `bridge exec`/`ssh`/`scp` 在 notebook-backed Profile 上会按 `tunnel.retries`/`tunnel.retry_pause` 配置自动重连；非 notebook 的手动 Profile 无法自动重建。对同一 `--save-as` 名称重复执行会自动刷新已有 Profile 的 tunnel 状态。

---

## 5. Image 管理

**镜像三分类：** 启智平台的镜像分为三类——**官方镜像**（`--source official`，平台预置，如 `ubuntu-inspire-base:22.04`、`pytorch-inspire-base:*`）、**个人可见镜像**（`--source private`，用户通过 `image save`/`register` 创建的私有镜像）、**公开可见镜像**（`--source public`，其他用户公开的镜像，如 `dhyu-wan-torch29:0.6`）。创建实例或提交任务时需显式指定 `--image-type`：使用个人可见镜像时为 `SOURCE_PRIVATE`，使用官方或公开镜像时为 `SOURCE_PUBLIC`。

**镜像查询：** `--source my-private` 是旧语义兼容通道（直查 `SOURCE_PRIVATE`），`--source all` 聚合四源按 `image_id` 去重。如果 UI 可见但 CLI 找不到，依次试 `private` → `my-private` → `all`。

**保存与注册：** 从正在运行的实例保存镜像用 `inspire image save <notebook_id> -n <name> -v <version> --json`。注册外部镜像有两种模式：`--method address`（推荐，直接注册已存在于 registry 的镜像地址）和 `--method push`（创建占位 → 从输出的 `address` 字段获取 registry URL → 本地 `docker tag` + `docker push` → 平台检测到推送后标记 READY）。push 失败时优先切 `--method address` 验证链路。

**详情与默认镜像：** `inspire image detail <image_id> --json` 查看详情。`inspire image set-default --job <image_ref> --notebook <image_ref>` 将镜像写入 `.inspire/config.toml` 作为默认值。注意 `set-default` 必须用 `--job` 和/或 `--notebook` 指定，无位置参数。

**删除镜像：** `inspire image delete <image_id> --force --json`，成功返回 `"status": "deleted"`，提示不存在可按幂等删除处理。

---

## 6. Bridge/Tunnel/Sync

### Bridge：远程命令执行与文件传输

`bridge exec` 远程执行命令（在 `INSPIRE_TARGET_DIR` 下运行），`bridge ssh` 打开交互式 SSH shell，`bridge scp` 传输文件。三者均需活跃的 SSH tunnel，`bridge exec` 还必须先配置 `INSPIRE_TARGET_DIR`。`bridge exec` 默认走 SSH tunnel，仅在请求 `--artifact-path`/`--download` 时触发 workflow 兜底。常用命令：

```bash
inspire bridge exec "hostname"                                      # 远程执行
inspire bridge exec "cd $INSPIRE_TARGET_DIR && git status -s"        # 在目标目录执行
inspire bridge exec "pip install torch" --timeout 600 --bridge gpu   # 自定义超时和 Bridge
inspire bridge ssh --bridge <bridge_name>                            # 交互式 SSH
inspire bridge scp ./local.txt /tmp/local.txt                        # 上传文件
inspire bridge scp -d /tmp/remote.txt ./remote.txt                   # 下载文件
inspire bridge scp -r ./src/ /tmp/src/ --bridge <bridge_name>        # 递归上传目录
```

### Tunnel：SSH 隧道管理

`inspire tunnel add <name> <url>` 添加 Profile，`tunnel update <name> --ssh-user root` 更新，`tunnel set-default <name>` 设为默认，`tunnel list` 列出所有 Profile（含连通状态标签），`tunnel status` 检查所有 Bridge 的 SSH 连通性并输出诊断信息，`tunnel test` 测试默认 Profile 的 SSH 连接并显示延迟（加 `-b <name>` 测指定 Profile），`tunnel ssh-config --install` 将所有 Bridge 写入 `~/.ssh/config`（`ProxyCommand` 自动 shell-quote，执行前建议备份），`tunnel remove <name>` 删除 Profile（无 `--force` 选项）。

### Sync：代码同步

`inspire sync` 默认使用 SSH tunnel 同步代码。`--transport workflow` 切换为 Workflow 同步（不依赖 tunnel，适合 `allow_ssh=false` 场景）。`--source auto|remote|bundle` 控制 SSH 下同步源（`auto` 有网用 remote、无网用 bundle），`--push-mode required|best-effort|skip` 控制 `git push` 策略，`--allow-dirty` 允许脏工作区（同步已提交 HEAD），`--no-push` 等同 `--push-mode skip`，`--force` 开启强制模式（含 `--allow-dirty`，默认 best-effort push，SSH 下 hard-reset 分歧分支）。经典保守同步：`inspire sync --allow-dirty --no-push --source bundle --force`。

---

## 7. 调度与存储策略

**调度与抢占：** 高优任务保障更强但更依赖配额，低优任务更容易被抢占但适合可断点恢复任务（必须高频写 checkpoint）。若长时间排队，可切低优任务尝试"见缝插针"。

**存储规范：** 代码与轻量配置放个人目录，数据集、权重、checkpoint 放公共目录。`INSPIRE_TARGET_DIR` 使用团队统一路径，便于 `sync` 与日志链路协同。

---

## 8. 认证与 API

**三条认证链路独立，不可互相代证：** (1) **OpenAPI**（`POST /auth/token` 获取 Bearer Token，端点 `/openapi/v1/...`，用于 `job`/`run`/`hpc`/`config check`）；(2) **Web SSO**（浏览器 CAS Cookie Session，端点 `/api/v1/...`，用于 `notebook`/`image`/`resources`/`project`）；(3) **Git Platform**（Gitea/GitHub Token，用于 `job logs`/`sync --transport workflow`/`bridge exec` workflow 兜底）。`config check` 通过不代表 Web Session 或 Git Platform 链路一定可用。

**OpenAPI 端点速查：** Token 获取 `POST /auth/token`；训练任务 `POST /openapi/v1/train_job/{create,detail,stop}`；HPC 任务 `POST /openapi/v1/hpc_jobs/{create,detail,stop}`。

**常见错误码：** `429`（频控限流，30/60/120 秒退避重试）、`-100000`/`400`（参数校验错误，检查 `spec_id`/`workspace`/镜像）、`500`（服务端错误，保留上下文后重试）。

---

## 9. 代理分流与快速验证

启智链路（`*.sii.edu.cn`）使用如下环境变量：`INSPIRE_BASE_URL='https://qz.sii.edu.cn'`、`INSPIRE_USERNAME`/`INSPIRE_PASSWORD`、`INSPIRE_REQUESTS_HTTP_PROXY='http://127.0.0.1:8888'`、`INSPIRE_REQUESTS_HTTPS_PROXY='http://127.0.0.1:8888'`、`INSPIRE_PLAYWRIGHT_PROXY='socks5://127.0.0.1:1080'`、`INSPIRE_RTUNNEL_PROXY='socks5://127.0.0.1:1080'`、`INSPIRE_FORCE_PROXY='true'`。公网链路（与启智链路分开使用）设 `http_proxy`/`https_proxy` 为 `http://127.0.0.1:7897`。不要在同一上下文混用两条链路。本地代理协议不要写 `https://127.0.0.1:<port>`。

**快速验证：** `curl -I --proxy http://127.0.0.1:8888 https://qz.sii.edu.cn/login`（启智 HTTP 代理）、`curl -I --socks5-hostname 127.0.0.1:1080 https://qz.sii.edu.cn/login`（启智 SOCKS5 代理）、`curl -I --proxy http://127.0.0.1:7897 https://github.com`（外网代理）。

**`8888` 异常时的 SOCKS5 兜底：** 将 `INSPIRE_REQUESTS_HTTP_PROXY` 和 `INSPIRE_REQUESTS_HTTPS_PROXY` 都改为 `socks5h://127.0.0.1:1080`。若报 `Missing dependencies for SOCKS support`，执行 `cd /Users/zillionx/.codex/skills/inspire/Inspire-cli && uv add PySocks`。

---

## 10. 故障排查决策树

**总则：** 先确认 `aTrust` 登录状态 → 区分 OpenAPI / Web SSO / Git Platform 链路 → 排查代理、隧道、参数。

**SSH/rtunnel 故障：** `allow_ssh=false` 是平台默认状态，不影响 SSH 功能。关键步骤：(1) 确认容器内 sshd 和 rtunnel 已安装并运行（`ps aux | grep -E 'sshd|rtunnel'`）；(2) 若未安装，在容器 Web 终端手动执行阶段 A 步骤 3 的安装命令；(3) 确认实例所在计算组有公网（`HPC-可上网区资源-2` 有网，`CPU资源-2` 无网）；(4) 运行 `inspire tunnel test -b <name>` 验证连通性。`exec format error` 表示 `rtunnel` 二进制架构不匹配（已修复为容器内动态检测平台）；`lookup ... no such host` 表示 `INSPIRE_RTUNNEL_PROXY` 配置有误；持续 ECONNREFUSED 表示 rtunnel 无法在实例内绑定端口（通常因为 sshd/rtunnel 未安装）。**Jupyter WebSocket 脚本注入可能静默失败**——`notebook ssh` 报 "Sent setup script" 但容器内无 `/tmp/rtunnel`，此时需手动安装。

**HPC 创建故障：** (1) `spec_id not found in predef_node_specs` → HPC 的 `spec_id` 必须用 `quota_id`（从 `inspire --json hpc status <existing_job>` 的 `slurm_cluster_spec.predef_quota_id` 获取），`resources specs` 返回的 spec_id 仅适用于 notebook；(2) `image not found` → `--image` 必须用完整 docker 地址（`docker.sii.shaipower.online/inspire-studio/<name>:<version>`），不能仅用镜像名；(3) `429 Too Many Requests` → CLI 已内置退避重试，持续 429 则等待数分钟后重试。

**Web Session 过期：** 症状为输出 `Session expired, re-authenticating...` 且持续卡住。处理：确认 `aTrust` → 验证 Playwright 代理可连通 → 必要时清理 `~/.cache/inspire-cli/` 的 Session 缓存。

**OpenAPI 与 Web SSO 混淆：** `config check` 通过但 `image`/`notebook`/`resources` 失败时，分开验证两条链路，不做跨链路外推。代理分流错误（启智请求走到 `7897` 或公网走到 `8888`），修正域名与代理端口映射后重跑同一命令对照验证。

**常见问题速查：**

| 场景 | 症状 | 处理 |
|---|---|---|
| CPU 组误选 | `notebook create` 长时间 PENDING | 只用 `CPU资源-2`/`HPC-可上网区资源-2`。 |
| 镜像查不到 | UI 可见但 CLI 不可见 | 依次对照 `private` → `my-private` → `all`。 |
| `image set-default` 参数错误 | 参数不识别 | 改为 `--job`/`--notebook` 指定。 |
| `hpc create` 限流 | 持续 `429` | 30/60/120 秒退避；或切 `job create` 链路。 |
| `hpc create` 参数缺失 | `exit code 10` | 检查是否指定了 `--project` 和 `--image`。 |
| `bridge exec` 缺配置 | `Missing target directory` | 配置 `INSPIRE_TARGET_DIR`。 |
| `bridge exec` 隧道异常 | `SSH tunnel not responding` | 先检查 `tunnel status`，再看 `allow_ssh`。 |
| `job logs` 缺配置 | `Missing INSPIRE_USERNAME` | 配置 Gitea/GitHub platform（`INSP_GITEA_*`）。 |
| `notebook top` 全部 error | `SSH tunnel not responding` | 所有 tunnel 的实例已关停或 `allow_ssh=false`。 |

---

## 11. 环境变量完整参考

### 核心配置

| 变量 | 说明 | 默认值 |
|---|---|---|
| `INSPIRE_USERNAME` | 平台用户名。 | 无 |
| `INSPIRE_PASSWORD` | 平台密码（兜底，优先用 `[accounts]`）。 | 无 |
| `INSPIRE_BASE_URL` | API 基地址。 | 由配置决定 |
| `INSPIRE_FORCE_PROXY` | 强制 OpenAPI 走代理（`true`/`false`）。 | `false` |
| `INSPIRE_TIMEOUT` / `MAX_RETRIES` / `RETRY_DELAY` | API 超时（秒）/ 重试次数 / 重试间隔（秒）。 | `30` / `3` / `1.0` |
| `INSPIRE_SKIP_SSL_VERIFY` | 跳过 SSL 校验。 | `false` |
| `INSPIRE_DOCKER_REGISTRY` | 镜像仓库地址。 | 由配置决定 |

### 代理

| 变量 | 说明 |
|---|---|
| `INSPIRE_REQUESTS_HTTP_PROXY` / `INSPIRE_REQUESTS_HTTPS_PROXY` | OpenAPI/requests 的 HTTP/HTTPS 代理。 |
| `INSPIRE_PLAYWRIGHT_PROXY` | Playwright 浏览器自动化代理。 |
| `INSPIRE_RTUNNEL_PROXY` | rtunnel SSH ProxyCommand 代理。 |

### 路径与缓存

| 变量 | 说明 | 默认值 |
|---|---|---|
| `INSPIRE_TARGET_DIR` | Bridge 共享目录目标路径（`sync`/`bridge exec` 必须）。 | 无 |
| `INSPIRE_LOG_PATTERN` | 日志文件匹配 glob。 | `training_master_*.log` |
| `INSPIRE_JOB_CACHE` | 本地作业缓存路径。 | `~/.inspire/jobs.json` |
| `INSP_LOG_CACHE_DIR` | 日志缓存目录。 | `~/.inspire/logs` |

### 工作空间与项目

| 变量 | 说明 |
|---|---|
| `INSPIRE_PROJECT_ID` / `INSPIRE_WORKSPACE_ID` | 默认项目 ID / 默认工作空间 ID。 |
| `INSPIRE_WORKSPACE_CPU_ID` / `GPU_ID` / `INTERNET_ID` | CPU / GPU / 可上网工作空间 ID。 |

### 作业与 Notebook

| 变量 | 说明 | 默认值 |
|---|---|---|
| `INSP_PRIORITY` | 默认任务优先级 1-10。 | `6` |
| `INSP_IMAGE` | 默认作业镜像（`hpc create`/`job create` 的 `--image` 默认值）。 | 无 |
| `INSPIRE_SHM_SIZE` | 默认共享内存大小。 | 无 |
| `INSPIRE_NOTEBOOK_RESOURCE` / `NOTEBOOK_IMAGE` | 默认 Notebook 资源规格 / 镜像。 | `1xH200` / 无 |

### SSH/Tunnel

| 变量 | 说明 | 默认值 |
|---|---|---|
| `INSPIRE_RTUNNEL_BIN` / `RTUNNEL_DOWNLOAD_URL` | rtunnel 二进制路径 / 下载地址。 | 无 / 系统默认 |
| `INSPIRE_SSHD_DEB_DIR` / `DROPBEAR_DEB_DIR` | sshd / dropbear 安装包目录。 | 无 |
| `INSPIRE_SETUP_SCRIPT` | SSH 初始化脚本路径。 | 无 |
| `INSPIRE_APT_MIRROR_URL` | APT 镜像地址（自动安装 dropbear 时使用）。 | 无 |
| `INSPIRE_TUNNEL_RETRIES` / `TUNNEL_RETRY_PAUSE` | 隧道重试次数 / 间隔秒数。 | `3` / `2.0` |

### Bridge/Sync/Git Platform

| 变量 | 说明 | 默认值 |
|---|---|---|
| `INSPIRE_BRIDGE_ACTION_TIMEOUT` | `bridge exec` 超时秒数。 | `600` |
| `INSPIRE_BRIDGE_DENYLIST` | Bridge 传输 denylist。 | 空 |
| `INSPIRE_DEFAULT_REMOTE` | 默认 git remote。 | `origin` |
| `INSP_GIT_PLATFORM` | `gitea` 或 `github`。 | `gitea` |
| `INSP_REMOTE_TIMEOUT` | 远程产物等待超时秒数。 | `90` |
| `INSP_GITEA_SERVER` / `REPO` / `TOKEN` | Gitea 服务地址 / 仓库 / Token。 | `https://codeberg.org` / 无 / 无 |
| `INSP_GITEA_LOG_WORKFLOW` / `SYNC_WORKFLOW` / `BRIDGE_WORKFLOW` | Gitea 日志 / 同步 / Bridge workflow 文件名。 | `retrieve_job_log.yml` / `sync_code.yml` / `run_bridge_action.yml` |
| `INSP_GITHUB_SERVER` / `REPO` / `TOKEN` | GitHub 服务地址 / 仓库 / Token。 | `https://github.com` / 无 / 无 |
| `INSP_GITHUB_LOG_WORKFLOW` / `SYNC_WORKFLOW` / `BRIDGE_WORKFLOW` | GitHub 日志 / 同步 / Bridge workflow 文件名。 | 同 Gitea 默认值 |

---

## 12. 退出码语义

| 退出码 | 含义 |
|---|---|
| `0` | 成功 |
| `1` | 通用错误 |
| `10` | 配置错误（缺参数/环境变量） |
| `11` | 认证失败 |
| `12` | 参数校验错误 |
| `13` | API 错误（含 429 限流、500 服务端错误） |
| `14` | 超时 |
| `15` | 日志不存在 |
| `16` | 作业不存在 |

---

## 13. 工作空间与计算组快照（`2026-03-04`）

> 用途：快速定位的先验参考。不同账号与不同时间窗口下 ID 和可用性可能变化，以 `inspire init --discover` 与 `inspire resources specs` 实测为准。

| 类型 | 名称（别名） | ID |
|---|---|---|
| Workspace | `CPU资源空间`（`cpu`） | `ws-6e6ba362-e98e-45b2-9c5a-311998e93d65` |
| Workspace | `分布式训练空间`（`gpu`） | `ws-9dcc0e1f-80a4-4af2-bc2f-0e352e7b17e6` |
| Workspace | `可上网GPU资源`（`internet`） | `ws-6040202d-b785-4b37-98b0-c68d65dd52ce` |
| Compute Group | `CPU资源-2`（CPU 可用，优先） | `lcg-d4b51af1-2168-4ee2-920f-4fc50e2aeb69` |
| Compute Group | `HPC-可上网区资源-2`（CPU 可用，优先） | `lcg-cb2de75c-40ac-4de1-bbb3-11e62b32f424` |
| Compute Group | `CPU资源`（当前租户下无可用规格，避免） | `lcg-726a1548-e399-45cb-87a0-8c3d9a605bb8` |
| Compute Group | `HPC-可上网区资源`（当前租户下无可用规格，避免） | `lcg-5a67176b-6489-45d8-a6a9-ec557f20facd` |
| Compute Group | `cuda12.8版本H100` | `lcg-79b2ad0e-a375-43f3-a0b1-b4ce79710fd7` |
| Compute Group | `cuda12.9版本H100`（基本无卡，避免） | `lcg-bc36d6bf-43e1-437a-b976-bc4d63dadf57` |
| Compute Group | `H200-2号机房` | `lcg-303ac8c6-aa19-4284-af03-2296592326e5` |
| Compute Group | `H200-3号机房` | `lcg-a91ad10b-415d-4abd-8170-828a2feae5d2` |
| Compute Group | `H200-3号机房-2` | `lcg-95e38be4-4842-4155-af13-4325aa744bca` |

---

## 14. 附录

### 14.1 Fork 上游 commit 合并

设置公网代理 `export http_proxy='http://127.0.0.1:7897' && export https_proxy='http://127.0.0.1:7897'`，然后在 `cd /Users/zillionx/.codex/skills/inspire/Inspire-cli` 下执行 `git fetch upstream --prune && git fetch origin --prune && git pull --rebase origin main && git merge --ff-only upstream/main && git push origin main`。脏工作区先 `commit` 或 `stash`，默认只允许 `ff-only`，合并后至少执行一轮测试再 `push`。

### 14.2 完成定义（DoD）

主流程覆盖 0/A/B/C/D 全阶段并给出可执行命令。至少完成一次启智链路验证与一次公网链路验证。镜像语义明确（`private`=个人可见，`my-private`=兼容通道，`all`=四源聚合去重）。`image set-default` 用 `--job`/`--notebook`。CPU 选组规则为 `CPU资源-2` 或 `HPC-可上网区资源-2`。长排队给出低优先级切换与退避策略。故障排查覆盖 OpenAPI、Web SSO、Git Platform 三条链路。阅读者不查源码即可执行常见操作与回退路径。
