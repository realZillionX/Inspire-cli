[**中文**](README.md) | English

# Inspire-cli is archived

> ## ⚠️ This repository is no longer maintained. Please move to **[InspireSkill](https://github.com/realZillionX/InspireSkill)**.

---

## Why the new repo

The old `Inspire-cli` was just a command-line tool. The new **InspireSkill** repackages the same CLI as a **dual-layer agent skill + CLI**, with a round of large-scale adaptation and upgrades:

- **Agent skill layer** — `SKILL.md` and `references/` are auto-installed into the skills directory of Claude Code / Codex CLI / Gemini CLI / OpenClaw / OpenCode. Your agent can drive the CLI as a black box without you typing commands.
- **Expanded command surface** — new `inspire serving` / `inspire model` / `inspire user` / `inspire project detail|owners` / `inspire notebook events` / `inspire notebook lifecycle`, covering Browser-API observability and user-info endpoints that were never wrapped before.
- **Endpoint drift re-adapted** — paths changed in the 2026-04 platform upgrade (`POST /notebook/events`, `/run_index/list`, `logic_compute_groups/list`) are all re-wrapped; the legacy `/notebook/{id}/events` path is routed to the new one automatically.
- **Reliability upgrades** — event auto-pagination (used to silently truncate at 200), stricter param validation (rejects `bool` / non-integer `float` slipping into payloads), friendlier OpenAPI error translation.
- **Reverse-capture toolkit** — `cli/scripts/reverse_capture/`: a Playwright-based `/api/v1/*` scanner plus known-endpoint diff, so the next silent path change is minutes away from being re-mapped.
- **Zero-drift sync** — `inspire update` refreshes CLI and skill together; the maintainer actively tracks upstream changes.
- **Proxy-agnostic** — ships an optional Clash Verge 7897 split-tunneling template, but the CLI itself isn't tied to it; any proxy that covers both the public internet and `*.sii.edu.cn` works.

Full capability tour, install, harness support: <https://github.com/realZillionX/InspireSkill>.

---

## Migration

```bash
# Uninstall the old inspire-cli if it's still around
pipx uninstall inspire-cli 2>/dev/null || pip uninstall -y inspire-cli 2>/dev/null || true

# Install the new version
curl -fsSL https://raw.githubusercontent.com/realZillionX/InspireSkill/main/scripts/install.sh | bash
```

The binary is still `inspire` and the daily subcommands (`notebook` / `job` / `hpc` / `image` / `resources`) are semantically compatible — switching should be seamless.

---

## What this repo becomes

**Archived only.** No more issues / PRs / releases. File anything new at <https://github.com/realZillionX/InspireSkill/issues>.
