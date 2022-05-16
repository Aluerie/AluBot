from discord import (
    Embed, Option, Member,
    option, ui, ButtonStyle
)
from discord.ext import bridge, commands, tasks, pages
from utils.var import *
import asyncio
from typing import Literal


class Zeta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @bridge.bridge_command()
    @option('member', description='Choose member')
    async def avatarpic(self, ctx, *, member: Member = None):
        mb = member or ctx.author
        # something
        await ctx.respond(mb.display_name)

    @commands.has_any_role(*Rid.bot_admins)
    @commands.command()
    async def allo(self, ctx):
        await ctx.respond(Ems.PepoBeliever)


########################################################################################

class ViewHelp(ui.View):
    def __init__(self, paginator):
        super().__init__()
        self.paginator = paginator

    @ui.button(label="One", style=ButtonStyle.primary)
    async def button0(self, button, interaction):
        await self.paginator.goto_page(page_number=0, interaction=interaction)

    @ui.button(label="Two", style=ButtonStyle.primary)
    async def button3(self, button, interaction):
        await self.paginator.goto_page(page_number=1, interaction=interaction)


class BetaTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command()
    async def page(self, ctx):
        pages_list = [Embed(description="one"), Embed(description="two")]
        paginator = pages.Paginator(pages=pages_list)
        await paginator.respond(ctx)


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


def setup(bot):
    if bot.yen:
        bot.add_cog(Zeta(bot))
        # bot.add_cog(BetaTest(bot))
        # bot.add_cog(AlphaTest(bot))

