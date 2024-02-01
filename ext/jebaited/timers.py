from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from ._base import JebaitedCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext


class Timers(JebaitedCog):
    async def cog_load(self) -> None:
        pass

    async def cog_unload(self) -> None:
        pass

    @commands.hybrid_group()
    async def timer(self, ctx: AluContext) -> None:
        """new timer"""
        await ctx.send_help(ctx.command)

    @timer.command()
    async def create(self, ctx: AluContext, category: str, frequency: str, probability: float) -> None:
        pass

    @commands.Cog.listener()  # Yep, that's the best name I came up with.
    async def on_timer_timer_complete(self) -> None:
        pass


async def setup(bot: AluBot) -> None:
    await bot.add_cog(Timers(bot))
