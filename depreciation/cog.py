from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from utils.bot import AluBot


class PartialCog(commands.Cog):

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot


class Cog(PartialCog):
    """
    Final cog for __init__.py files.
    These actually go as a final cog into bot structure and things like help menu.

    Always put this class first in inheritance so `cog_load`, `cog_unload`
    from this class are the ones being called due to inheritance order.
    """

    @property
    def help_emote(self) -> discord.PartialEmoji:
        raise NotImplementedError

    async def cog_load(self) -> None:
        for cls in self.__class__.__bases__[1:]:
            await discord.utils.maybe_coroutine(cls.cog_load, self)  # type: ignore # all bases inherit commands.Cog

    async def cog_unload(self) -> None:
        for cls in self.__class__.__bases__[1:]:
            await discord.utils.maybe_coroutine(cls.cog_unload, self)  # type: ignore # all bases inherit commands.Cog

