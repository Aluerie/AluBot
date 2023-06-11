from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from discord import app_commands

from .. import const

if TYPE_CHECKING:
    pass

T = TypeVar('T')

def is_in_guilds(*guild_ids: int):
    def decorator(func: T) -> T:
        app_commands.guild_only(func)
        app_commands.guilds(*guild_ids)
        return func

    return decorator

def is_my_guild():
    return is_in_guilds(*const.MY_GUILDS)