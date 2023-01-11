from __future__ import annotations
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    pass


def my_bool(argument: str):
    """My own bool converter

    Same as discord.py `(..., var: bool)` but with "in/out" -> True/False
    Example: $levels opt in/out - to opt in or out of levels system.
    """
    lowered = argument.lower()
    if lowered in ("in", "yes", "y", "true", "t", "1", "enable", "on"):
        return True
    elif lowered in ("out", "no", "n", "false", "f", "0", "disable", "off"):
        return False
    else:
        raise commands.errors.BadBoolArgument(lowered)
