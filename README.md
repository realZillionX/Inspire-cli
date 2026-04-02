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

## 内置代理配置

`Inspire-cli` 本身支持按流量类型分别配置代理，不必强依赖系统级 `HTTP_PROXY`。这类设置通常应该写在全局配置 `~/.config/inspire/config.toml`。

推荐示例：

```toml
[api]
base_url = "https://qz.sii.edu.cn"
force_proxy = true  # 仅在 system/no_proxy 绕过代理时需要

[proxy]
requests_http = "http://127.0.0.1:7897"
requests_https = "http://127.0.0.1:7897"
playwright = "http://127.0.0.1:7897"  # 可省略；未设置时回退到 requests 代理
rtunnel = "http://127.0.0.1:7897"     # 可省略；未设置时回退到 requests 代理
```

| 配置项 | 作用范围 | 对应环境变量 |
| --- | --- | --- |
| `[proxy].requests_http` / `[proxy].requests_https` | OpenAPI、Web Session、普通 `requests` 流量 | `INSPIRE_REQUESTS_HTTP_PROXY` / `INSPIRE_REQUESTS_HTTPS_PROXY` |
| `[proxy].playwright` | Playwright 浏览器自动化登录、页面抓取 | `INSPIRE_PLAYWRIGHT_PROXY` |
| `[proxy].rtunnel` | `notebook ssh`、`bridge ssh`、`bridge exec` 的 `rtunnel` / `SSH ProxyCommand` | `INSPIRE_RTUNNEL_PROXY` |
| `[api].force_proxy` | 对 OpenAPI 请求强制启用已解析出的代理，避免被 `no_proxy` 或系统代理规则绕过 | `INSPIRE_FORCE_PROXY` |

补充说明：

- 若 `playwright` 或 `rtunnel` 没单独设置，默认会回退到 `requests` 代理。
- 若只想临时验证，先 `export` 对应环境变量即可；再用 `inspire config show --compact` 查看最终生效值和来源。
- 想看包含代理项在内的完整环境变量模板，请运行 `inspire config env --template full`。

项目级默认镜像、远端路径和共享目录约定，建议写在项目自己的 `AGENTS.md`，不要继续堆在 README 里。

## 常用环境变量

更完整的列表请运行 `inspire config env --template full`。

| 变量 | 说明 |
| --- | --- |
| `INSPIRE_USERNAME` | 平台用户名 |
| `INSPIRE_PASSWORD` | 平台密码兜底 |
| `INSPIRE_BASE_URL` | API 基地址 |
| `INSPIRE_REQUESTS_HTTP_PROXY` / `INSPIRE_REQUESTS_HTTPS_PROXY` | `requests` / OpenAPI 代理 |
| `INSPIRE_PLAYWRIGHT_PROXY` | Playwright 代理 |
| `INSPIRE_RTUNNEL_PROXY` | `rtunnel` / `SSH ProxyCommand` 代理 |
| `INSPIRE_FORCE_PROXY` | 强制 OpenAPI 使用已解析出的代理 |
| `INSPIRE_GLOBAL_CONFIG_PATH` | 全局配置文件路径覆盖 |
