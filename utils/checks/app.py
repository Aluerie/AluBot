from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands

from .. import const

if TYPE_CHECKING:
    pass


def is_my_guild():
    return app_commands.guilds(*const.MY_GUILDS)


def is_community():
    return app_commands.guilds(const.Guild.community)


def is_hideout():
    return app_commands.guilds(const.Guild.hideout)
