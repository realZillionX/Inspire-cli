# 启智平台实践 GUIDE（Agent 版）

本文档给出一条可直接执行的启智平台工作流。若平台行为与文档不一致，以平台实时行为为准，并将差异回写文档。

默认项目域：`CI-情境智能-探索课题`。

---

## 1. 总体原则

- 先本地开发，再上平台放大规模。
- 写操作优先验证，不只做只读查询。
- 仅操作 `codex-skill-<timestamp>-*` 临时对象。
- 不触碰已有分布式训练实例。

CPU 资源空间的 CPU 任务必须优先。

- `CPU资源-2`。
- `HPC-可上网区资源-2`。

---

## 2. 一次性初始化

```bash
# 生成 env 模板并创建本地 env 文件。
./scripts/bootstrap_inspire_env.sh

# 编辑 .env.inspire.local 后加载到当前 shell。
set -a; source .env.inspire.local; set +a

# 初始化项目配置并校验。
inspire init --project --force
inspire config env --output .env.inspire.generated
inspire config check --json
```

代理分流约定。

- `*.sii.edu.cn`：`requests -> http://127.0.0.1:8888`，`playwright/rtunnel -> socks5://127.0.0.1:1080`。
- 公网：`7897` 代理链路。

OpenAPI 代理优先级。

1. `INSPIRE_REQUESTS_HTTP_PROXY`／`INSPIRE_REQUESTS_HTTPS_PROXY`。
2. TOML `[proxy].requests_http`／`[proxy].requests_https`。
3. 系统 `http_proxy`／`https_proxy`。

---

## 3. 阶段化工作流

### 3.1 本地代码开发

- 完成模型、数据、训练脚本与配置。
- 本地小样本先跑通。
- 保持清晰 git 提交历史。

### 3.2 代码同步到启智

优先 `inspire sync`。

```bash
inspire sync
inspire bridge exec "cd $INSPIRE_TARGET_DIR && git log -1"
```

断网桥或特殊场景可用。

```bash
inspire sync --allow-dirty --no-push --source bundle
```

文件级传输。

```bash
inspire tunnel ssh-config --install
scp ./file <bridge_name>:/path/
rsync -avz ./dir/ <bridge_name>:/path/
```

### 3.3 CPU 空间做容器配置

```bash
inspire notebook create \
  --workspace cpu \
  --resource 4CPU \
  --name codex-skill-<ts>-container-config \
  --project CI-情境智能-探索课题 \
  --wait --json

inspire image save <notebook_id> -n codex-skill-<ts>-img -v v1 --json
```

### 3.4 CPU 预处理（HPC）

先发现规格，再提交。

```bash
inspire resources specs --workspace cpu --group CPU资源-2 --json

inspire hpc create \
  -n codex-skill-<ts>-hpc \
  -c 'bash -lc "python preprocess.py"' \
  --logic-compute-group-id <logic_compute_group_id> \
  --spec-id <spec_id> \
  --workspace cpu \
  --cpus-per-task <cpu_count> \
  --memory-per-cpu <mem_per_cpu_gib> \
  --priority 10
```

若长时间排队或限流。

- 切低优先级（如 `--priority 10`）。
- 退避重试（10／20／30 秒）。
- 仍失败则转 `job create` 路径并保留上下文。

### 3.5 分布式训练空间

交互式调试。

```bash
inspire notebook create \
  --workspace gpu \
  --resource 1xH100 \
  --name codex-skill-<ts>-gpu-debug \
  --wait --json
```

任务提交。

```bash
# job create。
inspire job create \
  -n codex-skill-<ts>-job \
  -r 1xH100 \
  -c 'echo train && sleep 300' \
  --workspace gpu \
  --location 'cuda12.8版本H100' \
  --no-auto \
  --image 'docker.sii.shaipower.online/inspire-studio/mova:2'

# run 快速提交。
inspire run 'echo train && sleep 300' \
  --gpus 1 --type h100 \
  --workspace gpu \
  --location 'cuda12.8版本H100' \
  --image 'docker.sii.shaipower.online/inspire-studio/mova:2'
```

---

## 4. 命令注意事项（实测修正）

- `inspire image set-default` 必须使用 `--job` 和／或 `--notebook`，不能只传 `<image_id>`。
- `inspire image delete <image_id>` 已支持真实删除链路。
- `inspire image list --source private` 对应网页“个人可见镜像”。
- `inspire image list --source my-private` 对应旧语义 `SOURCE_PRIVATE` 直查。
- `inspire image list --source all` 聚合 `official/public/private/my-private` 并按 `image_id` 去重。
- `inspire tunnel remove` 不支持 `--force`。
- `inspire notebook ssh` 受 `allow_ssh` 约束，先看 `notebook status --json` 的 `start_config.allow_ssh`。

镜像查询速查（UI → CLI）。

- 官方镜像：`inspire image list --source official --json`。
- 公开可见镜像：`inspire image list --source public --json`。
- 个人可见镜像：`inspire image list --source private --json`。

`wanvideo:1.0` 排障示例。

```bash
inspire image list --source private --json | rg -n '"name": "wanvideo:1.0"'
inspire image list --source my-private --json
inspire image list --source all --json | rg -n 'wanvideo'
```

---

## 5. 调度与存储实践

### 5.1 调度

- 高优任务：保障更强，配额受限。
- 低优任务：易被抢占，适合“能断点恢复”的大批任务。

低优任务务必高频 checkpoint。

### 5.2 存储

- 代码与轻量脚本：个人目录。
- 数据、权重、checkpoint：公共目录。
- `INSPIRE_TARGET_DIR` 建议使用团队统一共享路径。

---

## 6. 与 Skill 的关系

`SKILL.md` 是本 GUIDE 的可执行黑盒手册版本。建议优先按 `SKILL.md` 执行，遇到差异以实测结果回写本 GUIDE。
