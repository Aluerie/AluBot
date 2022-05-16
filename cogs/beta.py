from discord import Embed, app_commands
from discord.ext import commands, tasks

from utils.var import *
from utils import pages


class BetaTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.hybrid_command()
    async def elp(self, ctx):
        pages_list = [Embed(description="one"), Embed(description="two")]
        paginator = pages.Paginator(pages=pages_list)
        await paginator.send(ctx)

class AlphaTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reload_info.start()

    @tasks.loop(count=1)
    async def reload_info(self):
        return

    @reload_info.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    if bot.yen:
        await bot.add_cog(BetaTest(bot))
        await bot.add_cog(AlphaTest(bot))
