"""Presentation helpers for notebook CLI output."""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from inspire.cli.formatters import json_formatter
from .notebook_lookup import _format_notebook_resource

if TYPE_CHECKING:
    pass


# Column formatters for notebook list
COLUMN_SPECS = {
    "name": ("Name", 25),
    "status": ("Status", 12),
    "resource": ("Resource", 12),
    "id": ("ID", 38),
    "created": ("Created", 20),
    "gpu": ("GPU", 8),
    "cpu": ("CPU", 8),
    "memory": ("Memory", 10),
    "image": ("Image", 25),
    "project": ("Project", 20),
    "workspace": ("Workspace", 15),
    "node": ("Node", 15),
    "uptime": ("Uptime", 10),
    "tunnel": ("Tunnel", 15),
}


def _format_uptime(item: dict) -> str:
    """Format uptime from live_time seconds."""
    live_seconds = int(item.get("live_time") or 0)
    if live_seconds <= 0:
        return "N/A"
    hours, rem = divmod(live_seconds, 3600)
    minutes = rem // 60
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    return " ".join(parts) or "< 1m"


def _format_memory(item: dict) -> str:
    """Format memory size."""
    quota = item.get("quota") or {}
    memory = quota.get("memory_size", 0)
    return f"{memory}GiB" if memory else "N/A"


def _normalize_notebook_id(notebook_id: str) -> str:
    """Normalize notebook ID to UUID format (without notebook- prefix)."""
    if notebook_id.startswith("notebook-"):
        return notebook_id[len("notebook-") :]
    return notebook_id


def _get_tunnel_name(item: dict, tunnel_config) -> str:
    """Get tunnel name for notebook, or '-'."""
    if not tunnel_config:
        return "-"
    notebook_id = item.get("notebook_id") or item.get("id", "")
    normalized_id = _normalize_notebook_id(notebook_id)
    for bridge in tunnel_config.list_bridges():
        if bridge.notebook_id and _normalize_notebook_id(bridge.notebook_id) == normalized_id:
            return bridge.name
    return "-"


def _format_column(item: dict, col: str, tunnel_config=None) -> str:
    """Format a single column value."""
    if col == "name":
        return item.get("name", "N/A")
    elif col == "status":
        return item.get("status", "Unknown")
    elif col == "resource":
        return _format_notebook_resource(item)
    elif col == "id":
        return item.get("notebook_id") or item.get("id", "N/A")
    elif col == "created":
        return str(item.get("created_at", "N/A"))
    elif col == "gpu":
        quota = item.get("quota") or {}
        return str(quota.get("gpu_count", 0))
    elif col == "cpu":
        quota = item.get("quota") or {}
        return str(quota.get("cpu_count", 0))
    elif col == "memory":
        return _format_memory(item)
    elif col == "image":
        image = item.get("image") or {}
        name = image.get("name", "")
        version = image.get("version", "")
        return f"{name}:{version}" if name and version else name or "N/A"
    elif col == "project":
        return item.get("project", {}).get("name") or item.get("project_name", "N/A")
    elif col == "workspace":
        return item.get("workspace", {}).get("name", "N/A")
    elif col == "node":
        return item.get("extra_info", {}).get("NodeName", "N/A")
    elif col == "uptime":
        return _format_uptime(item)
    elif col == "tunnel":
        return _get_tunnel_name(item, tunnel_config)
    return "N/A"


def _print_notebook_detail(notebook: dict) -> None:
    """Print detailed notebook information."""
    click.echo(f"\n{'=' * 60}")
    click.echo(f"Notebook: {notebook.get('name', 'N/A')}")
    click.echo(f"{'=' * 60}")

    project = notebook.get("project") or {}
    quota = notebook.get("quota") or {}
    compute_group = notebook.get("logic_compute_group") or {}
    extra = notebook.get("extra_info") or {}
    image = notebook.get("image") or {}
    start_cfg = notebook.get("start_config") or {}
    workspace = notebook.get("workspace") or {}
    node = notebook.get("node") or {}

    gpu_type = ""
    node_gpu_info = node.get("gpu_info")
    if isinstance(node_gpu_info, dict):
        gpu_type = node_gpu_info.get("gpu_product_simple", "")
    if not gpu_type:
        spec = notebook.get("resource_spec") or {}
        gpu_type = spec.get("gpu_type", "")

    gpu_count = quota.get("gpu_count", 0)
    gpu_str = f"{gpu_count}x {gpu_type}" if gpu_type and gpu_count else str(gpu_count or "N/A")

    img_name = image.get("name", "")
    img_ver = image.get("version", "")
    img_str = f"{img_name}:{img_ver}" if img_name and img_ver else img_name or "N/A"

    live_seconds = int(notebook.get("live_time") or 0)
    uptime = ""
    if live_seconds > 0:
        hours, rem = divmod(live_seconds, 3600)
        minutes = rem // 60
        parts = []
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        uptime = " ".join(parts) or "< 1m"

    shm = start_cfg.get("shared_memory_size", 0) or 0

    fields = [
        ("ID", notebook.get("notebook_id") or notebook.get("id")),
        ("Status", notebook.get("status")),
        ("Project", project.get("name") or notebook.get("project_name")),
        ("Priority", project.get("priority_name")),
        ("Compute Group", compute_group.get("name")),
        ("Image", img_str),
        ("GPU", gpu_str),
        ("CPU", quota.get("cpu_count")),
        ("Memory", f"{quota['memory_size']} GiB" if quota.get("memory_size") else None),
        ("SHM", f"{shm} GiB" if shm else None),
        ("Node", extra.get("NodeName") or None),
        ("Host IP", extra.get("HostIP") or None),
        ("Uptime", uptime or None),
        ("Workspace", workspace.get("name")),
        ("Created", notebook.get("created_at")),
    ]

    for label, value in fields:
        if value:
            click.echo(f"  {label:<15}: {value}")

    click.echo(f"{'=' * 60}\n")


def _print_notebook_list(
    items: list,
    json_output: bool,
    columns: str = "name,status,resource,id",
    tunnel_config=None,
) -> None:
    """Print notebook list in appropriate format with customizable columns."""
    if json_output:
        click.echo(json_formatter.format_json({"items": items, "total": len(items)}))
        return

    if not items:
        click.echo("No notebook instances found.")
        return

    column_list = [c.strip().lower() for c in columns.split(",")]

    # Validate columns
    valid_columns = [c for c in column_list if c in COLUMN_SPECS]
    if not valid_columns:
        valid_columns = ["name", "status", "resource", "id"]

    # Build header
    headers = []
    for col in valid_columns:
        header, width = COLUMN_SPECS[col]
        headers.append(f"{header:<{width}}")

    # Build separator
    total_width = sum(COLUMN_SPECS[c][1] + 1 for c in valid_columns) - 1

    lines = [" ".join(headers), "-" * total_width]

    # Build rows
    for item in items:
        row_parts = []
        for col in valid_columns:
            width = COLUMN_SPECS[col][1]
            value = _format_column(item, col, tunnel_config)
            # Truncate if too long
            if len(value) > width:
                value = value[: width - 3] + "..."
            row_parts.append(f"{value:<{width}}")
        lines.append(" ".join(row_parts))

    lines.append(f"\nShowing {len(items)} notebook(s)")
    click.echo("\n".join(lines))


__all__ = [
    "_print_notebook_detail",
    "_print_notebook_list",
    "COLUMN_SPECS",
]
