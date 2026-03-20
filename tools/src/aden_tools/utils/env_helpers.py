"""
Environment variable helpers for Aden Tools.
"""

from __future__ import annotations

import os
from typing import Literal, overload


@overload
def get_env_var(
    name: str,
    default: str | None = None,
    *,
    required: Literal[True],
    strict: bool = False,
) -> str:
    ...


@overload
def get_env_var(
    name: str,
    default: str | None = None,
    required: Literal[False] = False,
    strict: bool = False,
) -> str | None:
    ...


@overload
def get_env_var(
    name: str,
    default: str | None = None,
    required: bool = False,
    strict: bool = False,
) -> str | None:
    ...


def get_env_var(
    name: str,
    default: str | None = None,
    required: bool = False,
    strict: bool = False,
) -> str | None:
    """
    Get an environment variable with optional default and required validation.

    Args:
        name: Name of the environment variable
        default: Default value if not set
        required: If True, raises ValueError when not set and no default
        strict: If True, strips whitespace and treats empty strings as missing

    Returns:
        The environment variable value or default

    Raises:
        ValueError: If required=True and variable is not set with no default
    """
    value = os.environ.get(name)

    if strict and isinstance(value, str):
        value = value.strip() or None

    if value is None:
        value = default

    if required and value is None:
        raise ValueError(
            f"Required environment variable '{name}' is not set. "
            f"Please set it before using this tool."
        )
    return value
