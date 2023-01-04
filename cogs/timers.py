from __future__ import annotations
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from .utils.context import Context


class Timers(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    async def cog_load(self) -> None:
        pass

    async def cog_unload(self) -> None:
        pass

    @commands.Cog.listener()  # Yep, that's the best name I came up with.
    async def on_timer_timer_complete(self):
        pass


async def setup(bot: AluBot):
    await bot.add_cog(Timers(bot))

