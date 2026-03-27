中文 | [**English**](README.en.md)

# Inspire CLI

启智（Inspire）训练平台命令行工具 —— Notebook 管理、分布式训练 / 高性能计算提交、SSH 隧道、镜像管理、代码同步一站式解决。

> **README 边界：** 本文档只保留安装与一次性配置。
>
> **完整操作手册：** [Inspire Skill - 启智平台全流程操作手册](https://fudan-nlp.feishu.cn/wiki/D2RXwnZcQiUQadkadJgcC1aEnLh)
>
> **机密网络配置：** [Clash 7897 网络配置方法](https://fudan-nlp.feishu.cn/wiki/NDvbw0TZPiiNT2k1DzmcMovHnoc)

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

## 一次性配置

| 步骤 | 操作 | 说明 |
| --- | --- | --- |
| 1. 网络前置 | 参考上方飞书文档 | 仅在本机不能直连 `*.sii.edu.cn` 时需要 |
| 2. 自动发现 | `inspire init --discover -u <用户名> --base-url https://qz.sii.edu.cn` | 自动写入全局配置 `~/.config/inspire/config.toml` 和项目配置 `./.inspire/config.toml` |
| 3. 检查结果 | `inspire config show` / `inspire config check` | 查看合并后的配置并校验认证链路 |

补充说明：

- `INSPIRE_PASSWORD` 可以临时 `export`，也可以持久写进 shell 启动文件；若希望按账号长期保存，也可直接写入 `~/.config/inspire/config.toml` 的 `[accounts."<用户名>"].password`。
- 默认 `discover` 已经会尽量发现 `workdir` 和 `shared_path_group`。
- 只有当输出里仍有未知 shared path 时，再加 `--probe-shared-path` 做慢速补全；它会创建临时 `CPU notebook`。

## 配置文件

| 层级 | 默认路径 | 用途 |
| --- | --- | --- |
| 全局配置 | `~/.config/inspire/config.toml` | 账号、密码、基础 URL，以及少量机器级配置 |
| 项目配置 | `./.inspire/config.toml` | `discover` 自动写入的项目、workspace、compute group 等项目级元数据 |
| 环境变量 | 当前 shell / CI 环境 | 临时覆盖或敏感值兜底 |

默认合并顺序是 `默认值 < 全局 TOML < 项目 TOML < 环境变量`。若项目配置里设置 `cli.prefer_source = "toml"`，则冲突时改为项目 TOML 优先。

最小全局配置示例：

```toml
[auth]
username = "your_username"

[accounts."your_username"]
password = "your_password"

[api]
base_url = "https://qz.sii.edu.cn"
```

项目级默认镜像、远端路径和共享目录约定，建议写在项目自己的 `AGENTS.md`，不要继续堆在 README 里。

## 常用环境变量

更完整的列表请运行 `inspire config env`。

| 变量 | 说明 |
| --- | --- |
| `INSPIRE_USERNAME` | 平台用户名 |
| `INSPIRE_PASSWORD` | 平台密码兜底 |
| `INSPIRE_BASE_URL` | API 基地址 |
| `INSPIRE_GLOBAL_CONFIG_PATH` | 全局配置文件路径覆盖 |

## 开发与贡献

如果只是本地试用 CLI，参考上面的“本地开发”。若要修改仓库本身，建议至少跑完与 CI 对齐的检查：

| 目标 | 命令 |
| --- | --- |
| 安装开发依赖 | `uv sync --group dev` |
| 运行测试 | `uv run pytest -x -q --tb=short` |
| 运行静态检查 | `uv run ruff check inspire tests` |
| 检查格式 | `uv run black --check inspire tests` |

可选预检：`uv run pre-commit run --all-files`

提交时请使用 [Conventional Commits](https://www.conventionalcommits.org/) 前缀（如 `feat:`、`fix:`、`docs:`、`chore:`）；若改动会影响用户可见行为，请同步更新 [CHANGELOG.md](CHANGELOG.md)。

## 许可证

当前仓库**未附带单独的 `LICENSE` 文件**。打包元数据在 [pyproject.toml](pyproject.toml) 中声明为 `LicenseRef-Proprietary`；使用、复制和分发需获得 **Inspire Platform Team** 授权。
