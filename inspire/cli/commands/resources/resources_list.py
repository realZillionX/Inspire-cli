"""Resources list command (availability)."""

from __future__ import annotations

import logging
import os
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

import click

from inspire.cli.context import (
    Context,
    EXIT_API_ERROR,
    EXIT_AUTH_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_GENERAL_ERROR,
    pass_context,
)
from inspire.cli.formatters import json_formatter
from inspire.cli.utils.common import json_option
from inspire.cli.utils.errors import exit_with_error as _handle_error
from inspire.cli.utils.notebook_cli import resolve_json_output
from inspire.cli.utils.output import emit_error
from inspire.config import Config
from inspire.platform.web import browser_api as browser_api_module
from inspire.platform.web.resources import (
    clear_availability_cache,
    fetch_resource_availability,
)
from inspire.platform.web.session import (
    SessionExpiredError,
    fetch_workspace_availability,
    get_web_session,
)
from inspire.platform.web.session.models import DEFAULT_WORKSPACE_ID

_SECTION_TABLE_WIDTH = 108


@dataclass
class CPUResourceSummary:
    group_id: str
    group_name: str
    cpu_per_node_min: int | None = None
    cpu_per_node_max: int | None = None
    spec_cpu_min: int | None = None
    spec_cpu_max: int | None = None
    spec_memory_gib_min: int | None = None
    spec_memory_gib_max: int | None = None
    total_nodes: int = 0
    ready_nodes: int = 0
    free_nodes: int = 0
    has_cpu_specs: bool = False
    workspace_ids: list[str] = field(default_factory=list)
    workspace_aliases: list[str] = field(default_factory=list)


