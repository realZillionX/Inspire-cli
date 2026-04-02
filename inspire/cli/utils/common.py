"""Common CLI decorators and utilities."""

from __future__ import annotations

import functools
from typing import Any, Callable


def json_option(func: Callable[..., Any]) -> Callable[..., Any]:
    """Compatibility decorator for deprecated command-local JSON flags.

    ``--json`` is now global-only (for example ``inspire --json ...``), so
    this decorator no longer registers a command-local Click option.
    It only injects ``json_output=False`` for existing command signatures.
    """

    @functools.wraps(func)
    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("json_output", False)
        return func(*args, **kwargs)

    return _wrapped
