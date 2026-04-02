"""Tunnel list command."""

from __future__ import annotations

import concurrent.futures
from typing import Optional

import click

from inspire.bridge.tunnel import load_tunnel_config
from inspire.bridge.tunnel.ssh import _test_ssh_connection
from inspire.cli.context import Context, pass_context
from inspire.cli.formatters import json_formatter
from inspire.cli.utils.common import json_option
from inspire.cli.utils.notebook_cli import resolve_json_output

# Valid columns for tunnel list
VALID_COLUMNS = {
    "name",
    "status",
    "port",
    "notebook",
    "internet",
    "url",
    "user",
    "rtunnel",
    "identity",
}
DEFAULT_COLUMNS = "name,status,notebook,internet"
DEFAULT_LIMIT = 10


def _fetch_notebook_info(bridges) -> dict[str, tuple[str, str]]:
    """Fetch notebook names for bridges with notebook_id.

    Returns a dict mapping notebook_id to (name, id) tuple.
    Falls back to (id, id) if fetch fails.
    """
    from inspire.platform.web.browser_api import get_notebook_detail
    from inspire.platform.web.session import get_web_session

    notebook_info: dict[str, tuple[str, str]] = {}

    # Collect unique notebook IDs
    notebook_ids = set()
    for bridge in bridges:
        if bridge.notebook_id:
            notebook_ids.add(bridge.notebook_id)

    if not notebook_ids:
        return notebook_info

    # Try to get a web session
    try:
        session = get_web_session()
    except Exception:
        # No auth, use IDs as names
        for nid in notebook_ids:
            notebook_info[nid] = (nid, nid)
        return notebook_info

    # Fetch notebook details
    for nid in notebook_ids:
        try:
            detail = get_notebook_detail(nid, session=session)
            name = detail.get("name") or nid
            notebook_info[nid] = (name, nid)
        except Exception:
            notebook_info[nid] = (nid, nid)

    return notebook_info


def _check_bridges(bridges, config, timeout=5):
    """Test SSH connectivity for all bridges in parallel.

    Returns a dict mapping bridge name to bool (True = connected).
    """
    results: dict[str, bool] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(bridges)) as pool:
        futures = {pool.submit(_test_ssh_connection, b, config, timeout): b.name for b in bridges}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception:
                results[name] = False
    return results


def _sort_bridges_for_display(bridges, *, ssh_status: dict[str, bool], no_check: bool):
    """Sort bridges for output.

    When live checks are enabled, connected bridges are listed first, then the
    remaining bridges alphabetically.
    """
    if no_check:
        return sorted(bridges, key=lambda b: b.name)
    return sorted(
        bridges,
        key=lambda b: (
            0 if ssh_status.get(b.name, False) else 1,
            b.name,
        ),
    )


def _format_column(
    bridge,
    col: str,
    ssh_status: dict[str, bool],
    no_check: bool,
    styled: bool = True,
    notebook_info: Optional[dict[str, tuple[str, str]]] = None,
    name_counts: Optional[dict[str, int]] = None,
) -> str:
    """Format a single column value for a bridge."""
    if col == "name":
        return bridge.name
    elif col == "status":
        if no_check:
            return "unknown"
        elif ssh_status.get(bridge.name, False):
            if styled:
                return click.style("connected", fg="green")
            return "connected"
        else:
            if styled:
                return click.style("not-responding", fg="red")
            return "not-responding"
    elif col == "port":
        return str(bridge.ssh_port)
    elif col == "notebook":
        if not bridge.notebook_id:
            return "-"
        if notebook_info and bridge.notebook_id in notebook_info:
            name, nid = notebook_info[bridge.notebook_id]
            # Show UUID only if there are duplicate names
            if name_counts and name_counts.get(name, 0) > 1:
                return f"{name}:{nid[:8]}"
            return name
        return bridge.notebook_id
    elif col == "internet":
        return "yes" if bridge.has_internet else "no"
    elif col == "url":
        return bridge.proxy_url
    elif col == "user":
        return bridge.ssh_user
    elif col == "rtunnel":
        return str(bridge.rtunnel_port) if bridge.rtunnel_port else "-"
    elif col == "identity":
        return bridge.identity_file or "-"
    else:
        return "-"


