"""Resources specs command (discover spec_id/quota_id by compute group)."""

from __future__ import annotations

from typing import Optional

import click

from inspire.cli.context import (
    Context,
    EXIT_API_ERROR,
    EXIT_AUTH_ERROR,
    EXIT_CONFIG_ERROR,
    pass_context,
)
from inspire.cli.formatters import json_formatter
from inspire.cli.utils.errors import exit_with_error as _handle_error
from inspire.config import Config, ConfigError
from inspire.platform.web import browser_api as browser_api_module
from inspire.platform.web.session import SessionExpiredError, get_web_session


def _resolve_workspace_id(
    config: Config,
    *,
    workspace: Optional[str],
    workspace_id_override: Optional[str],
) -> Optional[str]:
    if workspace_id_override:
        return workspace_id_override
    if workspace:
        if workspace.startswith("ws-"):
            return workspace
        if workspace in config.workspaces:
            return config.workspaces[workspace]
        return workspace
    if config.job_workspace_id:
        return config.job_workspace_id
    return None


def _group_id(group: dict) -> str:
    return str(group.get("logic_compute_group_id") or group.get("id") or "").strip()


def _group_name(group: dict, fallback: str) -> str:
    return str(group.get("name") or group.get("logic_compute_group_name") or fallback).strip()


def _extract_gpu_type(price: dict) -> str:
    gpu_info = price.get("gpu_info") if isinstance(price.get("gpu_info"), dict) else {}
    return str(
        gpu_info.get("gpu_type_display")
        or gpu_info.get("gpu_type")
        or gpu_info.get("brand_name")
        or price.get("gpu_type")
        or ("CPU" if int(price.get("gpu_count") or 0) == 0 else "")
    ).strip()


def _extract_memory_gib(price: dict) -> int:
    value = (
        price.get("memory_size_gib")
        or price.get("memory_size")
        or price.get("memory_size_gb")
        or 0
    )
    try:
        return int(value)
    except Exception:
        return 0


@click.command("specs")
@click.option("--workspace", default=None, help="Workspace name (from [workspaces])")
@click.option("--workspace-id", "workspace_id_override", default=None, help="Workspace ID override")
@click.option("--group", default=None, help="Filter by compute group name (partial match)")
@click.option("--include-empty", is_flag=True, help="Include compute groups that return no specs")
@click.option("--json", "json_output_local", is_flag=True, help="Alias for global --json")
@pass_context
def list_specs(
    ctx: Context,
    workspace: Optional[str],
    workspace_id_override: Optional[str],
    group: Optional[str],
    include_empty: bool,
    json_output_local: bool,
) -> None:
    """Discover resource specs for notebook/HPC creation.

    Returns per-spec entries including:
    - logic_compute_group_id
    - spec_id (quota_id)
    - cpu_count / memory_size_gib / gpu_count / gpu_type
    - workspace_id
    """

    ctx.json_output = bool(ctx.json_output or json_output_local)
    try:
        config, _ = Config.from_files_and_env(require_credentials=False, require_target_dir=False)
        resolved_workspace_id = _resolve_workspace_id(
            config,
            workspace=workspace,
            workspace_id_override=workspace_id_override,
        )
        session = get_web_session()
        workspace_id = resolved_workspace_id or session.workspace_id

        groups = browser_api_module.list_notebook_compute_groups(
            workspace_id=workspace_id,
            session=session,
        )

        group_filter = (group or "").strip().lower()
        rows: list[dict] = []
        for item in groups:
            logic_compute_group_id = _group_id(item)
            if not logic_compute_group_id:
                continue
            compute_group_name = _group_name(item, fallback=logic_compute_group_id)
            if group_filter and group_filter not in compute_group_name.lower():
                continue

            prices = browser_api_module.get_resource_prices(
                workspace_id=workspace_id,
                logic_compute_group_id=logic_compute_group_id,
                session=session,
            )

            if not prices:
                if include_empty:
                    rows.append(
                        {
                            "workspace_id": workspace_id,
                            "compute_group_name": compute_group_name,
                            "logic_compute_group_id": logic_compute_group_id,
                            "spec_id": "",
                            "cpu_count": 0,
                            "memory_size_gib": 0,
                            "gpu_count": 0,
                            "gpu_type": "",
                            "total_price_per_hour": 0,
                        }
                    )
                continue

            for price in prices:
                spec_id = str(price.get("quota_id") or price.get("spec_id") or "").strip()
                rows.append(
                    {
                        "workspace_id": workspace_id,
                        "compute_group_name": compute_group_name,
                        "logic_compute_group_id": logic_compute_group_id,
                        "spec_id": spec_id,
                        "cpu_count": int(price.get("cpu_count") or 0),
                        "memory_size_gib": _extract_memory_gib(price),
                        "gpu_count": int(price.get("gpu_count") or 0),
                        "gpu_type": _extract_gpu_type(price),
                        "total_price_per_hour": price.get("total_price_per_hour", 0),
                    }
                )

        rows.sort(
            key=lambda r: (
                str(r.get("compute_group_name", "")),
                -int(r.get("gpu_count", 0)),
                -int(r.get("cpu_count", 0)),
                -int(r.get("memory_size_gib", 0)),
                str(r.get("spec_id", "")),
            )
        )

        if ctx.json_output:
            click.echo(
                json_formatter.format_json(
                    {
                        "workspace_id": workspace_id,
                        "specs": rows,
                        "total": len(rows),
                    }
                )
            )
            return

        if not rows:
            click.echo("No resource specs found.")
            return

        headers = (
            "Compute Group",
            "Spec ID",
            "GPU",
            "CPU",
            "MemGiB",
            "Logic Group ID",
        )
        widths = [24, 36, 8, 6, 8, 36]
        click.echo("")
        click.echo("Resource Specs (for notebook create / hpc create)")
        click.echo("-" * (sum(widths) + len(widths) - 1))
        click.echo(
            f"{headers[0]:<{widths[0]}} {headers[1]:<{widths[1]}} "
            f"{headers[2]:<{widths[2]}} {headers[3]:<{widths[3]}} "
            f"{headers[4]:<{widths[4]}} {headers[5]:<{widths[5]}}"
        )
        click.echo("-" * (sum(widths) + len(widths) - 1))
        for row in rows:
            gpu_desc = f"{row['gpu_count']}x{row['gpu_type'] or 'CPU'}"
            click.echo(
                f"{row['compute_group_name'][:widths[0]-1]:<{widths[0]}} "
                f"{row['spec_id'][:widths[1]-1]:<{widths[1]}} "
                f"{gpu_desc[:widths[2]-1]:<{widths[2]}} "
                f"{row['cpu_count']:<{widths[3]}} "
                f"{row['memory_size_gib']:<{widths[4]}} "
                f"{row['logic_compute_group_id'][:widths[5]-1]:<{widths[5]}}"
            )
        click.echo("-" * (sum(widths) + len(widths) - 1))
        click.echo(f"Workspace: {workspace_id}")
        click.echo(f"Total specs: {len(rows)}")
        click.echo("Use spec_id with: inspire hpc create --spec-id <spec_id>")
        click.echo("")

    except ConfigError as e:
        _handle_error(ctx, "ConfigError", str(e), EXIT_CONFIG_ERROR)
    except (SessionExpiredError, ValueError) as e:
        _handle_error(ctx, "AuthenticationError", str(e), EXIT_AUTH_ERROR)
    except Exception as e:
        _handle_error(ctx, "APIError", str(e), EXIT_API_ERROR)


__all__ = ["list_specs"]
