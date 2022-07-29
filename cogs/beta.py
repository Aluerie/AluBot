from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands, Interaction, Embed
from discord.ext import commands

from utils.var import *

if TYPE_CHECKING:
    from utils.context import Context
    from utils.bot import AluBot

from utils import dota


class BetaTest(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot

    @commands.hybrid_command()
    async def allu(self, ctx: Context):
        em = Embed(
            description=f'[Replay](https://dota2://matchid=668282480)'
        )
        await ctx.reply(embed=em)

    @app_commands.command()
    async def test_id(self, ntr: Interaction):
        await ntr.response.send_message(f'</{ntr.command.qualified_name}:{ntr.data["id"]}>')


async def setup(bot):
    if bot.yen:
        await bot.add_cog(BetaTest(bot))