@click.command("list")
@click.option(
    "--no-check",
    is_flag=True,
    help="Skip live SSH connectivity check (faster output).",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show full details (URL, SSH user, internet status).",
)
@click.option(
    "--columns",
    "-c",
    default=DEFAULT_COLUMNS,
    help="Comma-separated columns to display (name,status,port,notebook,internet,url,user,rtunnel,identity).",
)
@click.option(
    "--limit",
    "-n",
    type=int,
    default=DEFAULT_LIMIT,
    help=f"Maximum number of tunnels to display (default: {DEFAULT_LIMIT}).",
)
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    help="Show all tunnels (ignore --limit).",
)
@json_option
@pass_context
def tunnel_list(
    ctx: Context,
    no_check: bool,
    verbose: bool,
    columns: str,
    limit: int,
    show_all: bool,
    json_output: bool = False,
) -> None:
    json_output = resolve_json_output(ctx, json_output)
    """List all configured bridges.

    By default, shows up to 10 tunnels with connected ones listed first.

    \b
    Example:
        inspire tunnel list
        inspire tunnel list --verbose
        inspire tunnel list --no-check
        inspire tunnel list -c name,status,port
        inspire tunnel list -n 20
        inspire tunnel list --all
    """
    config = load_tunnel_config()

    bridges = config.list_bridges()

    if not bridges:
        if ctx.json_output:
            click.echo(json_formatter.format_json({"bridges": [], "default": None}))
        else:
            click.echo("No bridges configured.")
            click.echo("")
            click.echo("Add one with: inspire tunnel add <name> <URL>")
        return

    # Check SSH connectivity unless --no-check
    ssh_status: dict[str, bool] = {}
    if not no_check:
        ssh_status = _check_bridges(bridges, config)

    ordered_bridges = _sort_bridges_for_display(bridges, ssh_status=ssh_status, no_check=no_check)

    if ctx.json_output:
        bridge_dicts = []
        for b in ordered_bridges:
            d = b.to_dict()
            if not no_check:
                d["ssh_works"] = ssh_status.get(b.name, False)
            bridge_dicts.append(d)
        click.echo(
            json_formatter.format_json(
                {
                    "bridges": bridge_dicts,
                    "default": config.default_bridge,
                }
            )
        )
        return

    if verbose:
        _print_verbose(ordered_bridges, config=config, ssh_status=ssh_status, no_check=no_check)
    else:
        _print_compact(
            ordered_bridges,
            config=config,
            ssh_status=ssh_status,
            no_check=no_check,
            columns=columns,
            limit=limit,
            show_all=show_all,
        )


def _print_compact(
    bridges,
    *,
    config,
    ssh_status,
    no_check,
    columns: str,
    limit: int,
    show_all: bool,
):
    """Simple space-separated output."""
    column_list = [c.strip().lower() for c in columns.split(",")]
    valid_columns = [c for c in column_list if c in VALID_COLUMNS]
    if not valid_columns:
        valid_columns = DEFAULT_COLUMNS.split(",")

    # Apply limit unless --all
    if not show_all and len(bridges) > limit:
        displayed_bridges = bridges[:limit]
        hidden_count = len(bridges) - limit
    else:
        displayed_bridges = bridges
        hidden_count = 0

    # Fetch notebook info if notebook column is requested
    notebook_info: dict[str, tuple[str, str]] = {}
    name_counts: dict[str, int] = {}
    if "notebook" in valid_columns:
        notebook_info = _fetch_notebook_info(displayed_bridges)
        # Count occurrences of each name to detect duplicates
        for name, _ in notebook_info.values():
            name_counts[name] = name_counts.get(name, 0) + 1

    # Build and print each line (space-separated, no headers)
    for bridge in displayed_bridges:
        values = []
        for col in valid_columns:
            value = _format_column(
                bridge,
                col,
                ssh_status,
                no_check,
                styled=True,
                notebook_info=notebook_info,
                name_counts=name_counts,
            )
            values.append(value)
        click.echo(" ".join(values))

    # Summary
    click.echo(f"\nShowing {len(displayed_bridges)} of {len(bridges)} tunnel(s)")
    if hidden_count > 0:
        click.echo("Use --all to see all tunnels")


def _print_verbose(bridges, *, config, ssh_status, no_check):
    """Multi-line detail per bridge."""
    # Fetch notebook info for verbose output
    notebook_info = _fetch_notebook_info(bridges)

    click.echo("Configured bridges:")
    click.echo("=" * 50)
    for bridge in bridges:
        is_default = bridge.name == config.default_bridge
        default_mark = "* " if is_default else "  "
        no_internet_mark = " [no internet]" if not bridge.has_internet else ""

        status_mark = ""
        if not no_check:
            if ssh_status.get(bridge.name, False):
                status_mark = " " + click.style("[connected]", fg="green")
            else:
                status_mark = " " + click.style("[not responding]", fg="red")

        click.echo(f"{default_mark}{bridge.name}:{no_internet_mark}{status_mark}")
        click.echo(f"    URL: {bridge.proxy_url}")
        click.echo(f"    SSH: {bridge.ssh_user}@localhost:{bridge.ssh_port}")
        click.echo(f"    Internet: {'yes' if bridge.has_internet else 'no'}")
        if bridge.notebook_id:
            info = notebook_info.get(bridge.notebook_id)
            if info:
                name, nid = info
                click.echo(f"    Notebook: {name} ({nid})")
            else:
                click.echo(f"    Notebook: {bridge.notebook_id}")
        if bridge.rtunnel_port:
            click.echo(f"    RTunnel: {bridge.rtunnel_port}")
        if bridge.identity_file:
            click.echo(f"    Identity: {bridge.identity_file}")
        if is_default:
            click.echo("    (default)")
    click.echo("")
    click.echo("* = default bridge")
