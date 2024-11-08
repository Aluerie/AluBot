from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from ._base import DevBaseCog

if TYPE_CHECKING:
    from bot import AluBot, AluContext


class Deprecated(DevBaseCog):
    @commands.command(name="transfer_hero_emotes", hidden=True)
    async def nothing(self, ctx: AluContext) -> None:
        await ctx.typing()
        await ctx.send("Done")


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Deprecated(bot))
