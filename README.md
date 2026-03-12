中文 | [**English**](README.en.md)

# Inspire CLI

启智（Inspire）HPC 训练平台的命令行工具。支持 notebook 实例管理、分布式训练任务提交、代码同步、SSH 隧道、镜像管理等全流程操作。

> 📖 **完整操作手册：** [Inspire Skill - 启智平台全流程操作手册](https://fudan-nlp.feishu.cn/wiki/D2RXwnZcQiUQadkadJgcC1aEnLh)（飞书，需团队权限）

## 安装

```bash
# 通过 SSH（推荐）
uv tool install git+ssh://git@github.com/realZillionX/Inspire-cli.git

# 或通过 HTTPS
uv tool install git+https://github.com/realZillionX/Inspire-cli.git
```

### 本地开发

```bash
uv tool install -e .
inspire --help
```

---

## 快速开始

### 1. 自动发现平台资源

```bash
inspire init --discover -u <用户名> --base-url https://qz.sii.edu.cn
```

该命令会拉起浏览器完成 CAS Web SSO 登录，自动发现你的项目、工作空间、计算组、共享文件系统路径，并写入全局配置 `~/.config/inspire/config.toml` 和项目配置 `.inspire/config.toml`。
当账号可见多个 workspace 时，discover 会尽量聚合可见项目；项目级配置中的工作空间映射和计算组目录使用平台里的实际名称，而不是 `cpu/gpu/internet` 这类抽象别名。

设置密码环境变量可避免重复输入：

```bash
export INSPIRE_PASSWORD="your_password"
```

### 2. 验证配置

```bash
inspire config show    # 查看所有配置值及其来源
inspire config check   # 验证 API 认证
```

### 3. 开始使用

```bash
inspire resources list                          # 查看 GPU 可用性
inspire notebook create --name dev -r 4CPU --wait  # 创建 CPU 实例
inspire notebook ssh <id>                       # SSH 连接到实例（自动建立隧道）
```

---

## 命令速查表

### 配置与初始化

| 命令                      | 说明                                          |
| ------------------------- | --------------------------------------------- |
| `inspire init --discover` | 自动发现项目、工作空间、计算组并写入配置      |
| `inspire init`            | 从环境变量生成配置文件（模板模式 / 智能模式） |
| `inspire config show`     | 查看合并后的配置及值来源                      |
| `inspire config check`    | 验证配置 + API 认证状态                       |
| `inspire config env`      | 按 schema 生成配置模板（`.env` 格式，含注释） |

### Notebook 实例管理

| 命令                                         | 说明                                                              |
| -------------------------------------------- | ----------------------------------------------------------------- |
| `inspire notebook list`                      | 列出当前工作空间实例（加 `-A` 跨所有工作空间）                    |
| `inspire notebook create`                    | 创建实例（支持 `--workspace`, `--resource`, `--image`, `--wait`） |
| `inspire notebook status <id>`               | 查看实例详情                                                      |
| `inspire notebook start/stop <id>`           | 启动 / 停止实例                                                   |
| `inspire notebook ssh <id>`                  | SSH 连接到实例（自动安装 rtunnel + 建立隧道）                     |
| `inspire notebook ssh <id> --save-as <name>` | SSH 并保存为 Bridge Profile                                       |
| `inspire notebook top`                       | 显示所有 tunnel 实例的 GPU 利用率（加 `--watch` 持续监控）        |

### 训练任务

| 命令                       | 说明                                                |
| -------------------------- | --------------------------------------------------- |
| `inspire job create`       | 提交分布式训练任务（精细控制）                      |
| `inspire run "<cmd>"`      | 快速提交任务（自动选资源，支持 `--sync --watch`）   |
| `inspire job list`         | 列出本地缓存的作业                                  |
| `inspire job status <id>`  | 查询作业状态                                        |
| `inspire job logs <id>`    | 查看作业日志（支持 `--tail`, `--follow`, `--head`） |
| `inspire job wait <id>`    | 阻塞等待作业结束                                    |
| `inspire job stop <id>`    | 停止作业                                            |
| `inspire job update`       | 刷新缓存中活跃作业状态                              |
| `inspire job command <id>` | 查看提交时的命令                                    |

### HPC 任务

| 命令                      | 说明                        |
| ------------------------- | --------------------------- |
| `inspire hpc create`      | 创建 HPC 任务（Slurm 链路） |
| `inspire hpc list`        | 列出 HPC 任务               |
| `inspire hpc status <id>` | 查看 HPC 任务详情           |
| `inspire hpc stop <id>`   | 停止 HPC 任务               |

> **注意：** `hpc create` 的 `--spec-id` 必须使用 `quota_id`。可通过 `inspire resources specs` 获取（输出中会标注 `quota_id`），或从已有 HPC 任务的 `inspire --json hpc status <job_id>` 中提取。`--image` 必须用完整 docker 地址。

### 镜像管理

| 命令                               | 说明                                                  |
| ---------------------------------- | ----------------------------------------------------- |
| `inspire image list`               | 浏览镜像（`--source private/public/official/all`）    |
| `inspire image detail <id>`        | 查看镜像详情                                          |
| `inspire image save <notebook_id>` | 从运行中的实例保存镜像                                |
| `inspire image register`           | 注册外部镜像（`--method address` 或 `--method push`） |
| `inspire image delete <id>`        | 删除镜像                                              |
| `inspire image set-default`        | 设置默认镜像（`--job` 和/或 `--notebook`）            |

### 代码同步与远程操作

| 命令                             | 说明                                                            |
| -------------------------------- | --------------------------------------------------------------- |
| `inspire sync`                   | 同步代码到共享文件系统（默认 SSH，`--transport workflow` 切换） |
| `inspire bridge exec "<cmd>"`    | 在远端 `INSPIRE_TARGET_DIR` 下执行命令                          |
| `inspire bridge ssh`             | 打开交互式 SSH shell                                            |
| `inspire bridge scp <src> <dst>` | 上传/下载文件（加 `-r` 递归，加 `-d` 下载方向）                 |

### 隧道管理

| 命令                                  | 说明                           |
| ------------------------------------- | ------------------------------ |
| `inspire tunnel add <name> <url>`     | 添加隧道 Profile               |
| `inspire tunnel list`                 | 列出所有 Profile（含连通状态） |
| `inspire tunnel status`               | 检查所有 Bridge SSH 连通性     |
| `inspire tunnel test`                 | 测试默认 Profile 连接延迟      |
| `inspire tunnel ssh-config --install` | 写入 `~/.ssh/config`           |
| `inspire tunnel set-default <name>`   | 设默认 Profile                 |
| `inspire tunnel remove <name>`        | 删除 Profile                   |

### 资源与项目

| 命令                      | 说明                            |
| ------------------------- | ------------------------------- |
| `inspire resources list`  | 查看 GPU 可用性                 |
| `inspire resources nodes` | 查看节点状态                    |
| `inspire resources specs` | 查询计算组规格（支持 `--json`） |
| `inspire project list`    | 查看项目和配额                  |

---

## 使用示例

```bash
# 提交训练任务
inspire job create --name "train-v1" --resource "4xH200" --command "bash train.sh"

# 快速提交，自动同步代码并跟踪日志
inspire run "python train.py --epochs 100" --sync --watch

# 同步代码并验证
inspire sync && inspire bridge exec "git log -1"

# 建立 SSH 隧道并保存为 Bridge Profile
inspire notebook ssh <notebook-id> --save-as mybridge
ssh mybridge

# 监控 GPU 使用率
inspire notebook top --watch

# 通过 Bridge 传输文件
inspire bridge scp ./model.py /tmp/model.py --bridge mybridge
inspire bridge scp -d /tmp/checkpoints/ ./checkpoints/ -r --bridge mybridge

# 查看 GPU 可用性和项目配额
inspire resources list
inspire project list

# 查询计算组可用规格
inspire resources specs --workspace CPU资源空间 --group HPC-可上网区资源-2 --json
```

---

## 配置

### 分层配置模型

配置按以下优先级加载（后者覆盖前者）：

1. **全局配置**：`~/.config/inspire/config.toml`
2. **项目配置**：`./.inspire/config.toml`
3. **环境变量**

推荐使用 `inspire init --discover` 自动生成配置，或 `inspire config show` 查看合并结果。
默认分层下，全局配置主要保存账号级敏感信息，项目配置主要保存工作空间别名、计算组目录和默认值。
可选地通过 `INSPIRE_GLOBAL_CONFIG_PATH` 覆盖默认的全局配置路径。

Legacy `[auth].password` 仍然兼容，但当它与账号密码同时存在时，会优先使用 `[accounts."<username>"].password`。

### 多账号支持

在 TOML 中为不同账号配置密码：

```toml
[accounts."username_a"]
password = "password_a"

[accounts."username_b"]
password = "password_b"
```

密码查找顺序：`[accounts."<username>"].password`（global → project）→ `INSPIRE_PASSWORD`（兜底）。

### 配置文件示例

```toml
[auth]
username = "your_username"

[api]
base_url = "https://qz.sii.edu.cn"
force_proxy = true

[proxy]
# 代理配置是可选的。如果本地网络可直连 *.sii.edu.cn，无需配置。
# requests_http = "http://127.0.0.1:8888"
# requests_https = "http://127.0.0.1:8888"
# playwright = "socks5://127.0.0.1:1080"
# rtunnel = "socks5://127.0.0.1:1080"

[workspaces]
# 项目级 workspace 映射，使用平台里的实际名称。
"CPU资源空间" = "ws-..."
"分布式训练空间" = "ws-..."
"可上网GPU资源" = "ws-..."

[[compute_groups]]
# 项目级 compute group 目录，由当前仓库的 discover 结果生成。
name = "H100 Cluster"
id = "lcg-..."
gpu_type = "H100"

[bridge]
action_timeout = 600

[ssh]
# rtunnel_bin = "/inspire/shared/tools/rtunnel"
# apt_mirror_url = "http://nexus.example.com/repository/ubuntu/"
```

---

## 代理配置

### 代理是可选的

如果你的网络可以直连 `*.sii.edu.cn`（例如校园网内），**无需配置任何代理**，CLI 会直连目标。

### 需要代理时

适用于通过 aTrust VPN（Docker 容器化）访问启智平台的场景：

```toml
[proxy]
requests_http = "http://127.0.0.1:8888"    # aTrust HTTP 代理
requests_https = "http://127.0.0.1:8888"
playwright = "socks5://127.0.0.1:1080"     # aTrust SOCKS5 代理
rtunnel = "socks5://127.0.0.1:1080"
```

端口号取决于你的 [Docker-aTrust](https://github.com/realZillionX/Docker-aTrust) 容器配置（默认 `8888` / `1080`）。

### 代理优先级

1. 显式环境变量（`INSPIRE_*_PROXY`）
2. TOML `[proxy]` 配置
3. 系统 `http_proxy` / `https_proxy`

### 自动分流

当 `base_url` 属于 `.sii.edu.cn` 且 requests 代理为 `http://127.0.0.1:8888` 时，Playwright 和 rtunnel 会自动降级到 `socks5://127.0.0.1:1080`。

---

## 环境变量参考

### 核心配置

| 变量                  | 说明                    | 默认值     |
| --------------------- | ----------------------- | ---------- |
| `INSPIRE_USERNAME`    | 平台用户名              | —          |
| `INSPIRE_PASSWORD`    | 平台密码（兜底）        | —          |
| `INSPIRE_BASE_URL`    | API 基地址              | 由配置决定 |
| `INSPIRE_FORCE_PROXY` | 强制 OpenAPI 走代理     | `false`    |
| `INSPIRE_GLOBAL_CONFIG_PATH` | 全局配置文件路径覆盖 | —          |
| `INSPIRE_TARGET_DIR`  | Bridge 共享目录目标路径 | —          |

### 代理

| 变量                           | 说明                        |
| ------------------------------ | --------------------------- |
| `INSPIRE_REQUESTS_HTTP_PROXY`  | OpenAPI/requests HTTP 代理  |
| `INSPIRE_REQUESTS_HTTPS_PROXY` | OpenAPI/requests HTTPS 代理 |
| `INSPIRE_PLAYWRIGHT_PROXY`     | Playwright 浏览器代理       |
| `INSPIRE_RTUNNEL_PROXY`        | rtunnel SSH 代理            |

### 工作空间与项目

| 变量                            | 说明              |
| ------------------------------- | ----------------- |
| `INSPIRE_PROJECT_ID`            | 默认项目 ID       |
| `INSPIRE_WORKSPACE_CPU_ID`      | CPU 工作空间 ID   |
| `INSPIRE_WORKSPACE_GPU_ID`      | GPU 工作空间 ID   |
| `INSPIRE_WORKSPACE_INTERNET_ID` | 可上网工作空间 ID |

### 作业与 Notebook

| 变量                        | 说明                   | 默认值   |
| --------------------------- | ---------------------- | -------- |
| `INSP_IMAGE`                | 默认镜像               | —        |
| `INSP_PRIORITY`             | 默认优先级（1-10）     | `10`     |
| `INSPIRE_NOTEBOOK_RESOURCE` | 默认 Notebook 资源规格 | `1xH200` |
| `INSPIRE_NOTEBOOK_POST_START` | 默认 Notebook 启动后动作 | —      |

### 调试

| 变量                     | 说明                         |
| ------------------------ | ---------------------------- |
| `INSPIRE_DEBUG_LOG_DIR`  | `inspire --debug` 日志目录   |
| `INSPIRE_RTUNNEL_TIMING` | 输出 rtunnel 各步骤耗时      |

---

## SSH / 隧道机制

### 关键要点

- **没有 `inspire tunnel start` 命令。** 通过 `inspire notebook ssh <id> --save-as <name>` 创建或刷新 Profile。
- **`allow_ssh=false` 是平台默认状态。** SSH 需要容器内预装 `sshd` + `rtunnel`——如果连接失败，通常意味着镜像未包含 SSH 工具链。
- `notebook ssh` 首次引导会先打开 JupyterLab，优先通过 Jupyter Contents API 上传 `rtunnel`，再通过 terminal REST API + terminal WebSocket 下发安装脚本；如果这些路径失败，才退回 Playwright 终端自动化。**这条链路仍可能静默失败**——报 "Sent setup script" 但容器内无 `/tmp/rtunnel`。此时需在容器 Web 终端手动安装。
- 对无公网 notebook，如果已走上传二进制或 dropbear/apt-mirror 路径，CLI 会跳过注定失败的 `curl` 下载兜底。
- 从已安装 SSH 工具链的实例保存的镜像会保留 sshd，后续实例无需重复安装。
- `bridge exec` 和 `bridge ssh` 在 notebook-backed Profile 上会自动重连断开的隧道；`bridge scp` 仅检查隧道可用性，不会自动重建。
- rtunnel 安装脚本使用动态平台检测（`uname -s/-m`），不依赖本地主机架构。
- `inspire --debug` 会把脱敏后的调试报告写到 `~/.cache/inspire-cli/logs/`，便于排查上传、终端和代理链路。

### SSH 初始化（手动安装）

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

## HPC 任务注意事项

- `--spec-id` 必须使用 `quota_id`。可通过 `inspire resources specs`（输出中包含 `quota_id`）或从已有 HPC 任务的 `inspire --json hpc status <job_id>` → `slurm_cluster_spec.predef_quota_id` 获取。
- `--image` 必须用完整 docker 地址（如 `docker.sii.shaipower.online/inspire-studio/<name>:<version>`）。
- `memory_per_cpu` 发送为带 `G` 后缀的字符串，`cpus_per_task` 发送为字符串，匹配 OpenAPI 规范。
- 遇到 `429 Too Many Requests` 时 CLI 已内置指数退避重试。

---

## 认证链路

三条认证链路独立，不可互相代证：

1. **OpenAPI**：Bearer Token（`POST /auth/token`），用于 `job`/`run`/`hpc`/`config check`。
2. **Web SSO**：浏览器 CAS Cookie Session，用于 `notebook`/`image`/`resources`/`project`。
3. **Git Platform**：GitHub/Gitea Token，用于 `job logs`/`sync --transport workflow`。

`config check` 通过不代表 Web Session 或 Git Platform 链路可用。

---

## 退出码

| 退出码 | 含义                    |
| ------ | ----------------------- |
| `0`    | 成功                    |
| `1`    | 通用错误                |
| `10`   | 配置错误                |
| `11`   | 认证失败                |
| `12`   | 参数校验错误            |
| `13`   | API 错误（含 429 限流） |
| `14`   | 超时                    |
| `15`   | 日志不存在              |
| `16`   | 作业不存在              |

---

## 开发与贡献

```bash
# 创建开发环境
uv venv .venv && uv pip install -e .

# 运行测试
uv run python -m pytest tests/ -x -q

# 代码格式化
uv tool run black .

# Lint 检查
uv run ruff check inspire tests
```

提交规范：使用 [Conventional Commits](https://www.conventionalcommits.org/) 前缀（`feat:`, `fix:`, `docs:`, `chore:`）。

---

## 许可证

详见 [LICENSE](LICENSE) 文件。
