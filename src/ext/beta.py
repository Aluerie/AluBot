# pyright: reportImplicitOverride=false
from __future__ import annotations

from beta_base import *


class BanFlags(commands.FlagConverter):
    reason: str
    days: int = 1
    text: str = commands.flag(positional=True)


class BetaTest(BetaCog):
    @aluloop(count=1)
    async def beta_task(self) -> None:
        print("hi")

    @commands.command()
    async def wow(self, ctx: AluContext, *, flags: BanFlags) -> None:
        print(flags)
        await ctx.send("slash")


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(BetaTest(bot))
