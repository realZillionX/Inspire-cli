# Inspire-cli is archived

> ## ⚠️ This repository is no longer maintained. Please move to **[InspireSkill](https://github.com/realZillionX/InspireSkill)**.

See [README.md](README.md) for the full migration notes (bilingual).

## TL;DR

The old `Inspire-cli` was a plain CLI. The new **InspireSkill** is a
dual-layer **agent skill + CLI** with a larger command surface, platform-drift
adapters (notebook events / run_index / logic_compute_groups paths changed in
2026-04), reliability upgrades (event auto-pagination, stricter param
validation), and a reverse-capture toolkit for tracking future drift.

Install:

```bash
curl -fsSL https://raw.githubusercontent.com/realZillionX/InspireSkill/main/scripts/install.sh | bash
```

The command is still `inspire`; daily subcommands (`notebook` / `job` / `hpc` /
`image` / `resources`) are semantically compatible — switching should be
seamless.

Issues / feedback: <https://github.com/realZillionX/InspireSkill/issues>.
