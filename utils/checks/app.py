from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands

from .. import const

if TYPE_CHECKING:
    from collections.abc import Callable


def is_my_guild[T]() -> Callable[[T], T]:
    return app_commands.guilds(*const.MY_GUILDS)


def is_community[T]() -> Callable[[T], T]:
    return app_commands.guilds(const.Guild.community)


def is_hideout[T]() -> Callable[[T], T]:
    return app_commands.guilds(const.Guild.hideout)
