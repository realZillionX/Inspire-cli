"""Bridge commands for executing raw commands on the Bridge runner."""

from __future__ import annotations

import click

from .exec_cmd import exec_command
from .scp_cmd import bridge_scp
from .ssh_cmd import bridge_ssh


@click.group()
def bridge() -> None:
    """Run commands on a Bridge profile.

    ``bridge exec`` and ``bridge ssh`` execute in ``INSPIRE_TARGET_DIR`` and
    can rebuild notebook-backed tunnels when they drop.
    ``bridge scp`` transfers files only, never rebuilds tunnels, and does not
    change directory on the remote host.
    """


bridge.add_command(exec_command)
bridge.add_command(bridge_scp)
bridge.add_command(bridge_ssh)

__all__ = ["bridge"]
