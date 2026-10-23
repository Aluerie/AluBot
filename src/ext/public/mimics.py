"""Mimics.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any, TypedDict, override

from core import Cog
from shared import cache

if TYPE_CHECKING:
    from collections.abc import MutableMapping

    from core import Bot

    class GuildConfig(TypedDict):
        enabled: bool
        ignored_channels: list[int]


__all__ = ("Mimics",)


class Mimics(Cog):
    """Mimics.

    Attributes
    ----------
    mimic_messages
        Mapping of `message_id -> user_id` for Mimic Messages.
    """

    def __init__(self, bot: Bot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.guild_config: dict[int, GuildConfig] = {}
        self.mimic_messages: MutableMapping[int, int] = cache.ExpiringCache(
            seconds=dt.timedelta(days=7).total_seconds()
        )

    @override
    async def cog_load(self) -> None:
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        await super().cog_unload()

    #########################################################################################################################
    # EMBED FIXER
    #########################################################################################################################


async def setup(bot: Bot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Mimics(bot))
