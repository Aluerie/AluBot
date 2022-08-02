from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands, Interaction, Embed
from discord.ext import commands, tasks

from utils.var import *

if TYPE_CHECKING:
    from utils.context import Context
    from utils.bot import AluBot

from utils import dota


class BetaTest(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.autoparse_task.start()

    def cog_unload(self):
        self.autoparse_task.cancel()

    @commands.hybrid_command()
    async def allu(self, ctx: Context):
        em = Embed(
            description=f'[Replay](https://dota2://matchid=668282480)'
        )
        await ctx.reply(embed=em)

    @app_commands.command()
    async def test_id(self, ntr: Interaction):
        await ntr.response.send_message(f'</{ntr.command.qualified_name}:{ntr.data["id"]}>')

    @tasks.loop(seconds=5)
    async def autoparse_task(self):
        print(1)

    @autoparse_task.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    if bot.yen:
        await bot.add_cog(BetaTest(bot))