def _dedupe_ordered(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = str(raw_value or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _workspace_aliases_by_id(config: Config | None) -> dict[str, list[str]]:
    aliases_by_id: dict[str, list[str]] = {}
    if config is None:
        return aliases_by_id
    for alias, raw_workspace_id in (config.workspaces or {}).items():
        workspace_id = str(raw_workspace_id or "").strip()
        if not workspace_id:
            continue
        aliases_by_id.setdefault(workspace_id, [])
        if alias not in aliases_by_id[workspace_id]:
            aliases_by_id[workspace_id].append(alias)
    return aliases_by_id


def _enumerate_accessible_workspace_ids(session) -> list[str]:  # noqa: ANN001
    candidates = [str(session.workspace_id or "").strip()]
    candidates.extend(str(ws or "").strip() for ws in (session.all_workspace_ids or []))
    try:
        from inspire.platform.web.browser_api.workspaces import try_enumerate_workspaces

        for workspace in try_enumerate_workspaces(session, workspace_id=session.workspace_id):
            workspace_id = str(workspace.get("id") or "").strip()
            if workspace_id:
                candidates.append(workspace_id)
    except Exception:
        pass
    return [
        workspace_id
        for workspace_id in _dedupe_ordered(candidates)
        if workspace_id != DEFAULT_WORKSPACE_ID
    ]


def _resolve_resources_workspace_scope(
    *,
    config: Config | None,
    show_all: bool,
) -> tuple[list[str], dict[str, list[str]], str]:
    aliases_by_id = _workspace_aliases_by_id(config)
    session = get_web_session(require_workspace=True)

    if show_all:
        workspace_ids = _enumerate_accessible_workspace_ids(session)
        return workspace_ids, aliases_by_id, "Shows all accessible workspaces"

    configured_workspace_ids = _dedupe_ordered(
        list((config.workspaces or {}).values()) if config else []
    )
    if configured_workspace_ids:
        return (
            configured_workspace_ids,
            aliases_by_id,
            "Shows configured account workspaces only",
        )

    fallback_workspace_id = str(session.workspace_id or "").strip()
    if not fallback_workspace_id or fallback_workspace_id == DEFAULT_WORKSPACE_ID:
        return [], aliases_by_id, "No configured workspaces found"
    return (
        [fallback_workspace_id],
        aliases_by_id,
        "Shows current session workspace only (run 'inspire init --discover' to configure account workspaces)",
    )


def _apply_workspace_aliases(availability: list, aliases_by_id: dict[str, list[str]]) -> None:
    for entry in availability:
        entry.workspace_aliases = []
        for workspace_id in getattr(entry, "workspace_ids", []) or []:
            for alias in aliases_by_id.get(workspace_id, []):
                if alias not in entry.workspace_aliases:
                    entry.workspace_aliases.append(alias)


def _display_width(value: str) -> int:
    width = 0
    for char in value:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
    return width


def _truncate_display(value: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    if _display_width(value) <= max_width:
        return value
    ellipsis = "…"
    ellipsis_width = _display_width(ellipsis)
    trimmed = ""
    for char in value:
        char_width = _display_width(char)
        if _display_width(trimmed) + char_width + ellipsis_width > max_width:
            return trimmed + ellipsis
        trimmed += char
    return trimmed


def _pad_display(value: str, width: int, align: str = "left") -> str:
    actual_width = _display_width(value)
    padding = max(width - actual_width, 0)
    if align == "right":
        return f"{' ' * padding}{value}"
    return f"{value}{' ' * padding}"


def _render_table(
    columns: list[tuple[str, str]],
    rows: list[dict[str, str]],
    *,
    min_width: int = 0,
) -> list[str]:
    widths: list[int] = []
    for index, (header, _align) in enumerate(columns):
        cell_width = _display_width(header)
        for row in rows:
            values = list(row.values())
            if index < len(values):
                cell_width = max(cell_width, _display_width(values[index]))
        widths.append(cell_width)

    rendered: list[str] = []
    header_cells = []
    for (header, align), width in zip(columns, widths):
        header_cells.append(_pad_display(header, width, "right" if align == "right" else "left"))
    header_line = "  ".join(header_cells)
    border_width = max(_display_width(header_line), min_width)
    rendered.append("─" * border_width)
    rendered.append(header_line)
    rendered.append("─" * border_width)
    for row in rows:
        row_cells = []
        values = list(row.values())
        for (header, align), width, value in zip(columns, widths, values):
            row_cells.append(_pad_display(value, width, align))
        rendered.append("  ".join(row_cells))
    rendered.append("─" * border_width)
    return rendered


def _short_group_id(group_id: str) -> str:
    return group_id.split("-")[-1][-8:]


def _disambiguated_names(entries: list[object]) -> dict[str, str]:
    counts: dict[str, int] = {}
    for entry in entries:
        name = str(getattr(entry, "group_name", "") or "")
        counts[name] = counts.get(name, 0) + 1

    display_names: dict[str, str] = {}
    for entry in entries:
        group_id = str(getattr(entry, "group_id", "") or "")
        name = str(getattr(entry, "group_name", "") or "")
        if counts.get(name, 0) > 1 and group_id:
            display_names[group_id] = f"{name} [{_short_group_id(group_id)}]"
        else:
            display_names[group_id] = name
    return display_names


def _format_range(min_value: int | None, max_value: int | None, *, none_value: str = "none") -> str:
    if min_value is None or max_value is None:
        return none_value
    if min_value == max_value:
        return str(min_value)
    return f"{min_value}-{max_value}"


def _update_range(
    current_min: int | None,
    current_max: int | None,
    candidate: int | None,
) -> tuple[int | None, int | None]:
    if candidate is None:
        return current_min, current_max
    if current_min is None or candidate < current_min:
        current_min = candidate
    if current_max is None or candidate > current_max:
        current_max = candidate
    return current_min, current_max


def _group_base_url(config: Config | None) -> str:
    base_url = getattr(config, "base_url", None) if config is not None else None
    return base_url or os.environ.get("INSPIRE_BASE_URL", "https://api.example.com").strip()


def _is_node_free(node: dict) -> bool:
    return (
        not (node.get("task_list") or [])
        and not str(node.get("cordon_type") or "").strip()
        and not node.get("is_maint", False)
        and str(node.get("resource_pool") or "").lower() != "fault"
    )


def _collect_cpu_node_summaries(
    *,
    config: Config | None,
    workspace_ids: list[str],
    aliases_by_id: dict[str, list[str]],
) -> dict[str, CPUResourceSummary]:
    session = get_web_session(require_workspace=True)
    base_url = _group_base_url(config)
    summaries: dict[str, CPUResourceSummary] = {}

    for workspace_id in workspace_ids:
        nodes = fetch_workspace_availability(
            session,
            base_url=base_url,
            workspace_id=workspace_id,
        )
        for node in nodes:
            if int(node.get("gpu_count", 0) or 0) != 0:
                continue

            group_id = str(node.get("logic_compute_group_id") or "").strip()
            group_name = str(node.get("logic_compute_group_name") or "").strip()
            if not group_id or not group_name:
                continue

            summary = summaries.setdefault(
                group_id,
                CPUResourceSummary(group_id=group_id, group_name=group_name),
            )
            if workspace_id not in summary.workspace_ids:
                summary.workspace_ids.append(workspace_id)
            for alias in aliases_by_id.get(workspace_id, []):
                if alias not in summary.workspace_aliases:
                    summary.workspace_aliases.append(alias)

            cpu_count = node.get("cpu_count")
            cpu_value = int(cpu_count or 0) if cpu_count is not None else None
            summary.cpu_per_node_min, summary.cpu_per_node_max = _update_range(
                summary.cpu_per_node_min,
                summary.cpu_per_node_max,
                cpu_value,
            )
            summary.total_nodes += 1

            if str(node.get("status") or "").upper() == "READY":
                summary.ready_nodes += 1
                if _is_node_free(node):
                    summary.free_nodes += 1

    return summaries


def _collect_cpu_spec_summaries(
    *,
    workspace_ids: list[str],
    aliases_by_id: dict[str, list[str]],
) -> dict[str, CPUResourceSummary]:
    summaries: dict[str, CPUResourceSummary] = {}
    seen_workspace_group_pairs: set[tuple[str, str]] = set()

    for workspace_id in workspace_ids:
        groups = browser_api_module.list_notebook_compute_groups(workspace_id=workspace_id)
        for group in groups:
            group_id = str(group.get("logic_compute_group_id") or group.get("id") or "").strip()
            group_name = str(group.get("name") or "").strip()
            if not group_id or not group_name:
                continue
            if (workspace_id, group_id) in seen_workspace_group_pairs:
                continue
            seen_workspace_group_pairs.add((workspace_id, group_id))

            prices = browser_api_module.get_resource_prices(
                workspace_id=workspace_id,
                logic_compute_group_id=group_id,
            )
            cpu_rows = [row for row in prices if int(row.get("gpu_count", 0) or 0) == 0]
            if not cpu_rows:
                continue

            summary = summaries.setdefault(
                group_id,
                CPUResourceSummary(group_id=group_id, group_name=group_name),
            )
            if workspace_id not in summary.workspace_ids:
                summary.workspace_ids.append(workspace_id)
            for alias in aliases_by_id.get(workspace_id, []):
                if alias not in summary.workspace_aliases:
                    summary.workspace_aliases.append(alias)

            summary.has_cpu_specs = True
            for row in cpu_rows:
                cpu_count = row.get("cpu_count")
                cpu_value = int(cpu_count or 0) if cpu_count is not None else None
                memory_gib = row.get("memory_size_gib")
                memory_value = int(memory_gib or 0) if memory_gib is not None else None
                summary.spec_cpu_min, summary.spec_cpu_max = _update_range(
                    summary.spec_cpu_min,
                    summary.spec_cpu_max,
                    cpu_value,
                )
                summary.spec_memory_gib_min, summary.spec_memory_gib_max = _update_range(
                    summary.spec_memory_gib_min,
                    summary.spec_memory_gib_max,
                    memory_value,
                )

    return summaries


def _merge_cpu_resources(
    live_cpu: dict[str, CPUResourceSummary],
    spec_cpu: dict[str, CPUResourceSummary],
) -> list[CPUResourceSummary]:
    merged: dict[str, CPUResourceSummary] = {}
    for source in (live_cpu, spec_cpu):
        for group_id, entry in source.items():
            target = merged.setdefault(
                group_id,
                CPUResourceSummary(group_id=entry.group_id, group_name=entry.group_name),
            )
            if entry.group_name and not target.group_name:
                target.group_name = entry.group_name
            target.cpu_per_node_min, target.cpu_per_node_max = _update_range(
                target.cpu_per_node_min,
                target.cpu_per_node_max,
                entry.cpu_per_node_min,
            )
            target.cpu_per_node_min, target.cpu_per_node_max = _update_range(
                target.cpu_per_node_min,
                target.cpu_per_node_max,
                entry.cpu_per_node_max,
            )
            target.spec_cpu_min, target.spec_cpu_max = _update_range(
                target.spec_cpu_min,
                target.spec_cpu_max,
                entry.spec_cpu_min,
            )
            target.spec_cpu_min, target.spec_cpu_max = _update_range(
                target.spec_cpu_min,
                target.spec_cpu_max,
                entry.spec_cpu_max,
            )
            target.spec_memory_gib_min, target.spec_memory_gib_max = _update_range(
                target.spec_memory_gib_min,
                target.spec_memory_gib_max,
                entry.spec_memory_gib_min,
            )
            target.spec_memory_gib_min, target.spec_memory_gib_max = _update_range(
                target.spec_memory_gib_min,
                target.spec_memory_gib_max,
                entry.spec_memory_gib_max,
            )
            target.total_nodes += entry.total_nodes
            target.ready_nodes += entry.ready_nodes
            target.free_nodes += entry.free_nodes
            target.has_cpu_specs = target.has_cpu_specs or entry.has_cpu_specs
            for workspace_id in entry.workspace_ids:
                if workspace_id not in target.workspace_ids:
                    target.workspace_ids.append(workspace_id)
            for alias in entry.workspace_aliases:
                if alias not in target.workspace_aliases:
                    target.workspace_aliases.append(alias)

    return sorted(
        merged.values(),
        key=lambda item: (item.free_nodes, item.ready_nodes, item.total_nodes, item.group_name),
        reverse=True,
    )


def _collect_cpu_resources(
    *,
    config: Config | None,
    workspace_ids: list[str],
    aliases_by_id: dict[str, list[str]],
) -> list[CPUResourceSummary]:
    live_cpu = _collect_cpu_node_summaries(
        config=config,
        workspace_ids=workspace_ids,
        aliases_by_id=aliases_by_id,
    )
    spec_cpu = _collect_cpu_spec_summaries(
        workspace_ids=workspace_ids,
        aliases_by_id=aliases_by_id,
    )
    return _merge_cpu_resources(live_cpu, spec_cpu)


def _cpu_resources_to_json(cpu_resources: list[CPUResourceSummary]) -> list[dict]:
    return [
        {
            "group_id": item.group_id,
            "group_name": item.group_name,
            "workspace_ids": item.workspace_ids,
            "workspace_aliases": item.workspace_aliases,
            "cpu_per_node_min": item.cpu_per_node_min,
            "cpu_per_node_max": item.cpu_per_node_max,
            "spec_cpu_min": item.spec_cpu_min,
            "spec_cpu_max": item.spec_cpu_max,
            "spec_memory_gib_min": item.spec_memory_gib_min,
            "spec_memory_gib_max": item.spec_memory_gib_max,
            "total_nodes": item.total_nodes,
            "ready_nodes": item.ready_nodes,
            "free_nodes": item.free_nodes,
            "has_cpu_specs": item.has_cpu_specs,
        }
        for item in cpu_resources
    ]


def _format_availability_table(
    availability,
    cpu_resources: list[CPUResourceSummary],
    workspace_mode: bool = False,
    scope_note: str = "",
) -> None:
    title = "📊 Resources (Node View)" if workspace_mode else "📊 Resources (Summary View)"
    if workspace_mode and not scope_note:
        scope_note = "Shows node availability in your workspace only"

    lines = ["", title]
    if scope_note:
        lines.append(scope_note)
    lines.append("")
    lines.extend(_render_gpu_nodes_section(availability))
    lines.append("")
    lines.extend(_render_cpu_section(cpu_resources))
    lines.append("")
    lines.append("💡 Usage:")
    lines.append('  inspire run "python train.py"              # Auto-select best group')
    lines.append('  inspire run "python train.py" --type H100   # Prefer H100')
    lines.append('  inspire run "python train.py" --gpus 4      # Use 4 GPUs')
    lines.append("")
    click.echo("\n".join(lines))


def _render_gpu_summary_section(availability: list) -> list[str]:
    display_names = _disambiguated_names(availability)
    rows: list[dict[str, str]] = []
    total_available = 0
    total_used = 0
    total_low_pri = 0
    total_gpus = 0

    for item in sorted(availability, key=lambda value: value.available_gpus, reverse=True):
        total_available += item.available_gpus
        total_used += item.used_gpus
        total_low_pri += item.low_priority_gpus
        total_gpus += item.total_gpus
        rows.append(
            {
                "GPU Type": _truncate_display(item.gpu_type, 22),
                "Compute Group": _truncate_display(display_names[item.group_id], 28),
                "Available": str(item.available_gpus),
                "Used": str(item.used_gpus),
                "Low Pri": str(item.low_priority_gpus),
                "Total": str(item.total_gpus),
            }
        )

    lines = ["GPU Availability"]
    lines.extend(
        _render_table(
            [
                ("GPU Type", "left"),
                ("Compute Group", "left"),
                ("Available", "right"),
                ("Used", "right"),
                ("Low Pri", "right"),
                ("Total", "right"),
            ],
            rows,
            min_width=_SECTION_TABLE_WIDTH,
        )
    )
    lines.append(
        _pad_display("TOTAL", _display_width("GPU Type"), "left")
        + "  "
        + _pad_display("", max(_display_width("Compute Group"), 28), "left")
        + "  "
        + _pad_display(str(total_available), max(_display_width("Available"), 9), "right")
        + "  "
        + _pad_display(str(total_used), max(_display_width("Used"), 4), "right")
        + "  "
        + _pad_display(str(total_low_pri), max(_display_width("Low Pri"), 7), "right")
        + "  "
        + _pad_display(str(total_gpus), max(_display_width("Total"), 5), "right")
    )
    lines.append("")
    lines.append("Legend: Available = ready to use; Low Pri = preemptible usage")
    return lines


def _render_gpu_nodes_section(availability: list) -> list[str]:
    display_names = _disambiguated_names(availability)
    rows: list[dict[str, str]] = []
    total_free = 0
    total_ready = 0
    total_nodes = 0

    for item in sorted(availability, key=lambda value: value.free_gpus, reverse=True):
        total_free += item.free_gpus
        total_ready += item.ready_nodes
        total_nodes += item.total_nodes
        rows.append(
            {
                "GPU Type": _truncate_display(item.gpu_type, 16),
                "Compute Group": _truncate_display(display_names[item.group_id], 28),
                "Ready": str(item.ready_nodes),
                "Free": str(item.free_nodes),
                "Free GPUs": str(item.free_gpus),
                "Total Nodes": str(item.total_nodes),
            }
        )

    lines = ["GPU Node Availability"]
    lines.extend(
        _render_table(
            [
                ("GPU Type", "left"),
                ("Compute Group", "left"),
                ("Ready", "right"),
                ("Free", "right"),
                ("Free GPUs", "right"),
                ("Total Nodes", "right"),
            ],
            rows,
            min_width=_SECTION_TABLE_WIDTH,
        )
    )
    lines.append(
        f"TOTAL  Ready {total_ready}  Free {sum(item.free_nodes for item in availability)}  "
        f"Free GPUs {total_free}  Nodes {total_nodes}"
    )
    return lines


def _render_cpu_section(cpu_resources: list[CPUResourceSummary]) -> list[str]:
    if not cpu_resources:
        return ["CPU Resources", "No CPU resources found"]

    display_names = _disambiguated_names(cpu_resources)
    rows: list[dict[str, str]] = []
    total_ready = 0
    total_free = 0
    total_nodes = 0

    for item in cpu_resources:
        total_ready += item.ready_nodes
        total_free += item.free_nodes
        total_nodes += item.total_nodes
        rows.append(
            {
                "Compute Group": _truncate_display(display_names[item.group_id], 30),
                "CPU/Node": _format_range(item.cpu_per_node_min, item.cpu_per_node_max),
                "Spec CPUs": _format_range(item.spec_cpu_min, item.spec_cpu_max),
                "Mem GiB": _format_range(item.spec_memory_gib_min, item.spec_memory_gib_max),
                "Ready": str(item.ready_nodes),
                "Free": str(item.free_nodes),
                "Total": str(item.total_nodes),
                "Specs": "yes" if item.has_cpu_specs else "no",
            }
        )

    lines = ["CPU Resources"]
    lines.extend(
        _render_table(
            [
                ("Compute Group", "left"),
                ("CPU/Node", "right"),
                ("Spec CPUs", "right"),
                ("Mem GiB", "right"),
                ("Ready", "right"),
                ("Free", "right"),
                ("Total", "right"),
                ("Specs", "right"),
            ],
            rows,
            min_width=_SECTION_TABLE_WIDTH,
        )
    )
    lines.append(f"TOTAL  Ready {total_ready}  Free {total_free}  Nodes {total_nodes}")
    lines.append(
        "Specs=no means the live CPU group exists but no CPU notebook specs were returned."
    )
    return lines


def _format_accurate_availability_table(
    availability,
    cpu_resources: list[CPUResourceSummary],
    scope_note: str = "",
) -> None:
    lines = ["", "📊 Resources (Summary View)"]
    if scope_note:
        lines.append(scope_note)
    lines.append("")
    lines.extend(_render_gpu_summary_section(availability))
    lines.append("")
    lines.extend(_render_cpu_section(cpu_resources))
    lines.append("")
    lines.append("💡 Usage:")
    lines.append('  inspire run "python train.py"              # Auto-select best group')
    lines.append('  inspire run "python train.py" --type H100   # Prefer H100')
    lines.append('  inspire run "python train.py" --gpus 4      # Use 4 GPUs')
    lines.append("")
    click.echo("\n".join(lines))


def _list_accurate_resources(ctx: Context, show_all: bool) -> None:
    """List accurate GPU availability using browser API."""
    try:
        config = None
        try:
            config, _ = Config.from_files_and_env(require_credentials=False)
        except Exception:
            pass

        workspace_ids, aliases_by_id, scope_note = _resolve_resources_workspace_scope(
            config=config,
            show_all=show_all,
        )
        availability = browser_api_module.get_accurate_gpu_availability(
            workspace_ids=workspace_ids,
        )
        availability = [item for item in availability if getattr(item, "total_gpus", 0) > 0]
        _apply_workspace_aliases(availability, aliases_by_id)
        cpu_resources = _collect_cpu_resources(
            config=config,
            workspace_ids=workspace_ids,
            aliases_by_id=aliases_by_id,
        )

        if not availability and not cpu_resources:
            if ctx.json_output:
                click.echo(json_formatter.format_json({"availability": [], "cpu_resources": []}))
            else:
                emit_error(
                    ctx,
                    error_type="ResourcesNotFound",
                    message="No resources found",
                    exit_code=EXIT_GENERAL_ERROR,
                )
            return

        if ctx.json_output:
            output = [
                {
                    "group_id": a.group_id,
                    "group_name": a.group_name,
                    "gpu_type": a.gpu_type,
                    "total_gpus": a.total_gpus,
                    "used_gpus": a.used_gpus,
                    "available_gpus": a.available_gpus,
                    "low_priority_gpus": a.low_priority_gpus,
                    "workspace_ids": getattr(a, "workspace_ids", []),
                    "workspace_aliases": getattr(a, "workspace_aliases", []),
                }
                for a in availability
            ]
            click.echo(
                json_formatter.format_json(
                    {
                        "availability": output,
                        "cpu_resources": _cpu_resources_to_json(cpu_resources),
                    }
                )
            )
        else:
            _format_accurate_availability_table(
                availability,
                cpu_resources,
                scope_note=scope_note,
            )

    except (SessionExpiredError, ValueError) as e:
        _handle_error(ctx, "AuthenticationError", str(e), EXIT_AUTH_ERROR)
    except Exception as e:
        _handle_error(ctx, "APIError", str(e), EXIT_API_ERROR)


def _list_workspace_resources(ctx: Context, show_all: bool, no_cache: bool) -> None:
    """List workspace-specific GPU availability using browser API."""
    try:
        if no_cache:
            clear_availability_cache()

        config = None
        try:
            config, _ = Config.from_files_and_env(require_credentials=False)
        except Exception:
            pass
        workspace_ids, aliases_by_id, scope_note = _resolve_resources_workspace_scope(
            config=config,
            show_all=show_all,
        )

        availability = fetch_resource_availability(
            config=config,
            known_only=False,
            workspace_ids=workspace_ids,
            workspace_aliases_by_id=aliases_by_id,
        )
        cpu_resources = _collect_cpu_resources(
            config=config,
            workspace_ids=workspace_ids,
            aliases_by_id=aliases_by_id,
        )

        if not availability and not cpu_resources:
            if ctx.json_output:
                click.echo(json_formatter.format_json({"availability": [], "cpu_resources": []}))
            else:
                emit_error(
                    ctx,
                    error_type="ResourcesNotFound",
                    message="No resources found in the selected workspace scope",
                    exit_code=EXIT_GENERAL_ERROR,
                )
            return

        if ctx.json_output:
            output = [
                {
                    "group_id": a.group_id,
                    "group_name": a.group_name,
                    "gpu_type": a.gpu_type,
                    "gpus_per_node": a.gpu_per_node,
                    "total_nodes": a.total_nodes,
                    "ready_nodes": a.ready_nodes,
                    "free_nodes": a.free_nodes,
                    "free_gpus": a.free_gpus,
                    "workspace_ids": getattr(a, "workspace_ids", []),
                    "workspace_aliases": getattr(a, "workspace_aliases", []),
                }
                for a in availability
            ]
            click.echo(
                json_formatter.format_json(
                    {
                        "availability": output,
                        "cpu_resources": _cpu_resources_to_json(cpu_resources),
                    }
                )
            )
            return

        _format_availability_table(
            availability,
            cpu_resources,
            workspace_mode=True,
            scope_note=scope_note,
        )

    except (SessionExpiredError, ValueError) as e:
        _handle_error(ctx, "AuthenticationError", str(e), EXIT_AUTH_ERROR)
    except Exception as e:
        _handle_error(ctx, "APIError", str(e), EXIT_API_ERROR)


def _progress_bar(current: int, total: int, width: int = 20) -> str:
    if total == 0:
        return "░" * width
    filled = int(width * current / total)
    return "█" * filled + "░" * (width - filled)


def _render_nodes_display(
    availability: list,
    cpu_resources: list[CPUResourceSummary],
    *,
    phase: str,
    timestamp: str,
    interval: int,
    progress_state: dict[str, int],
    scope_note: str,
) -> None:
    os.system("clear")

    if phase == "fetching":
        fetched = progress_state["fetched"]
        total = progress_state["total"] or 1
        bar = _progress_bar(fetched, total)
        if total > 1:
            click.echo(f"🔄 [{bar}] Fetching {fetched}/{total} nodes...\n")
        else:
            click.echo(f"🔄 [{bar}] Fetching availability...\n")
    else:
        bar = _progress_bar(1, 1)
        click.echo(f"✅ [{bar}] Updated at {timestamp} (Workspace) (interval: {interval}s)\n")

    if scope_note:
        click.echo(f"{scope_note}\n")

    if not availability:
        if phase != "fetching" and not cpu_resources:
            click.echo("No resources found")
            return

    lines: list[str] = []
    if availability:
        lines.extend(_render_gpu_nodes_section(availability))
        lines.append("")
    lines.extend(_render_cpu_section(cpu_resources))
    click.echo("\n".join(lines))
    click.echo("")
    click.echo("Ctrl+C to stop")


def _render_accurate_display(
    availability: list,
    cpu_resources: list[CPUResourceSummary],
    *,
    phase: str,
    timestamp: str,
    interval: int,
    scope_note: str,
) -> None:
    os.system("clear")

    if phase == "fetching":
        click.echo("🔄 Fetching accurate availability...\n")
    else:
        click.echo(f"✅ Updated at {timestamp} (Accurate) (interval: {interval}s)\n")

    if scope_note:
        click.echo(f"{scope_note}\n")

    if not availability and not cpu_resources:
        if phase != "fetching":
            click.echo("No resources found")
        return

    lines: list[str] = []
    if availability:
        lines.extend(_render_gpu_summary_section(availability))
        lines.append("")
    lines.extend(_render_cpu_section(cpu_resources))
    lines.append("")
    lines.append("Ctrl+C to stop")

    click.echo("\n".join(lines))


def _render_display(
    *,
    mode: str,
    availability: list,
    cpu_resources: list[CPUResourceSummary],
    phase: str,
    timestamp: str,
    interval: int,
    progress_state: dict[str, int],
    scope_note: str,
) -> None:
    if mode == "nodes":
        _render_nodes_display(
            availability,
            cpu_resources,
            phase=phase,
            timestamp=timestamp,
            interval=interval,
            progress_state=progress_state,
            scope_note=scope_note,
        )
    else:
        _render_accurate_display(
            availability,
            cpu_resources,
            phase=phase,
            timestamp=timestamp,
            interval=interval,
            scope_note=scope_note,
        )


def _watch_resources(
    ctx: Context,
    show_all: bool,
    interval: int,
    view: str,
) -> None:
    api_logger = logging.getLogger("inspire.inspire_api_control")
    original_level = api_logger.level
    api_logger.setLevel(logging.CRITICAL)

    mode = "nodes" if view == "nodes" else "accurate"

    try:
        if mode == "nodes":
            get_web_session(require_workspace=True)
        else:
            get_web_session()
    except Exception as e:
        emit_error(
            ctx,
            error_type="WebSessionError",
            message=f"Failed to get web session: {e}",
            exit_code=EXIT_AUTH_ERROR,
        )
        sys.exit(EXIT_AUTH_ERROR)

    progress_state = {"fetched": 0, "total": 0}
    config = None
    try:
        config, _ = Config.from_files_and_env(require_credentials=False)
    except Exception:
        pass
    workspace_ids, aliases_by_id, scope_note = _resolve_resources_workspace_scope(
        config=config,
        show_all=show_all,
    )

    def on_progress(fetched: int, total: int) -> None:
        if mode != "nodes":
            return
        progress_state["fetched"] = fetched
        progress_state["total"] = total
        now = datetime.now().strftime("%H:%M:%S")
        _render_display(
            mode=mode,
            availability=availability,
            phase="fetching",
            timestamp=now,
            interval=interval,
            progress_state=progress_state,
            scope_note=scope_note,
        )

    try:
        availability: list = []
        cpu_resources: list[CPUResourceSummary] = []
        while True:
            progress_state["fetched"] = 0
            progress_state["total"] = 0

            now = datetime.now().strftime("%H:%M:%S")
            _render_display(
                mode=mode,
                availability=availability,
                cpu_resources=cpu_resources,
                phase="fetching",
                timestamp=now,
                interval=interval,
                progress_state=progress_state,
                scope_note=scope_note,
            )

            try:
                if mode == "nodes":
                    clear_availability_cache()
                    availability = fetch_resource_availability(
                        config=config,
                        known_only=False,
                        workspace_ids=workspace_ids,
                        workspace_aliases_by_id=aliases_by_id,
                        progress_callback=on_progress,
                    )
                    cpu_resources = _collect_cpu_resources(
                        config=config,
                        workspace_ids=workspace_ids,
                        aliases_by_id=aliases_by_id,
                    )
                else:
                    availability = browser_api_module.get_accurate_gpu_availability(
                        workspace_ids=workspace_ids,
                    )
                    availability = [
                        item for item in availability if getattr(item, "total_gpus", 0) > 0
                    ]
                    _apply_workspace_aliases(availability, aliases_by_id)
                    cpu_resources = _collect_cpu_resources(
                        config=config,
                        workspace_ids=workspace_ids,
                        aliases_by_id=aliases_by_id,
                    )
            except (SessionExpiredError, ValueError) as e:
                api_logger.setLevel(original_level)
                emit_error(ctx, error_type="AuthError", message=str(e), exit_code=EXIT_AUTH_ERROR)
                sys.exit(EXIT_AUTH_ERROR)
            except Exception as e:
                os.system("clear")
                click.echo(f"⚠️  API error: {e}")
                click.echo(f"Retrying in {interval}s...")
                time.sleep(interval)
                continue

            now = datetime.now().strftime("%H:%M:%S")
            _render_display(
                mode=mode,
                availability=availability,
                cpu_resources=cpu_resources,
                phase="done",
                timestamp=now,
                interval=interval,
                progress_state=progress_state,
                scope_note=scope_note,
            )

            time.sleep(interval)

    except KeyboardInterrupt:
        click.echo("\nStopped watching.")
        sys.exit(0)
    finally:
        api_logger.setLevel(original_level)


def run_resources_list(
    ctx: Context,
    *,
    no_cache: bool,
    show_all: bool,
    watch: bool,
    interval: int,
    view: str,
    use_global: bool,
) -> None:
    if use_global:
        click.echo(
            "Note: --global is deprecated; use --view nodes instead.",
            err=True,
        )
        if view == "summary":
            view = "nodes"

    if watch:
        if ctx.json_output:
            click.echo(
                json_formatter.format_json_error(
                    "InvalidOption",
                    "Watch mode not supported with JSON output",
                    EXIT_CONFIG_ERROR,
                ),
                err=True,
            )
            sys.exit(EXIT_CONFIG_ERROR)

        _watch_resources(ctx, show_all, interval, view)
        return

    if view == "nodes":
        _list_workspace_resources(ctx, show_all, no_cache)
        return

    _list_accurate_resources(ctx, show_all)


@click.command("list")
@click.option(
    "--no-cache",
    is_flag=True,
    help="Bypass cached node availability (workspace view only)",
)
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    help="Expand scope to all accessible workspaces (default: configured account workspaces)",
)
@click.option(
    "--watch",
    "-w",
    is_flag=True,
    help="Continuously watch availability (refreshes every 30s)",
)
@click.option(
    "--interval",
    "-i",
    type=int,
    default=30,
    help="Watch refresh interval in seconds (default: 30)",
)
@click.option(
    "--view",
    type=click.Choice(["summary", "nodes"]),
    default="summary",
    show_default=True,
    help="Display summary or node-level availability",
)
@click.option(
    "--global",
    "use_global",
    is_flag=True,
    help="Deprecated: alias for --view nodes",
)
@json_option
@pass_context
def list_resources(
    ctx: Context,
    no_cache: bool,
    show_all: bool,
    watch: bool,
    interval: int,
    view: str,
    use_global: bool = False,
    json_output: bool = False,
) -> None:
    """List GPU availability across compute groups.

    By default, shows summary availability across configured account workspaces,
    including CPU resources. Use --view nodes for per-node availability across
    the same scope.

    \b
    Examples:
        inspire resources list              # Summary availability across configured workspaces
        inspire resources list --view nodes # Node-level availability across configured workspaces
        inspire resources list --all        # Expand to all accessible workspaces
        inspire resources list --watch      # Watch mode
    """
    json_output = resolve_json_output(ctx, json_output)
    run_resources_list(
        ctx,
        no_cache=no_cache,
        show_all=show_all,
        watch=watch,
        interval=interval,
        view=view,
        use_global=use_global,
    )
