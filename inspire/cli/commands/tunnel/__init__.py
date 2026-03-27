"""Tunnel commands for SSH access to Bridge via ProxyCommand."""

from __future__ import annotations

import click

from .add import tunnel_add
from .list_cmd import tunnel_list
from .remove import tunnel_remove
from .set_default import tunnel_set_default
from .ssh_config import tunnel_ssh_config
from .status import tunnel_status
from .test_cmd import tunnel_test
from .update import tunnel_update


@click.group()
def tunnel() -> None:
    """Manage SSH tunnel profiles for fast Bridge access.

    The main flow is notebook-backed: use ``inspire notebook ssh <id> --save-as
    <name>`` to create or refresh a bridge profile, then reuse it with
    ``inspire bridge exec`` or ``ssh <name>``. There is no ``tunnel start``
    subcommand; profiles are created by ``notebook ssh --save-as`` or
    ``tunnel add``.

    \b
    Quick Start:
        1. inspire notebook ssh <id> --save-as mybridge
        2. inspire tunnel status
        3. inspire bridge exec --bridge mybridge "hostname"

    \b
    Manual profiles:
        inspire tunnel add bridge1 "https://..."
        inspire tunnel add bridge2 "https://..."
        inspire tunnel list

    \b
    For direct SSH access:
        inspire tunnel ssh-config --install
        ssh bridge1
    """


tunnel.add_command(tunnel_status)
tunnel.add_command(tunnel_add)
tunnel.add_command(tunnel_remove)
tunnel.add_command(tunnel_update)
tunnel.add_command(tunnel_set_default)
tunnel.add_command(tunnel_list)
tunnel.add_command(tunnel_ssh_config)
tunnel.add_command(tunnel_test)


__all__ = ["tunnel"]
