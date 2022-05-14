from discord import (
    Embed, Member,
    option, ui, ButtonStyle
)
from discord.ext import bridge, commands, tasks, pages
from utils.var import *
import asyncio
from typing import List
from datetime import datetime, timezone


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

    @bridge.bridge_command()
    @option('sort', description='Choose ', choices=['one', 'two'], default='one')
    async def cmd(self, ctx, sort: str = 'one'):
        await ctx.respond(sort)

    @commands.is_owner()
    @option(name="seconds", choices=range(1, 11))
    @commands.slash_command()
    async def allo(self, ctx, seconds: int = 5):
        await ctx.defer()
        await asyncio.sleep(seconds)
        await ctx.respond(f"Waited for {seconds} seconds!")
        await ctx.send(content=Ems.PepoBeliever)

    @commands.is_owner()
    @commands.command()
    async def elp(self, ctx: commands.Context, members: commands.Greedy[Member], reason: str = None):
        embed = Embed()
        embed.timestamp = datetime.now(timezone.utc)
        embed.description = 'nice'
        await ctx.send(content=f'{umntn(Uid.irene)} {Ems.PepoBeliever}')

    @commands.is_owner()
    @commands.command()
    async def page(self, ctx):
        pages_list = [Embed(description="one"), Embed(description="two")]
        paginator = pages.Paginator(
            pages=pages_list
        )
        msg = await paginator.respond(ctx)


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
        bot.add_cog(BetaTest(bot))
        bot.add_cog(AlphaTest(bot))

