"""Inspire CLI - Main entry point.

Usage:
    inspire job create --name "pr-123" --resource "4xH200" --command "bash train.sh"
    inspire job status <job-id>
    inspire job logs <job-id> --tail 100
    inspire resources list
"""

import logging
import sys
from typing import Sequence

import click

from inspire import __version__
from inspire.cli.utils.profile import apply_env_profile
from inspire.cli.logging_setup import (
    _configure_json_logging,
    clear_debug_logging,
    configure_debug_logging,
)
from inspire.cli.formatters import json_formatter
from inspire.cli.context import (
    Context,
    pass_context,
    EXIT_GENERAL_ERROR,
)
from inspire.cli.commands import (
    job,
    resources,
    config,
    sync,
    bridge,
    tunnel,
    run,
    notebook,
    init,
    image,
    project,
    mount,
)


def _apply_profile_option(
    ctx: click.Context, param: click.Parameter, value: str | None
) -> str | None:
    if value:
        apply_env_profile(value)
    return value


@click.group()
@click.option(
    "--profile",
    help="Apply env profile (INSPIRE_PROFILE_<NAME>_*)",
    expose_value=False,
    is_eager=True,
    callback=_apply_profile_option,
)
@click.version_option(version=__version__, prog_name="inspire")
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output as JSON (machine-readable)",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging",
)
@pass_context
def main(ctx: Context, json_output: bool, debug: bool) -> None:
    """Inspire Training Platform CLI.

    Interact with the Inspire HPC platform to submit training jobs,
    monitor their status, and retrieve logs.

    \b
    Examples:
        inspire job create --name "pr-123" --resource "4xH200" --command "bash train.sh"
        inspire job status job-abc-123
        inspire job logs job-abc-123 --tail 100
        inspire resources list
    """
    ctx.debug = debug

    if debug:
        ctx.debug_report_path = configure_debug_logging(argv=sys.argv)
    else:
        clear_debug_logging()

    click_ctx = click.get_current_context(silent=True)
    if click_ctx is not None:
        click_ctx.call_on_close(clear_debug_logging)

    ctx.json_output = json_output
    if ctx.json_output:
        _configure_json_logging()


def _global_json_requested(argv: Sequence[str]) -> bool:
    """Return whether the top-level ``--json`` flag is enabled."""
    root_ctx = main.make_context(
        "inspire",
        list(argv),
        resilient_parsing=True,
        allow_extra_args=True,
        ignore_unknown_options=True,
    )
    return bool(root_ctx.params.get("json_output"))


# Register command groups
main.add_command(job)
main.add_command(resources)
main.add_command(config)
main.add_command(sync)
main.add_command(bridge)
main.add_command(tunnel)
main.add_command(run)
main.add_command(notebook)
main.add_command(init)
main.add_command(image)
main.add_command(project)
main.add_command(mount)


def cli(argv: Sequence[str] | None = None) -> None:
    """Entry point for the CLI."""
    run_argv = list(argv) if argv is not None else sys.argv[1:]
    json_requested = _global_json_requested(run_argv)

    try:
        main.main(args=run_argv, prog_name="inspire", standalone_mode=False, obj=Context())
    except click.ClickException as e:
        if json_requested:
            click.echo(
                json_formatter.format_json_error(type(e).__name__, e.format_message(), e.exit_code),
                err=True,
            )
        else:
            e.show(file=sys.stderr)
        sys.exit(e.exit_code)
    except click.Abort:
        if json_requested:
            click.echo(
                json_formatter.format_json_error("Abort", "Aborted!", EXIT_GENERAL_ERROR),
                err=True,
            )
        else:
            click.echo("Aborted!", err=True)
        sys.exit(EXIT_GENERAL_ERROR)
    except Exception as e:  # pragma: no cover - top-level safety net
        logging.getLogger(__name__).exception("Unhandled exception in inspire CLI")
        if json_requested:
            click.echo(
                json_formatter.format_json_error("UnhandledError", str(e), EXIT_GENERAL_ERROR),
                err=True,
            )
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(EXIT_GENERAL_ERROR)
    finally:
        clear_debug_logging()


if __name__ == "__main__":  # pragma: no cover
    cli()
