中文 | [**English**](README.en.md)

# Inspire-cli 已归档

> ## ⚠️ 这个仓库不再更新。请迁移到 **[InspireSkill](https://github.com/realZillionX/InspireSkill)**。

---

## 为什么换仓库

原来的 `Inspire-cli` 只是一个命令行工具；新仓库 **InspireSkill** 把同一个 CLI 重新打包成**面向 Agent 的 skill + CLI 双层包**，并做了一轮大规模适配 / 升级：

- **Agent skill 层**：`SKILL.md` + `references/` 被安装脚本自动拷进 Claude Code / Codex CLI / Gemini CLI / OpenClaw / OpenCode 的 skills 目录，Agent 可直接作为黑盒驱动 CLI，不用你手打命令
- **命令面扩展**：新增 `inspire serving` / `inspire model` / `inspire user` / `inspire project detail|owners` / `inspire notebook events` / `inspire notebook lifecycle` —— 覆盖 Browser API 上的观测性和用户信息端点
- **端点自适应**：`POST /notebook/events` / `/run_index/list` / `logic_compute_groups/list` 等 2026-04 平台升级后更新的新路径已全部重新封装；老的 `/notebook/{id}/events` 路径 InspireSkill 自动走新路
- **可靠性改进**：事件自动分页（曾经截断只返 200，现在拉全量）、参数类型校验（拒 `bool` / 非整 `float` 悄悄进 payload）、OpenAPI 错误友好翻译
- **反向抓包工具链**：`cli/scripts/reverse_capture/` —— Playwright 驱动的 `/api/v1/*` 扫描器 + 已知端点 diff，平台下次悄悄改路径时几分钟定位
- **零漂移同步**：`inspire update` 一条命令同时刷新 CLI 和 skill，维护者持续跟进平台变更
- **代理方案中立**：可选 Clash Verge 7897 模板，但 CLI 本身不绑定，任意覆盖公网 + `*.sii.edu.cn` 的代理都能接

完整能力、安装、harness 支持见新仓库 README：<https://github.com/realZillionX/InspireSkill>

---

## 迁移

```bash
# 如果你之前用 pip/pipx 装了 inspire-cli 请先卸载
pipx uninstall inspire-cli 2>/dev/null || pip uninstall -y inspire-cli 2>/dev/null || true

# 安装新版
curl -fsSL https://raw.githubusercontent.com/realZillionX/InspireSkill/main/scripts/install.sh | bash
```

命令名仍是 `inspire`，日常子命令（`notebook` / `job` / `hpc` / `image` / `resources`）语义保持兼容，可以无缝切。

---

## 这个仓库会保留做什么

只做**归档**。不再接 issue / PR，不再发版本。有问题请去新仓库：<https://github.com/realZillionX/InspireSkill/issues>。
